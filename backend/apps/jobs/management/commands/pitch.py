"""Gera o "Apresente-se" da Gupy para uma vaga, e imprime para voce revisar.

    python manage.py pitch 64
    python manage.py pitch 64 --max-chars 800
    python manage.py pitch 64 --instrucao "puxa mais o lado de dados"
    python manage.py pitch            # lista as vagas do topo da fila

Nada e gravado: voce le, ajusta e cola na Gupy.
"""

import sys
import textwrap

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Perfil
from apps.jobs.models import Job
from apps.jobs.pitch import (
    DossieAusenteError,
    DossieVazioError,
    GeminiIndisponivelError,
    GeminiSemTextoError,
    gerar_apresentacao,
)
from apps.jobs.pitch.service import MAX_CHARS_PADRAO


class Command(BaseCommand):
    help = 'Gera o texto de "Apresente-se" para uma vaga, usando o Gemini.'

    def add_arguments(self, parser):
        parser.add_argument(
            "job_id",
            nargs="?",
            type=int,
            help="Id da vaga. Sem isso, lista as vagas do topo da fila.",
        )
        parser.add_argument(
            "--max-chars",
            type=int,
            default=MAX_CHARS_PADRAO,
            help=f"Tamanho alvo do texto (padrao: {MAX_CHARS_PADRAO}).",
        )
        parser.add_argument(
            "--instrucao",
            default="",
            help='Ajuste para esta versao, ex: "mais curto" ou "puxa o lado de dados".',
        )
        parser.add_argument("--modelo", default="", help="Sobrescreve o GEMINI_MODEL do .env.")

    def handle(self, *args, **options):
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")

        if not options["job_id"]:
            self._listar()
            return

        try:
            job = Job.objects.get(pk=options["job_id"])
        except Job.DoesNotExist as exc:
            raise CommandError(
                f"Vaga {options['job_id']} nao existe. Rode sem argumento para ver a fila."
            ) from exc

        self.stdout.write(self.style.HTTP_INFO(f"\n{job.title}"))
        empresa = job.company or "empresa nao informada"
        self.stdout.write(f"{empresa} | score {job.score} | {', '.join(job.tags) or 'sem tags'}")
        self.stdout.write(f"{job.url}\n")
        self.stdout.write("Gerando...\n")

        try:
            resultado = gerar_apresentacao(
                job,
                perfil=Perfil.objects.filter(dossie__gt="").first(),
                max_chars=options["max_chars"],
                instrucao_extra=options["instrucao"],
                modelo=options["modelo"],
            )
        except (DossieAusenteError, DossieVazioError, GeminiIndisponivelError, GeminiSemTextoError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("-" * 72)
        for paragrafo in resultado.texto.split("\n"):
            self.stdout.write(textwrap.fill(paragrafo, width=72) if paragrafo.strip() else "")
        self.stdout.write("-" * 72)

        alvo = options["max_chars"]
        aviso = "" if resultado.caracteres <= alvo else self.style.WARNING("  (acima do alvo)")
        self.stdout.write(f"{resultado.caracteres} caracteres, alvo {alvo}{aviso}")
        self.stdout.write(
            f"{resultado.modelo}: {resultado.tokens_entrada} tokens de entrada, "
            f"{resultado.tokens_saida} de saida, "
            f"{resultado.tokens_pensamento} de pensamento"
        )
        self.stdout.write(self.style.SUCCESS("\nRevise antes de colar. Nada foi gravado."))

    def _listar(self):
        self.stdout.write("Vagas do topo da fila (use o id):\n")
        for job in Job.objects.triage()[:15]:
            empresa = f" @ {job.company[:26]}" if job.company else ""
            self.stdout.write(f"  {job.id:>5}  [{job.score:>4}]  {job.title[:52]}{empresa}")
        self.stdout.write("\n  python manage.py pitch <id>")
