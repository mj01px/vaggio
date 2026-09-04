"""API do funil: board agrupado por coluna, edicao e linha do tempo."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissoes import GERENCIAR_FUNIL, VER_FUNIL
from apps.jobs.models import Job

from .models import ACTIVE_STATUSES, CLOSED_STATUSES, Application, ApplicationStatus
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationUpdateSerializer,
    InteractionSerializer,
)
from .services import change_status, enter_pipeline


class ApplicationViewSet(ModelViewSet):
    """Candidaturas.

    Sair do funil e mudar o status para Rejeitada ou Desisti, nao apagar: a
    linha do tempo de um processo perdido e o que ensina para o proximo.

    Apagar de vez existe, mas so depois disso: da para remover uma candidatura
    ja encerrada, quando ela virou ruido na lista. Enquanto ela esta no funil
    ativo o DELETE e recusado.
    """

    permissao_exigida = {
        "default": VER_FUNIL,
        "create": GERENCIAR_FUNIL,
        "update": GERENCIAR_FUNIL,
        "partial_update": GERENCIAR_FUNIL,
        "destroy": GERENCIAR_FUNIL,
        "interactions": VER_FUNIL,
        "interactions:post": GERENCIAR_FUNIL,
        "interaction": GERENCIAR_FUNIL,
    }
    filterset_fields = ["status", "priority", "has_referral"]
    ordering_fields = ["priority", "updated_at", "next_step_on"]
    ordering = ["priority", "-updated_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Application.objects.select_related("job")

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        if self.action in ("update", "partial_update"):
            return ApplicationUpdateSerializer
        return ApplicationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application, created = enter_pipeline(serializer.validated_data["job"])
        return Response(
            ApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def perform_update(self, serializer):
        # `serializer.instance` ainda tem o valor do banco: e a unica chance de
        # saber de onde a candidatura veio antes de o save sobrescrever.
        previous_status = serializer.instance.status
        application = serializer.save()
        change_status(application, previous_status)

    def perform_destroy(self, instance):
        """So apaga o que ja saiu do funil.

        Sem esta trava, um DELETE perdido levaria junto uma candidatura viva e
        toda a linha do tempo dela, que a FK apaga em cascata. Encerrada e outra
        historia: ali o processo ja acabou e a linha nao ensina mais nada.
        """
        if instance.status not in CLOSED_STATUSES:
            raise ValidationError(
                "So da para apagar candidatura encerrada. "
                "Marque como Rejeitada ou Desisti antes."
            )
        instance.delete()

    @action(detail=False, methods=["get"])
    def board(self, request):
        """O board inteiro numa resposta: colunas, atrasadas e os contadores."""
        applications = list(self.get_queryset().active())

        columns = []
        for value in ACTIVE_STATUSES:
            items = [app for app in applications if app.status == value]
            items.sort(key=lambda app: (app.priority, -app.id))
            columns.append(
                {
                    "status": value,
                    "label": ApplicationStatus(value).label,
                    "total": len(items),
                    "items": ApplicationSerializer(items, many=True).data,
                }
            )

        overdue = [app for app in applications if app.is_overdue]

        return Response(
            {
                "columns": columns,
                "overdue": ApplicationSerializer(overdue, many=True).data,
                "stats": {
                    "in_funnel": sum(
                        1 for app in applications if app.status != ApplicationStatus.INTEREST
                    ),
                    "overdue": len(overdue),
                    "radar_queue": Job.objects.triage().count(),
                    "closed": Application.objects.closed().count(),
                },
                "statuses": [
                    {"value": value, "label": label}
                    for value, label in ApplicationStatus.choices
                ],
            }
        )

    @action(detail=False, methods=["get"])
    def closed(self, request):
        """As candidaturas que sairam do funil: rejeitadas e desistidas.

        Rota propria, e nao `?status=rejected` na lista, porque sao dois status
        e a tela quer os dois juntos. Ordena pela ultima mexida, que e quando o
        processo de fato acabou: `priority` do funil ativo nao diz nada aqui.
        """
        encerradas = self.get_queryset().closed().order_by("-updated_at")
        return Response(
            {
                "results": ApplicationSerializer(encerradas, many=True).data,
                "stats": {
                    "rejected": sum(
                        1 for app in encerradas if app.status == ApplicationStatus.REJECTED
                    ),
                    "withdrawn": sum(
                        1 for app in encerradas if app.status == ApplicationStatus.WITHDRAWN
                    ),
                },
            }
        )

    @action(detail=True, methods=["get", "post"])
    def interactions(self, request, pk=None):
        """GET lista a linha do tempo; POST acrescenta um evento.

        Escrever aqui era so pelo admin do Django. Com a tela propria, quem
        registra "mandei o e-mail hoje" e a aplicacao, e o admin deixa de ser
        caminho obrigatorio para uma acao do dia a dia.
        """
        application = self.get_object()

        if request.method == "GET":
            return Response(
                InteractionSerializer(application.interactions.all(), many=True).data
            )

        serializer = InteractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"interactions/(?P<interacao>[^/.]+)",
    )
    def interaction(self, request, pk=None, interacao=None):
        """Edita ou apaga um evento da linha do tempo."""
        application = self.get_object()
        evento = get_object_or_404(application.interactions, pk=interacao)

        if request.method == "DELETE":
            evento.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = InteractionSerializer(evento, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
