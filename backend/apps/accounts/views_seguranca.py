"""Senha, recuperacao, troca de e-mail e segundo fator.

Vive fora de `views.py` porque e outro assunto: aqui nada depende de cargo. O
que protege estas rotas nao e permissao, e prova de identidade: a senha atual,
um link de uso unico mandado por e-mail, ou um codigo do aplicativo.

As rotas publicas (as de link e a do codigo) sao as unicas do projeto que
respondem sem sessao, e por isso as unicas com limite de tentativa por escopo.
Todas exigem CSRF explicitamente: `APIView` sai de `as_view()` embrulhado em
`csrf_exempt`, e o `SessionAuthentication` so cobra o token de quem ja tem
sessao autenticada, que nao e o caso de nenhuma delas.
"""

import logging

from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import dois_fatores, links
from .serializers import (
    CodigoSerializer,
    DesativarDoisFatoresSerializer,
    EsqueciSerializer,
    PerfilSerializer,
    RedefinirSerializer,
    TrocarEmailSerializer,
    TrocarSenhaSerializer,
)
from .views import perfil_de

logger = logging.getLogger(__name__)
seguranca = logging.getLogger("apps.seguranca")
User = get_user_model()

# Estas seis rotas declaram `permissao_exigida = None` de proposito, e nao um
# slug: mexer na PROPRIA senha, no PROPRIO e-mail e no PROPRIO segundo fator
# nao e coisa que cargo libera. Elas ja pedem prova de identidade (a senha
# atual, ou um codigo do aplicativo), que e a tranca certa aqui.
#
# Exigir `perfil.editar` como antes trancava do lado de fora justamente quem
# mais precisa: o cargo "Somente leitura", que a migration semeia, nao tem essa
# permissao e por isso nao conseguia rotacionar a propria senha depois de um
# vazamento nem ligar o segundo fator.
SEM_CARGO = None

# Chave onde o login guarda quem passou pela senha e ainda deve o codigo. Nao
# e uma sessao autenticada: `request.user` continua anonimo ate o segundo passo.
SESSAO_PENDENTE = "vaggio.2fa.usuario"

# Quantos codigos errados o segundo passo aceita antes de mandar a pessoa
# comecar de novo. Sem isto a sessao pendente sobrevivia a qualquer quantidade
# de tentativas, e o unico obstaculo era o limite por IP: quem trocasse de IP
# tinha o espaco inteiro de codigos, incluindo os oito de reserva.
#
# Cinco cobre dedo trocado e relogio do celular fora de hora; a partir dai nao
# e mais engano.
MAX_ERROS_DE_CODIGO = 5
ERROS_PENDENTES = f"{SESSAO_PENDENTE}.erros"


class TrocarSenhaView(APIView):
    """Troca da propria senha, com a senha atual como prova."""

    permissao_exigida = SEM_CARGO

    def post(self, request):
        serializer = TrocarSenhaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["nova"])
        request.user.save(update_fields=["password"])
        seguranca.info("senha trocada pelo dono: %s", request.user.email)
        # Trocar a senha invalida a sessao no Django. Sem isto voce cairia na
        # tela de login logo depois de trocar, sem entender por que.
        update_session_auth_hash(request, request.user)

        return Response({"detail": "Senha alterada."})

    @property
    def action(self):
        return None


@method_decorator(csrf_protect, name="post")
class EsqueciSenhaView(APIView):
    """Publica: pede o link de recuperacao.

    Responde sempre a mesma coisa, exista ou nao a conta. Dizer "esse e-mail
    nao esta cadastrado" transformaria esta rota numa lista de quem usa o
    sistema, para quem quiser ficar tentando.
    """

    permission_classes = [AllowAny]
    permissao_exigida = None
    throttle_scope = "recuperacao"

    RESPOSTA = {"detail": "Se existir uma conta com esse e-mail, o link já está a caminho."}

    def post(self, request):
        serializer = EsqueciSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pedido = serializer.validated_data["email"].strip()
        usuario = User.objects.filter(email__iexact=pedido, is_active=True).first()
        if usuario:
            # Fora da requisicao: o conteudo da resposta ja era igual nos dois
            # casos, mas esperar o SMTP so quando a conta existe media a mesma
            # informacao pelo relogio.
            links.em_segundo_plano(links.manda_recuperacao, usuario)

        seguranca.info("recuperacao pedida para %s (existe=%s)", pedido, bool(usuario))
        return Response(self.RESPOSTA)


@method_decorator(csrf_protect, name="post")
class RedefinirSenhaView(APIView):
    """Publica: fecha o link de recuperacao e o do convite.

    Os dois usam o mesmo token, entao a mesma rota atende os dois: quem chega
    pelo convite so ve um texto diferente na tela.
    """

    permission_classes = [AllowAny]
    permissao_exigida = None
    throttle_scope = "recuperacao"

    def post(self, request):
        serializer = RedefinirSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        usuario = links.usuario_do_uid(dados["uid"], User)
        if not usuario or not links.token_confere(usuario, dados["token"]):
            return Response(
                {"detail": "Esse link não vale mais. Peça um novo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not usuario.is_active:
            return Response(
                {"detail": "Esta conta está desativada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.set_password(dados["nova"])
        usuario.save(update_fields=["password"])
        seguranca.warning("senha redefinida por link para %s", usuario.email)
        # O token e um hash do estado do usuario, e a senha entra nesse hash:
        # gravar a senha nova ja derruba este link, sem tabela de usados.
        return Response({"detail": "Senha definida. Agora é só entrar."})


@method_decorator(csrf_protect, name="post")
class ConfirmarLinkView(APIView):
    """Publica: diz se um link de senha ainda vale, antes de pedir a senha.

    Sem isto, a tela so descobriria que o link venceu depois de a pessoa
    escolher e digitar a senha duas vezes.
    """

    permission_classes = [AllowAny]
    permissao_exigida = None
    throttle_scope = "recuperacao"

    def post(self, request):
        uid = str(request.data.get("uid", ""))
        token = str(request.data.get("token", ""))
        usuario = links.usuario_do_uid(uid, User)
        vale = bool(usuario and usuario.is_active and links.token_confere(usuario, token))
        return Response({"valido": vale, "email": usuario.email if vale else ""})


class TrocarEmailView(APIView):
    """Pede a troca do proprio e-mail. Nada muda ate o link ser aberto."""

    permissao_exigida = SEM_CARGO

    def post(self, request):
        serializer = TrocarEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        novo = serializer.validated_data["email"]

        links.manda_confirmacao_de_email(request.user, novo)
        # O endereco antigo e quem tem o acesso hoje: ele precisa saber que
        # estao trocando a porta de entrada, mesmo que o link va para o novo.
        # Falha aqui nao derruba o pedido, que ja saiu.
        try:
            links.avisa_troca_de_email(request.user, novo, confirmada=False)
        except Exception:
            logger.exception("aviso de troca nao saiu para %s", request.user.email)

        seguranca.warning(
            "troca de e-mail pedida: %s para %s", request.user.email, novo
        )
        return Response({"detail": f"Confirme no link que mandamos para {novo}."})

    @property
    def action(self):
        return None


@method_decorator(csrf_protect, name="post")
class ConfirmarEmailView(APIView):
    """Publica: aplica a troca de e-mail que o link autoriza."""

    permission_classes = [AllowAny]
    permissao_exigida = None
    throttle_scope = "recuperacao"

    def post(self, request):
        dados = links.ler_troca_de_email(str(request.data.get("codigo", "")))
        if not dados:
            return Response(
                {"detail": "Esse link não vale mais. Peça a troca de novo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = User.objects.filter(pk=dados["uid"], is_active=True).first()
        if not usuario:
            return Response(
                {"detail": "Conta não encontrada."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Trocar a senha cancela a troca pendente. E o que da uma saida a quem
        # descobriu que alguem mexeu na conta: trocar a senha resolve tudo de
        # uma vez, em vez de deixar um link vivo por mais duas horas.
        if not links.chave_da_senha_confere(usuario, dados):
            seguranca.warning(
                "troca de e-mail recusada (senha mudou depois do pedido): %s",
                usuario.email,
            )
            return Response(
                {"detail": "Esse link não vale mais: a senha da conta mudou."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Confere de novo na hora de aplicar: entre o pedido e o clique, alguem
        # pode ter cadastrado uma conta com esse endereco.
        email = dados["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=usuario.pk).exists():
            return Response(
                {"detail": "Já existe uma conta com esse e-mail."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        antigo = usuario.email
        usuario.email = email
        usuario.save(update_fields=["email"])
        seguranca.warning("e-mail de acesso trocado: %s para %s", antigo, email)

        try:
            usuario.email = antigo
            links.avisa_troca_de_email(usuario, email, confirmada=True)
        except Exception:
            logger.exception("aviso de troca concluida nao saiu para %s", antigo)
        finally:
            usuario.email = email

        return Response({"detail": f"Pronto. Agora você entra com {email}."})


class DoisFatoresView(APIView):
    """Estado do segundo fator, e o comeco da ativacao.

    O POST so prepara: gera o segredo e o QR, e nao liga nada. Ligar sem provar
    que o aplicativo funciona trancaria a pessoa para fora na entrada seguinte.
    """

    permissao_exigida = SEM_CARGO

    def get(self, request):
        perfil = perfil_de(request.user)
        return Response(
            {
                "ativo": perfil.totp_ativo,
                "codigos_restantes": len(perfil.codigos_de_reserva),
            }
        )

    def post(self, request):
        perfil = perfil_de(request.user)
        if perfil.totp_ativo:
            return Response(
                {"detail": "O segundo fator já está ativo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perfil.totp_secret = dois_fatores.novo_segredo()
        perfil.save(update_fields=["totp_secret", "updated_at"])

        return Response(
            {
                "qr": dois_fatores.qr_base64(perfil.totp_secret, request.user.email),
                # Para quem nao consegue ler o QR e prefere digitar.
                "segredo": perfil.totp_secret,
            }
        )

    @property
    def action(self):
        return None


class ConfirmarDoisFatoresView(APIView):
    """Liga o segundo fator, depois de o aplicativo provar que funciona."""

    permissao_exigida = SEM_CARGO
    throttle_scope = "2fa"

    @transaction.atomic
    def post(self, request):
        perfil = perfil_de(request.user)
        serializer = CodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not perfil.totp_secret:
            return Response(
                {"detail": "Comece a ativação de novo."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not dois_fatores.confere_uma_vez(perfil, serializer.validated_data["codigo"]):
            seguranca.info("2fa: codigo errado na ativacao de %s", request.user.email)
            return Response(
                {"detail": "Código incorreto. Confira a hora do celular e tente de novo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Os codigos de reserva nascem junto com a ativacao, e nao como passo
        # opcional depois: perder o celular sem eles nao tem volta.
        codigos = perfil.gerar_codigos_de_reserva()
        perfil.totp_ativo = True
        perfil.save(update_fields=["totp_ativo", "codigos_de_reserva", "updated_at"])
        seguranca.warning("2fa: ativado por %s", request.user.email)

        return Response({"detail": "Segundo fator ativado.", "codigos": codigos})

    @property
    def action(self):
        return None


class DesativarDoisFatoresView(APIView):
    """Desliga o segundo fator. Exige a senha atual."""

    permissao_exigida = SEM_CARGO

    def post(self, request):
        perfil = perfil_de(request.user)
        serializer = DesativarDoisFatoresSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        perfil.totp_ativo = False
        perfil.totp_secret = ""
        perfil.codigos_de_reserva = []
        perfil.totp_ultimo_passo = 0
        perfil.save(
            update_fields=[
                "totp_ativo",
                "totp_secret",
                "codigos_de_reserva",
                "totp_ultimo_passo",
                "updated_at",
            ]
        )
        seguranca.warning("2fa: desativado por %s", request.user.email)
        return Response({"detail": "Segundo fator desativado."})

    @property
    def action(self):
        return None


class NovosCodigosView(APIView):
    """Gera codigos de reserva novos e invalida os antigos."""

    permissao_exigida = SEM_CARGO

    def post(self, request):
        perfil = perfil_de(request.user)
        serializer = DesativarDoisFatoresSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        if not perfil.totp_ativo:
            return Response(
                {"detail": "O segundo fator não está ativo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        codigos = perfil.gerar_codigos_de_reserva()
        perfil.save(update_fields=["codigos_de_reserva", "updated_at"])
        seguranca.warning("2fa: codigos de reserva regerados por %s", request.user.email)
        return Response({"codigos": codigos})

    @property
    def action(self):
        return None


@method_decorator(csrf_protect, name="post")
class SessaoDoisFatoresView(APIView):
    """Segundo passo da entrada: o codigo, depois da senha certa.

    Entre os dois passos nao existe sessao autenticada, so o id guardado na
    sessao anonima. Quem para no meio nao entrou.
    """

    permission_classes = [AllowAny]
    permissao_exigida = None
    throttle_scope = "2fa"

    def post(self, request):
        pendente = request.session.get(SESSAO_PENDENTE)
        if not pendente:
            return Response(
                {"detail": "Entre com e-mail e senha primeiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codigo = serializer.validated_data["codigo"]

        usuario = User.objects.filter(pk=pendente, is_active=True).first()
        if not usuario:
            del request.session[SESSAO_PENDENTE]
            request.session.pop(ERROS_PENDENTES, None)
            return Response(
                {"detail": "Entre com e-mail e senha de novo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perfil = perfil_de(usuario)
        # `confere_uma_vez` e nao `confere`: o codigo do aplicativo passa a
        # valer uma entrada so, em vez de todas as que couberem na janela.
        ok = dois_fatores.confere_uma_vez(perfil, codigo)
        if not ok:
            # Cada codigo de reserva vale uma entrada e some ao ser usado.
            ok = perfil.queimar_codigo_de_reserva(codigo)

        if not ok:
            erros = request.session.get(ERROS_PENDENTES, 0) + 1
            request.session[ERROS_PENDENTES] = erros
            seguranca.warning(
                "2fa: codigo errado (%s de %s) para %s",
                erros,
                MAX_ERROS_DE_CODIGO,
                usuario.email,
            )

            if erros >= MAX_ERROS_DE_CODIGO:
                # Derruba o pendente: a partir daqui e preciso a senha de novo.
                # E o que impede a sessao pendente de virar um balcao aberto
                # para tentar codigo ate acertar.
                del request.session[SESSAO_PENDENTE]
                request.session.pop(ERROS_PENDENTES, None)
                request.session.pop(f"{SESSAO_PENDENTE}.lembrar", None)
                seguranca.warning(
                    "2fa: entrada pendente derrubada apos %s erros para %s",
                    erros,
                    usuario.email,
                )
                return Response(
                    {"detail": "Erros demais. Entre com e-mail e senha de novo."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {"detail": "Código incorreto."}, status=status.HTTP_400_BAD_REQUEST
            )

        lembrar = bool(request.session.get(f"{SESSAO_PENDENTE}.lembrar", True))
        del request.session[SESSAO_PENDENTE]
        request.session.pop(ERROS_PENDENTES, None)
        seguranca.info("entrada: segundo fator conferido para %s", usuario.email)
        login(request, usuario)
        if not lembrar:
            request.session.set_expiry(0)

        return Response({"autenticado": True, "perfil": PerfilSerializer(perfil).data})


class SessaoAtualView(APIView):
    """Marcado como autenticado so para o DRF nao liberar sem sessao."""

    permission_classes = [IsAuthenticated]
    permissao_exigida = None
