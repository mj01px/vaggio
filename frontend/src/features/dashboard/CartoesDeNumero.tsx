import type { LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/Card'

export interface Metrica {
  rotulo: string
  valor: number
  /** Opcional: a linha curta que explica o que o numero conta. */
  legenda?: string
  /** Opcional: nem todo numero ganha icone. */
  icone?: LucideIcon
  /** Vermelho so quando o numero pede acao. Zero atrasadas nao e alarme. */
  alerta?: boolean
}

/**
 * A faixa de numeros do topo.
 *
 * Quatro colunas quando ha espaco, duas no meio do caminho e uma no estreito:
 * o numero grande so funciona enquanto o cartao tem largura para ele.
 *
 * A medida e da area de conteudo, nao da janela: com a sidebar aberta sobram
 * 1192px numa tela de 1440, e um breakpoint de viewport nao enxerga isso.
 */
export function CartoesDeNumero({ metricas }: { metricas: Metrica[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 @2xl:grid-cols-2 @5xl:grid-cols-4">
      {metricas.map(({ rotulo, valor, legenda, icone: Icone, alerta }) => (
        <Card key={rotulo} tone={alerta ? 'bad' : 'default'} className="px-4 py-3.5">
          <div className="flex items-start justify-between gap-2">
            <span className="text-[11.5px] font-semibold tracking-wide text-muted uppercase">
              {rotulo}
            </span>
            {Icone && (
              <Icone size={17} className={alerta ? 'text-bad' : 'text-muted'} aria-hidden />
            )}
          </div>

          <div
            className={`mt-1 text-[30px] leading-[36px] font-semibold tabular-nums ${
              alerta ? 'text-bad' : 'text-ink'
            }`}
          >
            {valor}
          </div>
          {legenda && <div className="text-[12.5px] text-muted">{legenda}</div>}
        </Card>
      ))}
    </div>
  )
}
