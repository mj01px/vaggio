"""Fixtures compartilhadas dos testes.

O scoring e funcao pura e roda sem `django_db`. Os testes de API e de funil
usam a fixture padrao do pytest-django.

Desde o RBAC, `api` ja vem com um cargo que pode tudo: os testes de vaga e funil
existem para exercitar aquelas regras, nao a de acesso. Quem testa acesso e o
`tests/test_accounts.py`, com o cliente anonimo e os cargos restritos.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Cargo, Perfil, Permissao
from apps.accounts.permissoes import CARGOS_PADRAO, PERMISSOES_PADRAO
from apps.jobs.models import Job, JobSource


@pytest.fixture
def catalogo(db):
    """Permissoes e cargos padrao, como a migration de dados deixa o banco.

    Devolve um cargo com o catalogo inteiro. Ele nao e semeado em producao:
    acesso total ali sai do `is_superuser`. Aqui ele existe para o cliente
    padrao dos testes exercitar as regras de negocio sem esbarrar no RBAC.
    """
    for slug, nome, descricao in PERMISSOES_PADRAO:
        Permissao.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )
    for slug, (nome, descricao, permissoes) in CARGOS_PADRAO.items():
        cargo, _ = Cargo.objects.update_or_create(
            slug=slug, defaults={"nome": nome, "descricao": descricao}
        )
        cargo.permissoes.set(Permissao.objects.filter(slug__in=permissoes))

    completo, _ = Cargo.objects.update_or_create(
        slug="tudo", defaults={"nome": "Tudo", "descricao": "Cargo de teste: pode tudo."}
    )
    completo.permissoes.set(Permissao.objects.all())
    return completo


@pytest.fixture
def cria_perfil(db, catalogo, django_user_model):
    """Cria usuario com perfil e um conjunto exato de permissoes."""

    def _cria(
        email="alguem@teste.dev", permissoes=None, cargo_slug="cargo-do-teste", superuser=False
    ):
        # O username so existe porque o `auth.User` exige um; quem entra digita
        # o e-mail. Derivar do e-mail evita inventar um segundo nome no teste.
        user = django_user_model.objects.create_user(
            username=email.split("@")[0], email=email, password="senha-de-teste"
        )
        user.is_superuser = superuser
        user.save()

        cargo = None
        if permissoes is not None:
            cargo, _ = Cargo.objects.get_or_create(
                slug=cargo_slug, defaults={"nome": cargo_slug}
            )
            cargo.permissoes.set(Permissao.objects.filter(slug__in=permissoes))
        elif not superuser:
            cargo = catalogo

        return Perfil.objects.create(user=user, nome=email.split("@")[0], cargo=cargo)

    return _cria


@pytest.fixture
def api(cria_perfil):
    """Cliente logado com o cargo que tem o catalogo inteiro."""
    perfil = cria_perfil(email="dono@teste.dev")
    client = APIClient()
    client.force_authenticate(user=perfil.user)
    return client


@pytest.fixture
def api_anonimo():
    """Cliente sem sessao, para checar que a porta esta fechada."""
    return APIClient()


@pytest.fixture
def make_job(db):
    """Cria vagas com o minimo de ruido: so o que o teste precisa dizer."""

    def _make(title="Desenvolvedor Python Junior", **kwargs):
        kwargs.setdefault("url", f"https://exemplo.dev/vaga/{Job.objects.count() + 1}")
        kwargs.setdefault("source", JobSource.GITHUB)
        kwargs.setdefault("company", "Empresa Teste")
        return Job.objects.create(title=title, **kwargs)

    return _make


@pytest.fixture
def sem_espera(monkeypatch):
    """Zera a pausa entre as tentativas da Gupy.

    Sem isto o teste de falha dorme os 4 segundos de verdade, e a espera e
    justamente a parte que nao precisa ser exercitada.
    """
    from apps.collectors.sources import gupy

    monkeypatch.setattr(gupy, "ESPERA_ENTRE_TENTATIVAS", (0, 0))
    return None


@pytest.fixture(autouse=True)
def zera_o_limite_de_tentativa():
    """O throttle do DRF guarda a contagem em cache, e o cache atravessa testes.

    Sem zerar, o quinto teste que bate numa rota publica ja apanha de 429 por
    causa dos quatro anteriores. Quem exercita o limite de proposito
    (`TestLimiteDeTentativa`) conta as chamadas a partir do zero, entao esta
    fixture ajuda em vez de atrapalhar.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
