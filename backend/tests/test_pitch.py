"""Geracao do "Apresente-se": dossie, prompt e orquestracao.

Nenhum teste chama a API. O que importa aqui e o que a gente monta e manda, e
as travas que impedem uma geracao ruim de acontecer.
"""

from types import SimpleNamespace

import pytest

from apps.jobs.pitch import dossie as dossie_mod
from apps.jobs.pitch import service
from apps.jobs.pitch.dossie import DossieAusenteError, DossieVazioError, carregar_dossie
from apps.jobs.pitch.gemini import GeminiIndisponivelError, TextoGerado
from apps.jobs.pitch.prompt import INSTRUCAO, MAX_DESCRICAO, descrever_vaga, montar_entrada

DOSSIE_VALIDO = "# Dossie\n\n" + ("Trabalhei com Django e PostgreSQL em producao. " * 20)


def escrever_dossie(tmp_path, conteudo=DOSSIE_VALIDO):
    caminho = tmp_path / "dossie.md"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


class TestDossie:
    def test_arquivo_ausente_explica_o_que_fazer(self, tmp_path):
        with pytest.raises(DossieAusenteError, match="fora do git"):
            carregar_dossie(tmp_path / "nao-existe.md")

    def test_arquivo_curto_demais_e_recusado(self, tmp_path):
        # Dossie raso so consegue gerar texto generico, que e pior que nenhum.
        caminho = escrever_dossie(tmp_path, "# Dossie\n\nSou dev.")

        with pytest.raises(DossieVazioError, match="generico"):
            carregar_dossie(caminho)

    def test_comentarios_de_lembrete_nao_vao_para_o_modelo(self, tmp_path):
        # Os "PENDENTE" do arquivo sao recado seu para voce, nao informacao
        # sobre voce: mandar tarefa pendente para o modelo so atrapalha.
        caminho = escrever_dossie(
            tmp_path, DOSSIE_VALIDO + "\n<!-- PENDENTE: conferir a divisao -->\n"
        )

        texto = carregar_dossie(caminho)

        assert "PENDENTE" not in texto
        assert "Django" in texto

    def test_o_dossie_do_projeto_aponta_para_dentro_do_pacote(self):
        assert dossie_mod.CAMINHO.name == "dossie.md"
        assert dossie_mod.CAMINHO.parent.name == "pitch"


@pytest.mark.django_db
class TestPrompt:
    def test_descreve_a_vaga_com_o_que_importa(self, make_job):
        job = make_job(
            "Desenvolvedor Python Junior",
            company="Fintech X",
            location="Remoto",
            description="Django, Postgres e integracoes",
            tags=["python", "django"],
        )

        texto = descrever_vaga(job)

        assert "Desenvolvedor Python Junior" in texto
        assert "Fintech X" in texto
        assert "python, django" in texto
        assert "Django, Postgres e integracoes" in texto

    def test_descricao_gigante_e_truncada(self, make_job):
        job = make_job(description="x" * (MAX_DESCRICAO + 5000))

        texto = descrever_vaga(job)

        assert "[descricao truncada]" in texto
        assert len(texto) < MAX_DESCRICAO + 1000

    def test_entrada_junta_vaga_dossie_e_tamanho(self, make_job):
        entrada = montar_entrada(make_job("Dev Python"), DOSSIE_VALIDO, max_chars=900)

        assert "=== VAGA ===" in entrada
        assert "=== DOSSIE DO CANDIDATO" in entrada
        assert "no maximo 900 caracteres" in entrada

    def test_instrucao_extra_entra_quando_existe(self, make_job):
        job = make_job()

        com = montar_entrada(job, DOSSIE_VALIDO, 900, instrucao_extra="puxa o lado de dados")
        sem = montar_entrada(job, DOSSIE_VALIDO, 900, instrucao_extra="   ")

        assert "puxa o lado de dados" in com
        assert "Ajuste pedido" not in sem

    def test_regras_duras_estao_na_instrucao(self):
        # Se alguem apagar isso sem querer, o texto passa a poder inventar.
        assert "unica fonte de verdade" in INSTRUCAO
        assert "Nao invente" in INSTRUCAO


@pytest.mark.django_db
class TestGerarApresentacao:
    def test_usa_o_dossie_e_a_vaga(self, make_job, monkeypatch):
        job = make_job("Dev Python Junior", company="Acme")
        capturado = {}

        def fake_gerar(instrucao, entrada, modelo=""):
            capturado["instrucao"] = instrucao
            capturado["entrada"] = entrada
            capturado["modelo"] = modelo
            return TextoGerado("texto gerado", "modelo-x", 10, 20, 5)

        monkeypatch.setattr(service, "carregar_dossie", lambda **kwargs: DOSSIE_VALIDO)
        monkeypatch.setattr(service, "gerar_texto", fake_gerar)

        resultado = service.gerar_apresentacao(job, max_chars=800)

        assert resultado.texto == "texto gerado"
        assert resultado.caracteres == len("texto gerado")
        assert "Dev Python Junior" in capturado["entrada"]
        assert "Django e PostgreSQL" in capturado["entrada"]
        assert "no maximo 800 caracteres" in capturado["entrada"]
        assert capturado["instrucao"] == INSTRUCAO

    def test_dossie_ausente_interrompe_antes_de_gastar_chamada(self, make_job, monkeypatch):
        def explode(**kwargs):
            raise DossieAusenteError("sem dossie")

        chamou = []
        monkeypatch.setattr(service, "carregar_dossie", explode)
        monkeypatch.setattr(service, "gerar_texto", lambda *a, **k: chamou.append(1))

        with pytest.raises(DossieAusenteError):
            service.gerar_apresentacao(make_job())

        assert chamou == []


def cliente_falso(create):
    """Cliente do SDK reduzido ao unico metodo que a gente chama."""
    return SimpleNamespace(interactions=SimpleNamespace(create=create))


class TestChamadaAoGemini:
    def test_timeout_vira_mensagem_acionavel(self, monkeypatch):
        # Sem timeout a chamada pendura para sempre, e no endpoint isso segura
        # a trava: todo clique seguinte responderia 409 ate o processo morrer.
        from apps.jobs.pitch import gemini

        def create(**kwargs):
            assert kwargs["timeout"] == gemini.TIMEOUT_SEGUNDOS
            raise TimeoutError("estourou")

        monkeypatch.setattr(gemini, "_cliente", lambda: cliente_falso(create))

        with pytest.raises(gemini.GeminiIndisponivelError, match="free tier"):
            gemini.gerar_texto("instrucao", "entrada", modelo="modelo-x")

    def test_resposta_sem_texto_e_recusada(self, monkeypatch):
        from apps.jobs.pitch import gemini

        class RespostaVazia:
            output_text = "  "
            status = "blocked"
            usage = None

        monkeypatch.setattr(gemini, "_cliente", lambda: cliente_falso(lambda **k: RespostaVazia()))

        with pytest.raises(gemini.GeminiSemTextoError, match="blocked"):
            gemini.gerar_texto("instrucao", "entrada", modelo="modelo-x")


@pytest.mark.django_db
class TestApiDePitch:
    """POST /jobs/{id}/pitch/, que e o botao do Board."""

    @pytest.fixture
    def gerador_falso(self, monkeypatch):
        """Troca a chamada ao Gemini por texto fixo: teste nao toca a rede."""
        chamadas = []

        def fake(instrucao, entrada, modelo=""):
            chamadas.append({"entrada": entrada, "modelo": modelo})
            return TextoGerado("Apresentacao gerada para a vaga.", "modelo-x", 3000, 150, 0)

        monkeypatch.setattr(service, "gerar_texto", fake)
        monkeypatch.setattr(service, "carregar_dossie", lambda **kwargs: DOSSIE_VALIDO)
        return chamadas

    def test_gera_e_guarda(self, api, make_job, gerador_falso):
        job = make_job("Dev Python Junior")

        response = api.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json")

        assert response.status_code == 201
        corpo = response.json()
        assert corpo["texto"] == "Apresentacao gerada para a vaga."
        assert corpo["caracteres"] == len("Apresentacao gerada para a vaga.")
        assert corpo["tokens_entrada"] == 3000
        assert job.pitches.count() == 1

    def test_gerar_de_novo_substitui_a_anterior(self, api, make_job, gerador_falso):
        job = make_job()
        primeira = api.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json").json()
        segunda = api.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json").json()

        versoes = api.get(f"/api/v1/jobs/{job.id}/pitch/").json()

        assert len(versoes) == 1
        assert versoes[0]["id"] == segunda["id"]
        assert not job.pitches.filter(pk=primeira["id"]).exists()

    def test_falha_ao_gerar_nao_apaga_o_texto_que_ja_existia(
        self, api, make_job, gerador_falso, monkeypatch
    ):
        # O apagar so pode acontecer depois de a geracao dar certo: senao uma
        # falha do Gemini deixaria a vaga sem texto nenhum.
        job = make_job()
        antiga = api.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json").json()

        def explode(*args, **kwargs):
            raise GeminiIndisponivelError("Gemini fora do ar.")

        monkeypatch.setattr(service, "gerar_texto", explode)

        assert api.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json").status_code >= 400

        versoes = api.get(f"/api/v1/jobs/{job.id}/pitch/").json()
        assert [versao["id"] for versao in versoes] == [antiga["id"]]

    def test_repassa_tamanho_e_instrucao(self, api, make_job, gerador_falso):
        job = make_job()

        corpo = api.post(
            f"/api/v1/jobs/{job.id}/pitch/",
            {"max_chars": 600, "instrucao": "puxa o lado de dados"},
            format="json",
        ).json()

        assert corpo["max_chars"] == 600
        assert corpo["instrucao"] == "puxa o lado de dados"
        assert "no maximo 600 caracteres" in gerador_falso[0]["entrada"]
        assert "puxa o lado de dados" in gerador_falso[0]["entrada"]

    def test_tamanho_fora_da_faixa_e_recusado(self, api, make_job, gerador_falso):
        job = make_job()

        assert api.post(
            f"/api/v1/jobs/{job.id}/pitch/", {"max_chars": 50}, format="json"
        ).status_code == 400
        assert job.pitches.count() == 0

    def test_recusa_geracao_concorrente(self, api, make_job, gerador_falso):
        from apps.jobs import views

        job = make_job()
        views._pitch_lock.acquire()
        try:
            response = api.post(f"/api/v1/jobs/{job.id}/pitch/", {}, format="json")
        finally:
            views._pitch_lock.release()

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PITCH_IN_PROGRESS"

    def test_falha_do_gemini_vira_503_com_explicacao(self, api, make_job, monkeypatch):
        def explode(*args, **kwargs):
            raise GeminiIndisponivelError("GEMINI_API_KEY vazia.")

        monkeypatch.setattr(service, "carregar_dossie", lambda **kwargs: DOSSIE_VALIDO)
        monkeypatch.setattr(service, "gerar_texto", explode)

        response = api.post(f"/api/v1/jobs/{make_job().id}/pitch/", {}, format="json")

        assert response.status_code == 503
        assert "GEMINI_API_KEY" in response.json()["error"]["message"]

    def test_a_trava_e_liberada_quando_a_geracao_estoura(self, api, make_job, monkeypatch):
        from apps.jobs import views

        monkeypatch.setattr(service, "carregar_dossie", lambda **kwargs: DOSSIE_VALIDO)
        monkeypatch.setattr(
            service, "gerar_texto", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        )

        api.post(f"/api/v1/jobs/{make_job().id}/pitch/", {}, format="json")

        assert views._pitch_lock.acquire(blocking=False)
        views._pitch_lock.release()
