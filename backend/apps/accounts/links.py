"""Links de uso unico mandados por e-mail.

Tres fluxos usam a mesma maquina: recuperar a senha esquecida, convidar alguem
que o admin acabou de cadastrar, e confirmar a troca do proprio e-mail. Muda o
texto e o prazo, nao o mecanismo.

Duas ferramentas, e a diferenca importa:

- `PasswordResetTokenGenerator` para o que mexe em senha. Ele nao guarda nada:
  o token e um hash do estado atual do usuario (senha, `last_login`, e-mail),
  entao **usar o link invalida ele sozinho**, porque a senha mudou. E o que
  impede o mesmo link de valer duas vezes sem precisar de tabela.
- `signing.dumps` para a troca de e-mail, que precisa carregar o endereco novo
  ate a confirmacao. Guardar isso no banco daria um registro pendente para
  limpar; assinado, o dado viaja no proprio link e expira sozinho.
"""

import hashlib
import logging
import threading

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

logger = logging.getLogger(__name__)

# Salt proprio por fluxo: um token de troca de e-mail nao pode ser aceito onde
# se espera outro assunto, mesmo tendo a mesma SECRET_KEY por tras.
SALT_EMAIL = "vaggio.troca-de-email"

gerador = PasswordResetTokenGenerator()


def em_segundo_plano(funcao, *args) -> threading.Thread:
    """Manda o e-mail fora da requisicao, e devolve a thread.

    Existe por causa do "esqueci minha senha": o conteudo da resposta e igual
    para e-mail que existe e e-mail que nao existe, mas o TEMPO nao era. Quem
    existe esperava o handshake com o SMTP; quem nao existe voltava na hora, e
    a diferenca passava de 200 ms. Isso e a mesma lista de contas que a
    resposta se recusa a dar, entregue pelo relogio.

    `connection.close()` no fim nao e detalhe: thread nova ganha conexao propria
    com o banco, e sem fechar elas vazam uma por pedido de recuperacao.
    """

    def alvo():
        try:
            funcao(*args)
        except Exception:
            logger.exception("envio em segundo plano falhou (%s)", funcao.__name__)
        finally:
            connection.close()

    thread = threading.Thread(target=alvo, daemon=True)
    thread.start()
    return thread


def _chave_da_senha(user) -> str:
    """Marca curta da senha atual, para o link morrer quando ela mudar."""
    return hashlib.sha256(force_bytes(user.password)).hexdigest()[:16]


def _uid(user) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def usuario_do_uid(uid: str, modelo):
    """Devolve o usuario do uid do link, ou None se ele nao decodifica."""
    try:
        return modelo.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, modelo.DoesNotExist):
        return None


def link_de_senha(user, caminho: str) -> str:
    """URL da tela do front que recebe o token, com uid e token na query."""
    return f"{settings.FRONTEND_URL}/{caminho}?uid={_uid(user)}&token={gerador.make_token(user)}"


def token_confere(user, token: str) -> bool:
    return gerador.check_token(user, token)


def link_de_troca_de_email(user, email_novo: str) -> str:
    # A marca da senha viaja junto: trocar a senha derruba o link pendente. Sem
    # ela, quem pediu a troca com uma sessao roubada ainda tinha duas horas
    # para confirmar depois de o dono trocar a senha e achar que resolveu.
    codigo = signing.dumps(
        {"uid": user.pk, "email": email_novo, "chave": _chave_da_senha(user)},
        salt=SALT_EMAIL,
    )
    return f"{settings.FRONTEND_URL}/confirmar-email?codigo={codigo}"


def ler_troca_de_email(codigo: str) -> dict | None:
    """Abre o codigo assinado. None quando invalido ou vencido."""
    prazo = settings.PRAZO_LINK_EMAIL_HORAS * 3600
    try:
        return signing.loads(codigo, salt=SALT_EMAIL, max_age=prazo)
    except signing.BadSignature:
        return None


def chave_da_senha_confere(user, dados: dict) -> bool:
    """O link foi feito com a senha que a conta tem agora?

    Codigo antigo, de antes de este campo existir, nao tem a chave: ele vale
    ate vencer, o que e no maximo duas horas depois do deploy.
    """
    if "chave" not in dados:
        return True
    return dados["chave"] == _chave_da_senha(user)


def _nome_de(user) -> str:
    return getattr(getattr(user, "perfil", None), "nome", "") or user.email


def _enviar(
    *,
    assunto: str,
    resumo: str,
    titulo: str,
    paragrafos: list[str],
    rotulo: str,
    url: str,
    rodape: list[str],
    para: str,
) -> None:
    """Manda a mensagem nas duas versoes, texto e HTML.

    As duas de proposito: cliente que so le texto existe, quem filtra spam
    desconfia de mensagem so-HTML, e o texto ainda e o que sobra quando o
    layout nao renderiza. O HTML e a alternativa, e nao o contrario, entao o
    texto e escrito para ser lido, nao e um resto.
    """
    corpo = "\n".join(
        [
            *paragrafos,
            "",
            "Abra este endereço:",
            url,
            "",
            *rodape,
            "",
            "Vaggio · mensagem automatica, nao responda este e-mail.",
        ]
    )

    mensagem = EmailMultiAlternatives(
        subject=f"Vaggio · {assunto}",
        body=corpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[para],
    )
    mensagem.attach_alternative(
        render_to_string(
            "emails/link.html",
            {
                "resumo": resumo,
                "titulo": titulo,
                "paragrafos": paragrafos,
                "rotulo": rotulo,
                "url": url,
                "rodape": rodape,
            },
        ),
        "text/html",
    )
    # `fail_silently` desligado de proposito: um envio que falha tem de virar
    # erro visivel na hora, e nao um link que a pessoa espera para sempre.
    mensagem.send(fail_silently=False)


def manda_recuperacao(user) -> None:
    horas = settings.PRAZO_LINK_SENHA_HORAS
    _enviar(
        assunto="redefinir sua senha",
        resumo="Link para escolher uma senha nova.",
        titulo="Redefinir sua senha",
        paragrafos=[
            f"Oi, {_nome_de(user)}.",
            "Segue o link para você escolher uma senha nova.",
        ],
        rotulo="Escolher senha nova",
        url=link_de_senha(user, "redefinir-senha"),
        rodape=[
            f"O link vale por {horas} hora(s) e funciona uma vez só.",
            "Se não foi você quem pediu, ignore este e-mail: sua senha continua a mesma.",
        ],
        para=user.email,
    )


def manda_convite(user) -> None:
    horas = settings.PRAZO_LINK_CONVITE_HORAS
    _enviar(
        assunto="sua conta foi criada",
        resumo="Escolha sua senha e comece a usar o Vaggio.",
        titulo="Sua conta no Vaggio está pronta",
        paragrafos=[
            f"Oi, {_nome_de(user)}.",
            "Criaram uma conta para você. Falta só escolher sua senha, e ninguém "
            "além de você vai saber qual é.",
            f"Você entra com o e-mail {user.email}.",
        ],
        rotulo="Escolher minha senha",
        url=link_de_senha(user, "definir-senha"),
        rodape=[f"O link vale por {horas} horas e funciona uma vez só."],
        para=user.email,
    )


def avisa_troca_de_email(user, email_novo: str, *, confirmada: bool) -> None:
    """Conta ao endereco ANTIGO que estao mexendo na credencial de entrada.

    O link de confirmacao vai para o endereco novo, que e o jeito de provar que
    ele existe. Mas quem precisa saber que o acesso esta sendo trocado e quem
    tem o acesso hoje: sem este aviso, uma sessao aberta esquecida bastava para
    trocar a porta de entrada da conta em silencio.
    """
    if confirmada:
        paragrafos = [
            f"O e-mail de acesso da sua conta no Vaggio passou a ser {email_novo}.",
            "Este endereco nao entra mais.",
        ]
        assunto = "seu e-mail de acesso mudou"
    else:
        paragrafos = [
            f"Pediram para trocar o e-mail de acesso da sua conta para {email_novo}.",
            "Nada muda ate o link que mandamos para la ser aberto.",
        ]
        assunto = "pediram para trocar seu e-mail"

    _enviar(
        assunto=assunto,
        resumo="Aviso sobre o e-mail de acesso da sua conta.",
        titulo="Mexeram no seu e-mail de acesso",
        paragrafos=paragrafos,
        rotulo="Trocar minha senha agora",
        url=f"{settings.FRONTEND_URL}/esqueci-senha",
        rodape=[
            "Se nao foi voce, troque sua senha agora: isso derruba as sessoes "
            "abertas e cancela a troca pendente.",
        ],
        para=user.email,
    )


def manda_confirmacao_de_email(user, email_novo: str) -> None:
    horas = settings.PRAZO_LINK_EMAIL_HORAS
    # Vai para o endereco NOVO de proposito: e o unico jeito de provar que ele
    # existe e e seu antes de trocar a credencial de entrada por ele.
    _enviar(
        assunto="confirme seu e-mail novo",
        resumo="Confirme este endereço para passar a entrar com ele.",
        titulo="Confirme seu e-mail novo",
        paragrafos=[
            "Você pediu para trocar o e-mail de acesso do Vaggio para este endereço. "
            "Confirme para a troca valer.",
        ],
        rotulo="Confirmar este e-mail",
        url=link_de_troca_de_email(user, email_novo),
        rodape=[
            f"O link vale por {horas} hora(s).",
            f"Até você confirmar, sua entrada continua sendo {user.email}.",
            "Se não foi você quem pediu, ignore este e-mail: nada muda sozinho.",
        ],
        para=email_novo,
    )
