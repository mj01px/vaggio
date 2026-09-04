"""Autenticacao por e-mail.

O Vaggio nasceu com login por username, que e o padrao do `auth.User` do
Django. Ninguem lembra do username que o administrador escolheu; todo mundo
lembra do proprio e-mail. Entao o e-mail virou a credencial, e o username
continua existindo so como identificador interno da conta (a coluna e NOT NULL
e unica no Django e nao da para largar sem trocar o modelo de usuario inteiro).

Este backend e o unico em `AUTHENTICATION_BACKENDS` de proposito: com o
`ModelBackend` ao lado, o login por username continuaria valendo e a mudanca
seria so de fachada.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class BackendDeEmail(ModelBackend):
    """Confere a senha contra a conta que tem aquele e-mail."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # O Django chama isto com `username=`; quem chama direto tende a usar
        # `email=`. Os dois caem aqui para nao existir um jeito certo secreto.
        email = kwargs.get("email") or username
        if not email or not password:
            return None

        candidatos = list(UserModel.objects.filter(email__iexact=email.strip())[:2])

        if len(candidatos) != 1:
            # Zero: nao existe. Dois: o banco tem e-mail repetido de antes do
            # indice unico, e ai nenhuma das contas entra ate alguem arrumar.
            # Nos dois casos gastamos um hash assim mesmo, senao o tempo de
            # resposta conta quais e-mails existem.
            UserModel().set_password(password)
            return None

        usuario = candidatos[0]
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
