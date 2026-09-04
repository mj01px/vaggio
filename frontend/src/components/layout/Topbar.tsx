import { Menu } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { IconButton } from '@/components/ui/Button'
import { useSessao } from '@/hooks/useSessao'

/** As iniciais que o avatar mostra quando nao ha foto. */
function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean)
  if (partes.length === 0) return '?'
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase()
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase()
}

/**
 * A barra de cima: so o menu do mobile e quem esta logado.
 *
 * O titulo da tela nao mora aqui. Ele e do conteudo, e o `AppLayout` desenha
 * logo acima do que a pagina renderiza, para ficar junto do que ele nomeia.
 */
export function Topbar({ onAbrirMenu }: { onAbrirMenu: () => void }) {
  const { perfil } = useSessao()
  const nome = perfil?.nome || perfil?.email || '?'

  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-line bg-card pr-5 pl-3 lg:pl-6">
      <IconButton
        type="button"
        aria-label="Abrir menu"
        onClick={onAbrirMenu}
        className="lg:hidden"
      >
        <Menu size={21} />
      </IconButton>

      <NavLink
        to="/perfil"
        className="ml-auto flex shrink-0 items-center gap-2.5 rounded-full py-1 pr-2 pl-1 outline-none hover:bg-surface focus-visible:border focus-visible:border-ink"
      >
        <span className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full bg-accent text-[13px] font-semibold text-white">
          {iniciais(nome)}
        </span>
        <span className="hidden max-w-[180px] truncate text-[13.5px] font-semibold sm:block">
          {nome}
        </span>
      </NavLink>
    </header>
  )
}
