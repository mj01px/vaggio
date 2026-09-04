/** Regras do board que nao dependem de React: mover cartao e ler prioridade. */

import type { Application, ApplicationStatusKey, Board } from '@/types/api'

/**
 * O board com a candidatura ja no status novo, sem esperar a API.
 *
 * Arrastar cartao e a acao mais repetida da tela, e esperar o roundtrip para
 * ver o cartao trocar de coluna faz o board parecer travado. O resultado real
 * chega depois pelo invalidate; aqui so antecipamos o que o backend vai fazer.
 *
 * Detalhe que nao da para ignorar: Rejeitada e Desisti nao tem coluna. Mover
 * para uma delas tira a candidatura do board inteiro, inclusive da lista de
 * atrasadas, porque `is_overdue` no backend e falso fora do funil ativo.
 */
export function moverNoBoard(
  board: Board,
  id: number,
  status: ApplicationStatusKey,
): Board {
  const atual = board.columns.flatMap((coluna) => coluna.items).find((item) => item.id === id)
  if (!atual || atual.status === status) return board

  // O status existir entre as colunas e o que separa "continua no funil" de
  // "saiu do board", sem repetir aqui a lista de status ativos do backend.
  const continuaNoFunil = board.columns.some((coluna) => coluna.status === status)

  const movida: Application = {
    ...atual,
    status,
    status_display: board.statuses.find((item) => item.value === status)?.label ?? '',
    is_overdue: continuaNoFunil && atual.is_overdue,
  }

  const columns = board.columns.map((coluna) => {
    const items = coluna.items.filter((item) => item.id !== id)
    if (continuaNoFunil && coluna.status === status) items.push(movida)
    // Mesma ordem do endpoint: prioridade primeiro, id decrescente para desempatar.
    items.sort((a, b) => a.priority - b.priority || b.id - a.id)
    return { ...coluna, items, total: items.length }
  })

  const overdue = continuaNoFunil
    ? board.overdue.map((item) => (item.id === id ? movida : item))
    : board.overdue.filter((item) => item.id !== id)

  return { ...board, columns, overdue }
}

/**
 * Quantas candidaturas da coluna estao com follow-up vencido.
 *
 * No mobile so uma coluna aparece por vez, entao o seletor de etapa precisa
 * dizer onde esta o atraso sem que a pessoa entre em cada etapa para descobrir.
 */
export function contarAtrasadas(items: Application[]): number {
  return items.reduce((total, item) => total + (item.is_overdue ? 1 : 0), 0)
}
