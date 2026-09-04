import { Card, CardHeader } from '@/components/ui/Card'
import type { BoardColumn } from '@/types/api'

/**
 * Quantas candidaturas param em cada etapa do funil.
 *
 * A barra e proporcional ao maior valor, e nao ao total somado: o que se le
 * aqui e onde a fila engrossa, e com fatia do total as etapas pequenas
 * viravam todas o mesmo tracinho.
 */
export function FunilPorEtapa({ colunas }: { colunas: BoardColumn[] }) {
  const maior = colunas.reduce((maximo, coluna) => Math.max(maximo, coluna.total), 0)
  const total = colunas.reduce((soma, coluna) => soma + coluna.total, 0)

  return (
    <Card className="p-4">
      <CardHeader titulo="Funil por etapa">
        <span className="ml-auto text-[12.5px] text-muted">
          {total} {total === 1 ? 'candidatura ativa' : 'candidaturas ativas'}
        </span>
      </CardHeader>

      <ul className="mt-3.5 flex flex-col gap-2.5">
        {colunas.map((coluna) => (
          <li key={coluna.status}>
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="truncate">{coluna.label}</span>
              <span className="shrink-0 font-semibold tabular-nums">{coluna.total}</span>
            </div>

            {/* Decorativa: o numero ao lado ja diz o valor para quem usa leitor de tela. */}
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface" aria-hidden>
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: maior > 0 ? `${(coluna.total / maior) * 100}%` : '0%' }}
              />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}
