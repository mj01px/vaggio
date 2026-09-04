import { Button } from '@/components/ui/Button'

interface Props {
  /** Pagina atual, 1-based. */
  page: number
  /** Total de itens que o filtro atual encontrou, nao o da pagina. */
  count: number
  pageSize: number
  onChange: (page: number) => void
}

/**
 * Navegacao de paginas da fila.
 *
 * Mostra a faixa de itens ("101 a 200 de 1256") em vez de so o numero da
 * pagina: com a fila na casa do milhar, saber onde voce esta na lista importa
 * mais do que saber que esta na pagina 2.
 */
export function Pagination({ page, count, pageSize, onChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  if (count === 0) return null

  const primeiro = (page - 1) * pageSize + 1
  const ultimo = Math.min(page * pageSize, count)

  return (
    <nav className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3.5 text-xs text-muted">
      <span>
        <b className="text-ink">
          {primeiro} - {ultimo}
        </b>{' '}
        de {count}
      </span>

      {/* O rotulo visivel e so a seta; o acessivel vai por extenso no
          aria-label, senao o botao fica mudo em leitor de tela. */}
      <div className="ml-auto flex items-center gap-1.5">
        <Button
          size="sm"
          type="button"
          aria-label="Página anterior"
          title="Página anterior"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          &lt;&lt;
        </Button>
        <span className="px-1">
          <b className="text-ink">{page}</b> de {totalPages}
        </span>
        <Button
          size="sm"
          type="button"
          aria-label="Próxima página"
          title="Próxima página"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          &gt;&gt;
        </Button>
      </div>
    </nav>
  )
}
