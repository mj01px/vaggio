import { api } from '@/lib/api'
import type { JobSourceKey, Paginated } from '@/types/api'

/**
 * Uma execucao da coleta, como /collections/ devolve.
 *
 * O tipo mora aqui, e nao em types/api.ts, porque so o dashboard le esta rota
 * por enquanto: quando uma segunda tela precisar, ele sobe para o contrato.
 */
export interface ColetaRun {
  id: number
  source: JobSourceKey
  source_display: string
  started_at: string
  finished_at: string | null
  duration_seconds: number | null
  found_count: number
  new_count: number
  error: string
}

/** Quantas execucoes cabem no cartao sem virar um historico. */
export const LIMITE_COLETAS = 3

/**
 * As coletas mais recentes.
 *
 * A API ja ordena por `-started_at`, entao a primeira pagina e exatamente o
 * comeco da lista: nao precisa de ordering na query.
 */
export async function fetchColetasRecentes(): Promise<ColetaRun[]> {
  const { data } = await api.get<Paginated<ColetaRun>>('/collections/', {
    params: { page_size: LIMITE_COLETAS },
  })
  return data.results
}
