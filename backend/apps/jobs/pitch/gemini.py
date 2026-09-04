"""Chamada ao Gemini (Google AI Studio).

Formato confirmado contra a API em 02/09/2026: `client.interactions.create` com
`model`, `system_instruction`, `input` e `generation_config` como argumentos
nomeados, e a resposta trazendo `output_text` e `usage` ja prontos.
"""

import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)

# Escrever uma apresentacao nao e problema de raciocinio profundo, e o nivel
# baixo ja gasta uns 200 tokens de pensamento. Subir daqui queima cota do free
# tier sem melhorar texto.
THINKING_LEVEL = "low"

# Teto generoso: o `max_output_tokens` conta tambem os tokens de pensamento, e
# estourar o limite corta o texto no meio da frase.
MAX_OUTPUT_TOKENS = 4000

# Sem teto explicito a chamada pendura indefinidamente quando a API engasga ou
# limita a cota, e no endpoint isso e pior que lento: a geracao segura a trava,
# e todo clique seguinte no botao responde 409 ate o processo morrer. Uma
# geracao normal leva de 3 a 15 segundos.
TIMEOUT_SEGUNDOS = 90.0


class GeminiSemTextoError(RuntimeError):
    """A API respondeu, mas nao com um texto utilizavel."""


class GeminiIndisponivelError(RuntimeError):
    """Nao deu para falar com a API: falta de chave, rede ou cota."""


@dataclass(frozen=True)
class TextoGerado:
    texto: str
    modelo: str
    tokens_entrada: int
    tokens_saida: int
    tokens_pensamento: int

    @property
    def caracteres(self) -> int:
        return len(self.texto)


def _cliente():
    chave = (settings.GEMINI_API_KEY or "").strip()
    if not chave:
        raise GeminiIndisponivelError(
            "GEMINI_API_KEY vazia. Crie uma chave em aistudio.google.com e "
            "coloque no .env do backend."
        )
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - dependencia declarada
        raise GeminiIndisponivelError(
            "Pacote google-genai nao instalado: pip install -r requirements/base.txt"
        ) from exc
    return genai.Client(api_key=chave)


def gerar_texto(instrucao: str, entrada: str, modelo: str = "") -> TextoGerado:
    """Manda instrucao e entrada, devolve o texto e o custo em tokens."""
    modelo = modelo or settings.GEMINI_MODEL
    cliente = _cliente()

    try:
        resposta = cliente.interactions.create(
            model=modelo,
            system_instruction=instrucao,
            input=entrada,
            generation_config={
                "thinking_level": THINKING_LEVEL,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            },
            timeout=TIMEOUT_SEGUNDOS,
        )
    except Exception as exc:
        logger.exception("falha chamando o Gemini (modelo %s)", modelo)
        if "timeout" in type(exc).__name__.lower() or isinstance(exc, TimeoutError):
            raise GeminiIndisponivelError(
                f"O Gemini nao respondeu em {TIMEOUT_SEGUNDOS:.0f}s. Pode ser limite "
                "do free tier: espere um minuto e tente de novo."
            ) from exc
        raise GeminiIndisponivelError(f"Gemini nao respondeu: {exc}") from exc

    texto = (resposta.output_text or "").strip()
    if not texto:
        # Acontece quando o modelo e barrado por filtro de seguranca ou quando o
        # teto de tokens some com a saida. Sem isso o comando imprimiria vazio.
        raise GeminiSemTextoError(
            f"O Gemini respondeu sem texto (status: {resposta.status}). "
            "Veja se o dossie ou a descricao da vaga tem algo que dispare filtro."
        )

    uso = resposta.usage
    return TextoGerado(
        texto=texto,
        modelo=modelo,
        tokens_entrada=getattr(uso, "total_input_tokens", 0) or 0,
        tokens_saida=getattr(uso, "total_output_tokens", 0) or 0,
        tokens_pensamento=getattr(uso, "total_thought_tokens", 0) or 0,
    )
