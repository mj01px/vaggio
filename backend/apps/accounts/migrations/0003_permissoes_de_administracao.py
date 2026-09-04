"""Acrescenta as permissoes de administrar usuario e cargo.

O catalogo vive em `permissoes.py`; esta migration so reaplica ele no banco de
quem ja tinha o RBAC instalado. Nao remove nada: cargo montado na mao continua
como esta.
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

    # So os cargos padrao sao reajustados. Quem criou cargo proprio decide
    # sozinho se quer as permissoes novas.
    for slug, (nome, descricao, permissoes) in CARGOS_PADRAO.items():
        cargo, _ = Cargo.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )
        cargo.permissoes.set(Permissao.objects.filter(slug__in=permissoes))


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_semeia_permissoes_e_cargos")]

    operations = [migrations.RunPython(semear, migrations.RunPython.noop)]
