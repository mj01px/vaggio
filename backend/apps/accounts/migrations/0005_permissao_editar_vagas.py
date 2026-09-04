"""Acrescenta a permissao de editar vaga.

Mesma forma da 0003: o catalogo vive em `permissoes.py` e esta migration so
reaplica ele. Nao mexe em cargo montado a mao, so nos padrao.
"""

from django.db import migrations

from apps.accounts.permissoes import CARGOS_PADRAO, PERMISSOES_PADRAO


def semear(apps, schema_editor):
    Permissao = apps.get_model("accounts", "Permissao")
    Cargo = apps.get_model("accounts", "Cargo")

    for slug, nome, descricao in PERMISSOES_PADRAO:
        Permissao.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )

    for slug, (nome, descricao, permissoes) in CARGOS_PADRAO.items():
        cargo, _ = Cargo.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )
        cargo.permissoes.set(Permissao.objects.filter(slug__in=permissoes))


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_email_unico")]

    operations = [migrations.RunPython(semear, migrations.RunPython.noop)]
