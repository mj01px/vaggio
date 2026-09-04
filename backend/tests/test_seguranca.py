"""Senha, recuperacao por e-mail, troca de e-mail e segundo fator."""

import re
import time

import pyotp
import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

User = get_user_model()


def link_do_email(mensagem) -> dict:
    """Tira uid e token da URL que foi para a caixa de entrada."""
    achado = re.search(r"[?&]uid=([^&\s]+)&token=([^\s]+)", mensagem.body)
    assert achado, f"nenhum link no corpo:\n{mensagem.body}"
    return {"uid": achado.group(1), "token": achado.group(2)}


class TestTrocarPropriaSenha:
    def test_troca_com_a_senha_atual(self, api, cria_perfil):
        response = api.post(
            "/api/v1/perfil/senha/",
            {"senha_atual": "senha-de-teste", "nova": "OutraSenhaLonga1!"},
            format="json",
        )

        assert response.status_code == 200
        usuario = User.objects.get(email="dono@teste.dev")
        assert usuario.check_password("OutraSenhaLonga1!")

    def test_continua_logado_depois_de_trocar(self, api):
        """Trocar a senha cicla a sessao do Django; sem cuidado, derruba voce."""
        api.post(
            "/api/v1/perfil/senha/",
            {"senha_atual": "senha-de-teste", "nova": "OutraSenhaLonga1!"},
            format="json",
        )

        assert api.get("/api/v1/perfil/").status_code == 200

    def test_senha_atual_errada_e_recusada(self, api):
        response = api.post(
            "/api/v1/perfil/senha/",
            {"senha_atual": "nao-e-essa", "nova": "OutraSenhaLonga1!"},
            format="json",
        )

        assert response.status_code == 400

    def test_senha_nova_fraca_e_recusada(self, api):
        response = api.post(
            "/api/v1/perfil/senha/",
            {"senha_atual": "senha-de-teste", "nova": "123"},
            format="json",
        )

        assert response.status_code == 400

    def test_repetir_a_mesma_senha_e_recusado(self, api):
        response = api.post(
            "/api/v1/perfil/senha/",
            {"senha_atual": "senha-de-teste", "nova": "senha-de-teste"},
            format="json",
        )

        assert response.status_code == 400

    def test_anonimo_nao_troca_senha(self, api_anonimo):
        response = api_anonimo.post(
            "/api/v1/perfil/senha/",
            {"senha_atual": "x", "nova": "OutraSenhaLonga1!"},
            format="json",
        )

        assert response.status_code == 403


class TestEsqueciSenha:
    def test_manda_o_link(self, api_anonimo, cria_perfil, mailoutbox):
        cria_perfil(email="perdido@teste.dev")

        response = api_anonimo.post(
            "/api/v1/senha/esqueci/", {"email": "perdido@teste.dev"}, format="json"
        )

        assert response.status_code == 200
        assert len(mailoutbox) == 1
        assert "redefinir-senha" in mailoutbox[0].body

    def test_email_desconhecido_responde_igual(self, api_anonimo, catalogo, mailoutbox):
        """A resposta nao pode entregar quais contas existem."""
        conhecido = api_anonimo.post(
            "/api/v1/senha/esqueci/", {"email": "ninguem@teste.dev"}, format="json"
        )

        assert conhecido.status_code == 200
        assert conhecido.json()["detail"].startswith("Se existir")
        assert mailoutbox == []

    def test_conta_desativada_nao_recebe(self, api_anonimo, cria_perfil, mailoutbox):
        perfil = cria_perfil(email="desligado@teste.dev")
        perfil.user.is_active = False
        perfil.user.save()

        response = api_anonimo.post(
            "/api/v1/senha/esqueci/", {"email": "desligado@teste.dev"}, format="json"
        )

        assert response.status_code == 200
        assert mailoutbox == []

    def test_redefine_e_entra_com_a_senha_nova(self, api_anonimo, cria_perfil, mailoutbox):
        cria_perfil(email="perdido@teste.dev")
        api_anonimo.post(
            "/api/v1/senha/esqueci/", {"email": "perdido@teste.dev"}, format="json"
        )

        response = api_anonimo.post(
            "/api/v1/senha/redefinir/",
            {**link_do_email(mailoutbox[0]), "nova": "SenhaNovaLonga1!"},
            format="json",
        )

        assert response.status_code == 200
        entrada = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "perdido@teste.dev", "password": "SenhaNovaLonga1!"},
            format="json",
        )
        assert entrada.json()["autenticado"] is True

    def test_o_link_so_vale_uma_vez(self, api_anonimo, cria_perfil, mailoutbox):
        """Gravar a senha nova ja derruba o token, sem tabela de usados."""
        cria_perfil(email="perdido@teste.dev")
        api_anonimo.post(
            "/api/v1/senha/esqueci/", {"email": "perdido@teste.dev"}, format="json"
        )
        dados = link_do_email(mailoutbox[0])

        primeira = api_anonimo.post(
            "/api/v1/senha/redefinir/", {**dados, "nova": "SenhaNovaLonga1!"}, format="json"
        )
        segunda = api_anonimo.post(
            "/api/v1/senha/redefinir/", {**dados, "nova": "TerceiraSenha1!"}, format="json"
        )

        assert primeira.status_code == 200
        assert segunda.status_code == 400

    def test_token_de_outra_conta_nao_serve(self, api_anonimo, cria_perfil, mailoutbox):
        cria_perfil(email="um@teste.dev")
        outro = cria_perfil(email="dois@teste.dev")
        api_anonimo.post("/api/v1/senha/esqueci/", {"email": "um@teste.dev"}, format="json")

        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        dados = link_do_email(mailoutbox[0])
        dados["uid"] = urlsafe_base64_encode(force_bytes(outro.user.pk))

        response = api_anonimo.post(
            "/api/v1/senha/redefinir/", {**dados, "nova": "SenhaNovaLonga1!"}, format="json"
        )

        assert response.status_code == 400

    def test_conferir_link_antes_de_pedir_a_senha(self, api_anonimo, cria_perfil, mailoutbox):
        cria_perfil(email="perdido@teste.dev")
        api_anonimo.post(
            "/api/v1/senha/esqueci/", {"email": "perdido@teste.dev"}, format="json"
        )

        response = api_anonimo.post(
            "/api/v1/senha/conferir-link/", link_do_email(mailoutbox[0]), format="json"
        )

        assert response.json() == {"valido": True, "email": "perdido@teste.dev"}

    def test_conferir_link_invalido(self, api_anonimo, catalogo):
        response = api_anonimo.post(
            "/api/v1/senha/conferir-link/", {"uid": "xx", "token": "yy"}, format="json"
        )

        assert response.json()["valido"] is False


class TestConvite:
    def test_convidado_define_a_senha_e_entra(self, api, api_anonimo, mailoutbox):
        api.post(
            "/api/v1/usuarios/",
            {"email": "novato@teste.dev", "nome": "Novato"},
            format="json",
        )

        api_anonimo.post(
            "/api/v1/senha/redefinir/",
            {**link_do_email(mailoutbox[0]), "nova": "MinhaPrimeira1!"},
            format="json",
        )

        entrada = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "novato@teste.dev", "password": "MinhaPrimeira1!"},
            format="json",
        )
        assert entrada.json()["autenticado"] is True

    def test_sem_definir_a_senha_ninguem_entra(self, api, api_anonimo, mailoutbox):
        api.post("/api/v1/usuarios/", {"email": "novato@teste.dev"}, format="json")

        entrada = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "novato@teste.dev", "password": ""},
            format="json",
        )

        assert entrada.status_code == 400


class TestTrocarEmail:
    def test_o_link_vai_para_o_endereco_novo(self, api, mailoutbox):
        """Unico jeito de provar que o endereco novo existe e e da pessoa."""
        response = api.post(
            "/api/v1/perfil/email/",
            {"senha_atual": "senha-de-teste", "email": "novo@teste.dev"},
            format="json",
        )

        assert response.status_code == 200
        assert mailoutbox[0].to == ["novo@teste.dev"]

    def test_nada_muda_antes_da_confirmacao(self, api, mailoutbox):
        api.post(
            "/api/v1/perfil/email/",
            {"senha_atual": "senha-de-teste", "email": "novo@teste.dev"},
            format="json",
        )

        assert User.objects.get(email="dono@teste.dev")

    def test_confirmar_troca_o_acesso(self, api, api_anonimo, mailoutbox):
        api.post(
            "/api/v1/perfil/email/",
            {"senha_atual": "senha-de-teste", "email": "novo@teste.dev"},
            format="json",
        )
        codigo = re.search(r"codigo=([^\s]+)", mailoutbox[0].body).group(1)

        response = api_anonimo.post(
            "/api/v1/email/confirmar/", {"codigo": codigo}, format="json"
        )

        assert response.status_code == 200
        assert User.objects.filter(email="novo@teste.dev").exists()

    def test_senha_errada_nao_pede_troca(self, api, mailoutbox):
        response = api.post(
            "/api/v1/perfil/email/",
            {"senha_atual": "nao-e-essa", "email": "novo@teste.dev"},
            format="json",
        )

        assert response.status_code == 400
        assert mailoutbox == []

    def test_email_de_outra_conta_e_recusado(self, api, cria_perfil, mailoutbox):
        cria_perfil(email="ocupado@teste.dev")

        response = api.post(
            "/api/v1/perfil/email/",
            {"senha_atual": "senha-de-teste", "email": "ocupado@teste.dev"},
            format="json",
        )

        assert response.status_code == 400
        assert mailoutbox == []

    def test_codigo_adulterado_e_recusado(self, api_anonimo, catalogo):
        response = api_anonimo.post(
            "/api/v1/email/confirmar/", {"codigo": "nao-assinado"}, format="json"
        )

        assert response.status_code == 400


def codigo_de(segredo: str, passos: int = 0) -> str:
    """Codigo do aplicativo, opcionalmente o do passo seguinte.

    Precisa existir porque o codigo passou a valer UMA entrada: o mesmo numero
    que ligou o segundo fator nao serve de novo para entrar logo depois. Cada
    passo tem 30 segundos, e a janela de tolerancia aceita o vizinho.
    """
    return pyotp.TOTP(segredo).at(int(time.time()) + passos * 30)


class TestDoisFatores:
    def liga(self, api):
        """Faz o caminho inteiro de ativacao e devolve (segredo, codigos)."""
        preparo = api.post("/api/v1/perfil/2fa/").json()
        segredo = preparo["segredo"]
        confirmacao = api.post(
            "/api/v1/perfil/2fa/confirmar/",
            {"codigo": pyotp.TOTP(segredo).now()},
            format="json",
        )
        return segredo, confirmacao.json()["codigos"]

    def test_preparar_nao_liga_nada(self, api):
        """Quem abre a tela e desiste no meio nao pode ficar trancado fora."""
        api.post("/api/v1/perfil/2fa/")

        assert api.get("/api/v1/perfil/2fa/").json()["ativo"] is False

    def test_ativa_com_o_codigo_do_aplicativo(self, api):
        _, codigos = self.liga(api)

        estado = api.get("/api/v1/perfil/2fa/").json()
        assert estado["ativo"] is True
        # Os codigos de reserva nascem junto: perder o celular tem volta.
        assert len(codigos) == 8
        assert estado["codigos_restantes"] == 8

    def test_codigo_errado_nao_ativa(self, api):
        api.post("/api/v1/perfil/2fa/")

        response = api.post("/api/v1/perfil/2fa/confirmar/", {"codigo": "000000"}, format="json")

        assert response.status_code == 400
        assert api.get("/api/v1/perfil/2fa/").json()["ativo"] is False

    def test_senha_certa_ainda_nao_entra(self, api, api_anonimo):
        self.liga(api)

        entrada = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "dono@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        assert entrada.json() == {"autenticado": False, "precisa_codigo": True}
        # A sessao continua anonima ate o codigo.
        assert api_anonimo.get("/api/v1/perfil/").status_code == 403

    def test_codigo_fecha_a_entrada(self, api, api_anonimo):
        segredo, _ = self.liga(api)
        api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "dono@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        # Passo seguinte de proposito: o codigo que ligou o 2FA acabou de ser
        # queimado, e reusar ele aqui e justamente o que nao pode mais.
        response = api_anonimo.post(
            "/api/v1/sessao/codigo/", {"codigo": codigo_de(segredo, 1)}, format="json"
        )

        assert response.json()["autenticado"] is True
        assert api_anonimo.get("/api/v1/perfil/").status_code == 200

    def test_codigo_de_reserva_entra_e_queima(self, api, api_anonimo):
        _, codigos = self.liga(api)
        api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "dono@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        primeira = api_anonimo.post(
            "/api/v1/sessao/codigo/", {"codigo": codigos[0]}, format="json"
        )
        assert primeira.json()["autenticado"] is True

        # O mesmo codigo nao entra de novo.
        api_anonimo.delete("/api/v1/sessao/")
        api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "dono@teste.dev", "password": "senha-de-teste"},
            format="json",
        )
        segunda = api_anonimo.post(
            "/api/v1/sessao/codigo/", {"codigo": codigos[0]}, format="json"
        )
        assert segunda.status_code == 400

    def test_codigo_sem_ter_passado_pela_senha(self, api_anonimo, catalogo):
        response = api_anonimo.post(
            "/api/v1/sessao/codigo/", {"codigo": "123456"}, format="json"
        )

        assert response.status_code == 400

    def test_desativar_exige_a_senha(self, api):
        self.liga(api)

        recusado = api.post(
            "/api/v1/perfil/2fa/desativar/", {"senha_atual": "nao-e-essa"}, format="json"
        )
        assert recusado.status_code == 400

        aceito = api.post(
            "/api/v1/perfil/2fa/desativar/", {"senha_atual": "senha-de-teste"}, format="json"
        )
        assert aceito.status_code == 200
        assert api.get("/api/v1/perfil/2fa/").json()["ativo"] is False

    def test_codigos_novos_invalidam_os_antigos(self, api):
        _, antigos = self.liga(api)

        novos = api.post(
            "/api/v1/perfil/2fa/codigos/", {"senha_atual": "senha-de-teste"}, format="json"
        ).json()["codigos"]

        assert set(novos).isdisjoint(antigos)
        assert len(novos) == 8


class TestLimiteDeTentativa:
    """Rota publica sem limite vira ferramenta de encher caixa de entrada."""

    def test_esqueci_senha_para_depois_de_cinco(self, api_anonimo, cria_perfil, mailoutbox):
        cria_perfil(email="alvo@teste.dev")
        corpo = {"email": "alvo@teste.dev"}

        codigos = [
            api_anonimo.post("/api/v1/senha/esqueci/", corpo, format="json").status_code
            for _ in range(6)
        ]

        assert codigos[:5] == [200] * 5
        assert codigos[5] == 429
        assert len(mailoutbox) == 5

    def test_codigo_de_2fa_tem_limite(self, api, api_anonimo):
        segredo = api.post("/api/v1/perfil/2fa/").json()["segredo"]
        api.post(
            "/api/v1/perfil/2fa/confirmar/",
            {"codigo": pyotp.TOTP(segredo).now()},
            format="json",
        )
        api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "dono@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        codigos = [
            api_anonimo.post(
                "/api/v1/sessao/codigo/", {"codigo": "000000"}, format="json"
            ).status_code
            for _ in range(11)
        ]

        assert codigos[-1] == 429
