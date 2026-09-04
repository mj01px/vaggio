"""PERFIL: grupos de termos, pesos e penalidades.

Este e o unico arquivo a editar para mudar o criterio de "vaga boa pra mim".
Depois de mexer, rode `manage.py rescore` para reaplicar nas vagas ja salvas.

Regras que valem para todo grupo:

- os termos entram normalizados (minusculo e sem acento), porque e assim que o
  texto da vaga chega em `engine`;
- acerto no titulo vale o dobro do acerto no corpo;
- um acerto por grupo ja basta, para repeticao nao inflar o score.
"""

import re

WEIGHT_CORE = 12
WEIGHT_DOMAIN = 10
WEIGHT_LEVEL_MATCH = 10
WEIGHT_ADJACENT = 6
WEIGHT_ACTIVITY = 5
WEIGHT_WORK_MODE = 4

PENALTY_LEVEL_TOO_HIGH = -25
PENALTY_STACK_MISMATCH = -20
PENALTY_AREA_MISMATCH = -15
PENALTY_LEVEL_MID = -8

PROFILE: dict[str, dict] = {
    # Peso alto: e o nucleo do que voce quer fazer.
    "core": {
        "weight": WEIGHT_CORE,
        "terms": [
            "python", "django", "django rest", "drf", "postgres", "postgresql", "sql",
        ],
    },
    # Peso medio: stack adjacente que voce ja usa.
    "adjacent": {
        "weight": WEIGHT_ADJACENT,
        "terms": [
            "java", "spring", "spring boot", "api rest", "apis rest", "rest api",
            "backend", "back-end", "back end", "docker", "typescript", "react",
        ],
    },
    # O nicho onde sua experiencia bancaria vale ouro.
    # Cuidado ao editar: "banco" sozinho casa com "banco de dados" e infla o
    # score de qualquer vaga de back-end. Use termos que so existem no setor.
    "domain": {
        "weight": WEIGHT_DOMAIN,
        "terms": [
            "fintech", "bancario", "bancaria", "banco digital", "setor bancario",
            "instituicao financeira", "mercado financeiro", "financeiro", "financeira",
            "investimento", "investimentos", "credito", "pagamentos", "meios de pagamento",
            "seguradora", "seguros", "cooperativa de credito", "erp",
            "conciliacao", "antifraude", "prevencao a fraude", "compliance",
        ],
    },
    # O tipo de trabalho descrito na vaga que casa com o que voce faz.
    "activity": {
        "weight": WEIGHT_ACTIVITY,
        "terms": [
            "automacao", "automatizar", "analise de dados", "tratamento de dados",
            "integracao", "integracoes", "scripts", "etl", "relatorios",
        ],
    },
    # Nivel compativel.
    "level_match": {
        "weight": WEIGHT_LEVEL_MATCH,
        "terms": [
            "estagio", "estagiario", "junior", "jr", "trainee", "aprendiz",
            "primeiro emprego", "entry level", "programa de formacao",
        ],
    },
    # Formato.
    "work_mode": {
        "weight": WEIGHT_WORK_MODE,
        "terms": ["remoto", "home office", "hibrido", "anywhere"],
    },
    # Penalidade: nivel acima do seu alcance hoje.
    # "sr" e "pl" entram sem ponto de proposito: as vagas escrevem "Python SR",
    # "Analista PL". O casamento e por limite de palavra, entao nao pega "srv".
    "level_too_high": {
        "weight": PENALTY_LEVEL_TOO_HIGH,
        "terms": [
            "senior", "sr", "sr.", "especialista", "tech lead", "staff", "principal",
            "arquiteto", "coordenador", "gerente", "head of", "iii", "iv",
        ],
    },
    "level_mid": {
        "weight": PENALTY_LEVEL_MID,
        "terms": ["pleno", "pl", "pl.", "mid level", "mid-level"],
    },
    # Penalidade: stack que voce nao tem e nao vai aprender pra essa vaga.
    # Peso alto de proposito: e o que mais enche o radar de ruido.
    "stack_mismatch": {
        "weight": PENALTY_STACK_MISMATCH,
        "terms": [
            "php", "laravel", "wordpress", "delphi", "cobol", "abap", ".net", "c#",
            "ruby on rails", "flutter", "react native", "android nativo", "ios",
            "salesforce", "sap", "vba", "sharepoint",
        ],
    },
    # Penalidade: area diferente.
    "area_mismatch": {
        "weight": PENALTY_AREA_MISMATCH,
        "terms": [
            "designer", "ux/ui", "social media", "marketing", "vendas", "comercial",
            "suporte tecnico n1", "help desk", "infraestrutura de redes", "recrutamento",
        ],
    },
}

# Anos de experiencia exigidos: cada faixa acima de 2 anos derruba a vaga.
YEARS_RE = re.compile(r"(\d+)\s*\+?\s*anos?\s+de\s+(experi|atua|vivenc)", re.IGNORECASE)

# Do mais exigente para o menos: a primeira faixa que casar e a que vale.
YEARS_PENALTIES: list[tuple[int, int]] = [(5, -25), (3, -12)]

# Termos que classificam a senioridade da vaga, na ordem em que sao testados.
# Estagio antes de junior, e senior antes de pleno, porque "pl" e o mais
# generico dos quatro e casaria em titulo que ja disse o nivel real.
SENIORITY_TERMS: list[tuple[str, tuple[str, ...]]] = [
    ("internship", ("estagio", "estagiario", "estagiaria")),
    ("junior", ("junior", "jr", "trainee", "aprendiz")),
    ("senior", ("senior", "especialista", "tech lead", "staff")),
    ("mid", ("pleno", "pl")),
]

WORK_MODE_TERMS: list[tuple[str, tuple[str, ...]]] = [
    ("remote", ("remoto", "home office", "anywhere", "100% remoto")),
    ("hybrid", ("hibrido",)),
    ("onsite", ("presencial",)),
]
