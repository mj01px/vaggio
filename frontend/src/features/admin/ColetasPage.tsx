import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Pagination } from '@/components/ui/Pagination'
import { apiErrorMessage } from '@/lib/api'
import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'

interface Coleta {
  id: number
  source: string
  source_display: string
  started_at: string
  finished_at: string | null
  duration_seconds: number | null
  found_count: number
  new_count: number
  error: string
}

/** Quinze linhas cabem na tela sem rolar a pagina para achar a paginacao. */
const POR_PAGINA = 15

async function fetchColetas(page: number): Promise<Paginated<Coleta>> {
  const { data } = await api.get<Paginated<Coleta>>('/collections/', {
    params: { page_size: POR_PAGINA, ...(page > 1 ? { page } : {}) },
  })
  return data
}

const CABECALHO =
  'px-4 py-2.5 text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase lg:px-5'
const CELULA = 'px-4 py-3 lg:px-5'

function quando(valor: string): string {
  return new Date(valor).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Historico das coletas. Era so no admin do Django. */
export function ColetasPage() {
  const [page, setPage] = useState(1)

  const coletas = useQuery({
    queryKey: ['coletas', page],
    queryFn: () => fetchColetas(page),
    // Segura a pagina anterior enquanto a proxima carrega: sem isto a tabela
    // some no clique da seta e a tela salta.
    placeholderData: keepPreviousData,
  })

  const lista = coletas.data?.results

  // Card com borda e `overflow-hidden`: sem ele a faixa cinza do cabecalho
  // vaza por cima dos cantos arredondados e sobra um canto quadrado.
  return (
    <div>
      <div className="overflow-hidden rounded-[10px] border border-line bg-card">
        {coletas.isPending && <p className="p-8 text-center text-muted">Carregando...</p>}

        {coletas.isError && (
          <p className="p-8 text-center text-bad">
            {apiErrorMessage(coletas.error, 'Nao deu para carregar o histórico.')}
          </p>
        )}

        {lista?.length === 0 && (
          <div className="p-8 text-center text-muted">
            <p className="text-[14.5px] font-medium text-ink">Nenhuma coleta ainda</p>
            <p className="mt-1 text-[13px]">O botão de buscar vagas novas fica no Radar.</p>
          </div>
        )}

        {/* A tabela rola dentro do card. Sem a largura minima o navegador
            quebra "GitHub Issues" em duas linhas antes de aceitar rolar. */}
        {lista && lista.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] table-fixed text-left text-[13.5px]">
              <thead className="bg-surface">
                <tr>
                  <th className={`w-[24%] ${CABECALHO}`}>Quando</th>
                  <th className={`w-[22%] ${CABECALHO}`}>Fonte</th>
                  <th className={`w-[12%] text-right ${CABECALHO}`}>Vistas</th>
                  <th className={`w-[12%] text-right ${CABECALHO}`}>Novas</th>
                  <th className={`w-[12%] text-right ${CABECALHO}`}>Duração</th>
                  <th className={`w-[18%] ${CABECALHO}`}>Erro</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {lista.map((coleta) => (
                  <tr key={coleta.id} className="transition-colors hover:bg-surface">
                    <td className={`${CELULA} whitespace-nowrap text-muted tabular-nums`}>
                      {quando(coleta.started_at)}
                    </td>
                    <td className={`${CELULA} truncate`}>{coleta.source_display}</td>
                    <td className={`${CELULA} text-right tabular-nums`}>{coleta.found_count}</td>
                    {/* Vagas novas e o unico numero que responde "valeu a pena
                        rodar", entao ele fica em cor e o resto em cinza. */}
                    <td
                      className={`${CELULA} text-right font-semibold tabular-nums ${
                        coleta.new_count > 0 ? 'text-ok' : 'text-muted'
                      }`}
                    >
                      {coleta.new_count}
                    </td>
                    <td className={`${CELULA} text-right text-muted tabular-nums`}>
                      {coleta.duration_seconds ? `${coleta.duration_seconds.toFixed(0)}s` : '—'}
                    </td>
                    <td
                      className={`${CELULA} truncate text-bad`}
                      title={coleta.error || undefined}
                    >
                      {coleta.error || <span className="text-muted">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Pagination
        page={page}
        count={coletas.data?.count ?? 0}
        pageSize={POR_PAGINA}
        onChange={setPage}
      />
    </div>
  )
}
