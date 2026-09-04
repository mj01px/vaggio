import { useCallback, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { cabecalhoDaRota } from './navegacao'

const CHAVE_TRILHO = 'vaggio:sidebar-trilho'

/**
 * O shell de todas as telas de dentro: sidebar, topbar e a area de conteudo.
 *
 * `data-tema="claro"` fixa os tokens claros neste ramo da arvore, como o login
 * ja fazia. O app inteiro segue a mesma regua; o tema do SO de quem abre nao
 * decide a aparencia do produto.
 */
export function AppLayout() {
  const { pathname } = useLocation()
  const cabecalho = cabecalhoDaRota(pathname)
  const [gaveta, setGaveta] = useState(false)
  const [trilho, setTrilho] = useState(
    () => localStorage.getItem(CHAVE_TRILHO) === '1',
  )

  const alternarTrilho = useCallback(() => {
    setTrilho((atual) => {
      const proximo = !atual
      localStorage.setItem(CHAVE_TRILHO, proximo ? '1' : '0')
      return proximo
    })
  }, [])

  // A gaveta fecha no clique do proprio item de navegacao (`onFechar` desce
  // para cada NavLink), e nao num efeito ouvindo a rota: sincronizar estado com
  // efeito aqui so causaria uma renderizacao a mais para chegar no mesmo lugar.

  return (
    <div data-tema="claro" className="flex h-screen overflow-hidden bg-surface text-ink">
      <div className="hidden lg:flex">
        <Sidebar trilho={trilho} onAlternarTrilho={alternarTrilho} />
      </div>

      {gaveta && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="absolute inset-0 bg-ink/45"
            onClick={() => setGaveta(false)}
            aria-hidden
          />
          <div className="relative">
            <Sidebar
              trilho={false}
              onAlternarTrilho={alternarTrilho}
              gaveta
              onFechar={() => setGaveta(false)}
            />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onAbrirMenu={() => setGaveta(true)} />

        {/* O cabecalho e desenhado aqui, e nao em cada pagina, porque nenhuma
            precisa decidir nada sobre ele: o nome e a descricao ja saem da
            rota. Fica no conteudo, colado no que ele nomeia. */}
        <main className="flex flex-1 flex-col overflow-y-auto p-4 lg:p-6">
          <div className={`mb-4 shrink-0 ${cabecalho.largura ?? ''}`}>
            <h1 className="text-[22px] leading-tight font-semibold tracking-tight">
              {cabecalho.titulo}
            </h1>
            {cabecalho.descricao && (
              <p className="mt-1 text-[13.5px] text-muted">{cabecalho.descricao}</p>
            )}
          </div>

          <div className={`min-h-0 flex-1 ${cabecalho.largura ?? ''}`}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
