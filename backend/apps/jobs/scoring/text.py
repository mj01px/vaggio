"""Normalizacao de texto e casamento de termos. Funcao pura, sem Django."""

import re
import unicodedata

_SPACES_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Minusculas, sem acento, espacos colapsados. Comparacao fica previsivel."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _SPACES_RE.sub(" ", text.lower())


def contains(text: str, term: str) -> bool:
    """Casa o termo respeitando limite de palavra.

    E o que permite ter "jr" e "sr" na lista sem casar dentro de "jrxyz" ou
    "srv". Os dois lados precisam ja estar normalizados.
    """
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
