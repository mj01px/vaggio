import type { Job } from '@/types/api'

const maiuscula = (texto: string) => texto.charAt(0).toUpperCase() + texto.slice(1)

/** Sem acento e em minuscula, so para comparar tag com senioridade. */
const chave = (texto: string) =>
  texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')

/**
 * A linha de apoio de uma vaga: senioridade na frente, depois as tags.
 *
 * Mora em `lib` porque o Radar e as Candidaturas mostram a mesma linha: sao
 * duas telas olhando a mesma vaga, e duas copias divergiriam na primeira vez
 * que uma das duas mudasse de ideia sobre o corte.
 *
 * A senioridade vem primeiro porque e o primeiro corte de quem tria. As tags
 * cobrem tecnologia e setor ("python", "seguros") e completam ate tres, que e
 * onde a linha para de crescer.
 *
 * 'unknown' vem preenchido no contrato para metade da fila; nesse caso a vaga
 * cede o lugar para mais uma tag em vez de gastar a linha com "Nao informada".
 * A tag que repete a senioridade tambem sai: "Junior, Junior, Python" e ruido,
 * e ela pode chegar como 'internship' ou como 'Estagio', entao compara os dois.
 */
export function resumoDaVaga(job: Job): string {
  const partes: string[] = []
  const repetida = new Set([chave(job.seniority), chave(job.seniority_display)])

  if (job.seniority !== 'unknown') partes.push(job.seniority_display)

  for (const tag of job.tags) {
    if (partes.length >= 3) break
    if (repetida.has(chave(tag))) continue
    partes.push(maiuscula(tag))
  }

  return partes.join(', ')
}
