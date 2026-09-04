"""Funil: entrada, mudanca de status, linha do tempo e board."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.pipeline.models import Application, ApplicationStatus, Interaction
from apps.pipeline.services import enter_pipeline

pytestmark = pytest.mark.django_db


class TestEnterPipeline:
    def test_entrada_grava_interacao(self, api, make_job):
        job = make_job()

        response = api.post("/api/v1/applications/", {"job": job.id}, format="json")

        assert response.status_code == 201
        application = Application.objects.get(job=job)
        assert application.status == ApplicationStatus.INTEREST
        assert [i.title for i in application.interactions.all()] == ["Entrou no funil"]

    def test_entrada_repetida_nao_duplica(self, api, make_job):
        job = make_job()
        api.post("/api/v1/applications/", {"job": job.id}, format="json")

        response = api.post("/api/v1/applications/", {"job": job.id}, format="json")

        assert response.status_code == 200
        assert Application.objects.count() == 1
        assert Interaction.objects.count() == 1

    def test_vaga_sai_da_fila_de_triagem(self, api, make_job):
        job = make_job()

        api.post("/api/v1/applications/", {"job": job.id}, format="json")

        assert api.get("/api/v1/jobs/").json()["count"] == 0


class TestStatusChange:
    def test_mudanca_registra_a_transicao(self, api, make_job):
        application, _ = enter_pipeline(make_job())

        response = api.patch(
            f"/api/v1/applications/{application.id}/",
            {"status": ApplicationStatus.INTERVIEW},
            format="json",
        )

        assert response.status_code == 200
        titles = [i.title for i in application.interactions.all()]
        assert "Quero aplicar -> Entrevista" in titles

    def test_aplicada_carimba_a_data(self, api, make_job):
        application, _ = enter_pipeline(make_job())

        api.patch(
            f"/api/v1/applications/{application.id}/",
            {"status": ApplicationStatus.APPLIED},
            format="json",
        )

        application.refresh_from_db()
        assert application.applied_on == timezone.localdate()

    def test_data_de_aplicacao_nao_e_sobrescrita(self, api, make_job):
        application, _ = enter_pipeline(make_job())
        api.patch(
            f"/api/v1/applications/{application.id}/",
            {"status": ApplicationStatus.APPLIED},
            format="json",
        )
        original = Application.objects.get(pk=application.pk).applied_on

        api.patch(
            f"/api/v1/applications/{application.id}/",
            {"status": ApplicationStatus.SCREENING},
            format="json",
        )
        api.patch(
            f"/api/v1/applications/{application.id}/",
            {"status": ApplicationStatus.APPLIED},
            format="json",
        )

        assert Application.objects.get(pk=application.pk).applied_on == original

    def test_edicao_sem_mudar_status_nao_gera_interacao(self, api, make_job):
        application, _ = enter_pipeline(make_job())

        api.patch(
            f"/api/v1/applications/{application.id}/",
            {"next_step": "cobrar retorno"},
            format="json",
        )

        assert application.interactions.count() == 1

    def test_status_invalido_e_recusado(self, api, make_job):
        application, _ = enter_pipeline(make_job())

        response = api.patch(
            f"/api/v1/applications/{application.id}/", {"status": "inventado"}, format="json"
        )

        assert response.status_code == 400
        assert response.json()["error"]["details"][0]["field"] == "status"


class TestOverdue:
    def test_vencido_no_funil_ativo(self, make_job):
        application, _ = enter_pipeline(make_job())
        application.next_step_on = timezone.localdate() - timedelta(days=1)
        application.save()

        assert application.is_overdue is True

    def test_encerrada_nao_conta_como_vencida(self, make_job):
        application, _ = enter_pipeline(make_job())
        application.next_step_on = timezone.localdate() - timedelta(days=5)
        application.status = ApplicationStatus.REJECTED
        application.save()

        assert application.is_overdue is False

    def test_sem_data_nao_e_vencida(self, make_job):
        application, _ = enter_pipeline(make_job())

        assert application.is_overdue is False


class TestBoard:
    def test_agrupa_por_coluna_ativa(self, api, make_job):
        enter_pipeline(make_job("Vaga A"))
        segunda, _ = enter_pipeline(make_job("Vaga B"))
        segunda.status = ApplicationStatus.INTERVIEW
        segunda.save()

        board = api.get("/api/v1/applications/board/").json()

        colunas = {c["status"]: c["total"] for c in board["columns"]}
        assert [c["status"] for c in board["columns"]] == [
            "interest",
            "applied",
            "screening",
            "challenge",
            "interview",
            "offer",
        ]
        assert colunas["interest"] == 1
        assert colunas["interview"] == 1

    def test_encerradas_ficam_fora_das_colunas(self, api, make_job):
        rejeitada, _ = enter_pipeline(make_job())
        rejeitada.status = ApplicationStatus.REJECTED
        rejeitada.save()

        board = api.get("/api/v1/applications/board/").json()

        assert sum(c["total"] for c in board["columns"]) == 0
        assert board["stats"]["closed"] == 1

    def test_stats_e_atrasadas(self, api, make_job):
        atrasada, _ = enter_pipeline(make_job("Atrasada"))
        atrasada.status = ApplicationStatus.APPLIED
        atrasada.next_step_on = timezone.localdate() - timedelta(days=2)
        atrasada.save()
        make_job("Ainda na fila")

        board = api.get("/api/v1/applications/board/").json()

        assert [item["id"] for item in board["overdue"]] == [atrasada.id]
        assert board["stats"] == {
            "in_funnel": 1,
            "overdue": 1,
            "radar_queue": 1,
            "closed": 0,
        }

    def test_ordena_coluna_por_prioridade(self, api, make_job):
        baixa, _ = enter_pipeline(make_job("Prioridade 5"))
        baixa.priority = 5
        baixa.save()
        alta, _ = enter_pipeline(make_job("Prioridade 1"))
        alta.priority = 1
        alta.save()

        board = api.get("/api/v1/applications/board/").json()

        interesse = next(c for c in board["columns"] if c["status"] == "interest")
        assert [item["id"] for item in interesse["items"]] == [alta.id, baixa.id]


class TestInteractionsEndpoint:
    def test_lista_a_linha_do_tempo(self, api, make_job):
        application, _ = enter_pipeline(make_job())
        api.patch(
            f"/api/v1/applications/{application.id}/",
            {"status": ApplicationStatus.APPLIED},
            format="json",
        )

        response = api.get(f"/api/v1/applications/{application.id}/interactions/")

        assert response.status_code == 200
        assert len(response.json()) == 2


class TestEncerradas:
    """GET /applications/closed/, a lista de quem saiu do funil."""

    def test_traz_rejeitadas_e_desistidas_juntas(self, api, make_job):
        from apps.pipeline.services import enter_pipeline

        rejeitada, _ = enter_pipeline(make_job("Rejeitada"))
        rejeitada.status = "rejected"
        rejeitada.save()

        desisti, _ = enter_pipeline(make_job("Desisti"))
        desisti.status = "withdrawn"
        desisti.save()

        # Esta continua no funil ativo e nao pode aparecer.
        enter_pipeline(make_job("Ainda viva"))

        corpo = api.get("/api/v1/applications/closed/").json()

        assert {item["id"] for item in corpo["results"]} == {rejeitada.id, desisti.id}
        assert corpo["stats"] == {"rejected": 1, "withdrawn": 1}

    def test_vazio_quando_nada_encerrou(self, api, make_job):
        from apps.pipeline.services import enter_pipeline

        enter_pipeline(make_job())

        corpo = api.get("/api/v1/applications/closed/").json()

        assert corpo["results"] == []
        assert corpo["stats"] == {"rejected": 0, "withdrawn": 0}


class TestApagarEncerrada:
    """DELETE /applications/{id}/, a lixeira da tela de encerradas."""

    def test_apaga_encerrada(self, api, make_job):
        from apps.pipeline.services import enter_pipeline

        application, _ = enter_pipeline(make_job())
        application.status = "rejected"
        application.save()

        assert api.delete(f"/api/v1/applications/{application.id}/").status_code == 204
        assert api.get("/api/v1/applications/closed/").json()["results"] == []

    def test_recusa_apagar_quem_ainda_esta_no_funil(self, api, make_job):
        from apps.pipeline.models import Application
        from apps.pipeline.services import enter_pipeline

        # A trava existe para um DELETE perdido nao levar junto a linha do
        # tempo de um processo que ainda esta acontecendo.
        application, _ = enter_pipeline(make_job())

        assert api.delete(f"/api/v1/applications/{application.id}/").status_code == 400
        assert Application.objects.filter(pk=application.id).exists()


class TestLinhaDoTempo:
    """Escrever na linha do tempo, que antes so existia no admin do Django."""

    @pytest.fixture
    def candidatura(self, make_job):
        from apps.pipeline.services import enter_pipeline

        application, _ = enter_pipeline(make_job())
        return application

    def test_registra_um_evento(self, api, candidatura):
        response = api.post(
            f"/api/v1/applications/{candidatura.id}/interactions/",
            {"title": "Mandei e-mail", "detail": "Falei com a recrutadora"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["title"] == "Mandei e-mail"

        linha = api.get(f"/api/v1/applications/{candidatura.id}/interactions/").json()
        assert [item["title"] for item in linha] == ["Mandei e-mail", "Entrou no funil"]

    def test_edita_um_evento(self, api, candidatura):
        criado = api.post(
            f"/api/v1/applications/{candidatura.id}/interactions/",
            {"title": "Titulo torto"},
            format="json",
        ).json()

        corpo = api.patch(
            f"/api/v1/applications/{candidatura.id}/interactions/{criado['id']}/",
            {"title": "Titulo certo"},
            format="json",
        ).json()

        assert corpo["title"] == "Titulo certo"

    def test_apaga_um_evento(self, api, candidatura):
        criado = api.post(
            f"/api/v1/applications/{candidatura.id}/interactions/",
            {"title": "Engano"},
            format="json",
        ).json()

        assert (
            api.delete(
                f"/api/v1/applications/{candidatura.id}/interactions/{criado['id']}/"
            ).status_code
            == 204
        )
        assert not candidatura.interactions.filter(pk=criado["id"]).exists()

    def test_evento_de_outra_candidatura_nao_e_alcancavel(self, api, candidatura, make_job):
        from apps.pipeline.services import enter_pipeline

        outra, _ = enter_pipeline(make_job("Outra vaga"))
        alheio = outra.interactions.first()

        resposta = api.delete(
            f"/api/v1/applications/{candidatura.id}/interactions/{alheio.id}/"
        )

        assert resposta.status_code == 404
        assert outra.interactions.filter(pk=alheio.id).exists()

    def test_quem_so_ve_o_funil_nao_escreve(self, api_anonimo, cria_perfil, candidatura):
        from apps.accounts.permissoes import VER_FUNIL

        perfil = cria_perfil(email="observador@teste.dev", permissoes=[VER_FUNIL])
        api_anonimo.force_authenticate(user=perfil.user)

        assert (
            api_anonimo.get(
                f"/api/v1/applications/{candidatura.id}/interactions/"
            ).status_code
            == 200
        )
        assert (
            api_anonimo.post(
                f"/api/v1/applications/{candidatura.id}/interactions/",
                {"title": "Nao devia entrar"},
                format="json",
            ).status_code
            == 403
        )
