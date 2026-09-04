"""Registro das fontes de vaga.

Cada fonte e uma subclasse de Source: recebe configuracao, vai na origem e
devolve RawJob. Nenhuma fala com o banco nem pontua nada, entao da para testar
sem Django. Quem grava e pontua e o service de coleta.

Para adicionar uma fonte: crie o modulo, subclasse Source, e registre em SOURCES.
"""

from .base import RawJob, Source
from .github_issues import GithubIssuesSource
from .gupy import GupySource

SOURCES: dict[str, type[Source]] = {
    GithubIssuesSource.key: GithubIssuesSource,
    GupySource.key: GupySource,
}

__all__ = ["SOURCES", "GithubIssuesSource", "GupySource", "RawJob", "Source"]
