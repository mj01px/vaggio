"""Monta a instrucao e a entrada mandadas ao modelo.

A divisao segue a API: `system_instruction` carrega as regras, que nao mudam
entre vagas, e `input` carrega os dados desta vaga e o dossie.
"""

from apps.jobs.models import Job

# A descricao da Gupy tem mediana de 2848 caracteres, mas a cauda vai a 14 mil.
# O corte existe para uma vaga gigante nao dominar a entrada; o que interessa
# (empresa, area, stack, responsabilidades) vem sempre no comeco.
MAX_DESCRICAO = 6000

INSTRUCAO = """\
Voce escreve o campo "Apresente-se" de candidaturas na Gupy, na voz do
candidato, em primeira pessoa e em portugues do Brasil.

REGRA MAIS IMPORTANTE
O dossie e a unica fonte de verdade sobre o candidato. Nao invente experiencia,
tecnologia, tempo de casa, formacao, numero ou resultado que nao esteja escrito
nele. Se a vaga pedir algo que o dossie nao sustenta, simplesmente nao fale
disso: nao invente, nao prometa e nao peca desculpa pela falta.

O QUE O TEXTO PRECISA TER
- Pelo menos dois elementos concretos e nomeados da vaga: a area, o produto, a
  stack, um problema citado na descricao. Nada de elogio generico a empresa.
- Ligacao explicita entre esses elementos e algo que o candidato de fato fez,
  citando o projeto ou a experiencia pelo nome que aparece no dossie.
- Prioridade para os pontos de contato listados na vaga, que sao os termos onde
  o perfil do candidato ja casa com ela.
- Evidencia no lugar de adjetivo. "Entreguei um ERP em producao" vale; "sou
  proativo e dedicado" nao entra.

FORMA
- Texto corrido, dois a quatro paragrafos curtos, sem titulo, sem lista, sem
  markdown, sem emoji.
- Sem saudacao formal antiga: nada de "Prezados senhores" ou "venho por meio
  desta". Comece pelo assunto.
- Sem despedida assinada, sem telefone e sem e-mail.
- Nao repita a descricao da vaga de volta para a empresa, e nao recite o
  curriculo em ordem cronologica.
- Respeite o limite de caracteres pedido. Ficar abaixo dele e melhor que
  encher linguica.

Responda apenas com o texto da apresentacao, nada mais.\
"""


def descrever_vaga(job: Job) -> str:
    """A vaga no formato que o modelo le."""
    descricao = (job.description or "").strip()
    if len(descricao) > MAX_DESCRICAO:
        descricao = descricao[:MAX_DESCRICAO] + "\n[descricao truncada]"

    linhas = [
        f"Titulo: {job.title}",
        f"Empresa: {job.company or 'nao informada'}",
        f"Local: {job.location or 'nao informado'}",
        f"Senioridade detectada: {job.get_seniority_display()}",
        f"Modalidade: {job.get_work_mode_display()}",
    ]
    if job.tags:
        linhas.append(f"Pontos de contato com o perfil: {', '.join(job.tags)}")
    linhas.append(f"\nDescricao da vaga:\n{descricao or 'sem descricao'}")
    return "\n".join(linhas)


def montar_entrada(job: Job, dossie: str, max_chars: int, instrucao_extra: str = "") -> str:
    """Junta vaga, dossie e o pedido numa entrada so."""
    partes = [
        "=== VAGA ===",
        descrever_vaga(job),
        "",
        "=== DOSSIE DO CANDIDATO (unica fonte de verdade sobre ele) ===",
        dossie,
        "",
        "=== PEDIDO ===",
        f"Escreva a apresentacao para esta vaga, com no maximo {max_chars} caracteres.",
    ]
    if instrucao_extra.strip():
        partes.append(f"Ajuste pedido nesta versao: {instrucao_extra.strip()}")
    return "\n".join(partes)
