from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CargoViewSet, MeuPerfilView, PermissaoViewSet, SessaoView, UsuarioViewSet
from .views_seguranca import (
    ConfirmarDoisFatoresView,
    ConfirmarEmailView,
    ConfirmarLinkView,
    DesativarDoisFatoresView,
    DoisFatoresView,
    EsqueciSenhaView,
    NovosCodigosView,
    RedefinirSenhaView,
    SessaoDoisFatoresView,
    TrocarEmailView,
    TrocarSenhaView,
)

router = SimpleRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("cargos", CargoViewSet, basename="cargo")
router.register("permissoes", PermissaoViewSet, basename="permissao")

urlpatterns = [
    path("sessao/", SessaoView.as_view(), name="sessao"),
    # Segundo passo da entrada: sem sessao autenticada ainda.
    path("sessao/codigo/", SessaoDoisFatoresView.as_view(), name="sessao-codigo"),
    path("perfil/", MeuPerfilView.as_view(), name="perfil"),
    # Estas quatro exigem a senha atual ou a sessao; nao dependem de cargo.
    path("perfil/senha/", TrocarSenhaView.as_view(), name="perfil-senha"),
    path("perfil/email/", TrocarEmailView.as_view(), name="perfil-email"),
    path("perfil/2fa/", DoisFatoresView.as_view(), name="perfil-2fa"),
    path("perfil/2fa/confirmar/", ConfirmarDoisFatoresView.as_view(), name="perfil-2fa-confirmar"),
    path("perfil/2fa/desativar/", DesativarDoisFatoresView.as_view(), name="perfil-2fa-desativar"),
    path("perfil/2fa/codigos/", NovosCodigosView.as_view(), name="perfil-2fa-codigos"),
    # Publicas: as unicas rotas do projeto que respondem sem sessao.
    path("senha/esqueci/", EsqueciSenhaView.as_view(), name="senha-esqueci"),
    path("senha/redefinir/", RedefinirSenhaView.as_view(), name="senha-redefinir"),
    path("senha/conferir-link/", ConfirmarLinkView.as_view(), name="senha-conferir-link"),
    path("email/confirmar/", ConfirmarEmailView.as_view(), name="email-confirmar"),
    path("", include(router.urls)),
]
