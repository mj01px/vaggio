"""Sessao, perfil e RBAC: quem entra, quem pode o que."""

import pytest

from apps.accounts.models import Perfil
from apps.accounts.permissoes import (
    EDITAR_PERFIL,
    GERAR_APRESENTACAO,
    GERENCIAR_FUNIL,
    GERENCIAR_VAGAS,
    TRIAR_VAGAS,
    VER_FUNIL,
    VER_VAGAS,
)

pytestmark = pytest.mark.django_db


class TestPortaFechada:
    """Antes do RBAC a API inteira era aberta. Estes testes sao a trava."""

    @pytest.mark.parametrize(
        "rota",
        [
            "/api/v1/jobs/",
            "/api/v1/jobs/stats/",
            "/api/v1/applications/",
            "/api/v1/applications/board/",
            "/api/v1/collections/",
            "/api/v1/perfil/",
        ],
    )
    def test_sem_sessao_nao_le_nada(self, api_anonimo, rota):
        assert api_anonimo.get(rota).status_code in (401, 403)

    def test_health_continua_aberto(self, api_anonimo):
        # E ping de infra: exigir login quebraria healthcheck de container.
        assert api_anonimo.get("/api/v1/health/").status_code == 200


class TestSessao:
    def test_entra_com_senha_certa(self, api_anonimo, cria_perfil):
        cria_perfil(email="mauro@teste.dev")

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "mauro@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["autenticado"] is True
        assert corpo["perfil"]["email"] == "mauro@teste.dev"

    def test_senha_errada_nao_diz_se_o_usuario_existe(self, api_anonimo, cria_perfil):
        cria_perfil(email="mauro@teste.dev")

        existe = api_anonimo.post(
            "/api/v1/sessao/", {"email": "mauro@teste.dev", "password": "errada"}, format="json"
        )
        nao_existe = api_anonimo.post(
            "/api/v1/sessao/", {"email": "ninguem@teste.dev", "password": "errada"}, format="json"
        )

        assert existe.status_code == nao_existe.status_code == 400
        assert existe.json()["error"]["message"] == nao_existe.json()["error"]["message"]

    def test_conta_desativada_nao_entra(self, api_anonimo, cria_perfil):
        perfil = cria_perfil(email="antigo@teste.dev")
        perfil.user.is_active = False
        perfil.user.save()

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "antigo@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        assert response.status_code == 400

    def test_sem_lembrar_a_sessao_morre_com_o_navegador(self, api_anonimo, cria_perfil):
        cria_perfil(email="mauro@teste.dev")

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "mauro@teste.dev", "password": "senha-de-teste", "lembrar": False},
            format="json",
        )

        assert response.status_code == 200
        # expiry 0 e o contrato do Django para "cookie de sessao do navegador".
        assert response.wsgi_request.session.get_expire_at_browser_close() is True

    def test_lembrar_e_o_padrao_de_quem_nao_manda_o_campo(self, api_anonimo, cria_perfil):
        cria_perfil(email="mauro@teste.dev")

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "mauro@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        assert response.status_code == 200
        assert response.wsgi_request.session.get_expire_at_browser_close() is False

    def test_username_nao_entra_mais(self, api_anonimo, cria_perfil):
        # A conta existe e a senha esta certa; o que mudou e a credencial.
        cria_perfil(email="mauro@teste.dev")

        response = api_anonimo.post(
            "/api/v1/sessao/", {"email": "mauro", "password": "senha-de-teste"}, format="json"
        )

        assert response.status_code == 400

    def test_e_mail_entra_sem_ligar_para_maiuscula(self, api_anonimo, cria_perfil):
        cria_perfil(email="mauro@teste.dev")

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "Mauro@Teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        assert response.status_code == 200

    def test_sessao_diz_quem_sou(self, api):
        corpo = api.get("/api/v1/sessao/").json()

        assert corpo["autenticado"] is True
        assert VER_VAGAS in corpo["perfil"]["permissoes"]

    def test_sair_encerra(self, api):
        assert api.delete("/api/v1/sessao/").status_code == 204


class TestPermissoesPorCargo:
    def test_leitura_ve_mas_nao_tria(self, api_anonimo, cria_perfil, make_job):
        perfil = cria_perfil(email="visita@teste.dev", permissoes=[VER_VAGAS, VER_FUNIL])
        api_anonimo.force_authenticate(user=perfil.user)
        job = make_job()

        assert api_anonimo.get("/api/v1/jobs/").status_code == 200
        assert api_anonimo.post(f"/api/v1/jobs/{job.id}/discard/").status_code == 403

    def test_quem_tria_nao_necessariamente_gera_apresentacao(
        self, api_anonimo, cria_perfil, make_job
    ):
        perfil = cria_perfil(email="triador@teste.dev", permissoes=[VER_VAGAS, TRIAR_VAGAS])
        api_anonimo.force_authenticate(user=perfil.user)
        job = make_job()

        assert api_anonimo.post(f"/api/v1/jobs/{job.id}/discard/").status_code == 200
        assert api_anonimo.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json").status_code == 403

    def test_triar_nao_deixa_editar_a_vaga(self, api_anonimo, cria_perfil, make_job):
        """Descartar e corrigir sao decisoes de peso diferente.

        Quem tria escolhe se a vaga interessa; quem edita reescreve o que a
        coleta trouxe, inclusive a URL que identifica a vaga.
        """
        perfil = cria_perfil(email="triador2@teste.dev", permissoes=[VER_VAGAS, TRIAR_VAGAS])
        api_anonimo.force_authenticate(user=perfil.user)
        job = make_job()

        resposta = api_anonimo.patch(
            f"/api/v1/jobs/{job.id}/", {"title": "Outro"}, format="json"
        )

        assert resposta.status_code == 403
        job.refresh_from_db()
        assert job.title != "Outro"

    def test_gerenciar_vagas_edita(self, api_anonimo, cria_perfil, make_job):
        perfil = cria_perfil(
            email="editor@teste.dev", permissoes=[VER_VAGAS, GERENCIAR_VAGAS]
        )
        api_anonimo.force_authenticate(user=perfil.user)
        job = make_job()

        resposta = api_anonimo.patch(
            f"/api/v1/jobs/{job.id}/", {"title": "Outro"}, format="json"
        )

        assert resposta.status_code == 200

    def test_ver_funil_nao_deixa_mover(self, api_anonimo, cria_perfil, make_job):
        from apps.pipeline.services import enter_pipeline

        perfil = cria_perfil(email="observador@teste.dev", permissoes=[VER_FUNIL])
        api_anonimo.force_authenticate(user=perfil.user)
        application, _ = enter_pipeline(make_job())

        assert api_anonimo.get("/api/v1/applications/board/").status_code == 200
        assert (
            api_anonimo.patch(
                f"/api/v1/applications/{application.id}/", {"priority": 1}, format="json"
            ).status_code
            == 403
        )

    def test_gerenciar_funil_deixa_mover(self, api_anonimo, cria_perfil, make_job):
        perfil = cria_perfil(
            email="dono-do-funil@teste.dev", permissoes=[VER_FUNIL, GERENCIAR_FUNIL]
        )
        api_anonimo.force_authenticate(user=perfil.user)
        job = make_job()

        assert (
            api_anonimo.post("/api/v1/applications/", {"job": job.id}, format="json").status_code
            == 201
        )

    def test_rodar_coleta_e_permissao_separada(self, api_anonimo, cria_perfil):
        from apps.accounts.permissoes import VER_COLETA

        perfil = cria_perfil(email="curioso@teste.dev", permissoes=[VER_COLETA])
        api_anonimo.force_authenticate(user=perfil.user)

        assert api_anonimo.get("/api/v1/collections/").status_code == 200
        assert api_anonimo.post("/api/v1/collections/run/").status_code == 403

    def test_perfil_sem_cargo_nao_pode_nada(self, api_anonimo, cria_perfil):
        # Errar para o lado seguro: conta pela metade nao vira acesso.
        perfil = cria_perfil(email="sem-cargo@teste.dev", permissoes=[])
        perfil.cargo = None
        perfil.save()
        api_anonimo.force_authenticate(user=perfil.user)

        assert api_anonimo.get("/api/v1/jobs/").status_code == 403

    def test_superusuario_passa_por_tudo(self, api_anonimo, cria_perfil, make_job):
        perfil = cria_perfil(email="root@teste.dev", permissoes=[], superuser=True)
        api_anonimo.force_authenticate(user=perfil.user)
        job = make_job()

        assert api_anonimo.get("/api/v1/jobs/").status_code == 200
        assert api_anonimo.post(f"/api/v1/jobs/{job.id}/discard/").status_code == 200
        assert perfil.permissoes  # ve o catalogo inteiro, sem cargo nenhum


class TestMeuPerfil:
    def test_le_o_proprio_perfil(self, api):
        corpo = api.get("/api/v1/perfil/").json()

        assert corpo["cargo"]["slug"] == "tudo"
        assert GERAR_APRESENTACAO in corpo["permissoes"]
        assert corpo["tem_dossie"] is False

    def test_edita_dossie_e_preferencia(self, api):
        dossie = "Sou dev. " * 60

        corpo = api.patch(
            "/api/v1/perfil/", {"dossie": dossie, "pitch_max_chars": 900}, format="json"
        ).json()

        assert corpo["tem_dossie"] is True
        assert corpo["pitch_max_chars"] == 900

    def test_nao_da_para_se_promover_editando_o_proprio_perfil(self, api, catalogo):
        # `cargo` fica fora do serializer de escrita de proposito.
        antes = api.get("/api/v1/perfil/").json()["cargo"]["slug"]

        api.patch("/api/v1/perfil/", {"cargo": None, "nome": "Mauro"}, format="json")

        assert api.get("/api/v1/perfil/").json()["cargo"]["slug"] == antes

    def test_termos_invalidos_sao_recusados(self, api):
        ruins = [
            {"core": "python"},
            {"core": {"weight": "doze", "terms": ["python"]}},
            {"core": {"weight": 12, "terms": "python"}},
        ]

        for termos in ruins:
            resposta = api.patch("/api/v1/perfil/", {"termos": termos}, format="json")
            assert resposta.status_code == 400, termos

    def test_termos_validos_entram(self, api):
        termos = {"core": {"weight": 12, "terms": ["python", "django"]}}

        corpo = api.patch("/api/v1/perfil/", {"termos": termos}, format="json").json()

        assert corpo["termos"] == termos

    def test_sem_permissao_de_editar_so_le(self, api_anonimo, cria_perfil):
        perfil = cria_perfil(email="so-leitura@teste.dev", permissoes=[VER_VAGAS])
        api_anonimo.force_authenticate(user=perfil.user)

        assert api_anonimo.get("/api/v1/perfil/").status_code == 200
        assert (
            api_anonimo.patch("/api/v1/perfil/", {"nome": "x"}, format="json").status_code == 403
        )

    def test_com_permissao_edita(self, api_anonimo, cria_perfil):
        perfil = cria_perfil(email="editor@teste.dev", permissoes=[EDITAR_PERFIL])
        api_anonimo.force_authenticate(user=perfil.user)

        assert (
            api_anonimo.patch("/api/v1/perfil/", {"nome": "Mauro"}, format="json").status_code
            == 200
        )


class TestPerfilDonoDoScoring:
    def test_termos_do_perfil_mudam_a_pontuacao(self, cria_perfil):
        from apps.jobs.scoring import classify, perfil_de_scoring

        perfil = cria_perfil(email="outro@teste.dev")
        padrao = classify("Desenvolvedor Python Junior")

        perfil.termos = {"core": {"weight": 50, "terms": ["cobol"]}}
        perfil.save()
        proprio = classify(
            "Desenvolvedor Cobol Senior", profile=perfil_de_scoring(perfil)
        )

        assert padrao.score > 0
        # Com termos proprios, o que era ruim para um vira bom para o outro.
        assert proprio.score == 100

    def test_perfil_sem_termos_cai_no_padrao(self, cria_perfil):
        from apps.jobs.scoring import PROFILE, perfil_de_scoring

        assert perfil_de_scoring(cria_perfil(email="cru@teste.dev")) is PROFILE
        assert perfil_de_scoring(None) is PROFILE


class TestDossieDoPerfil:
    def test_dossie_do_perfil_ganha_do_arquivo(self, cria_perfil):
        from apps.jobs.pitch.dossie import carregar_dossie

        perfil = cria_perfil(email="com-dossie@teste.dev")
        perfil.dossie = "Trabalhei com Django e PostgreSQL em producao. " * 20
        perfil.save()

        assert "Django" in carregar_dossie(perfil=perfil)

    def test_dossie_curto_no_perfil_e_recusado(self, cria_perfil):
        from apps.jobs.pitch.dossie import DossieVazioError, carregar_dossie

        perfil = cria_perfil(email="raso@teste.dev")
        perfil.dossie = "Sou dev."
        perfil.save()

        with pytest.raises(DossieVazioError):
            carregar_dossie(perfil=perfil)


class TestPerfilAutomatico:
    def test_conta_sem_perfil_ganha_um_ao_entrar(self, api_anonimo, django_user_model, catalogo):
        # `createsuperuser` nao cria perfil: sem isso a primeira visita quebra.
        django_user_model.objects.create_superuser(
            "raiz", email="raiz@teste.dev", password="senha-de-teste"
        )

        response = api_anonimo.post(
            "/api/v1/sessao/",
            {"email": "raiz@teste.dev", "password": "senha-de-teste"},
            format="json",
        )

        assert response.status_code == 200
        assert Perfil.objects.filter(user__email="raiz@teste.dev").exists()
