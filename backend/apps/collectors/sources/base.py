"""Contrato das fontes.

Uma fonte recebe configuracao, vai na origem e devolve `RawJob`. Ela nao fala
com o banco e nao pontua nada: quem faz isso e o service de coleta. E o que
mantem cada fonte pequena e testavel sem Django.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime

import httpx

TIMEOUT = httpx.Timeout(20.0, connect=10.0)
USER_AGENT = "vaggio/1.0 (uso pessoal; busca de emprego)"


@dataclass(slots=True)
class RawJob:
    """Vaga como a fonte devolveu, antes de pontuar e antes de tocar no banco."""

    title: str
    url: str
    company: str = ""
    location: str = ""
    description: str = ""
    source_id: str = ""
    published_at: datetime | None = None
    extras: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        """Campos do modelo Job, ja aparados no tamanho de cada coluna."""
        return {
            "title": self.title.strip()[:300],
            "url": self.url.strip()[:1000],
            "company": self.company.strip()[:200],
            "location": self.location.strip()[:200],
            "description": self.description.strip(),
            "source_id": str(self.source_id)[:200],
            "published_at": self.published_at,
        }


class Source:
    """Subclasse isso, defina `key` e `label`, e implemente `fetch`."""

    key: str = ""
    label: str = ""

    def fetch(self) -> Iterator[RawJob]:
        raise NotImplementedError

    def client(self) -> httpx.Client:
        return httpx.Client(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
