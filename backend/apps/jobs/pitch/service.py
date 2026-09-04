"""Orquestra a geracao: dossie + vaga -> prompt -> Gemini -> texto.

Vive aqui, e nao no comando, pelo mesmo motivo da coleta: o dia que a API
disparar isso por um botao, ela reusa exatamente este caminho.
"""

from apps.jobs.models import Job, Pitch

from .dossie import carregar_dossie
from .gemini import TextoGerado, gerar_texto
from .prompt import INSTRUCAO, montar_entrada

# O campo da Gupy nao documenta o limite publicamente. 1200 caracteres e um
# alvo conservador: cabe em qualquer limite plausivel e ja e mais longo do que
# um recrutador le com atencao.
MAX_CHARS_PADRAO = 1200


def gerar_apresentacao(
    job: Job,
    *,
    max_chars: int = MAX_CHARS_PADRAO,
    instrucao_extra: str = "",
    modelo: str = "",
    perfil=None,
) -> TextoGerado:
    dossie = carregar_dossie(perfil=perfil)
    entrada = montar_entrada(job, dossie, max_chars, instrucao_extra)
    return gerar_texto(INSTRUCAO, entrada, modelo=modelo)


def gerar_e_salvar(
    job: Job,
    *,
    max_chars: int = MAX_CHARS_PADRAO,
    instrucao_extra: str = "",
    modelo: str = "",
    perfil=None,
    autor=None,
) -> Pitch:
    """Igual a `gerar_apresentacao`, mas guarda a versao gerada.

    E o caminho da API. O comando continua no `gerar_apresentacao`, que nao
    grava: no console voce esta experimentando prompt, e encher o banco de
    rascunho descartavel so atrapalha o historico que interessa.
    """
    resultado = gerar_apresentacao(
        job,
        max_chars=max_chars,
        instrucao_extra=instrucao_extra,
        modelo=modelo,
        perfil=perfil,
    )
    return Pitch.objects.create(
        job=job,
        autor=autor,
        texto=resultado.texto,
        modelo=resultado.modelo,
        instrucao=instrucao_extra.strip()[:300],
        max_chars=max_chars,
        tokens_entrada=resultado.tokens_entrada,
        tokens_saida=resultado.tokens_saida,
        tokens_pensamento=resultado.tokens_pensamento,
    )
