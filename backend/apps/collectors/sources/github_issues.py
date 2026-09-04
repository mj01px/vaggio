"""Fonte: repositorios de vagas da comunidade brasileira no GitHub.

Cada vaga e uma issue aberta. A API e publica e documentada, o dado vem
estruturado e nao ha risco de bloqueio de conta. Sem token o limite e 60
requisicoes/hora; com um token pessoal (so escopo publico) sobe para 5000.
Defina GITHUB_TOKEN no .env para usar o limite maior.
"""

import logging
import re
from collections.abc import Iterator
from datetime import datetime

from django.conf import settings

from .base import RawJob, Source

logger = logging.getLogger(__name__)

# Repositorios medidos em 02/09/2026: existem, nao estao arquivados e tem
# issue aberta. O numero e a data sao do que a API devolveu naquele dia.
REPOS = [
    "backend-br/vagas",    # ~49 abertas, ativo (ultimo push 31/08/2026)
    "soujava/vagas-java",  # ~43 abertas, ativo (ultimo push 28/08/2026)
    "frontendbr/vagas",    # ~31 abertas, parado desde 03/2026
    "react-brasil/vagas",  # ~10 abertas, parado desde 01/2024
]

# Os dois ultimos rendem pouco e boa parte do que trazem e vaga velha, mas
# custam uma requisicao cada e o corte de idade da coleta limpa o resto.
#
# Existem e ficaram de fora por estarem fora do alvo ou parados ha anos:
# "phpdevbr/vagas", "androiddevbr/vagas", "vuejs-br/vagas", "qa-brasil/vagas",
# "uxbrasil/vagas", "CangaceirosDevels/vagas_de_emprego".
# "lerrua/remote-jobs-brazil" esta arquivado: nao entra.

API = "https://api.github.com/repos/{repo}/issues"

# Issues fixadas de regras/moderacao nao sao vagas.
NOT_A_JOB_RE = re.compile(
    r"(regras?\b|rules\b|leia\b|read me|como (postar|divulgar)|template|aten[çc][ãa]o)",
    re.IGNORECASE,
)

# O corpo costuma seguir um template com uma linha de empresa. O `[*_`\s]*`
# depois de "empresa" cobre as duas formas que aparecem de verdade,
# "**Empresa:** Acme" e "**Empresa**: Acme", que so diferem em onde o negrito
# fecha em relacao aos dois pontos.
COMPANY_RE = re.compile(
    r"^\s*(?:[#*\->\s]*)(?:nome\s+da\s+)?empresa[*_`\s]*[:\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


class GithubIssuesSource(Source):
    key = "github"
    label = "GitHub Issues"

    def __init__(self, repos: list[str] | None = None, per_repo: int = 100, pages: int = 3):
        # 100 e o teto da API do GitHub por pagina. Tres paginas cobrem 300
        # issues por repo, bem acima da maior fila medida (49).
        self.repos = repos or REPOS
        self.per_repo = min(per_repo, 100)
        self.pages = pages

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json"}
        token = (settings.GITHUB_TOKEN or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def fetch(self) -> Iterator[RawJob]:
        with self.client() as client:
            for repo in self.repos:
                for page in range(1, self.pages + 1):
                    try:
                        response = client.get(
                            API.format(repo=repo),
                            params={
                                "state": "open",
                                "sort": "created",
                                "direction": "desc",
                                "per_page": self.per_repo,
                                "page": page,
                            },
                            headers=self._headers(),
                        )
                        response.raise_for_status()
                        issues = response.json()
                    except Exception as exc:
                        # Uma fonte fora do ar nao derruba a coleta inteira.
                        logger.warning("github %s pagina %s: %s", repo, page, exc)
                        break

                    if not issues:
                        break

                    for issue in issues:
                        if "pull_request" in issue:
                            continue
                        job = self.parse(issue, repo)
                        if job:
                            yield job

                    # Pagina incompleta e a ultima: nao gasta requisicao (e
                    # cota, que sem token e de 60/hora) pedindo pagina vazia.
                    if len(issues) < self.per_repo:
                        break

    def parse(self, issue: dict, repo: str) -> RawJob | None:
        title = (issue.get("title") or "").strip()
        if not title or NOT_A_JOB_RE.search(title):
            return None

        body = issue.get("body") or ""
        labels = [label.get("name", "") for label in issue.get("labels", [])]

        published_at = None
        if issue.get("created_at"):
            published_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))

        # A empresa sai do corpo, nunca do titulo. O padrao de titulo nesses
        # repositorios e livre demais ("[CLT] Empresa - Cargo", "Cargo | Empresa",
        # "Cargo na Empresa"), e tentar separar corrompia o titulo e o score.
        return RawJob(
            title=title,
            company=self.company_from_body(body),
            url=issue.get("html_url", ""),
            description=f"{body}\n\nLabels: {', '.join(labels)}\nRepo: {repo}",
            source_id=f"{repo}#{issue.get('number')}",
            published_at=published_at,
            extras={"labels": labels, "repo": repo},
        )

    @staticmethod
    def company_from_body(body: str) -> str:
        """Aproveita a linha de empresa quando o corpo segue o template.

        Quando nao segue, devolve vazio em vez de inventar.
        """
        match = COMPANY_RE.search(body)
        if not match:
            return ""
        value = re.sub(r"[*_`#\[\]]", "", match.group(1)).strip()
        return value[:200] if 1 < len(value) < 120 else ""
