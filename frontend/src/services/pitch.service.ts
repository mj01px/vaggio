import { api } from '@/lib/api'
import type { Pitch } from '@/types/api'

export interface PitchOptions {
  max_chars?: number
  instrucao?: string
}

/** Versoes ja geradas para a vaga, da mais nova para a mais antiga. */
export async function fetchPitches(jobId: number): Promise<Pitch[]> {
  const { data } = await api.get<Pitch[]>(`/jobs/${jobId}/pitch/`)
  return data
}

/**
 * Gera uma versao nova e espera ela ficar pronta.
 *
 * Leva uns 10 segundos, entao o timeout aqui e explicito: o padrao do axios e
 * nenhum, e uma chamada pendurada deixaria o botao girando para sempre.
 */
export async function generatePitch(jobId: number, options: PitchOptions = {}): Promise<Pitch> {
  const { data } = await api.post<Pitch>(`/jobs/${jobId}/pitch/`, options, { timeout: 120_000 })
  return data
}
