"""Perfil, cargo e permissao.

O `Perfil` e o dono de tudo que o app sabe sobre uma pessoa: o dossie usado para
escrever a apresentacao, os termos que pontuam uma vaga como boa para ela, e as
preferencias de geracao. Antes disso, essas coisas moravam em arquivo
(`scoring/profile.py` e `pitch/dossie.md`), o que so funcionava para uma pessoa.

O controle de acesso e por cargo, com as permissoes em tabela em vez de fixas no
codigo: dar ou tirar acesso vira dado, nao deploy.
"""

import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps.core.models import TimeStampedModel

# Quantos codigos de reserva uma ativacao de 2FA gera. Oito cobre perder o
# celular e ainda ter margem antes de precisar gerar de novo.
CODIGOS_DE_RESERVA = 8


class Permissao(models.Model):
    """Uma acao que se pode liberar. Os slugs vivem em `PERMISSOES_PADRAO`."""

    slug = models.SlugField("Chave", max_length=60, unique=True)
    nome = models.CharField("Nome", max_length=120)
    descricao = models.CharField("Descrição", max_length=300, blank=True)

    class Meta:
        db_table = "accounts_permissao"
        verbose_name = "permissão"
        verbose_name_plural = "permissões"
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.slug


class Cargo(TimeStampedModel):
    """Um conjunto de permissoes com nome."""

    slug = models.SlugField("Chave", max_length=60, unique=True)
    nome = models.CharField("Nome", max_length=120)
    descricao = models.CharField("Descrição", max_length=300, blank=True)
    permissoes = models.ManyToManyField(Permissao, related_name="cargos", blank=True)

    class Meta:
        db_table = "accounts_cargo"
        verbose_name = "cargo"
        verbose_name_plural = "cargos"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    def pode(self, slug: str) -> bool:
        return self.permissoes.filter(slug=slug).exists()


class Perfil(TimeStampedModel):
    """Quem usa o Vaggio, e tudo que o app sabe sobre a pessoa."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    nome = models.CharField("Nome", max_length=120, blank=True)
    cargo = models.ForeignKey(
        Cargo, on_delete=models.PROTECT, related_name="perfis", null=True, blank=True
    )

    # Fonte de verdade sobre a pessoa para escrever a apresentacao. Era o
    # arquivo dossie.md, que so servia para um usuario e ficava fora do git.
    dossie = models.TextField("Dossiê", blank=True)

    # Sobrescreve os grupos de termos do scoring. Vazio significa "use o perfil
    # padrao de apps/jobs/scoring/profile.py", que continua sendo o ponto de
    # partida de quem nunca mexeu nisso.
    termos = models.JSONField("Termos de scoring", default=dict, blank=True)

    pitch_max_chars = models.PositiveIntegerField("Tamanho da apresentação", default=1200)

    # ── Segundo fator ─────────────────────────────────────────────────────
    # O segredo so vira 2FA de verdade depois que a pessoa prova que consegue
    # gerar um codigo com ele: por isso `totp_ativo` e um campo a parte, e nao
    # `bool(totp_secret)`. Sem isso, quem abrisse a tela de ativacao e
    # desistisse no meio ficaria trancado fora na proxima entrada.
    totp_secret = models.CharField("Segredo TOTP", max_length=64, blank=True)
    totp_ativo = models.BooleanField("2FA ativo", default=False)
    # O maior passo de 30 segundos que ja foi aceito nesta conta. Sem guardar
    # isso, `verify()` so responde "esse codigo bate com o segredo agora", e o
    # mesmo codigo entrava quantas vezes coubessem na janela de ~90 segundos.
    # Codigo visto por cima do ombro continuava servindo depois de a pessoa
    # entrar, que e justo o cenario que o segundo fator existe para cobrir.
    totp_ultimo_passo = models.PositiveBigIntegerField("Último passo TOTP", default=0)
    # Guardados com hash, como senha: quem le o banco nao entra na conta.
    codigos_de_reserva = models.JSONField("Códigos de reserva", default=list, blank=True)

    class Meta:
        db_table = "accounts_perfil"
        verbose_name = "perfil"
        verbose_name_plural = "perfis"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome or self.user.get_username()

    def pode(self, slug: str) -> bool:
        """Superusuario passa por tudo; o resto depende do cargo."""
        if self.user.is_superuser:
            return True
        return bool(self.cargo and self.cargo.pode(slug))

    def gerar_codigos_de_reserva(self) -> list[str]:
        """Sorteia codigos novos, guarda o hash e devolve os codigos em claro.

        Os codigos em claro so existem neste retorno: e a unica vez que da para
        mostra-los. Guardar em claro para poder reexibir depois transformaria o
        banco numa copia da segunda chave.
        """
        codigos = [f"{secrets.randbelow(10**9):09d}" for _ in range(CODIGOS_DE_RESERVA)]
        self.codigos_de_reserva = [make_password(c) for c in codigos]
        return codigos

    def queimar_codigo_de_reserva(self, codigo: str) -> bool:
        """Confere um codigo e o remove. Cada um vale uma entrada so."""
        codigo = codigo.strip().replace("-", "").replace(" ", "")
        for guardado in list(self.codigos_de_reserva):
            if check_password(codigo, guardado):
                self.codigos_de_reserva = [
                    c for c in self.codigos_de_reserva if c != guardado
                ]
                self.save(update_fields=["codigos_de_reserva", "updated_at"])
                return True
        return False

    @property
    def permissoes(self) -> list[str]:
        if self.user.is_superuser:
            return sorted(Permissao.objects.values_list("slug", flat=True))
        if not self.cargo:
            return []
        return sorted(self.cargo.permissoes.values_list("slug", flat=True))
