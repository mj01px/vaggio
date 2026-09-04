"""Limite de tentativa por acao, e nao por view inteira.

O `ScopedRateThrottle` do DRF le `view.throttle_scope`, que vale para a viewset
toda: por a apresentacao em 30/hora desse jeito poria a LISTA de vagas em
30/hora junto, e a tela para de funcionar.

Aqui o escopo e escolhido pela view em `get_throttles()`, uma acao por vez. A
contagem e por pessoa (`UserRateThrottle`), e nao por IP: o custo que se quer
limitar e cota do Gemini e worker preso, que sao de quem clicou.
"""

from rest_framework.throttling import UserRateThrottle


class ThrottlePorEscopo(UserRateThrottle):
    """Um `UserRateThrottle` com o escopo escolhido na hora."""

    def __init__(self, escopo: str):
        self.scope = escopo
        super().__init__()
