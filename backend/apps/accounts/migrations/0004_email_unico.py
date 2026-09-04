"""E-mail passa a ser a credencial de login, entao precisa ser unico.

O `auth.User` do Django nao poe indice nenhum em `email`: para ele o campo e um
contato, nao uma identidade. Como agora o login resolve a conta pelo e-mail,
duas contas com o mesmo e-mail deixariam as duas sem entrar. O indice e
funcional (`LOWER`) porque o login compara sem diferenciar maiuscula, e parcial
porque conta antiga sem e-mail continua no banco, so nao entra mais.
"""

from django.db import migrations

INDICE = "auth_user_email_unico"

CRIA = f"CREATE UNIQUE INDEX {INDICE} ON auth_user (LOWER(email)) WHERE email <> ''"
APAGA = f"DROP INDEX {INDICE}"


def confere_antes(apps, schema_editor):
    """Barra a migration se o banco ja tiver e-mail repetido.

    Sem isso o CREATE INDEX estoura com erro de banco, que nao diz quais contas
    sao o problema.
    """
    User = apps.get_model("auth", "User")

    vistos: dict[str, list[str]] = {}
    for username, email in User.objects.exclude(email="").values_list("username", "email"):
        vistos.setdefault(email.strip().lower(), []).append(username)

    repetidos = {email: contas for email, contas in vistos.items() if len(contas) > 1}
    if repetidos:
        detalhe = "; ".join(f"{email}: {', '.join(contas)}" for email, contas in repetidos.items())
        raise RuntimeError(
            "Ha e-mails repetidos em auth_user e o login agora e por e-mail. "
            f"Acerte estas contas antes de migrar -> {detalhe}"
        )

    sem_email = list(User.objects.filter(email="").values_list("username", flat=True))
    if sem_email:
        print(
            f"\n  Aviso: {len(sem_email)} conta(s) sem e-mail nao conseguem mais entrar "
            f"({', '.join(sem_email)}). Defina o e-mail delas em /usuarios ou no admin."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_permissoes_de_administracao"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(confere_antes, migrations.RunPython.noop),
        migrations.RunSQL(sql=CRIA, reverse_sql=APAGA),
    ]
