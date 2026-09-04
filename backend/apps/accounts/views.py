"""Sessao e perfil: entrar, sair, saber quem sou e editar o proprio perfil."""

import logging

from django.contrib.auth import get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from . import links
from .models import Cargo, Perfil, Permissao
from .permissoes import (
    EDITAR_PERFIL,
    GERENCIAR_CARGOS,
    GERENCIAR_USUARIOS,
    VER_CARGOS,
    VER_USUARIOS,
    TemPermissao,
)
from .serializers import (
    CargoEscritaSerializer,
    CargoSerializer,
    LoginSerializer,
    PerfilSerializer,
    PerfilUpdateSerializer,
    PermissaoSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def perfil_de(usuario) -> Perfil:
    """O perfil do usuario, criado na hora se a conta veio do createsuperuser."""
    perfil, _ = Perfil.objects.get_or_create(
        user=usuario,
        defaults={"nome": usuario.get_full_name() or usuario.email or usuario.get_username()},
    )
    return perfil


@method_decorator(ensure_csrf_cookie, name="get")
class SessaoView(APIView):
    """GET diz quem esta logado, POST entra, DELETE sai.

    O GET tambem e quem planta o cookie de CSRF: o front chama isso ao abrir,
    antes de qualquer POST, senao o Django recusa o proprio login.
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"autenticado": False, "perfil": None})
        return Response(
            {"autenticado": True, "perfil": PerfilSerializer(perfil_de(request.user)).data}
        )

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        usuario = serializer.validated_data["user"]
        lembrar = serializer.validated_data["lembrar"]
        perfil = perfil_de(usuario)

        # Com segundo fator, a senha certa ainda nao e entrar: guarda quem
        # passou numa sessao ANONIMA e para aqui. `request.user` so vira essa
        # pessoa depois do codigo, no SessaoDoisFatoresView.
        if perfil.totp_ativo:
            from .views_seguranca import SESSAO_PENDENTE

            request.session[SESSAO_PENDENTE] = usuario.pk
            request.session[f"{SESSAO_PENDENTE}.lembrar"] = lembrar
            return Response({"autenticado": False, "precisa_codigo": True})

        login(request, usuario)

        # Sem "lembrar", o cookie morre quando o navegador fecha. Tem de vir
        # depois do login(): ele cicla a chave da sessao e zera a expiracao.
        if not lembrar:
            request.session.set_expiry(0)

        return Response(
            {"autenticado": True, "perfil": PerfilSerializer(perfil).data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeuPerfilView(APIView):
    """O perfil de quem esta logado. PATCH edita dossie, termos e preferencias."""

    permission_classes = [IsAuthenticated, TemPermissao]
    permissao_exigida = {"partial_update": EDITAR_PERFIL, "put": EDITAR_PERFIL}

    def get(self, request):
        return Response(PerfilSerializer(perfil_de(request.user)).data)

    def patch(self, request):
        perfil = perfil_de(request.user)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @property
    def action(self):
        # A classe de permissao le `view.action`, que so existe em viewset.
        # Aqui a acao e o metodo, e escrita exige `perfil.editar`.
        return "partial_update" if self.request.method in ("PATCH", "PUT") else None


class UsuarioViewSet(ModelViewSet):
    """Quem tem acesso ao Vaggio.

    Substitui a tela de usuarios do admin do Django. Conta nao se apaga: se
    desativa, porque candidatura e apresentacao ficam penduradas em quem as
    criou e apagar levaria historico junto.
    """

    permissao_exigida = {
        "default": VER_USUARIOS,
        "create": GERENCIAR_USUARIOS,
        "update": GERENCIAR_USUARIOS,
        "partial_update": GERENCIAR_USUARIOS,
        "convite": GERENCIAR_USUARIOS,
    }
    http_method_names = ["get", "post", "patch", "head", "options"]
    # Ordena e busca pelo e-mail: e o que a tela mostra e o que a pessoa digita
    # para entrar. O username virou identificador interno.
    ordering = ["email"]
    search_fields = ["email", "perfil__nome"]

    def get_queryset(self):
        return User.objects.select_related("perfil__cargo").order_by("email")

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        if self.action in ("update", "partial_update"):
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def perform_update(self, serializer):
        alvo = serializer.instance
        mudancas = serializer.validated_data

        # Duas travas contra se trancar para fora: quem esta editando nao pode
        # se desativar nem se tirar do proprio cargo. Com um administrador so,
        # qualquer uma das duas deixaria o Vaggio sem dono.
        if alvo == self.request.user:
            if mudancas.get("is_active") is False:
                raise ValidationError("Voce nao pode desativar a propria conta.")
            if "cargo" in mudancas and mudancas["cargo"] != getattr(
                getattr(alvo, "perfil", None), "cargo", None
            ):
                raise ValidationError("Voce nao pode trocar o proprio cargo.")

        if alvo.is_superuser and mudancas.get("is_active") is False:
            raise ValidationError("Conta de superusuario nao se desativa por aqui.")

        serializer.save()

    def perform_create(self, serializer):
        """Cria a conta e ja manda o convite, quando ela nasceu sem senha.

        Fora da transacao do serializer de proposito: SMTP fora do ar nao pode
        desfazer a criacao da conta. Se o envio falhar, a conta existe e o
        admin reenvia o convite pela tela.
        """
        usuario = serializer.save()
        if not usuario.has_usable_password():
            try:
                links.manda_convite(usuario)
            except Exception:
                logger.exception("convite nao saiu para %s", usuario.email)

    @action(detail=True, methods=["post"])
    def convite(self, request, pk=None):
        """Manda (ou reenvia) o link para a pessoa escolher a propria senha.

        Substitui o endpoint em que o admin digitava a senha do outro. A
        diferenca nao e de conforto: por aqui ninguem alem do dono chega a
        saber aquela senha.
        """
        usuario = self.get_object()
        if not usuario.is_active:
            raise ValidationError("Conta desativada nao recebe convite. Reative antes.")

        links.manda_convite(usuario)
        return Response({"detail": f"Convite enviado para {usuario.email}."})


class CargoViewSet(ModelViewSet):
    """Cargos e o que cada um libera."""

    permissao_exigida = {
        "default": VER_CARGOS,
        "create": GERENCIAR_CARGOS,
        "update": GERENCIAR_CARGOS,
        "partial_update": GERENCIAR_CARGOS,
        "destroy": GERENCIAR_CARGOS,
    }
    ordering = ["nome"]

    def get_queryset(self):
        return Cargo.objects.prefetch_related("permissoes", "perfis").order_by("nome")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CargoEscritaSerializer
        return CargoSerializer

    def perform_destroy(self, instance):
        if instance.perfis.exists():
            raise ValidationError(
                f"{instance.perfis.count()} pessoa(s) usam este cargo. "
                "Mova elas antes de apagar."
            )
        instance.delete()


class PermissaoViewSet(ReadOnlyModelViewSet):
    """O catalogo de permissoes, para a tela de cargos montar as caixas.

    Somente leitura: permissao nova nasce em `permissoes.py` e entra pelo
    `sync_permissoes`, porque cada slug precisa de codigo que o respeite.
    """

    permissao_exigida = VER_CARGOS
    queryset = Permissao.objects.all().order_by("slug")
    serializer_class = PermissaoSerializer
    pagination_class = None
