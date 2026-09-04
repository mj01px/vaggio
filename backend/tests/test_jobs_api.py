"""Fila de triagem, filtros e descarte."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.jobs.models import Job, JobSource
from apps.pipeline.services import enter_pipeline

pytestmark = pytest.mark.django_db


class TestDedupKey:
    def test_url_e_o_identificador(self):
        assert Job.build_key("https://X.com/vaga/1 ") == Job.build_key("https://x.com/vaga/1")

    def test_sem_url_cai_para_titulo_e_empresa(self):
        assert Job.build_key("", "Dev Python", "Acme") == Job.build_key("", "dev python", "acme")

    def test_key_preenchida_no_save(self, make_job):
        job = make_job(url="https://exemplo.dev/vaga/xyz")
        assert job.key == Job.build_key("https://exemplo.dev/vaga/xyz")


class TestTriageQueue:
    def test_lista_so_o_que_falta_triar(self, api, make_job):
        na_fila = make_job("Dev Python Junior")
        descartada = make_job("Dev PHP", discarded=True)
        ja_no_funil = make_job("Dev Java")
        enter_pipeline(ja_no_funil)

        response = api.get("/api/v1/jobs/")

        assert response.status_code == 200
        ids = [item["id"] for item in response.json()["results"]]
        assert ids == [na_fila.id]
        assert descartada.id not in ids

    def test_queue_discarded(self, api, make_job):
        make_job("Dev Python")
        descartada = make_job("Dev PHP", discarded=True)

        response = api.get("/api/v1/jobs/", {"queue": "discarded"})

        assert [item["id"] for item in response.json()["results"]] == [descartada.id]

    def test_ordena_por_score(self, api, make_job):
        baixa = make_job("Dev generico", score=5)
        alta = make_job("Dev Python", score=50)

        response = api.get("/api/v1/jobs/")

        assert [item["id"] for item in response.json()["results"]] == [alta.id, baixa.id]


class TestFilters:
    def test_busca_por_texto(self, api, make_job):
        alvo = make_job("Desenvolvedor Django")
        make_job("Analista de Suporte")

        response = api.get("/api/v1/jobs/", {"q": "django"})

        assert [item["id"] for item in response.json()["results"]] == [alvo.id]

    def test_busca_tambem_na_empresa(self, api, make_job):
        alvo = make_job("Dev", company="Nubank")
        make_job("Dev", company="Outra")

        response = api.get("/api/v1/jobs/", {"q": "nubank"})

        assert [item["id"] for item in response.json()["results"]] == [alvo.id]

    def test_score_minimo(self, api, make_job):
        make_job("Baixa", score=5)
        alta = make_job("Alta", score=40)

        response = api.get("/api/v1/jobs/", {"min_score": 20})

        assert [item["id"] for item in response.json()["results"]] == [alta.id]

    def test_janela_de_recencia(self, api, make_job):
        recente = make_job("Da semana", published_at=timezone.now() - timedelta(days=2))
        make_job("Do mes passado", published_at=timezone.now() - timedelta(days=45))

        response = api.get("/api/v1/jobs/", {"published_within": 7})

        assert [item["id"] for item in response.json()["results"]] == [recente.id]

    def test_janela_usa_a_data_da_coleta_quando_nao_ha_publicacao(self, api, make_job):
        # Cadastro manual nao tem published_at. Sem o fallback ele sumiria
        # justamente do filtro mais usado.
        manual = make_job("Cadastrada na mao", published_at=None)

        response = api.get("/api/v1/jobs/", {"published_within": 7})

        assert [item["id"] for item in response.json()["results"]] == [manual.id]

    def test_janela_invalida_nao_filtra(self, api, make_job):
        make_job("Qualquer uma", published_at=timezone.now() - timedelta(days=400))

        assert api.get("/api/v1/jobs/", {"published_within": 0}).json()["count"] == 1
        assert api.get("/api/v1/jobs/", {"published_within": -5}).json()["count"] == 1

    def test_faixa_de_datas(self, api, make_job):
        hoje = timezone.localdate()
        antiga = make_job("Antiga", published_at=timezone.now() - timedelta(days=20))
        no_meio = make_job("No meio", published_at=timezone.now() - timedelta(days=10))
        make_job("De ontem", published_at=timezone.now() - timedelta(days=1))

        response = api.get(
            "/api/v1/jobs/",
            {
                "published_after": (hoje - timedelta(days=15)).isoformat(),
                "published_before": (hoje - timedelta(days=5)).isoformat(),
            },
        )

        ids = [item["id"] for item in response.json()["results"]]
        assert ids == [no_meio.id]
        assert antiga.id not in ids

    def test_faixa_inclui_o_dia_inteiro_do_limite(self, api, make_job):
        # Quem escolhe 01/09 no "ate" espera ver a vaga das 18h de 01/09, e nao
        # so as de antes da meia-noite.
        agora = timezone.now()
        do_dia = make_job("Publicada mais tarde", published_at=agora)

        response = api.get(
            "/api/v1/jobs/", {"published_before": timezone.localdate().isoformat()}
        )

        assert [item["id"] for item in response.json()["results"]] == [do_dia.id]

    def test_faixa_usa_a_data_da_coleta_quando_nao_ha_publicacao(self, api, make_job):
        manual = make_job("Cadastrada na mao", published_at=None)

        response = api.get(
            "/api/v1/jobs/",
            {"published_after": (timezone.localdate() - timedelta(days=1)).isoformat()},
        )

        assert [item["id"] for item in response.json()["results"]] == [manual.id]

    def test_fonte(self, api, make_job):
        make_job("Do github", source=JobSource.GITHUB)
        gupy = make_job("Da gupy", source=JobSource.GUPY)

        response = api.get("/api/v1/jobs/", {"source": "gupy"})

        assert [item["id"] for item in response.json()["results"]] == [gupy.id]


class TestActions:
    def test_descartar_tira_da_fila(self, api, make_job):
        job = make_job()

        response = api.post(f"/api/v1/jobs/{job.id}/discard/")

        assert response.status_code == 200
        assert response.json()["discarded"] is True
        assert api.get("/api/v1/jobs/").json()["count"] == 0

    def test_restaurar_devolve_para_a_fila(self, api, make_job):
        job = make_job(discarded=True)

        api.post(f"/api/v1/jobs/{job.id}/restore/")

        assert api.get("/api/v1/jobs/").json()["count"] == 1

    def test_stats(self, api, make_job):
        make_job()
        make_job(discarded=True)

        stats = api.get("/api/v1/jobs/stats/").json()

        assert stats == {"triage": 1, "discarded": 1, "total": 2}


class TestManualEntry:
    def test_cadastro_manual_pontua_sozinho(self, api):
        payload = {
            "title": "Desenvolvedor Python Junior",
            "company": "Fintech X",
            "location": "Remoto",
            "url": "https://linkedin.com/jobs/123",
            "description": "Django e PostgreSQL",
        }

        response = api.post("/api/v1/jobs/", payload, format="json")

        assert response.status_code == 201
        body = response.json()
        assert body["source"] == JobSource.MANUAL
        assert body["score"] > 0
        assert body["seniority"] == "junior"

    def test_recusa_url_repetida(self, api, make_job):
        make_job(url="https://linkedin.com/jobs/123")

        response = api.post(
            "/api/v1/jobs/",
            {"title": "Outra", "url": "https://linkedin.com/jobs/123"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID"

    def test_nao_aceita_delete(self, api, make_job):
        job = make_job()

        assert api.delete(f"/api/v1/jobs/{job.id}/").status_code == 405



class TestPagination:
    def test_page_size_grande_nao_e_cortado_em_silencio(self, api):
        # Um teto menor que o pedido corta a lista sem erro nenhum, e o
        # contador do header passa a discordar do que esta na tela.
        self._encher(130)

        body = api.get("/api/v1/jobs/", {"page_size": 120}).json()

        assert body["count"] == 130
        assert len(body["results"]) == 120

    def test_navega_pelas_paginas(self, api):
        # O Radar pagina de 100 em 100 e precisa alcancar a fila inteira.
        self._encher(250)

        primeira = api.get("/api/v1/jobs/", {"page_size": 100}).json()
        terceira = api.get("/api/v1/jobs/", {"page_size": 100, "page": 3}).json()

        assert (primeira["count"], len(primeira["results"])) == (250, 100)
        assert primeira["next"] is not None
        assert len(terceira["results"]) == 50
        assert terceira["next"] is None

        vistos = {item["id"] for item in primeira["results"]}
        assert vistos.isdisjoint({item["id"] for item in terceira["results"]})

    def test_pagina_fora_do_alcance_responde_404(self, api):
        # A tela conta com isso para voltar ao comeco em vez de travar.
        self._encher(10)

        response = api.get("/api/v1/jobs/", {"page_size": 100, "page": 9})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    @staticmethod
    def _encher(quantidade):
        Job.objects.bulk_create(
            Job(
                title=f"Vaga {i}",
                url=f"https://exemplo.dev/pagina/{i}",
                source=JobSource.GITHUB,
                key=Job.build_key(f"https://exemplo.dev/pagina/{i}"),
            )
            for i in range(quantidade)
        )


class TestEdicaoDeVaga:
    """PATCH em vaga: o que o admin do Django fazia, agora sob `vagas.gerenciar`."""

    def test_corrige_os_campos_do_conteudo(self, api, make_job):
        job = make_job("Dev Pyhton Junio", company="")

        response = api.patch(
            f"/api/v1/jobs/{job.id}/",
            {
                "title": "Desenvolvedor Python Junior",
                "company": "Acme",
                "seniority": "junior",
                "work_mode": "remote",
                "score": 42,
                "tags": ["Python", "python", " Django "],
            },
            format="json",
        )

        assert response.status_code == 200
        job.refresh_from_db()
        assert job.title == "Desenvolvedor Python Junior"
        assert job.company == "Acme"
        assert job.seniority == "junior"
        assert job.score == 42
        # Minusculas e sem repetir, como o classificador grava.
        assert job.tags == ["python", "django"]

    def test_resposta_traz_a_vaga_inteira(self, api, make_job):
        job = make_job("Dev Python")

        response = api.patch(
            f"/api/v1/jobs/{job.id}/", {"company": "Acme"}, format="json"
        )

        corpo = response.json()
        assert corpo["id"] == job.id
        # Campos que a lista mostra e o serializer de escrita nao aceita.
        assert "has_application" in corpo
        assert "seniority_display" in corpo

    def test_trocar_a_url_recalcula_a_chave(self, api, make_job):
        job = make_job(url="https://exemplo.dev/vaga/errada")

        api.patch(
            f"/api/v1/jobs/{job.id}/",
            {"url": "https://exemplo.dev/vaga/certa"},
            format="json",
        )

        job.refresh_from_db()
        assert job.key == Job.build_key("https://exemplo.dev/vaga/certa")

    def test_recusa_url_de_outra_vaga(self, api, make_job):
        outra = make_job("Dev Java", url="https://exemplo.dev/vaga/java")
        job = make_job("Dev Python", url="https://exemplo.dev/vaga/python")

        response = api.patch(
            f"/api/v1/jobs/{job.id}/", {"url": outra.url}, format="json"
        )

        assert response.status_code == 400
        job.refresh_from_db()
        assert job.url == "https://exemplo.dev/vaga/python"

    def test_manter_a_propria_url_passa(self, api, make_job):
        job = make_job(url="https://exemplo.dev/vaga/mesma")

        response = api.patch(
            f"/api/v1/jobs/{job.id}/",
            {"url": job.url, "title": "Outro titulo"},
            format="json",
        )

        assert response.status_code == 200

    def test_score_fora_da_faixa_e_recusado(self, api, make_job):
        job = make_job(score=10)

        response = api.patch(f"/api/v1/jobs/{job.id}/", {"score": 9999}, format="json")

        assert response.status_code == 400
        job.refresh_from_db()
        assert job.score == 10

    def test_put_continua_fora(self, api, make_job):
        job = make_job()

        response = api.put(f"/api/v1/jobs/{job.id}/", {"title": "X"}, format="json")

        assert response.status_code == 405

    def test_nao_apaga_vaga(self, api, make_job):
        job = make_job()

        assert api.delete(f"/api/v1/jobs/{job.id}/").status_code == 405
