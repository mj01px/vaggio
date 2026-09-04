"""De onde saem os termos que pontuam uma vaga.

O `profile.py` continua sendo o ponto de partida de quem nunca mexeu em nada.
Um `Perfil` com `termos` preenchidos sobrescreve, e e assim que duas pessoas
usando o mesmo Vaggio pontuam a mesma vaga de formas diferentes.

Mora aqui, e nao no `engine`, para o engine seguir sem saber que banco existe.
"""

from .profile import PROFILE


def perfil_de_scoring(perfil=None) -> dict:
    """Os grupos de termos de um `accounts.Perfil`, ou o padrao do projeto."""
    termos = getattr(perfil, "termos", None)
    return termos if isinstance(termos, dict) and termos else PROFILE
