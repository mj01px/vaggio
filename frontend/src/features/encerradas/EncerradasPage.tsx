import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { StateMessage } from '@/components/ui/StateMessage'
import { useToast } from '@/hooks/useToast'
import { apiErrorMessage } from '@/lib/api'
import { formatJobDate } from '@/lib/format'
import { resumoDaVaga } from '@/lib/vaga'
import { deleteApplication, fetchEncerradas } from '@/services/applications.service'
import type { Application, Encerradas } from '@/types/api'

type Corte = 'todas' | 'rejected' | 'withdrawn'

/**
 * As candidaturas que sairam do funil.
 *
 * Rejeitada e Desisti moram na mesma tela porque as duas respondem a mesma
 * pergunta, "o que ja acabou", e separa-las em duas paginas obrigaria a abrir
 * as duas para ter a lista inteira. O filtro em cima resolve quando so uma das
 * pontas interessa.
 */
export function EncerradasPage() {
  const [corte, setCorte] = useState<Corte>('todas')
  // A linha esperando confirmacao de apagar, ou nenhuma.
  const [confirmando, setConfirmando] = useState<number | null>(null)

  const queryClient = useQueryClient()
  const toast = useToast()

  const encerradas = useQuery({ queryKey: ['encerradas'], queryFn: fetchEncerradas })

  const apagar = useMutation({
    mutationFn: deleteApplication,
    // Otimista: a linha some no clique. Apagar e a unica acao da tela, e
    // esperar a volta da rede para ver a lista encolher parece travado.
    onMutate: async (id: number) => {
      setConfirmando(null)
      await queryClient.cancelQueries({ queryKey: ['encerradas'] })
      const anterior = queryClient.getQueryData<Encerradas>(['encerradas'])
      queryClient.setQueryData<Encerradas>(['encerradas'], (atual) => {
        if (!atual) return atual
        const alvo = atual.results.find((item) => item.id === id)
        if (!alvo) return atual
        return {
          results: atual.results.filter((item) => item.id !== id),
          stats: {
            rejected: atual.stats.rejected - (alvo.status === 'rejected' ? 1 : 0),
            withdrawn: atual.stats.withdrawn - (alvo.status === 'withdrawn' ? 1 : 0),
          },
        }
      })
      return { anterior }
    },
    onError: (err, _id, contexto) => {
      if (contexto?.anterior) queryClient.setQueryData(['encerradas'], contexto.anterior)
      toast.mostrar({
        tom: 'bad',
        titulo: apiErrorMessage(err, 'Nao deu para apagar a candidatura.'),
        duracao: null,
      })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['encerradas'] })
      // O contador de encerradas do Dashboard sai da mesma contagem.
      void queryClient.invalidateQueries({ queryKey: ['board'] })
    },
  })

  if (encerradas.isPending) return <StateMessage>Carregando as encerradas...</StateMessage>

  if (encerradas.isError) {
    return (
      <StateMessage tone="bad">
        {apiErrorMessage(encerradas.error, 'Nao deu para carregar as encerradas.')}
      </StateMessage>
    )
  }

  const { results, stats } = encerradas.data
  const lista = corte === 'todas' ? results : results.filter((item) => item.status === corte)

  if (results.length === 0) {
    return (
      <EmptyState>
        <p className="text-[14.5px] font-medium text-ink">Nada encerrado ainda</p>
        <p className="mt-1 text-[13px]">
          Uma candidatura chega aqui quando você a marca como rejeitada ou desiste dela.
        </p>
      </EmptyState>
    )
  }

  const cortes: { valor: Corte; rotulo: string; total: number }[] = [
    { valor: 'todas', rotulo: 'Todas', total: results.length },
    { valor: 'rejected', rotulo: 'Não passei', total: stats.rejected },
    { valor: 'withdrawn', rotulo: 'Desistiu', total: stats.withdrawn },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {cortes.map(({ valor, rotulo, total }) => (
          <Button
            key={valor}
            type="button"
            size="sm"
            aria-pressed={corte === valor}
            onClick={() => setCorte(valor)}
            className={corte === valor ? 'border-ink! bg-surface! font-semibold' : ''}
          >
            {rotulo}
            <span className="text-muted tabular-nums">{total}</span>
          </Button>
        ))}
      </div>

      {lista.length === 0 ? (
        <EmptyState>Nenhuma candidatura nesse corte.</EmptyState>
      ) : (
        <ul className="flex flex-col gap-2">
          {lista.map((application) => (
            <Linha
              key={application.id}
              application={application}
              confirmando={confirmando === application.id}
              onPedirConfirmacao={() => setConfirmando(application.id)}
              onCancelar={() => setConfirmando(null)}
              onApagar={() => apagar.mutate(application.id)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

interface LinhaProps {
  application: Application
  confirmando: boolean
  onPedirConfirmacao: () => void
  onCancelar: () => void
  onApagar: () => void
}

function Linha({
  application,
  confirmando,
  onPedirConfirmacao,
  onCancelar,
  onApagar,
}: LinhaProps) {
  const { job } = application
  const apoio = resumoDaVaga(job)
  const desistiu = application.status === 'withdrawn'

  return (
    <li className="rounded-[10px] border border-line bg-card px-4 py-3.5">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-[15px] leading-snug font-semibold">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-ink outline-none hover:text-accent hover:underline focus-visible:underline"
            >
              {job.title}
            </a>
          </h3>

          <p className="mt-1 text-[12.5px] text-muted">
            {job.location}
            {job.location && ' - '}
            Encerrada em: {formatJobDate(application.updated_at)}
          </p>

          {apoio && <p className="mt-1.5 text-[12.5px] text-muted">{apoio}</p>}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1.5">
          {/* A cor separa as duas saidas sem precisar de rotulo comprido: quem
              desistiu foi decisao sua, quem rejeitou foi decisao deles. */}
          <span className={`text-[12.5px] font-medium ${desistiu ? 'text-muted' : 'text-bad'}`}>
            {desistiu ? 'Desistiu' : 'Não passei'}
          </span>

          {/* Confirmacao na propria linha, e nao num modal: apagar aqui e
              definitivo e leva a linha do tempo junto, entao um clique so nao
              pode bastar. */}
          {confirmando ? (
            <div className="flex items-center gap-1.5">
              <span className="text-[12.5px] text-muted">Apagar?</span>
              <Button
                type="button"
                size="sm"
                variant="destrutivo"
                onClick={onApagar}
                className="max-lg:h-11"
              >
                sim
              </Button>
              <Button type="button" size="sm" onClick={onCancelar} className="max-lg:h-11">
                não
              </Button>
            </div>
          ) : (
            <IconButton
              type="button"
              aria-label={`Apagar a candidatura para ${job.title}`}
              title="Apagar de vez"
              onClick={onPedirConfirmacao}
              className="hover:text-bad max-lg:h-11 max-lg:w-11"
            >
              <Trash2 size={16} />
            </IconButton>
          )}
        </div>
      </div>
    </li>
  )
}
