"""Tira o cargo "dono" semeado.

Acesso total sai do `is_superuser`, que passa por cima da checagem inteira. Um
cargo "pode tudo" era um segundo lugar para dar o mesmo acesso, e envelhecia a
cada permissao nova.

So apaga se ninguem estiver usando: cargo em uso e decisao de quem administra,
nao de uma migration.
"""

from django.db import migrations


def apagar(apps, schema_editor):
    Cargo = apps.get_model("accounts", "Cargo")
    Perfil = apps.get_model("accounts", "Perfil")

    cargo = Cargo.objects.filter(slug="dono").first()
    if cargo and not Perfil.objects.filter(cargo=cargo).exists():
        cargo.delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_permissao_editar_vagas")]

    operations = [migrations.RunPython(apagar, migrations.RunPython.noop)]
