"""Move o dossie do arquivo para o perfil, que virou o dono dele.

    python manage.py importar_dossie --usuario mauro@exemplo.dev

O arquivo `apps/jobs/pitch/dossie.md` continua funcionando como fallback, mas
so serve para uma pessoa. Depois de importar, o texto vive no banco e da para
editar pela API.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import models

from apps.accounts.models import Perfil
from apps.jobs.pitch.dossie import CAMINHO


class Command(BaseCommand):
    help = "Copia o dossie.md para o campo dossie de um perfil."

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuario", required=True, help="E-mail (ou username antigo) do dono do perfil."
        )
        parser.add_argument(
            "--forcar",
            action="store_true",
            help="Sobrescreve o dossie que ja estiver no perfil.",
        )

    def handle(self, *args, **options):
        if not CAMINHO.exists():
            raise CommandError(f"Nao achei {CAMINHO}.")

        # Procura pelo e-mail, que e como as contas se identificam desde o
        # login por e-mail, e cai no username para nao quebrar conta antiga.
        quem = options["usuario"]
        perfil = (
            Perfil.objects.select_related("user")
            .filter(models.Q(user__email__iexact=quem) | models.Q(user__username__iexact=quem))
            .first()
        )
        if perfil is None:
            raise CommandError(
                f'Nenhum perfil para "{quem}". Entre uma vez pelo app ou crie o perfil no admin.'
            )

        if perfil.dossie.strip() and not options["forcar"]:
            raise CommandError(
                f"O perfil de {perfil} ja tem dossie ({len(perfil.dossie)} caracteres). "
                "Use --forcar para sobrescrever."
            )

        perfil.dossie = CAMINHO.read_text(encoding="utf-8")
        perfil.save(update_fields=["dossie", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Dossie de {len(perfil.dossie)} caracteres importado para {perfil}."
            )
        )
