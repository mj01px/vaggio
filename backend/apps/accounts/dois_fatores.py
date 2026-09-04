"""Segundo fator por TOTP.

TOTP e nao codigo por e-mail de proposito: com "esqueci minha senha" indo por
e-mail, a caixa de entrada ja e a chave mestra da conta, e um segundo fator que
chega no mesmo lugar nao seria um segundo fator.

O preco disso e a recuperacao, que tem de existir junto e nao depois: quem
perde o celular sem codigo de reserva fica trancado fora para sempre.
"""

import base64
from io import BytesIO

import pyotp
import qrcode

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


def confere(segredo: str, codigo: str) -> bool:
    if not segredo or not codigo:
        return False
    codigo = codigo.strip().replace(" ", "")
    if not codigo.isdigit():
        return False
    return pyotp.TOTP(segredo).verify(codigo, valid_window=JANELA)
