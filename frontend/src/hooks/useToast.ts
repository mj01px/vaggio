import { createContext, useContext } from 'react'

export type ToastTom = 'carregando' | 'ok' | 'bad'

export interface Toast {
  id: number
  tom: ToastTom
  titulo: string
  detalhe?: string
  /** Em ms. `null` deixa fixo ate alguem fechar. */
  duracao: number | null
}

export interface Aviso {
  tom?: ToastTom
  titulo: string
  detalhe?: string
  duracao?: number | null
}

export interface ToastApi {
  /** Devolve o id, para quem abriu poder fechar antes da hora. */
  mostrar: (aviso: Aviso) => number
  fechar: (id: number) => void
}

/**
 * O contexto mora aqui, e nao junto do componente, porque exportar hook e
 * componente do mesmo arquivo derruba o fast refresh do Vite.
 */
export const ToastContext = createContext<ToastApi>({ mostrar: () => 0, fechar: () => {} })

export function useToast(): ToastApi {
  return useContext(ToastContext)
}
