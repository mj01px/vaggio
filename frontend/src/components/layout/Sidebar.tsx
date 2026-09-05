import { LogOut, PanelLeft, PanelRight, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { IconButton } from '@/components/ui/Button'
import { useSessao } from '@/hooks/useSessao'
import { GRUPOS, type ItemNav } from './navegacao'

interface Props {
  /** Recolhida: 64px, so icones. */
  trilho: boolean
  onAlternarTrilho: () => void
  /** No mobile a sidebar vira gaveta sobreposta. */
  gaveta?: boolean
  onFechar?: () => void
}

const item = (trilho: boolean) =>
  ({ isActive }: { isActive: boolean }) =>
    [
      'flex h-10 items-center rounded-lg text-sm outline-none focus-visible:border focus-visible:border-ink',
      trilho ? 'w-10 justify-center' : 'gap-[11px] px-3',
      // Item parado usa `muted`, o mesmo do sair e do recolher: a sidebar
      // inteira fala num tom so, e ai o unico realce da coluna e o item ativo.
      isActive
        ? 'bg-wash font-semibold text-accent'
        : 'font-medium text-muted hover:bg-surface hover:text-ink',
    ].join(' ')

export function Sidebar({ trilho, onAlternarTrilho, gaveta = false, onFechar }: Props) {
  const { perfil, sair } = useSessao()

  const podeVer = (i: ItemNav) =>
    !i.exige || (perfil?.permissoes.includes(i.exige) ?? false)

  // Na gaveta o trilho nao existe: quem abriu quer ler os rotulos.
  const compacto = trilho && !gaveta

  return (
    // `h-full` e o que segura a gaveta no mobile. No desktop o pai e flex e
    // estica o filho sozinho; na gaveta o pai e um bloco posicionado, entao
    // sem altura explicita a barra parava na altura do conteudo e o fundo da
    // tela aparecia por baixo do "Sair".
    <div
      className={`flex h-full shrink-0 flex-col border-r border-line bg-card ${
        compacto ? 'w-16 items-center' : 'w-62'
      }`}
    >
      {/* Sem divisor sob a marca. A altura de 64px continua, para a logo ficar
          na mesma linha do topo do conteudo. */}
      <div
        className={`flex h-16 shrink-0 items-center ${
          compacto ? 'w-full justify-center' : 'w-full justify-between pr-4 pl-5'
        }`}
      >
        {/* A marca leva para o dashboard, que e a home do app. O bloco inteiro
            e o alvo, e nao so a imagem: 22px de logo e um alvo pequeno demais. */}
        <NavLink
          to="/dashboard"
          onClick={onFechar}
          title="Ir para o Dashboard"
          className="flex items-center gap-2.5 rounded-lg px-1 py-1 outline-none hover:opacity-75 focus-visible:border focus-visible:border-ink"
        >
          <img src="/logo-mark.png" alt="Vaggio" className="h-[22px] w-auto" />
          {!compacto && (
            <span className="text-sm font-semibold tracking-[0.08em] uppercase">Vaggio</span>
          )}
        </NavLink>
        {/* So o fechar da gaveta fica aqui em cima. Recolher e expandir moram
            no rodape, junto do sair: sao as duas acoes da moldura, e nao da
            navegacao, entao ficam no mesmo canto. */}
        {gaveta && !compacto && (
          <IconButton type="button" aria-label="Fechar menu" onClick={onFechar}>
            <X size={19} />
          </IconButton>
        )}
      </div>

      <nav
        className={`flex flex-1 flex-col overflow-y-auto py-3.5 ${compacto ? 'items-center gap-1' : 'px-3'}`}
      >
        {GRUPOS.map((grupo, indice) => {
          const itens = grupo.itens.filter(podeVer)
          if (itens.length === 0) return null

          return (
            <div key={grupo.titulo} className={compacto ? 'contents' : ''}>
              {compacto ? (
                // No trilho nao cabe rotulo de grupo; o divisor faz esse papel.
                indice > 0 && <div className="my-3 h-px w-6 bg-line" />
              ) : (
                <div
                  className={`px-3 text-[11px] font-semibold tracking-[0.09em] text-muted uppercase ${
                    indice > 0 ? 'mt-[22px] mb-[7px]' : 'mb-[7px]'
                  }`}
                >
                  {grupo.titulo}
                </div>
              )}

              <div className={compacto ? 'contents' : 'flex flex-col gap-0.5'}>
                {itens.map(({ para, rotulo, icone: Icone }) => (
                  <NavLink
                    key={para}
                    to={para}
                    onClick={onFechar}
                    className={item(compacto)}
                    title={compacto ? rotulo : undefined}
                  >
                    <Icone size={18} className="shrink-0" />
                    {!compacto && rotulo}
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      {/* Sair mora aqui, longe do bloco de identidade que subiu para a topbar,
          e ao lado dele o recolher. No trilho os dois empilham: 64px nao
          comportam dois alvos de 40px lado a lado. */}
      <div className={`shrink-0 border-t border-line p-3 ${compacto ? 'w-full' : ''}`}>
        <div className={`flex gap-1 ${compacto ? 'flex-col items-center' : 'items-center'}`}>
          <button
            type="button"
            onClick={sair}
            title={compacto ? 'Sair' : undefined}
            // Vermelho: e a unica acao da coluna que tem consequencia, e num
            // painel todo em `muted` a cor sozinha ja separa ela do resto.
            className={`flex h-10 cursor-pointer items-center rounded-lg text-sm font-medium text-bad outline-none hover:bg-bad/5 focus-visible:border focus-visible:border-bad ${
              compacto ? 'w-10 justify-center' : 'flex-1 gap-[11px] px-3'
            }`}
          >
            <LogOut size={18} className="shrink-0" />
            {!compacto && 'Sair'}
          </button>

          {/* Na gaveta nao existe trilho: ela so abre ou fecha, e o fechar
              ja esta no topo. */}
          {!gaveta && (
            <IconButton
              type="button"
              aria-label={compacto ? 'Expandir menu' : 'Recolher menu'}
              title={compacto ? 'Expandir menu' : 'Recolher menu'}
              onClick={onAlternarTrilho}
            >
              {compacto ? <PanelRight size={17} /> : <PanelLeft size={17} />}
            </IconButton>
          )}
        </div>
      </div>
    </div>
  )
}
