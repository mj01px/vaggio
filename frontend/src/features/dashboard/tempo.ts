/** Contas de data que so o dashboard faz: vencimento e "quando rodou". */

const UM_DIA = 86_400_000

/**
 * Quantos dias corridos ja se passaram desde a data (formato 'AAAA-MM-DD').
 *
 * O split manual existe porque `new Date('2026-08-20')` e lido como meia-noite
 * em UTC: em fuso negativo, como o nosso, isso volta o dia anterior e a conta
 * erra por um. Comparar as duas datas em UTC resolve sem depender do fuso.
 */
export function diasVencidos(dataISO: string | null): number | null {
  if (!dataISO) return null

  const [ano, mes, dia] = dataISO.slice(0, 10).split('-').map(Number)
  if (!ano || !mes || !dia) return null

  const agora = new Date()
  const hoje = Date.UTC(agora.getFullYear(), agora.getMonth(), agora.getDate())
  return Math.round((hoje - Date.UTC(ano, mes - 1, dia)) / UM_DIA)
}

/** "venceu ha 3 dias". A frase e o que se le na linha da candidatura atrasada. */
export function textoVencimento(dataISO: string | null): string {
  const dias = diasVencidos(dataISO)
  if (dias === null) return 'sem data marcada'
  if (dias <= 0) return 'vence hoje'
  if (dias === 1) return 'venceu ontem'
  return `venceu há ${dias} dias`
}

/**
 * Quando a coleta rodou, do jeito que se responde em voz alta.
 *
 * "hoje 14:32" diz mais que "20/08 14:32" para a execucao que acabou de sair,
 * que e justamente a que interessa neste cartao.
 */
export function quandoRodou(iso: string): string {
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return ''

  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const agora = new Date()
  const ontem = new Date(agora)
  ontem.setDate(ontem.getDate() - 1)

  if (data.toDateString() === agora.toDateString()) return `hoje ${hora}`
  if (data.toDateString() === ontem.toDateString()) return `ontem ${hora}`

  const dia = data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  return `${dia} ${hora}`
}
