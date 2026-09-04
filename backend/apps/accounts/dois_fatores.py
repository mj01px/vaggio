"""Segundo fator por TOTP.

TOTP e nao codigo por e-mail de proposito: com "esqueci minha senha" indo por
e-mail, a caixa de entrada ja e a chave mestra da conta, e um segundo fator que
chega no mesmo lugar nao seria um segundo fator.

O preco disso e a recuperacao, que tem de existir junto e nao depois: quem
perde o celular sem codigo de reserva fica trancado fora para sempre.
"""

import base64
import logging
import time
from io import BytesIO

import pyotp
import qrcode

seguranca = logging.getLogger("apps.seguranca")

# Nome que aparece na lista do aplicativo autenticador.
EMISSOR = "Vaggio"

# Uma janela para tras e uma para frente: relogio de celular atrasado alguns
# segundos e o motivo mais comum de codigo certo ser recusado.
JANELA = 1


def novo_segredo() -> str:
    return pyotp.random_base32()


def uri(segredo: str, email: str) -> str:
    """`otpauth://` que o aplicativo le do QR ou aceita digitado."""
    return pyotp.TOTP(segredo).provisioning_uri(name=email, issuer_name=EMISSOR)


def qr_base64(segredo: str, email: str) -> str:
    """O QR como PNG em data URI, pronto para o `src` de uma <img>.

    Desenhado aqui, e nao no front: assim o segredo nao precisa passear pelo
    JavaScript so para virar imagem.
    """
    imagem = qrcode.make(uri(segredo, email))
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _limpa(codigo: str) -> str:
    return (codigo or "").strip().replace(" ", "").replace("-", "")


def confere(segredo: str, codigo: str) -> bool:
    """Confere sem guardar nada. Use `confere_uma_vez` onde houver perfil."""
    codigo = _limpa(codigo)
    if not segredo or not codigo.isdigit():
        return False
    return pyotp.TOTP(segredo).verify(codigo, valid_window=JANELA)


def confere_uma_vez(perfil, codigo: str) -> bool:
    """Confere e queima: o passo aceito nao serve de novo.

    `verify()` sozinho nao sabe se o codigo ja entrou, entao o mesmo numero
    valia por toda a janela de tolerancia. Guardar o passo aceito no perfil e o
    que transforma "codigo valido agora" em "codigo valido uma vez".

    Recusar passo menor ou igual ao ultimo tambem cobre o codigo anterior:
    quem viu o de 30 segundos atras nao entra com ele depois que o seguinte
    passou.
    """
    codigo = _limpa(codigo)
    if not perfil.totp_secret or not codigo.isdigit():
        return False

    totp = pyotp.TOTP(perfil.totp_secret)
    agora = int(time.time()) // totp.interval

    for desvio in range(-JANELA, JANELA + 1):
        passo = agora + desvio
        if not totp.verify(codigo, for_time=passo * totp.interval):
            continue
        if passo <= perfil.totp_ultimo_passo:
            seguranca.warning(
                "2fa: codigo repetido recusado para %s", perfil.user.email
            )
            return False
        perfil.totp_ultimo_passo = passo
        perfil.save(update_fields=["totp_ultimo_passo", "updated_at"])
        return True

    return False
