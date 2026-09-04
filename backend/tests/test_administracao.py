"""Rotas de administracao: usuarios, cargos e permissoes.

Substituem o admin do Django. Os testes cobrem principalmente as travas, que
sao o que separa um painel de administracao de um pe na porta.
"""

import pytest

from apps.accounts.models import Cargo, Perfil
from apps.accounts.permissoes import (
    GERENCIAR_CARGOS,
    GERENCIAR_USUARIOS,
    VER_CARGOS,
    VER_USUARIOS,
)

pytestmark = pytest.mark.django_db


class TestAcessoAsRotasDeAdmin:
    @pytest.mark.parametrize("rota", ["/api/v1/usuarios/", "/api/v1/cargos/", "/api/v1/permissoes/"])
    def test_sem_sessao_nao_entra(self, api_anonimo, rota):
        assert api_anonimo.get(rota).status_code in (401, 403)

    def test_cargo_leitura_nao_ve_usuarios(self, api_anonimo, cria_perfil):
        perfil = cria_perfil(email="visita@teste.dev", permissoes=[])
        perfil.cargo = Cargo.objects.get(slug="leitura")
        perfil.save()
        api_anonimo.force_authenticate(user=perfil.user)

        assert api_anonimo.get("/api/v1/usuarios/").status_code == 403

    def test_ver_usuarios_nao_deixa_criar(self, api_anonimo, cria_perfil):
        perfil = cria_perfil(email="olheiro@teste.dev", permissoes=[VER_USUARIOS])
        api_anonimo.force_authenticate(user=perfil.user)

        assert api_anonimo.get("/api/v1/usuarios/").status_code == 200
        assert (
            api_anonimo.post(
                "/api/v1/usuarios/",
                {"email": "novo@teste.dev", "password": "SenhaLonga123!"},
                format="json",
            ).status_code
            == 403
        )


class TestUsuarios:
    def test_lista_com_cargo_e_permissoes(self, api):
        corpo = api.get("/api/v1/usuarios/").json()

        assert corpo["count"] == 1
        pessoa = corpo["results"][0]
        assert pessoa["cargo"]["slug"] == "tudo"
        assert VER_USUARIOS in pessoa["permissoes"]

    def test_cria_conta_com_perfil_junto(self, api):
        response = api.post(
            "/api/v1/usuarios/",
            {
                "email": "colega@exemplo.dev",
                "nome": "Colega",
                "password": "SenhaLonga123!",
                "cargo": "leitura",
            },
            format="json",
        )

        assert response.status_code == 201
        corpo = response.json()
        assert corpo["nome"] == "Colega"
        assert corpo["cargo"]["slug"] == "leitura"
        # Conta sem perfil nao consegue fazer nada: os dois nascem juntos.
        assert Perfil.objects.filter(user__email="colega@exemplo.dev").exists()

    def test_email_repetido_e_recusado(self, api, cria_perfil):
        # O e-mail e a credencial: duas contas com o mesmo deixariam as duas
        # sem entrar, porque o backend nao saberia qual senha conferir.
        cria_perfil(email="ocupado@teste.dev")

        response = api.post(
            "/api/v1/usuarios/",
            {"email": "OCUPADO@teste.dev", "password": "SenhaLonga123!"},
            format="json",
        )

        assert response.status_code == 400

    def test_conta_nova_entra_com_o_e_mail(self, api, api_anonimo):
        api.post(
            "/api/v1/usuarios/",
            {"email": "recem@teste.dev", "password": "SenhaLonga123!", "cargo": "leitura"},
            format="json",
        )

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "recem@teste.dev", "password": "SenhaLonga123!"},
            format="json",
        )

        assert response.status_code == 200

    def test_email_de_outra_pessoa_e_recusado_na_edicao(self, api, cria_perfil):
        outro = cria_perfil(email="livre@teste.dev", permissoes=[])
        cria_perfil(email="tomado@teste.dev", permissoes=[])

        response = api.patch(
            f"/api/v1/usuarios/{outro.user.id}/", {"email": "tomado@teste.dev"}, format="json"
        )

        assert response.status_code == 400

    def test_senha_fraca_e_recusada(self, api):
        response = api.post(
            "/api/v1/usuarios/", {"email": "fraco@teste.dev", "password": "123"}, format="json"
        )

        assert response.status_code == 400

    def test_troca_o_cargo_de_outra_pessoa(self, api, cria_perfil):
        outro = cria_perfil(email="outro@teste.dev", permissoes=[])

        corpo = api.patch(
            f"/api/v1/usuarios/{outro.user.id}/", {"cargo": "leitura"}, format="json"
        ).json()

        assert corpo["cargo"]["slug"] == "leitura"

    def test_desativa_outra_pessoa(self, api, cria_perfil):
        outro = cria_perfil(email="saiu@teste.dev", permissoes=[])

        corpo = api.patch(
            f"/api/v1/usuarios/{outro.user.id}/", {"is_active": False}, format="json"
        ).json()

        assert corpo["is_active"] is False

    def test_nao_da_para_se_desativar(self, api):
        eu = api.get("/api/v1/usuarios/").json()["results"][0]

        response = api.patch(
            f"/api/v1/usuarios/{eu['id']}/", {"is_active": False}, format="json"
        )

        assert response.status_code == 400
        assert "propria conta" in response.json()["error"]["message"]

    def test_nao_da_para_trocar_o_proprio_cargo(self, api):
        eu = api.get("/api/v1/usuarios/").json()["results"][0]

        response = api.patch(f"/api/v1/usuarios/{eu['id']}/", {"cargo": "leitura"}, format="json")

        assert response.status_code == 400
        assert "proprio cargo" in response.json()["error"]["message"]

    def test_conta_nao_se_apaga(self, api, cria_perfil):
        outro = cria_perfil(email="permanente@teste.dev", permissoes=[])

        # Candidatura e apresentacao ficam penduradas em quem criou.
        assert api.delete(f"/api/v1/usuarios/{outro.user.id}/").status_code == 405

    def test_convite_vai_para_a_pessoa(self, api, cria_perfil, mailoutbox):
        """O admin nao define senha de ninguem: manda o link e a pessoa escolhe."""
        outro = cria_perfil(email="convidado@teste.dev", permissoes=[])

        response = api.post(f"/api/v1/usuarios/{outro.user.id}/convite/")

        assert response.status_code == 200
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["convidado@teste.dev"]
        assert "definir-senha" in mailoutbox[0].body

    def test_conta_desativada_nao_recebe_convite(self, api, cria_perfil, mailoutbox):
        outro = cria_perfil(email="desligado@teste.dev", permissoes=[])
        outro.user.is_active = False
        outro.user.save()

        response = api.post(f"/api/v1/usuarios/{outro.user.id}/convite/")

        assert response.status_code == 400
        assert mailoutbox == []

    def test_conta_nova_nasce_sem_senha_e_recebe_convite(self, api, mailoutbox):
        """Sem senha no corpo, ninguem alem do dono conhece a senha da conta."""
        response = api.post(
            "/api/v1/usuarios/",
            {"email": "novato@teste.dev", "nome": "Novato"},
            format="json",
        )

        assert response.status_code == 201
        from django.contrib.auth import get_user_model

        criado = get_user_model().objects.get(email="novato@teste.dev")
        assert not criado.has_usable_password()
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["novato@teste.dev"]


class TestCargos:
    def test_lista_com_as_permissoes(self, api):
        corpo = api.get("/api/v1/cargos/").json()

        cargos = {c["slug"]: c for c in corpo["results"]}
        assert set(cargos) >= {"leitura", "tudo"}
        assert VER_CARGOS in cargos["tudo"]["permissoes"]

    def test_cria_cargo_com_permissoes_por_slug(self, api):
        response = api.post(
            "/api/v1/cargos/",
            {
                "slug": "triador",
                "nome": "Triador",
                "descricao": "So tria o radar.",
                "permissoes": ["vagas.ver", "vagas.triar"],
            },
            format="json",
        )

        assert response.status_code == 201
        assert sorted(response.json()["permissoes"]) == ["vagas.triar", "vagas.ver"]

    def test_muda_as_permissoes_de_um_cargo(self, api):
        corpo = api.patch(
            "/api/v1/cargos/",
            {},
            format="json",
        )
        cargo = Cargo.objects.get(slug="leitura")

        resposta = api.patch(
            f"/api/v1/cargos/{cargo.id}/",
            {"permissoes": ["vagas.ver"]},
            format="json",
        )

        assert corpo.status_code == 405  # PATCH na lista nao existe
        assert resposta.json()["permissoes"] == ["vagas.ver"]

    def test_permissao_inexistente_e_recusada(self, api):
        cargo = Cargo.objects.get(slug="leitura")

        resposta = api.patch(
            f"/api/v1/cargos/{cargo.id}/", {"permissoes": ["voar.alto"]}, format="json"
        )

        assert resposta.status_code == 400

    def test_cargo_em_uso_nao_se_apaga(self, api, cria_perfil):
        cargo = Cargo.objects.create(slug="temporario", nome="Temporario")
        perfil = cria_perfil(email="usa-o-cargo@teste.dev", permissoes=[])
        perfil.cargo = cargo
        perfil.save()

        resposta = api.delete(f"/api/v1/cargos/{cargo.id}/")

        assert resposta.status_code == 400
        assert "pessoa" in resposta.json()["error"]["message"]

    def test_cargo_livre_se_apaga(self, api):
        cargo = Cargo.objects.create(slug="sobrando", nome="Sobrando")

        assert api.delete(f"/api/v1/cargos/{cargo.id}/").status_code == 204

    def test_sem_permissao_de_gerenciar_so_le(self, api_anonimo, cria_perfil):
        perfil = cria_perfil(email="curioso@teste.dev", permissoes=[VER_CARGOS])
        api_anonimo.force_authenticate(user=perfil.user)

        assert api_anonimo.get("/api/v1/cargos/").status_code == 200
        assert (
            api_anonimo.post(
                "/api/v1/cargos/", {"slug": "x", "nome": "X"}, format="json"
            ).status_code
            == 403
        )


class TestPermissoes:
    def test_catalogo_e_somente_leitura(self, api):
        listagem = api.get("/api/v1/permissoes/")

        assert listagem.status_code == 200
        slugs = [p["slug"] for p in listagem.json()]
        assert GERENCIAR_USUARIOS in slugs
        assert GERENCIAR_CARGOS in slugs
        # Permissao nova precisa de codigo que a respeite: nasce em permissoes.py.
        assert api.post("/api/v1/permissoes/", {"slug": "x"}, format="json").status_code == 405

    def test_vem_sem_paginacao(self, api):
        # A tela de cargos monta uma caixa por permissao: paginar atrapalharia.
        assert isinstance(api.get("/api/v1/permissoes/").json(), list)
