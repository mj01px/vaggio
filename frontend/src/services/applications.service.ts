import { api } from '@/lib/api'
import type { Application, ApplicationStatusKey, Board, Encerradas } from '@/types/api'

export async function fetchBoard(): Promise<Board> {
  const { data } = await api.get<Board>('/applications/board/')
  return data
}

/** As candidaturas que sairam do funil, rejeitadas e desistidas juntas. */
export async function fetchEncerradas(): Promise<Encerradas> {
  const { data } = await api.get<Encerradas>('/applications/closed/')
  return data
}

/** Coloca a vaga no funil. O backend devolve a existente se ja estiver la. */
export async function createApplication(jobId: number): Promise<Application> {
  const { data } = await api.post<Application>('/applications/', { job: jobId })
  return data
}

/** Apaga de vez. O backend so aceita se a candidatura ja estiver encerrada. */
export async function deleteApplication(id: number): Promise<void> {
  await api.delete(`/applications/${id}/`)
}

export async function updateApplication(
  id: number,
  changes: Partial<{
    status: ApplicationStatusKey
    priority: number
    applied_on: string | null
    next_step: string
    next_step_on: string | null
    contact: string
    has_referral: boolean
    notes: string
  }>,
): Promise<Application> {
  const { data } = await api.patch<Application>(`/applications/${id}/`, changes)
  return data
}
