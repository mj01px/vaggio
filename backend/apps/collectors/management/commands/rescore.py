"""Recalcula score, tags, senioridade e modalidade das vagas ja salvas.

Rode sempre que mexer no PERFIL em apps/jobs/scoring/profile.py:

    python manage.py rescore
    python manage.py rescore --top 20
"""

import sys

from django.core.management.base import BaseCommand

from apps.jobs.models import Job
from apps.jobs.services import rescore_all


class Command(BaseCommand):
    help = "Repontua as vagas existentes com as regras atuais de scoring."

    def add_arguments(self, parser):
        parser.add_argument(
            "--top", type=int, default=15, help="Quantas vagas do topo listar ao fim."
        )

    def handle(self, *args, **options):
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")

        total, changed = rescore_all()
        self.stdout.write(self.style.SUCCESS(f"{total} vagas repontuadas, {changed} mudaram."))

        top = options["top"]
        self.stdout.write(f"\nTop {top}:")
        for job in Job.objects.filter(discarded=False).order_by("-score")[:top]:
            company = f" @ {job.company[:28]}" if job.company else ""
            self.stdout.write(f"  [{job.score:>4}] {job.title[:66]}{company}")
