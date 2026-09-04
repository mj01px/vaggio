"""API de vagas: fila de triagem, descarte, cadastro manual e apresentacao."""

import threading

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissoes import (
    GERAR_APRESENTACAO,
    GERENCIAR_VAGAS,
    TRIAR_VAGAS,
    VER_VAGAS,
)

from .filters import JobFilter
from .models import Job
from .pitch import (
    DossieAusenteError,
    DossieVazioError,
    GeminiIndisponivelError,
    GeminiSemTextoError,
    gerar_e_salvar,
)
from .serializers import (
    JobCreateSerializer,
    JobDetailSerializer,
    JobSerializer,
    JobUpdateSerializer,
    PitchCreateSerializer,
    PitchSerializer,
)

QUEUES = ("triage", "discarded", "all")

# Uma geracao por vez. O free tier do AI Studio tem limite por minuto, e dois
# cliques seguidos no botao gastariam duas chamadas para o mesmo texto.
_pitch_lock = threading.Lock()


class PitchEmAndamento(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ja tem uma apresentacao sendo gerada. Espere ela terminar."
    default_code = "pitch_in_progress"


class PitchIndisponivel(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "pitch_unavailable"


class JobViewSet(ModelViewSet):
    """Vagas coletadas.

    A lista responde a fila de triagem por padrao (`?queue=triage`), que e o
    que a tela Radar mostra: nao descartada e ainda sem candidatura.
    """

    permissao_exigida = {
        "default": VER_VAGAS,
        "create": TRIAR_VAGAS,
        "partial_update": GERENCIAR_VAGAS,
        "discard": TRIAR_VAGAS,
        "restore": TRIAR_VAGAS,
        "pitch": GERAR_APRESENTACAO,
    }
    filterset_class = JobFilter
    ordering_fields = ["score", "created_at", "published_at"]
    ordering = ["-score", "-created_at"]
    # Vaga nao se apaga: descarta. O historico e o que impede a mesma vaga de
    # voltar para a fila na proxima coleta.
    #
    # Editar existe para quem tem `vagas.gerenciar`, porque a coleta erra e
    # alguem precisa corrigir. PUT fica de fora: sobrescrever a vaga inteira
    # apagaria `tags` e `published_at`, que a tela nao manda de volta.
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        # select_related no reverse OneToOne: sem ele, `has_application`
        # dispara uma consulta por vaga na serializacao da lista.
        queryset = Job.objects.select_related("application")
        if self.action != "list":
            return queryset

        queue = self.request.query_params.get("queue", "triage")
        if queue == "discarded":
            return queryset.discarded()
        if queue == "all":
            return queryset
        return queryset.triage()

    def get_serializer_class(self):
        if self.action == "create":
            return JobCreateSerializer
        if self.action == "partial_update":
            return JobUpdateSerializer
        if self.action == "retrieve":
            return JobDetailSerializer
        return JobSerializer

    @action(detail=True, methods=["post"])
    def discard(self, request, pk=None):
        job = self.get_object()
        job.discarded = True
        job.save(update_fields=["discarded", "updated_at"])
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        job = self.get_object()
        job.discarded = False
        job.save(update_fields=["discarded", "updated_at"])
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["get", "post"])
    def pitch(self, request, pk=None):
        """GET lista as versoes ja geradas; POST gera mais uma.

        Sincrono, como a coleta: leva uns 10 segundos e devolver o texto pronto
        vale mais que responder na hora e a tela ficar perguntando se acabou.
        """
        job = self.get_object()

        if request.method == "GET":
            return Response(PitchSerializer(job.pitches.all(), many=True).data)

        perfil = getattr(request.user, "perfil", None)

        pedido = PitchCreateSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)

        if not _pitch_lock.acquire(blocking=False):
            raise PitchEmAndamento

        try:
            criado = gerar_e_salvar(
                job,
                max_chars=pedido.validated_data["max_chars"],
                instrucao_extra=pedido.validated_data["instrucao"],
                perfil=perfil,
            )
        except (DossieAusenteError, DossieVazioError) as exc:
            # Erro de configuracao sua, nao falha do servico: o texto da
            # excecao ja diz o que fazer, entao ele vai inteiro para a tela.
            raise PitchIndisponivel(str(exc)) from exc
        except (GeminiIndisponivelError, GeminiSemTextoError) as exc:
            raise PitchIndisponivel(str(exc)) from exc
        finally:
            _pitch_lock.release()

        # Uma versao por vaga: gerar de novo substitui a anterior. O apagar vem
        # depois da geracao dar certo de proposito, senao uma falha do Gemini
        # levaria junto o texto que ja estava pronto na tela.
        job.pitches.exclude(pk=criado.pk).delete()

        return Response(PitchSerializer(criado).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Contadores da tela Radar, numa consulta so por numero."""
        return Response(
            {
                "triage": Job.objects.triage().count(),
                "discarded": Job.objects.discarded().count(),
                "total": Job.objects.count(),
            },
            status=status.HTTP_200_OK,
        )
