"""Roda as fontes, pontua o resultado e grava so o que e novo.

    python manage.py collect
    python manage.py collect --source github
    python manage.py collect --max-age 7        # so o que saiu na ultima semana
    python manage.py collect --max-age 0        # sem corte de idade
    python manage.py collect --min-score 20
    python manage.py collect --dry-run
"""

import sys

from django.core.management.base import BaseCommand

from apps.collectors.services import DEFAULT_MAX_AGE_DAYS, collect_all
from apps.collectors.sources import SOURCES


class Command(BaseCommand):
    help = "Coleta vagas das fontes configuradas, pontua e salva as novas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=sorted(SOURCES),
            help="Roda so uma fonte. Sem isso, roda todas.",
        )
        parser.add_argument(
            "--max-age",
            type=int,
            default=DEFAULT_MAX_AGE_DAYS,
            metavar="DIAS",
            help=(
                f"Ignora vaga publicada ha mais de N dias (padrao: {DEFAULT_MAX_AGE_DAYS}). "
                "Use 0 para nao cortar por idade."
            ),
        )
        parser.add_argument(
            "--min-score",
            type=int,
            default=None,
            help=(
                "Descarta na entrada o que pontuar abaixo disso. "
                "Sem isso nada e cortado por score: a fila filtra e ordena depois."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria salvo, sem gravar nada.",
        )

    def handle(self, *args, **options):
        # O console do Windows e cp1252 e estoura em titulo com emoji, o que
        # abortava a coleta no meio. Forca UTF-8 com replace no que nao couber.
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")

        sources = [options["source"]] if options["source"] else sorted(SOURCES)
        dry_run = options["dry_run"]
        max_age = options["max_age"] or None

        janela = f"ultimos {max_age} dias" if max_age else "sem corte de idade"
        self.stdout.write(f"Coletando {', '.join(sources)} ({janela}).")

        results = collect_all(
            sources,
            min_score=options["min_score"],
            max_age_days=max_age,
            dry_run=dry_run,
            on_source=lambda key: self.stdout.write(self.style.HTTP_INFO(f"\n> {key}")),
            on_new=self._print_job,
        )

        self.stdout.write("")
        for result in results:
            self.stdout.write(
                f"  {result.source}: {result.found} vistas, {result.new} novas "
                f"({result.duplicate} repetidas, {result.old} antigas, "
                f"{result.low_score} abaixo do score)"
            )
            if result.error:
                self.stderr.write(self.style.ERROR(f"  erro em {result.source}: {result.error}"))

        total = sum(result.new for result in results)
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] {total} vagas novas seriam salvas."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{total} vagas novas salvas."))
            self.stdout.write("Abra http://localhost:5173/radar para triar.")

    def _print_job(self, payload: dict) -> None:
        score = payload["score"]
        title = payload["title"][:70]
        line = f"  + [{score:>4}] {title}"
        if payload["company"]:
            line += f"  @ {payload['company'][:30]}"
        self.stdout.write(line)
