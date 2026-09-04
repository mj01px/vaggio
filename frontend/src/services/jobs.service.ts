import { api } from '@/lib/api'
import type { CollectionResult, Job, JobDetalhe, JobStats, Paginated } from '@/types/api'

export interface JobFilters {
  q?: string
  source?: string
  min_score?: string
  /** Janela de recencia em dias. '0' (ou vazio) traz a fila inteira. */
  published_after?: string
  published_before?: string
  /** Pagina, 1-based. Ausente e a primeira. */
  page?: string
  /** '' cai no padrao do backend, que e a fila de triagem. */
  queue?: string
}

/** Cem por pagina: rola a olho sem virar uma lista infinita. */
export const PAGE_SIZE = 100

export async function fetchJobs(filters: JobFilters): Promise<Paginated<Job>> {
  const params: Record<string, string | number> = { page_size: PAGE_SIZE }
  if (filters.q) params.q = filters.q
  if (filters.source) params.source = filters.source
  if (filters.min_score) params.min_score = filters.min_score
  if (filters.published_after) params.published_after = filters.published_after
  if (filters.published_before) params.published_before = filters.published_before
  if (filters.page && filters.page !== '1') params.page = filters.page
  if (filters.queue) params.queue = filters.queue

  const { data } = await api.get<Paginated<Job>>('/jobs/', { params })
  return data
}

/** Uma vaga so, com a descricao que a lista omite por tamanho. */
export async function fetchJob(id: number): Promise<JobDetalhe> {
  const { data } = await api.get<JobDetalhe>(`/jobs/${id}/`)
  return data
}

/** Contadores da fila inteira, sem nenhum filtro da tela. */
export async function fetchJobStats(): Promise<JobStats> {
  const { data } = await api.get<JobStats>('/jobs/stats/')
  return data
}

export async function discardJob(id: number): Promise<Job> {
  const { data } = await api.post<Job>(`/jobs/${id}/discard/`)
  return data
}

export async function restoreJob(id: number): Promise<Job> {
  const { data } = await api.post<Job>(`/jobs/${id}/restore/`)
  return data
}

/** Cadastro manual: a vaga que voce achou fora das fontes automaticas. */
export async function createJob(vaga: {
  title: string
  company: string
  location: string
  url: string
  description: string
}): Promise<Job> {
  const { data } = await api.post<Job>('/jobs/', vaga)
  return data
}

/** O que da para corrigir numa vaga ja coletada. Tudo opcional: e um PATCH. */
export interface JobEdicao {
  title?: string
  company?: string
  location?: string
  url?: string
  description?: string
  seniority?: string
  work_mode?: string
  tags?: string[]
  score?: number
}

export async function updateJob(id: number, vaga: JobEdicao): Promise<Job> {
  const { data } = await api.patch<Job>(`/jobs/${id}/`, vaga)
  return data
}

/**
 * Dispara a coleta e espera ela terminar.
 *
 * Leva cerca de 40 segundos: sao ~75 requisicoes as fontes. O timeout do axios
 * e padrao (nenhum), entao o generoso aqui e explicito, para uma fonte pendurada
 * nao deixar o botao girando para sempre.
 */
export async function runCollection(): Promise<CollectionResult> {
  const { data } = await api.post<CollectionResult>('/collections/run/', null, {
    timeout: 180_000,
  })
  return data
}
