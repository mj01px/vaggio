"""Semeia permissoes e cargos, e da perfil a quem ja existe.

A tabela nasce preenchida porque um RBAC vazio nao nega direito: ele tranca a
porta para todo mundo, inclusive para quem criou o banco.
"""

from django.db import migrations

from apps.accounts.permissoes import CARGOS_PADRAO, PERMISSOES_PADRAO


def semear(apps, schema_editor):
    Permissao = apps.get_model("accounts", "Permissao")
    Cargo = apps.get_model("accounts", "Cargo")
    Perfil = apps.get_model("accounts", "Perfil")
    User = apps.get_model("auth", "User")

    for slug, nome, descricao in PERMISSOES_PADRAO:
        Permissao.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )

    for slug, (nome, descricao, permissoes) in CARGOS_PADRAO.items():
        cargo, _ = Cargo.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )
        cargo.permissoes.set(Permissao.objects.filter(slug__in=permissoes))

    # Quem ja tinha conta antes do RBAC existir nao pode ficar sem perfil: sem
    # perfil, toda permissao e negada e a pessoa perde o proprio app.
    #
    # `dono` era o cargo "pode tudo" desta semeadura e saiu do catalogo depois
    # (migration 0006): num banco novo ele nao existe mais, e superusuario nao
    # precisa dele para nada, porque passa por cima da checagem.
    dono = Cargo.objects.filter(slug="dono").first()
    for user in User.objects.all():
        Perfil.objects.get_or_create(
            user=user,
            defaults={
                "nome": user.get_full_name() or user.username,
                "cargo": dono if user.is_superuser else None,
            },
        )


def desfazer(apps, schema_editor):
    """Tira so o que a semeadura pos, deixando cargo criado na mao em paz."""
    Permissao = apps.get_model("accounts", "Permissao")
    Cargo = apps.get_model("accounts", "Cargo")

    Cargo.objects.filter(slug__in=CARGOS_PADRAO).delete()
    Permissao.objects.filter(slug__in=[slug for slug, _, _ in PERMISSOES_PADRAO]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(semear, desfazer)]
