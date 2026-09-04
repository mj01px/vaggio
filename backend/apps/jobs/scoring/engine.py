"""Aplica o PERFIL a uma vaga e devolve score, tags, senioridade e modalidade.

Funcao pura: nao importa modelo, nao toca no banco, e testavel sem Django.
"""

from dataclasses import dataclass, field

from .profile import (
    PROFILE,
    SENIORITY_TERMS,
    WORK_MODE_TERMS,
    YEARS_PENALTIES,
    YEARS_RE,
)
from .text import contains, normalize


@dataclass(frozen=True)
class Classification:
    """Resultado da pontuacao, no formato que o modelo Job consome."""

    score: int = 0
    tags: list[str] = field(default_factory=list)
    seniority: str = "unknown"
    work_mode: str = "unknown"

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "tags": self.tags,
            "seniority": self.seniority,
            "work_mode": self.work_mode,
        }


def score_text(title: str, body: str, profile: dict | None = None) -> tuple[int, list[str]]:
    """(score, tags) de um titulo e um corpo ja normalizados.

    O titulo pesa dobrado: e onde esta o sinal mais confiavel.

    `profile` permite pontuar pelos termos de outra pessoa. Continua funcao
    pura: quem sabe qual perfil usar e o chamador, nao este modulo.
    """
    score = 0
    tags: list[str] = []

    for group in (profile or PROFILE).values():
        weight = group["weight"]
        for term in group["terms"]:
            term_n = normalize(term)
            in_title = contains(title, term_n)
            if not (in_title or contains(body, term_n)):
                continue
            score += weight * 2 if in_title else weight
            if weight > 0 and term_n not in tags:
                tags.append(term_n)
            # Um acerto por grupo ja basta: evita inflar score por repeticao.
            break

    return score, tags


def years_penalty(text: str) -> int:
    """Penalidade pela exigencia de anos de experiencia, 0 quando nao ha.

    Normaliza antes de casar: sem isso "vivencia" nunca pega "vivência", que e
    como a palavra aparece em vaga escrita em portugues.
    """
    match = YEARS_RE.search(normalize(text))
    if not match:
        return 0
    years = int(match.group(1))
    for threshold, penalty in YEARS_PENALTIES:
        if years >= threshold:
            return penalty
    return 0


def detect_seniority(text: str) -> str:
    for level, terms in SENIORITY_TERMS:
        if any(contains(text, term) for term in terms):
            return level
    return "unknown"


def detect_work_mode(text: str) -> str:
    for mode, terms in WORK_MODE_TERMS:
        if any(contains(text, term) for term in terms):
            return mode
    return "unknown"


def classify(
    title: str,
    description: str = "",
    company: str = "",
    location: str = "",
    profile: dict | None = None,
) -> Classification:
    title_n = normalize(title)
    body_n = normalize(f"{description} {company} {location}")

    score, tags = score_text(title_n, body_n, profile)
    score += years_penalty(f"{title} {description}")

    full = f"{title_n} {normalize(description)}"
    return Classification(
        score=score,
        tags=tags,
        seniority=detect_seniority(full),
        work_mode=detect_work_mode(f"{full} {normalize(location)}"),
    )
