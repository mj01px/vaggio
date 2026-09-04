"""Reaplica o catalogo de permissoes e cargos no banco.

    python manage.py sync_permissoes

Rode depois de acrescentar um slug em `apps/accounts/permissoes.py`. Existe para
criar acao nova nao virar migration de dados toda vez.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import Cargo, Permissao
from apps.accounts.permissoes import CARGOS_PADRAO, PERMISSOES_PADRAO


class Command(BaseCommand):
    help = "Cria ou atualiza as permissoes e os cargos padrao."

    def handle(self, *args, **options):
        criadas = 0
        for slug, nome, descricao in PERMISSOES_PADRAO:
            _, nova = Permissao.objects.update_or_create(
                slug=slug, defaults={"nome": nome, "descricao": descricao}
            )
            criadas += nova

        for slug, (nome, descricao, permissoes) in CARGOS_PADRAO.items():
            cargo, _ = Cargo.objects.update_or_create(
                slug=slug, defaults={"nome": nome, "descricao": descricao}
            )
            cargo.permissoes.set(Permissao.objects.filter(slug__in=permissoes))

        self.stdout.write(
            self.style.SUCCESS(
                f"{Permissao.objects.count()} permissoes ({criadas} novas), "
                f"{Cargo.objects.count()} cargos."
            )
        )

        orfas = Permissao.objects.exclude(
            slug__in=[slug for slug, _, _ in PERMISSOES_PADRAO]
        )
        if orfas.exists():
            # Nao apaga sozinho: pode ser permissao que voce criou na mao.
            self.stdout.write(
                self.style.WARNING(
                    "Fora do catalogo (nao removidas): "
                    + ", ".join(orfas.values_list("slug", flat=True))
                )
            )
