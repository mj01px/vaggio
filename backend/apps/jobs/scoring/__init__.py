"""Pontuacao de vagas pelo perfil do candidato.

Separado em tres modulos de proposito unico:

- `text`    normalizacao e casamento de termo com limite de palavra;
- `profile` o dicionario PERFIL, que e o unico lugar que se edita para
            mudar o que conta como "vaga boa pra mim";
- `engine`  aplica o perfil e devolve score, tags, senioridade e modalidade.

Nada aqui toca no banco: e funcao pura, testavel sem Django.
"""

from .engine import Classification, classify, detect_seniority, detect_work_mode, score_text
from .perfil_ativo import perfil_de_scoring
from .profile import PROFILE
from .text import contains, normalize

__all__ = [
    "PROFILE",
    "Classification",
    "classify",
    "contains",
    "detect_seniority",
    "detect_work_mode",
    "normalize",
    "perfil_de_scoring",
    "score_text",
]
