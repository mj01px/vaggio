import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { Card, CardHeader } from '@/components/ui/Card'
import type { ColetaRun } from './dashboard.service'
import { quandoRodou } from './tempo'

interface Props {
  coletas: ColetaRun[]
  carregando: boolean
  /** Mensagem da API quando a consulta falhou, ou nulo. */
  erro: string | null
}

/**
 * As ultimas execucoes da coleta.
 *
 * O que se procura aqui e uma coisa so: as fontes ainda estao trazendo vaga?
 * Por isso "novas de encontradas" no lugar do numero solto, e a falha em
 * vermelho na propria linha, sem precisar abrir o historico.
 */
export function UltimasColetas({ coletas, carregando, erro }: Props) {
  return (
    <Card className="p-4">
      <CardHeader titulo="Últimas coletas">
        <Link
          to="/coletas"
          className="ml-auto inline-flex items-center gap-1 rounded-lg text-[13px] font-medium text-accent outline-none hover:underline focus-visible:border focus-visible:border-ink"
        >
          Histórico
          <ChevronRight size={14} aria-hidden />
        </Link>
      </CardHeader>

      {carregando && <p className="mt-3 text-[13px] text-muted">Carregando as coletas...</p>}

      {erro && <p className="mt-3 text-[13px] text-bad">{erro}</p>}

      {!carregando && !erro && coletas.length === 0 && (
        <p className="mt-3 text-[13px] text-muted">
          Nenhuma coleta registrada ainda. O botão que dispara a busca fica no Radar.
        </p>
      )}

      {!carregando && !erro && coletas.length > 0 && (
        <ul className="mt-1.5">
          {coletas.map((coleta) => (
            <li
              key={coleta.id}
              className="flex items-baseline justify-between gap-3 border-b border-line py-2.5 last:border-0 last:pb-0"
            >
              <div className="min-w-0">
                <div className="text-[13.5px] font-medium">{coleta.source_display}</div>
                <div className="text-[12px] text-muted">{quandoRodou(coleta.started_at)}</div>
              </div>

              <div className="min-w-0 text-right">
                <div className="text-[13px] tabular-nums">
                  <span className="font-semibold">{coleta.new_count}</span>
                  <span className="text-muted"> novas de {coleta.found_count}</span>
                </div>
                {coleta.error && (
                  <div className="truncate text-[12px] text-bad" title={coleta.error}>
                    {coleta.error}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
