import { useState, type ReactNode } from 'react'

interface Props {
  label: string
  /** Total real da etapa, o que o endpoint contou antes de qualquer filtro. */
  total: number
  /** Quantos cartoes estao visiveis agora, que muda quando o filtro liga. */
  visiveis: number
  filtrando: boolean
  /** Falso no mobile, onde o seletor de etapa ja diz onde a pessoa esta. */
  comCabecalho?: boolean
  /** Nulo desliga a soltura: quem so ve o funil nao recebe cartao. */
  onSoltar?: (() => void) | null
  /** Ha um cartao sendo arrastado agora, de qualquer coluna. */
  arrastando?: boolean
  className?: string
  children: ReactNode
}

/**
 * Uma etapa do funil: cabecalho parado em cima, cartoes rolando embaixo.
 *
 * O cabecalho fica fora da area rolavel de proposito. Com seis colunas de
 * alturas diferentes, saber em que etapa voce esta olhando so funciona se o
 * rotulo nao subir junto com os cartoes.
 */
export function BoardColuna({
  label,
  total,
  visiveis,
  filtrando,
  comCabecalho = true,
  onSoltar = null,
  arrastando = false,
  className = '',
  children,
}: Props) {
  const [sobre, setSobre] = useState(false)
  const recebe = onSoltar !== null

  return (
    <section
      aria-label={label}
      // `preventDefault` no dragOver e o que autoriza a soltura: sem ele o
      // navegador recusa o drop e o cartao volta para a coluna de origem.
      onDragOver={recebe ? (evento) => { evento.preventDefault(); setSobre(true) } : undefined}
      onDragLeave={recebe ? (evento) => {
        // So apaga o realce quando o ponteiro sai da coluna de verdade: passar
        // por cima de um cartao filho tambem dispara dragLeave.
        if (!evento.currentTarget.contains(evento.relatedTarget as Node)) setSobre(false)
      } : undefined}
      onDrop={recebe ? (evento) => { evento.preventDefault(); setSobre(false); onSoltar() } : undefined}
      className={`flex min-h-0 flex-col rounded-[10px] border bg-surface ${
        sobre ? 'border-accent bg-wash' : arrastando ? 'border-dashed border-field' : 'border-line'
      } ${className}`}
    >
      {comCabecalho && (
        <header className="flex shrink-0 items-center gap-2 border-b border-line px-3 py-2.5">
          <h2 className="truncate text-[11.5px] font-semibold tracking-wide text-muted uppercase">
            {label}
          </h2>
          <span className="ml-auto shrink-0 text-xs text-muted tabular-nums">
            {filtrando ? (
              <>
                <b className="text-ink">{visiveis}</b> de {total}
              </>
            ) : (
              <b className="text-ink">{total}</b>
            )}
          </span>
        </header>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2">{children}</div>
    </section>
  )
}

/** O buraco na coluna, discreto: e o estado normal de metade do funil. */
export function ColunaVazia({ filtrando }: { filtrando: boolean }) {
  return (
    <p className="rounded-lg border border-dashed border-line px-3 py-6 text-center text-xs text-muted">
      {filtrando ? 'nenhuma atrasada aqui' : 'nenhuma candidatura nesta etapa'}
    </p>
  )
}
