from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Ping para o front e para o docker healthcheck saberem que a API subiu."""

    # Continua aberto de proposito: e ping de infra, e exigir login para
    # responder "ok" quebraria healthcheck de container.
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})
