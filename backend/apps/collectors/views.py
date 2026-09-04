"""API de coleta: historico das execucoes e disparo pelo Radar."""

import threading
from dataclasses import asdict

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissoes import RODAR_COLETA, VER_COLETA

from .models import CollectionRun
from .serializers import CollectionRunSerializer
from .services import DEFAULT_MAX_AGE_DAYS, collect_all

# Uma coleta por vez. Duas em paralelo leriam o mesmo conjunto de chaves ja
# conhecidas antes de qualquer uma gravar, e as duas achariam que a mesma vaga
# e nova: a segunda so descobriria no unique do banco, no meio da gravacao.
#
# Trava de processo, nao de maquina: serve porque isto roda num runserver so,
# na sua propria maquina. Com mais de um worker, o lugar disso seria o banco.
_collect_lock = threading.Lock()


class CollectionInProgress(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ja tem uma coleta rodando. Espere ela terminar."
    default_code = "collection_in_progress"


class CollectionRunViewSet(ReadOnlyModelViewSet):
    """Log das coletas, e o disparo delas.

    A coleta e sincrona de proposito: ela leva cerca de 40 segundos, e devolver
    o resultado exato na resposta ("42 novas") vale mais que responder na hora
    e obrigar a tela a ficar perguntando se ja acabou.
    """

    permissao_exigida = {"default": VER_COLETA, "run": RODAR_COLETA}
    queryset = CollectionRun.objects.all()
    serializer_class = CollectionRunSerializer
    filterset_fields = ["source"]
    ordering_fields = ["started_at", "new_count"]
    ordering = ["-started_at"]

    @action(detail=False, methods=["post"])
    def run(self, request):
        """Roda todas as fontes agora e responde com o que cada uma trouxe."""
        if not _collect_lock.acquire(blocking=False):
            raise CollectionInProgress

        try:
            results = collect_all(max_age_days=DEFAULT_MAX_AGE_DAYS)
        finally:
            _collect_lock.release()

        return Response(
            {
                "new": sum(result.new for result in results),
                "sources": [asdict(result) for result in results],
                "errors": [
                    {"source": result.source, "message": result.error}
                    for result in results
                    if result.error
                ],
            }
        )
