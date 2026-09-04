"""Coleta: parsing das fontes (sem rede) e o service que grava."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.collectors import services
from apps.collectors.models import CollectionRun
from apps.collectors.sources.base import RawJob, Source
from apps.collectors.sources.github_issues import GithubIssuesSource
from apps.collectors.sources.gupy import GupySource, strip_html
from apps.jobs.models import Job


class FakeSource(Source):
    key = "github"
    label = "Fake"
    jobs: list[RawJob] = []

    def fetch(self):
        yield from self.jobs


@pytest.fixture
def fake_source(monkeypatch):
    """Troca a fonte real por uma lista fixa: coleta testavel sem rede."""

    def _use(jobs):
        FakeSource.jobs = jobs
        monkeypatch.setitem(services.SOURCES, "github", FakeSource)

    return _use


def raw(title="Dev Python Junior", url="https://exemplo.dev/1", **kwargs):
    return RawJob(title=title, url=url, **kwargs)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    """Cliente HTTP de mentira: devolve as paginas na ordem e anota os params."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append(params or {})
        if not self.pages:
            raise AssertionError("pagina pedida a mais: a fonte nao parou quando devia")
        return FakeResponse(self.pages.pop(0))


def gupy_page(total, quantidade, primeiro_id=0):
    return {
        "pagination": {"total": total, "limit": 100, "offset": 0},
        "data": [
            {
                "id": primeiro_id + i,
                "name": f"Desenvolvedor {primeiro_id + i}",
                "jobUrl": f"https://acme.gupy.io/job/{primeiro_id + i}",
            }
            for i in range(quantidade)
        ],
    }


class TestGithubParsing:
    def test_issue_vira_vaga(self):
        issue = {
            "title": "[CLT] Pessoa Desenvolvedora Python Junior",
            "body": "Empresa: Acme\n\nVaga remota.",
            "html_url": "https://github.com/backend-br/vagas/issues/1",
            "number": 1,
            "labels": [{"name": "CLT"}, {"name": "Remoto"}],
            "created_at": "2026-08-30T12:00:00Z",
        }

        job = GithubIssuesSource().parse(issue, "backend-br/vagas")

        assert job.title == "[CLT] Pessoa Desenvolvedora Python Junior"
        assert job.company == "Acme"
        assert job.source_id == "backend-br/vagas#1"
        assert "CLT, Remoto" in job.description
        assert job.published_at.year == 2026

    def test_issue_de_regras_e_ignorada(self):
        issue = {"title": "Regras para publicar vagas", "body": "", "html_url": "x"}

        assert GithubIssuesSource().parse(issue, "backend-br/vagas") is None

    def test_empresa_em_branco_quando_nao_segue_o_template(self):
        # Melhor vazio do que inventar: o titulo desses repositorios e livre
        # demais para separar empresa de cargo sem errar metade das vezes.
        assert GithubIssuesSource.company_from_body("Vaga bacana, sem template") == ""

    def test_empresa_com_marcacao_markdown(self):
        # As duas formas que aparecem de verdade nos repositorios.
        assert GithubIssuesSource.company_from_body("**Empresa**: *Acme*") == "Acme"
        assert GithubIssuesSource.company_from_body("**Empresa:** Acme") == "Acme"

    def test_empresa_longa_demais_e_descartada(self):
        # Linha gigante e texto corrido, nao nome de empresa.
        assert GithubIssuesSource.company_from_body(f"Empresa: {'x' * 200}") == ""


class TestGupyPaginacao:
    def test_varre_o_termo_inteiro(self):
        # 250 resultados a 100 por pagina: tres paginas, a ultima incompleta.
        source = GupySource(searches=["desenvolvedor"])
        client = FakeClient([
            gupy_page(100, 100, 0),
            gupy_page(100, 100, 100),
            gupy_page(100, 50, 200),
        ])

        jobs = list(source.fetch_term(client, "desenvolvedor"))

        assert len(jobs) == 250
        assert [c["offset"] for c in client.calls] == [0, 100, 200]
        assert {c["limit"] for c in client.calls} == {100}

    def test_nao_confia_no_total_do_envelope(self):
        # A Gupy crava total=100 com limit alto mesmo tendo 650. Parar por esse
        # campo custava 550 vagas de um termo so.
        source = GupySource()
        client = FakeClient([gupy_page(100, 100, 0), gupy_page(100, 30, 100)])

        jobs = list(source.fetch_term(client, "desenvolvedor"))

        assert len(jobs) == 130
        assert len(client.calls) == 2

    def test_para_na_pagina_incompleta(self):
        source = GupySource()
        client = FakeClient([gupy_page(100, 40)])

        jobs = list(source.fetch_term(client, "python"))

        assert len(jobs) == 40
        assert len(client.calls) == 1

    def test_para_em_pagina_vazia(self):
        source = GupySource()
        client = FakeClient([gupy_page(100, 100), gupy_page(100, 0)])

        jobs = list(source.fetch_term(client, "python"))

        assert len(jobs) == 100
        assert len(client.calls) == 2

    def test_respeita_a_trava_de_paginas(self):
        # Se a API nunca devolver pagina incompleta, a trava impede laco infinito.
        source = GupySource(max_pages=3)
        client = FakeClient([gupy_page(100, 100) for _ in range(10)])

        jobs = list(source.fetch_term(client, "python"))

        assert len(jobs) == 300
        assert len(client.calls) == 3

    def test_erro_num_termo_nao_derruba_a_fonte(self, sem_espera):
        class ClienteQuebrado:
            def get(self, *args, **kwargs):
                raise RuntimeError("503")

        fonte = GupySource()

        assert list(fonte.fetch_term(ClienteQuebrado(), "python")) == []
        # A busca sai anotada: coleta que trouxe menos vaga porque a API caiu
        # nao pode passar por dia fraco na tela de Coletas.
        assert fonte.falhas == ["python (offset 0): 503"]

    def test_tenta_de_novo_antes_de_desistir(self, sem_espera):
        """Uma pagina que engasga nao pode levar o resto do termo junto.

        "desenvolvedor" sao 7 paginas; desistir na terceira custa 400 vagas.
        """

        class ClienteInstavel:
            """Falha uma vez no offset 100 e responde na tentativa seguinte."""

            def __init__(self):
                self.calls = []
                self.falhou = False

            def get(self, url, params=None, headers=None):
                self.calls.append(params or {})
                if params["offset"] == 100 and not self.falhou:
                    self.falhou = True
                    raise RuntimeError("timeout")
                if params["offset"] >= 200:
                    return FakeResponse(gupy_page(100, 30, params["offset"]))
                return FakeResponse(gupy_page(100, 100, params["offset"]))

        fonte = GupySource()
        client = ClienteInstavel()

        jobs = list(fonte.fetch_term(client, "desenvolvedor"))

        # 100 + 100 + 30: a pagina que falhou foi refeita, nao pulada.
        assert len(jobs) == 230
        assert [c["offset"] for c in client.calls] == [0, 100, 100, 200]
        assert fonte.falhas == []

    def test_falha_parcial_vira_erro_da_coleta(self, db, sem_espera, monkeypatch):
        """O service tem que ver a falha que a fonte engoliu para seguir."""
        from apps.collectors import services

        class FonteFalha:
            def __init__(self):
                self.falhas = ["python (offset 0): 503"]

            def fetch(self):
                return iter(())

        monkeypatch.setitem(services.SOURCES, "gupy", FonteFalha)
        resultado = services.collect_source("gupy", dry_run=True)

        assert "1 busca(s) sem resposta" in resultado.error
        assert "python (offset 0): 503" in resultado.error

    def test_limit_respeita_o_teto_da_api(self):
        # Pedir mais de 100 devolve 400 na Gupy.
        assert GupySource(per_page=500).per_page == 100


class TestGithubPaginacao:
    def test_para_quando_a_pagina_vem_incompleta(self):
        source = GithubIssuesSource(repos=["backend-br/vagas"], per_repo=100, pages=3)
        issues = [
            {"title": f"Vaga {i}", "body": "", "html_url": f"https://gh/i/{i}", "number": i}
            for i in range(30)
        ]
        client = FakeClient([issues])

        jobs = []
        for repo in source.repos:
            for page in range(1, source.pages + 1):
                response = client.get("url", params={"page": page})
                lote = response.json()
                jobs.extend(j for j in (source.parse(i, repo) for i in lote) if j)
                if len(lote) < source.per_repo:
                    break

        assert len(jobs) == 30
        assert len(client.calls) == 1


class TestGupyParsing:
    def test_item_vira_vaga(self):
        item = {
            "id": 42,
            "name": "Desenvolvedor Back-end Junior",
            "jobUrl": "https://acme.gupy.io/job/42",
            "careerPageName": "Acme",
            "city": "Sao Paulo",
            "state": "SP",
            "isRemoteWork": True,
            "publishedDate": "2026-08-29T10:00:00Z",
            "description": "<p>Python &amp; Django</p>",
            "skills": [{"name": "python"}, {"name": "sql"}],
        }

        job = GupySource().parse(item)

        assert job.title == "Desenvolvedor Back-end Junior"
        assert job.company == "Acme"
        assert job.location == "Remoto, Sao Paulo, SP"
        assert "Python & Django" in job.description
        assert job.source_id == "42"

    def test_item_sem_url_e_ignorado(self):
        assert GupySource().parse({"name": "Dev"}) is None

    def test_envelope_em_variantes(self):
        assert GupySource.extract_list({"data": [1, 2]}) == [1, 2]
        assert GupySource.extract_list({"results": [3]}) == [3]
        assert GupySource.extract_list([4]) == [4]
        assert GupySource.extract_list({"outro": "coisa"}) == []

    def test_strip_html(self):
        assert strip_html("<p>Ola &amp;   mundo</p>") == "Ola & mundo"


@pytest.mark.django_db
class TestCollectService:
    def test_grava_e_pontua(self, fake_source):
        fake_source([raw("Desenvolvedor Python Junior", "https://exemplo.dev/1")])

        result = services.collect_source("github")

        assert (result.found, result.new) == (1, 1)
        job = Job.objects.get()
        assert job.source == "github"
        assert job.score > 0
        assert job.seniority == "junior"

    def test_nao_duplica_o_que_ja_existe(self, fake_source):
        fake_source([raw(url="https://exemplo.dev/1")])
        services.collect_source("github")

        result = services.collect_source("github")

        assert (result.found, result.new) == (1, 0)
        assert Job.objects.count() == 1

    def test_nao_duplica_dentro_da_mesma_execucao(self, fake_source):
        fake_source([raw(url="https://exemplo.dev/1"), raw(url="https://exemplo.dev/1")])

        result = services.collect_source("github")

        assert (result.found, result.new) == (2, 1)

    def test_score_minimo_corta_na_entrada(self, fake_source):
        fake_source([raw("Analista PHP Senior", "https://exemplo.dev/php")])

        result = services.collect_source("github", min_score=0)

        assert result.new == 0
        assert result.low_score == 1
        assert Job.objects.count() == 0

    def test_sem_min_score_nada_e_cortado_por_pontuacao(self, fake_source):
        # O padrao mudou: score ordena a fila, nao decide o que existe.
        fake_source([raw("Analista PHP Senior", "https://exemplo.dev/php")])

        result = services.collect_source("github")

        assert result.new == 1
        assert Job.objects.get().score < 0


    def test_dry_run_nao_grava_nem_loga(self, fake_source):
        fake_source([raw()])

        result = services.collect_source("github", dry_run=True)

        assert result.new == 1
        assert Job.objects.count() == 0
        assert CollectionRun.objects.count() == 0

    def test_registra_a_execucao(self, fake_source):
        fake_source([raw()])

        services.collect_source("github")

        run = CollectionRun.objects.get()
        assert (run.found_count, run.new_count) == (1, 1)
        assert run.finished_at is not None
        assert run.error == ""

    def test_fonte_quebrada_nao_derruba_a_coleta(self, fake_source, monkeypatch):
        fake_source([raw()])

        def explode(self):
            raise RuntimeError("API fora do ar")
            yield

        monkeypatch.setattr(FakeSource, "fetch", explode)

        result = services.collect_source("github")

        assert result.error == "API fora do ar"
        assert CollectionRun.objects.get().error == "API fora do ar"


@pytest.mark.django_db
class TestRescore:
    def test_repontua_com_as_regras_atuais(self, make_job):
        from apps.jobs.services import rescore_all

        job = make_job("Desenvolvedor Python Junior", score=0)

        total, changed = rescore_all()

        job.refresh_from_db()
        assert (total, changed) == (1, 1)
        assert job.score > 0
        assert "python" in job.tags


@pytest.mark.django_db
class TestCorteDeIdade:
    def test_vaga_velha_nao_entra(self, fake_source):
        antiga = timezone.now() - timedelta(days=120)
        fake_source([raw(url="https://exemplo.dev/velha", published_at=antiga)])

        result = services.collect_source("github", max_age_days=30)

        assert (result.new, result.old) == (0, 1)
        assert Job.objects.count() == 0

    def test_vaga_da_semana_entra(self, fake_source):
        recente = timezone.now() - timedelta(days=3)
        fake_source([raw(url="https://exemplo.dev/nova", published_at=recente)])

        result = services.collect_source("github", max_age_days=7)

        assert (result.new, result.old) == (1, 0)

    def test_sem_data_nao_e_considerada_velha(self, fake_source):
        # Sumir com o que nao se sabe e pior do que deixar passar.
        fake_source([raw(url="https://exemplo.dev/sem-data", published_at=None)])

        result = services.collect_source("github", max_age_days=7)

        assert result.new == 1

    def test_sem_max_age_nada_e_cortado_por_idade(self, fake_source):
        antiga = timezone.now() - timedelta(days=1500)
        fake_source([raw(url="https://exemplo.dev/2022", published_at=antiga)])

        assert services.collect_source("github").new == 1


@pytest.mark.django_db
class TestDisparoPelaApi:
    """POST /collections/run/, que e o botao 'buscar vagas' do Radar."""

    @pytest.fixture
    def so_a_fonte_falsa(self, monkeypatch):
        """Deixa so a fonte de mentira no registro: teste nao toca a rede."""
        FakeSource.jobs = [raw("Dev Python Junior", "https://exemplo.dev/nova")]
        monkeypatch.setattr(services, "SOURCES", {"github": FakeSource})

    def test_dispara_e_devolve_o_resultado(self, api, so_a_fonte_falsa):
        response = api.post("/api/v1/collections/run/")

        assert response.status_code == 200
        body = response.json()
        assert body["new"] == 1
        assert body["errors"] == []
        assert [s["source"] for s in body["sources"]] == ["github"]
        assert Job.objects.count() == 1

    def test_grava_a_execucao_no_log(self, api, so_a_fonte_falsa):
        api.post("/api/v1/collections/run/")

        run = CollectionRun.objects.get()
        assert run.new_count == 1
        assert run.finished_at is not None

    def test_segunda_chamada_nao_traz_repetida(self, api, so_a_fonte_falsa):
        api.post("/api/v1/collections/run/")

        body = api.post("/api/v1/collections/run/").json()

        assert body["new"] == 0
        assert Job.objects.count() == 1

    def test_recusa_coleta_concorrente(self, api, so_a_fonte_falsa):
        from apps.collectors import views

        views._collect_lock.acquire()
        try:
            response = api.post("/api/v1/collections/run/")
        finally:
            views._collect_lock.release()

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "COLLECTION_IN_PROGRESS"

    def test_a_trava_e_liberada_quando_a_coleta_estoura(self, api, monkeypatch):
        from apps.collectors import views

        def explode(*args, **kwargs):
            raise RuntimeError("banco fora do ar")

        monkeypatch.setattr(views, "collect_all", explode)

        response = api.post("/api/v1/collections/run/")

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        # Sem o finally, a trava ficaria presa e o botao morreria ate reiniciar
        # o servidor: o proximo clique responderia 409 para sempre.
        assert views._collect_lock.acquire(blocking=False)
        views._collect_lock.release()

    def test_log_continua_somente_leitura(self, api):
        assert api.post("/api/v1/collections/", {}, format="json").status_code == 405
        assert api.get("/api/v1/collections/").status_code == 200
