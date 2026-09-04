"""Scoring: funcao pura, sem banco e sem HTTP."""

from apps.jobs.scoring import classify, contains, normalize
from apps.jobs.scoring.engine import detect_seniority, detect_work_mode, score_text, years_penalty


class TestNormalize:
    def test_tira_acento_e_caixa(self):
        assert normalize("Estágio em Análise") == "estagio em analise"

    def test_colapsa_espaco(self):
        assert normalize("java    junior\n\nremoto") == "java junior remoto"

    def test_vazio(self):
        assert normalize("") == ""


class TestContains:
    def test_casa_palavra_inteira(self):
        assert contains("python jr remoto", "jr")

    def test_nao_casa_dentro_de_outra_palavra(self):
        # A armadilha que justifica o limite de palavra: "sr" nao pode casar
        # dentro de "srv", nem "jr" dentro de "jrxyz".
        assert not contains("servidor srv linux", "sr")
        assert not contains("vaga jrxyz", "jr")

    def test_casa_termo_composto(self):
        assert contains("vaga com home office", "home office")


class TestScoreText:
    def test_titulo_vale_dobro(self):
        no_titulo, _ = score_text("python", "")
        no_corpo, _ = score_text("", "python")
        assert no_titulo == no_corpo * 2

    def test_um_acerto_por_grupo(self):
        # python, django e sql sao todos do grupo "core": tres acertos no
        # titulo continuam valendo um acerto so.
        um, _ = score_text("python", "")
        tres, _ = score_text("python django sql", "")
        assert um == tres

    def test_tag_so_para_peso_positivo(self):
        _, tags = score_text("desenvolvedor php senior", "")
        assert tags == []

    def test_penalidade_derruba_o_score(self):
        positivo, _ = score_text("python junior", "")
        com_php, _ = score_text("python junior php", "")
        assert com_php < positivo


class TestYearsPenalty:
    def test_sem_exigencia(self):
        assert years_penalty("vaga para iniciante") == 0

    def test_dois_anos_nao_penaliza(self):
        assert years_penalty("2 anos de experiencia") == 0

    def test_tres_anos(self):
        assert years_penalty("3 anos de experiencia") == -12

    def test_cinco_anos_ou_mais(self):
        assert years_penalty("7 anos de atuacao") == -25

    def test_acento_nao_escapa_da_penalidade(self):
        # Vaga de verdade escreve com acento; sem normalizar, "vivencia" nunca
        # casava com "vivência" e a exigencia passava batida.
        assert years_penalty("5 anos de vivência na área") == -25
        assert years_penalty("3 anos de experiência") == -12


class TestDetectors:
    def test_estagio_vem_antes_de_junior(self):
        assert detect_seniority("estagio em desenvolvimento junior") == "internship"

    def test_senior_vem_antes_de_pleno(self):
        # "pl" e generico demais para ganhar de um titulo que ja disse senior.
        assert detect_seniority("desenvolvedor senior pl") == "senior"

    def test_sem_sinal(self):
        assert detect_seniority("desenvolvedor de software") == "unknown"

    def test_modalidade(self):
        assert detect_work_mode("vaga remoto") == "remote"
        assert detect_work_mode("modelo hibrido") == "hybrid"
        assert detect_work_mode("trabalho presencial") == "onsite"
        assert detect_work_mode("sem informacao") == "unknown"


class TestClassify:
    def test_vaga_alvo_pontua_alto(self):
        result = classify(
            "Desenvolvedor Python Junior - Fintech",
            "Vaga remota com Django e PostgreSQL.",
        )
        assert result.score == 64
        assert result.tags == ["python", "fintech", "junior"]
        assert result.seniority == "junior"

    def test_vaga_fora_do_perfil_fica_negativa(self):
        result = classify("Analista PHP Senior", "Laravel, 5 anos de experiencia em atuacao")
        assert result.score == -115
        assert result.seniority == "senior"

    def test_as_dict_tem_os_campos_do_modelo(self):
        assert set(classify("python").as_dict()) == {"score", "tags", "seniority", "work_mode"}
