"""Carrega o dossie: o arquivo que diz quem voce e.

E a unica fonte de verdade sobre voce no texto gerado. Fica fora do git, junto
com o `.env`, porque carrega historico de carreira real.
"""

import re
from pathlib import Path

CAMINHO = Path(__file__).resolve().parent / "dossie.md"

# Os comentarios HTML do arquivo sao lembretes para voce ("PENDENTE: confira
# esta divisao"), nao informacao sobre voce. Vao fora antes de virar prompt:
# mandar um lembrete de tarefa para o modelo so serve para confundi-lo.
COMENTARIO_RE = re.compile(r"<!--.*?-->", re.DOTALL)

MINIMO_UTIL = 400


class DossieAusenteError(FileNotFoundError):
    """O arquivo nao existe."""


class DossieVazioError(ValueError):
    """O arquivo existe mas nao tem conteudo suficiente para gerar nada."""


def carregar_dossie(caminho: Path | None = None, perfil=None) -> str:
    """Devolve o dossie limpo, pronto para entrar no prompt.

    O perfil e a fonte de verdade desde que o RBAC existe. O arquivo continua
    valendo como fallback: e de onde veio o dossie antes de haver banco, e
    quem ainda nao migrou o texto para o proprio perfil nao pode ficar sem.
    """
    do_perfil = (getattr(perfil, "dossie", "") or "").strip()
    if do_perfil:
        texto = COMENTARIO_RE.sub("", do_perfil).strip()
        if len(texto) < MINIMO_UTIL:
            raise DossieVazioError(
                f"O dossie do perfil tem menos de {MINIMO_UTIL} caracteres uteis. "
                "Sem experiencia e projeto escritos ali, o texto gerado so pode "
                "sair generico."
            )
        return texto

    caminho = caminho or CAMINHO

    if not caminho.exists():
        raise DossieAusenteError(
            f"Dossie nao encontrado em {caminho}. "
            "Ele fica fora do git de proposito: crie o arquivo com quem voce e "
            "antes de gerar apresentacao."
        )

    texto = COMENTARIO_RE.sub("", caminho.read_text(encoding="utf-8")).strip()

    if len(texto) < MINIMO_UTIL:
        raise DossieVazioError(
            f"O dossie em {caminho} tem menos de {MINIMO_UTIL} caracteres uteis. "
            "Sem experiencia e projeto escritos ali, o texto gerado so pode sair "
            "generico."
        )

    return texto
