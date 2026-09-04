import { useQuery } from '@tanstack/react-query'
import { Archive, TrendingUp } from 'lucide-react'
import { EmptyState } from '@/components/ui/EmptyState'
import { StateMessage } from '@/components/ui/StateMessage'
import { usePode } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { fetchBoard } from '@/services/applications.service'
import { fetchJobStats } from '@/services/jobs.service'
import { CartoesDeNumero, type Metrica } from './CartoesDeNumero'
import { FunilPorEtapa } from './FunilPorEtapa'
import { PrecisaDeVoce } from './PrecisaDeVoce'
import { UltimasColetas } from './UltimasColetas'
import { fetchColetasRecentes } from './dashboard.service'

/**
 * A primeira tela de dentro: o estado do dia em quatro numeros, o que venceu, a
 * forma do funil e se a coleta continua trazendo vaga.
 *
 * Todo numero daqui sai da API. Nada e derivado, estimado nem somado de duas
 * rotas: numero que a tela inventa e numero em que ninguem confia na segunda
 * vez que abre.
 *
 * Cada bloco depende de uma permissao diferente, e por isso cada consulta so
 * sai quando o cargo libera. Quem nao ve o funil ainda abre o dashboard: perde
 * os blocos de candidatura, nao a tela inteira.
 */
export function DashboardPage() {
  const podeVerFunil = usePode('funil.ver')
  const podeVerVagas = usePode('vagas.ver')
  const podeVerColeta = usePode('coleta.ver')

  // Mesma chave do Board de proposito: quem vem de la ja encontra o cache quente.
  const board = useQuery({ queryKey: ['board'], queryFn: fetchBoard, enabled: podeVerFunil })

  // Sem o funil, o unico numero real que sobra e a fila do radar. A consulta so
  // sai quando ela e a unica fonte: com o board na mao, `radar_queue` ja veio.
  const jobStats = useQuery({
    queryKey: ['job-stats'],
    queryFn: fetchJobStats,
    enabled: !podeVerFunil && podeVerVagas,
  })

  const coletas = useQuery({
    queryKey: ['coletas-recentes'],
    queryFn: fetchColetasRecentes,
    enabled: podeVerColeta,
  })

  const stats = board.data?.stats

  const metricas: Metrica[] = stats
    ? [
        {
          rotulo: 'No funil',
          valor: stats.in_funnel,
          legenda: 'candidaturas ativas',
          icone: TrendingUp,
        },
        {
          rotulo: 'Atrasadas',
          valor: stats.overdue,
          legenda: 'follow-up vencido',
          // Zero atrasadas e a boa noticia do dia: pintar de vermelho gastaria
          // o alarme justamente quando nao ha o que alarmar.
          alerta: stats.overdue > 0,
        },
        {
          rotulo: 'No radar',
          valor: stats.radar_queue,
        },
        {
          rotulo: 'Encerradas',
          valor: stats.closed,
          icone: Archive,
        },
      ]
    : jobStats.data
      ? [
          {
            rotulo: 'No radar',
            valor: jobStats.data.triage,
          },
        ]
      : []

  // `isLoading`, e nao `isPending`: consulta desligada pela permissao fica
  // pendente para sempre, e a tela ficaria carregando sem nunca ter pedido nada.
  const carregandoNumeros = board.isLoading || jobStats.isLoading

  const erroNumeros = board.isError
    ? apiErrorMessage(board.error, 'Nao deu para carregar os números do funil.')
    : jobStats.isError
      ? apiErrorMessage(jobStats.error, 'Nao deu para carregar a fila do radar.')
      : null

  // `@container` e nao breakpoint de viewport: a largura util muda quando a
  // sidebar recolhe, e `lg:` continuaria olhando a janela e decidindo errado.
  return (
    <div className="@container flex flex-col gap-4">
      {carregandoNumeros ? (
        <StateMessage>Carregando os números...</StateMessage>
      ) : erroNumeros ? (
        <StateMessage tone="bad">{erroNumeros}</StateMessage>
      ) : metricas.length > 0 ? (
        <CartoesDeNumero metricas={metricas} />
      ) : (
        <EmptyState>
          Seu cargo não libera o funil nem o radar, então não há número para mostrar aqui.
        </EmptyState>
      )}

      {!podeVerFunil && metricas.length > 0 && (
        <p className="text-[12.5px] text-muted">
          Seu cargo não libera ver o funil, então as candidaturas ficam de fora desta tela.
        </p>
      )}

      {board.isSuccess && (
        <div className="grid gap-4 @4xl:grid-cols-2">
          <PrecisaDeVoce atrasadas={board.data.overdue} />
          <FunilPorEtapa colunas={board.data.columns} />
        </div>
      )}

      {podeVerColeta && (
        <UltimasColetas
          coletas={coletas.data ?? []}
          carregando={coletas.isLoading}
          erro={
            coletas.isError
              ? apiErrorMessage(coletas.error, 'Nao deu para carregar as coletas.')
              : null
          }
        />
      )}
    </div>
  )
}
