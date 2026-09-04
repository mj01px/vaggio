import { createContext, useContext } from 'react'
import type { Perfil, PermissaoKey } from '@/types/api'

export interface SessaoContexto {
  perfil: Perfil | null
  recarregar: () => void
  sair: () => void
}

export const SessaoContext = createContext<SessaoContexto>({
  perfil: null,
  recarregar: () => {},
  sair: () => {},
})

export function useSessao() {
  return useContext(SessaoContext)
}

/**
 * Se o perfil logado pode a acao.
 *
 * A tela usa isto para esconder botao que ia dar 403. Nao e seguranca: quem
 * decide de verdade e o backend, e ele checa de novo em toda chamada.
 */
export function usePode(permissao: PermissaoKey): boolean {
  const { perfil } = useSessao()
  return perfil?.permissoes.includes(permissao) ?? false
}
