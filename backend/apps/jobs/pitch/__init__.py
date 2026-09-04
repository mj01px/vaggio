"""Geracao do "Apresente-se" da Gupy, personalizado por vaga.

Tres modulos de proposito unico:

- `dossie`  carrega o arquivo com quem voce e, que e a fonte de verdade;
- `prompt`  monta a instrucao e a entrada a partir da vaga e do dossie;
- `gemini`  fala com a API do Google e devolve o texto.

Nada aqui grava no banco: o comando imprime e voce revisa antes de colar.
"""

from .dossie import DossieAusenteError, DossieVazioError, carregar_dossie
from .gemini import GeminiIndisponivelError, GeminiSemTextoError, TextoGerado, gerar_texto
from .prompt import INSTRUCAO, montar_entrada
from .service import MAX_CHARS_PADRAO, gerar_apresentacao, gerar_e_salvar

__all__ = [
    "INSTRUCAO",
    "MAX_CHARS_PADRAO",
    "DossieAusenteError",
    "DossieVazioError",
    "GeminiIndisponivelError",
    "GeminiSemTextoError",
    "TextoGerado",
    "carregar_dossie",
    "gerar_apresentacao",
    "gerar_e_salvar",
    "gerar_texto",
    "montar_entrada",
]
