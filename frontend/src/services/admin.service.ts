import { api } from '@/lib/api'
import type { Cargo, Paginated, Permissao, PermissaoKey, Usuario } from '@/types/api'

export async function fetchUsuarios(): Promise<Usuario[]> {
  const { data } = await api.get<Paginated<Usuario>>('/usuarios/', { params: { page_size: 100 } })
  return data.results
}

export interface NovoUsuario {
  /** E por aqui que a pessoa entra, entao e obrigatorio e unico. */
  email: string
  nome?: string
  cargo?: string | null
}

export async function criarUsuario(dados: NovoUsuario): Promise<Usuario> {
  const { data } = await api.post<Usuario>('/usuarios/', dados)
  return data
}

export async function atualizarUsuario(
  id: number,
  mudancas: Partial<{ email: string; nome: string; cargo: string | null; is_active: boolean }>,
): Promise<Usuario> {
  const { data } = await api.patch<Usuario>(`/usuarios/${id}/`, mudancas)
  return data
}

/**
 * Manda (ou reenvia) o convite para a pessoa escolher a propria senha.
 *
 * Substituiu o endpoint em que o admin digitava a senha do outro: por aqui
 * ninguem alem do dono chega a saber aquela senha.
 */
export async function enviarConvite(id: number): Promise<string> {
  const { data } = await api.post<{ detail: string }>(`/usuarios/${id}/convite/`)
  return data.detail
}

export async function fetchCargos(): Promise<Cargo[]> {
  const { data } = await api.get<Paginated<Cargo>>('/cargos/', { params: { page_size: 100 } })
  return data.results
}

/** O catalogo inteiro, sem paginacao: a tela monta uma caixa por permissao. */
export async function fetchPermissoes(): Promise<Permissao[]> {
  const { data } = await api.get<Permissao[]>('/permissoes/')
  return data
}

export interface CargoEscrita {
  slug: string
  nome: string
  descricao?: string
  permissoes: PermissaoKey[]
}

export async function criarCargo(dados: CargoEscrita): Promise<Cargo> {
  const { data } = await api.post<Cargo>('/cargos/', dados)
  return data
}

export async function atualizarCargo(id: number, mudancas: Partial<CargoEscrita>): Promise<Cargo> {
  const { data } = await api.patch<Cargo>(`/cargos/${id}/`, mudancas)
  return data
}

export async function apagarCargo(id: number): Promise<void> {
  await api.delete(`/cargos/${id}/`)
}
