"""Orquestracao da coleta: roda uma fonte, pontua e grava so o que e novo.

A logica vive aqui, e nao no comando, para o teste rodar sem console e para um
disparo pela API (ou por um agendador) reusar exatamente o mesmo caminho.

Dois cortes acontecem na entrada, nessa ordem:

- **idade** (`max_age_days`), que e o corte principal. Vaga de meses atras nao
  vale triagem, e e o que enche a fila de "Banco de Talentos" eterno.
- **score** (`min_score`), desligado por padrao. O score serve para ordenar a
  fila, nao para decidir o que existe: a tela filtra por score quando voce
  quiser, e o `rescore` pode mudar de ideia depois. Cortar aqui joga fora um
  dado que nao volta sem recoletar.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from apps.jobs.models import Job
from apps.jobs.scoring import classify

from .models import CollectionRun
from .sources import SOURCES

logger = logging.getLogger(__name__)

# Um mes cobre de sobra o ciclo de uma vaga viva. A Gupy praticamente so
# devolve vaga desse periodo; o corte pega mesmo e o "Banco de Talentos"
# eterno e a issue de 2022 que ninguem fechou no GitHub.
#
# Mora aqui, e nao no comando, porque a API dispara a mesma coleta pelo botao
# do Radar e os dois precisam concordar sobre o que e "vaga velha".
DEFAULT_MAX_AGE_DAYS = 30


@dataclass
class CollectionResult:
    source: str
    found: int = 0
    new: int = 0
    old: int = 0
    low_score: int = 0
    duplicate: int = 0
    error: str = ""


def is_older_than(published_at: datetime | None, max_age_days: int) -> bool:
    """Vaga publicada ha mais de `max_age_days`.

    Sem data nao da para saber, e sumir com o que nao se sabe e pior do que
    deixar passar: o `published_at` fica nulo no cadastro manual e em fonte que
    nao informa. Nesse caso, nunca e velha.
    """
    if published_at is None:
        return False
    if timezone.is_naive(published_at):
        published_at = timezone.make_aware(published_at)
    return published_at < timezone.now() - timedelta(days=max_age_days)


def collect_source(
    source_key: str,
    *,
    min_score: int | None = None,
    max_age_days: int | None = None,
    dry_run: bool = False,
    on_new: Callable[[dict], None] | None = None,
) -> CollectionResult:
    """Roda uma fonte. `on_new` recebe cada vaga nova, para o comando imprimir."""
    source = SOURCES[source_key]()
    result = CollectionResult(source=source_key)
    run = None if dry_run else CollectionRun.objects.create(source=source_key)

    # Uma consulta so para as chaves ja conhecidas, em vez de um exists() por
    # vaga. Tambem e o que impede duas fontes de gravarem a mesma URL no mesmo
    # ciclo, antes de o unique do banco reclamar.
    seen: set[str] = set(Job.objects.values_list("key", flat=True))

    try:
        for raw in source.fetch():
            result.found += 1
            data = raw.as_dict()

            if max_age_days is not None and is_older_than(data["published_at"], max_age_days):
                result.old += 1
                continue

            # A chave antes do score: deduplicar e mais barato que classificar,
            # e com dezenas de termos de busca a maioria do que chega ja e
            # repetida: na Gupy sao ~5.900 respostas para ~3.300 vagas unicas.
            key = Job.build_key(data["url"], data["title"], data["company"])
            if key in seen:
                result.duplicate += 1
                continue

            classification = classify(
                data["title"], data["description"], data["company"], data["location"]
            )
            if min_score is not None and classification.score < min_score:
                result.low_score += 1
                continue

            seen.add(key)
            result.new += 1

            payload = {**data, **classification.as_dict(), "source": source_key, "key": key}
            if not dry_run:
                Job.objects.create(**payload)
            if on_new:
                on_new(payload)

    except Exception as exc:
        logger.exception("erro coletando %s", source_key)
        result.error = str(exc)

    # Falha parcial: a fonte seguiu em frente depois de uma busca nao responder,
    # entao nao houve excecao aqui. Sem isto, uma coleta que perdeu 400 vagas
    # por queda da API era gravada como rodada normal e passava por dia fraco.
    parciais = getattr(source, "falhas", None)
    if parciais and not result.error:
        result.error = f"{len(parciais)} busca(s) sem resposta: " + "; ".join(parciais[:3])

    if run:
        run.found_count = result.found
        run.new_count = result.new
        run.error = result.error
        run.finished_at = timezone.now()
        run.save(update_fields=["found_count", "new_count", "error", "finished_at"])

    return result


def collect_all(
    source_keys: list[str] | None = None,
    *,
    min_score: int | None = None,
    max_age_days: int | None = None,
    dry_run: bool = False,
    on_source: Callable[[str], None] | None = None,
    on_new: Callable[[dict], None] | None = None,
) -> list[CollectionResult]:
    results = []
    for key in source_keys or sorted(SOURCES):
        if on_source:
            on_source(key)
        results.append(
            collect_source(
                key,
                min_score=min_score,
                max_age_days=max_age_days,
                dry_run=dry_run,
                on_new=on_new,
            )
        )
    return results
