"""Fonte: portal publico de vagas da Gupy.

Endpoint confirmado em 02/09/2026:

    GET https://employability-portal.gupy.io/api/v1/jobs?jobName=<termo>&offset=0&limit=100

Devolve {"data": [...], "pagination": {"total": N, "limit": L, "offset": O}}. O
parametro de busca e `jobName` (usar `name` devolve 400).

O que a API aceita, medido:

- `limit` vai ate 100; 200 devolve 400.
- `offset` pagina de verdade, sem sobreposicao entre paginas.
- `pagination.total` NAO e confiavel: com `limit` de 40 ou mais ele volta
  cravado em 100, mesmo quando existem 650 resultados (medido em "desenvolvedor":
  `limit=1` diz 650, `limit=100` diz 100). Parar por esse campo custava 550 vagas
  de um termo so. A parada correta e pela pagina incompleta.
- nao existe parametro de ordenacao nem de data: `sort`, `orderBy` e
  `publishedDate` devolvem 400. Recencia se resolve do nosso lado, pelo
  `--max-age` da coleta.
- `jobName` e opcional: sem ele a API devolve o portal inteiro (82.536 vagas em
  03/09/2026). Nao serve: sao 826 requisicoes para trazer o RH e a logistica do
  Brasil junto. A busca por termo continua sendo o filtro.
- filtros que existem mas so estreitam, nunca ampliam: `workplaceType=remote` e
  `isRemoteWork=true` (~360 vagas). `jobType`, `careerPageId`, `publishedSince`,
  `skill` e `label` devolvem 400; `city`, `state` e `country` respondem 200 com
  zero resultado, ou seja, nao funcionam.

Se um dia parar de responder, o endereco fica em GUPY_API no .env. Para achar o
novo: abra portal.gupy.io, faca uma busca, DevTools na aba Network, filtro
Fetch/XHR, e veja qual requisicao devolve o JSON com a lista de vagas.
"""

import html
import logging
import re
import time
from collections.abc import Iterator
from datetime import datetime

import httpx
from django.conf import settings

from .base import RawJob, Source

logger = logging.getLogger(__name__)

# Como escolher termo, medido em 03/09/2026 varrendo a lista inteira e contando
# URL unica (o script vive no historico; o resumo e este):
#
# - **variante de grafia nao rende nada.** "back end", "front end", "full-stack",
#   "desenvolvedora" e "engenharia de software" trouxeram ZERO vaga que os
#   termos ja listados nao tinham. A busca nao e sensivel ao hifen.
# - **termo generico de nivel envenena a fila.** "estagio" (1.760), "junior"
#   (1.004) e "trainee" (226) sao 80% a 92% de vaga fora de TI: estagio em
#   logistica, direito, RH. Pior, o score nao protege: "estagio" e "junior"
#   valem 10 pontos no perfil, entao "Estagio em Logistica" entra com 47 e senta
#   ACIMA de vaga de dev de verdade. Filtrar dominio e trabalho do termo, nao do
#   score.
# - **cuidado com o casamento por prefixo.** "programacao" parece obvio e e
#   armadilha: casa com "Programa de Estagio" e trouxe 100 vagas de engenharia
#   civil da MRV. Mesma coisa com "go" (744) e "swift" (198, o SWIFT bancario).
# - **termo redundante nao existe de graca**, cada um custa no minimo uma
#   requisicao, mas termo com poucas exclusivas custa pouco e protege contra o
#   mes em que o mercado muda de vocabulario. Por isso "javascript" e
#   "typescript", hoje com zero exclusivas, ficam.
DEFAULT_SEARCHES = [
    # Cargo generico: e onde esta quase todo o volume.
    "desenvolvedor",
    "programador",
    "developer",
    "analista de sistemas",
    "analista de desenvolvimento",
    "engenheiro de software",
    "desenvolvimento de software",
    "software",
    "sistemas",
    # Camada.
    "backend",
    "back-end",
    "frontend",
    "front-end",
    "fullstack",
    "full stack",
    # Stack.
    "python",
    "java",
    "javascript",
    "typescript",
    "node",
    "react",
    "sql",
    "banco de dados",
    # Dados, que e vizinho o bastante para valer.
    "dados",
    "analista de dados",
    "engenheiro de dados",
    "cientista de dados",
    "inteligencia artificial",
    # Plataforma e operacao: nao e escrever produto, mas e a mesma area e a
    # vaga costuma pedir a mesma stack.
    "cloud",
    "devops",
    "seguranca da informacao",
    "analista de suporte",
    # Qualidade.
    "qa",
    "analista de testes",
    # Porta de entrada. Aqui o termo precisa dizer a area junto: "estagio"
    # sozinho traz o estagio do Brasil inteiro.
    "estagio desenvolvimento",
    "estagio tecnologia",
    "estagio ti",
    "estagio dados",
]


# Teto da API. Pedir mais devolve 400.
PAGE_SIZE = 100

# Trava de seguranca: 20 paginas de 100 e mais que o dobro do maior termo
# medido ("desenvolvedor", 662). Existe para um `total` errado da API nao
# transformar a coleta em laco infinito.
MAX_PAGES_PER_SEARCH = 20

# Uma pagina que falha nao pode levar o resto do termo junto: "desenvolvedor"
# sao 7 paginas, e desistir na terceira custa 400 vagas. Tres tentativas com
# espera crescente cobrem o engasgo passageiro sem prender a coleta.
TENTATIVAS_POR_PAGINA = 3
ESPERA_ENTRE_TENTATIVAS = (1.0, 3.0)

TAG_RE = re.compile(r"<[^>]+>")
SPACES_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """A descricao vem como HTML com entidades.

    Vira texto plano para o score nao pontuar por marcacao e para a leitura
    no admin nao doer.
    """
    if not text:
        return ""
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return SPACES_RE.sub(" ", text).strip()


class GupySource(Source):
    key = "gupy"
    label = "Gupy"

    def __init__(
        self,
        searches: list[str] | None = None,
        per_page: int = PAGE_SIZE,
        max_pages: int = MAX_PAGES_PER_SEARCH,
    ):
        self.api = settings.GUPY_API.rstrip("/")
        self.searches = searches or DEFAULT_SEARCHES
        self.per_page = min(per_page, PAGE_SIZE)
        self.max_pages = max_pages
        # Termos que a API nao entregou nesta varredura. O service le no fim
        # para a coleta nao registrar sucesso silencioso.
        self.falhas: list[str] = []

    def client(self):
        client = super().client()
        # O portal exige cara de navegador; sem isso a API responde 403.
        client.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
                "Origin": "https://portal.gupy.io",
                "Referer": "https://portal.gupy.io/",
            }
        )
        return client

    def fetch(self) -> Iterator[RawJob]:
        # Zerado a cada varredura: `falhas` descreve esta coleta, nao a fonte.
        self.falhas = []
        with self.client() as client:
            for term in self.searches:
                yield from self.fetch_term(client, term)

    def buscar_pagina(self, client: httpx.Client, term: str, offset: int) -> dict | None:
        """Uma pagina, com nova tentativa quando a resposta nao vem.

        Devolve `None` quando desistiu. Quem chama decide o que fazer com isso;
        aqui so garante que um engasgo de rede nao passe por fim de resultado.
        """
        for tentativa in range(TENTATIVAS_POR_PAGINA):
            try:
                response = client.get(
                    self.api,
                    params={"jobName": term, "offset": offset, "limit": self.per_page},
                )
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                ultima = tentativa == TENTATIVAS_POR_PAGINA - 1
                logger.warning(
                    "gupy '%s' offset %s, tentativa %s de %s: %s%s",
                    term,
                    offset,
                    tentativa + 1,
                    TENTATIVAS_POR_PAGINA,
                    exc,
                    "" if ultima else " (tentando de novo)",
                )
                if ultima:
                    self.falhas.append(f"{term} (offset {offset}): {exc}")
                    return None
                time.sleep(ESPERA_ENTRE_TENTATIVAS[tentativa])
        return None

    def fetch_term(self, client: httpx.Client, term: str) -> Iterator[RawJob]:
        """Varre um termo inteiro, pagina a pagina.

        Para na primeira pagina incompleta (menos itens que o `limit` pedido),
        que e o unico sinal de fim confiavel aqui: o `pagination.total` mente
        com `limit` alto. Pagina vazia e a trava de `max_pages` sao as saidas
        de seguranca.

        Um termo que falha nao derruba os outros 37, mas fica anotado em
        `falhas`: coleta que trouxe menos vaga porque a API caiu tem que
        aparecer na tela de Coletas, e nao passar por dia fraco.
        """
        offset = 0

        for _ in range(self.max_pages):
            payload = self.buscar_pagina(client, term, offset)
            if payload is None:
                return

            items = self.extract_list(payload)
            if not items:
                return

            for item in items:
                job = self.parse(item)
                if job:
                    yield job

            # Pagina incompleta e a ultima.
            if len(items) < self.per_page:
                return

            offset += len(items)

    @staticmethod
    def extract_list(payload) -> list:
        """A API ja mudou o formato do envelope antes. Aceita as variacoes."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "results", "jobs", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def parse(self, item: dict) -> RawJob | None:
        if not isinstance(item, dict):
            return None

        title = item.get("name") or item.get("title") or ""
        url = item.get("jobUrl") or item.get("careerPageUrl") or item.get("url") or ""
        if not title or not url:
            return None

        company = ""
        for key in ("careerPageName", "companyName", "company"):
            value = item.get(key)
            if isinstance(value, dict):
                value = value.get("name")
            if value:
                company = str(value)
                break

        location = ", ".join(
            str(part)
            for part in (item.get("city"), item.get("state"), item.get("country"))
            if part
        )
        if item.get("isRemoteWork"):
            location = f"Remoto{', ' + location if location else ''}"

        published_at = None
        raw_date = item.get("publishedDate") or item.get("createdAt")
        if raw_date:
            try:
                published_at = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            except ValueError:
                published_at = None

        skills = item.get("skills") or []
        if isinstance(skills, list):
            skills = " ".join(
                skill.get("name", "") if isinstance(skill, dict) else str(skill)
                for skill in skills
            )

        context = " ".join(str(item.get(key) or "") for key in ("workplaceType", "type"))
        description = strip_html(item.get("description", ""))

        return RawJob(
            title=title,
            company=company,
            url=url,
            location=location,
            description=f"{context} {skills}\n\n{description}".strip(),
            source_id=str(item.get("id") or ""),
            published_at=published_at,
        )
