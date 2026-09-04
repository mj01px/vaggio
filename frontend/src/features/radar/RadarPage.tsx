import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { CircleAlert } from 'lucide-react'
import { EmptyState } from '@/components/ui/EmptyState'
import { Pagination } from '@/components/ui/Pagination'
import { StateMessage } from '@/components/ui/StateMessage'
import { useToast } from '@/hooks/useToast'
import { EditarVagaPanel } from '@/features/radar/EditarVagaPanel'
import { JobCard } from '@/features/radar/JobCard'
import { NovaVagaPanel } from '@/features/radar/NovaVagaPanel'
import { RadarFilters } from '@/features/radar/RadarFilters'
import type { RadarFilterValues } from '@/features/radar/constants'
import { usePode } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { createApplication } from '@/services/applications.service'
import {
  PAGE_SIZE,
  discardJob,
  fetchJobs,
  restoreJob,
  runCollection,
} from '@/services/jobs.service'
import type { Job, Paginated } from '@/types/api'

type Acao = 'quero' | 'descartar'

export function RadarPage() {
  const [params, setParams] = useSearchParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  // O id do aviso de andamento, para fechar assim que a resposta chegar.
  const coletando = useRef<number | null>(null)
  const [error, setError] = useState('')
  const [cadastrando, setCadastrando] = useState(false)
  // A vaga aberta para edicao, ou nenhuma.
  const [editando, setEditando] = useState<Job | null>(null)
  const podeTriar = usePode('vagas.triar')
  const podeEditar = usePode('vagas.gerenciar')
  const podeColetar = usePode('coleta.rodar')

  const page = Math.max(1, Number(params.get('page') ?? 1) || 1)

  const filters: RadarFilterValues = {
    queue: params.get('queue') ?? '',
    q: params.get('q') ?? '',
    source: params.get('source') ?? '',
    min_score: params.get('min_score') ?? '',
    published_after: params.get('published_after') ?? '',
    published_before: params.get('published_before') ?? '',
  }
  const queryKey = ['jobs', { ...filters, page: String(page) }] as const

  const jobs = useQuery({
    queryKey,
    queryFn: () => fetchJobs({ ...filters, page: String(page) }),
  })

  const encontradas = jobs.data?.count ?? 0

  /** Tira um filtro sozinho, sem mexer nos outros nem na pagina. */
  function removerFiltro(chave: keyof RadarFilterValues) {
    const proximos = new URLSearchParams(params)
    proximos.delete(chave)
    proximos.delete('page')
    setParams(proximos)
  }

  function goToPage(next: number) {
    const proximos = new URLSearchParams(params)
    if (next <= 1) proximos.delete('page')
    else proximos.set('page', String(next))
    setParams(proximos)
    window.scrollTo({ top: 0 })
  }

  // Descartar as ultimas de uma pagina pode deixar voce numa pagina que nao
  // existe mais, e a API responde 404. Volta para o comeco em vez de travar
  // numa tela de erro sem saida.
  useEffect(() => {
    if (jobs.isError && page > 1) goToPage(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs.isError, page])

  /**
   * Triagem otimista.
   *
   * O cartao sai da lista no clique e so depois a chamada volta. Com 100 itens
   * por pagina, esperar o refetch a cada decisao custava mais tempo do que a
   * propria decisao, e a vaga ja triada seguia visivel enquanto isso.
   */
  const triar = useMutation({
    // Devolve void de proposito: quem manda na lista e o cache que o onMutate
    // ja ajustou, entao a resposta das duas rotas nao tem uso aqui.
    mutationFn: async ({ job, acao }: { job: Job; acao: Acao }): Promise<void> => {
      if (acao === 'quero') await createApplication(job.id)
      else await discardJob(job.id)
    },
    onMutate: async ({ job }) => {
      setError('')
      await queryClient.cancelQueries({ queryKey })
      const anterior = queryClient.getQueryData<Paginated<Job>>(queryKey)
      queryClient.setQueryData<Paginated<Job>>(queryKey, (atual) =>
        atual
          ? {
              ...atual,
              count: Math.max(0, atual.count - 1),
              results: atual.results.filter((item) => item.id !== job.id),
            }
          : atual,
      )
      return { anterior }
    },
    onError: (err, { acao }, contexto) => {
      if (contexto?.anterior) queryClient.setQueryData(queryKey, contexto.anterior)
      setError(
        apiErrorMessage(
          err,
          acao === 'quero'
            ? 'Nao deu para mandar a vaga para o board. Ela voltou para a fila.'
            : 'Nao deu para descartar a vaga. Ela voltou para a fila.',
        ),
      )
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['job-stats'] })
      void queryClient.invalidateQueries({ queryKey: ['board'] })
      // Sem refetch: a lista visivel ja esta correta e recarregar 100 itens a
      // cada triagem faria a pagina piscar. Ela se atualiza na proxima visita.
      void queryClient.invalidateQueries({ queryKey: ['jobs'], refetchType: 'none' })
    },
  })

  const restaurar = useMutation({
    mutationFn: (job: Job) => restoreJob(job.id),
    onMutate: async (job) => {
      setError('')
      await queryClient.cancelQueries({ queryKey })
      const anterior = queryClient.getQueryData<Paginated<Job>>(queryKey)
      // Na fila de descartadas a vaga sai da lista; em "todas" ela fica, so
      // troca de estado. Filtrar nos dois casos removeria do lugar errado.
      if (filters.queue === 'discarded') {
        queryClient.setQueryData<Paginated<Job>>(queryKey, (atual) =>
          atual
            ? {
                ...atual,
                count: Math.max(0, atual.count - 1),
                results: atual.results.filter((item) => item.id !== job.id),
              }
            : atual,
        )
      }
      return { anterior }
    },
    onError: (err, _job, contexto) => {
      if (contexto?.anterior) queryClient.setQueryData(queryKey, contexto.anterior)
      setError(apiErrorMessage(err, 'Nao deu para devolver a vaga para a fila.'))
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['job-stats'] })
    },
  })

  const collect = useMutation({
    mutationFn: runCollection,
    onMutate: () => {
      setError('')
      // Sem duracao: quem fecha e a resposta. Um relogio fixo apagaria o aviso
      // no meio de uma coleta lenta e a tela ficaria sem sinal de vida.
      coletando.current = toast.mostrar({
        tom: 'carregando',
        titulo: 'Consultando GitHub e Gupy.',
        duracao: null,
      })
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['job-stats'] })
      void queryClient.invalidateQueries({ queryKey: ['board'] })

      const vistas = result.sources.reduce((soma, fonte) => soma + fonte.found, 0)
      toast.mostrar({
        tom: 'ok',
        titulo:
          result.new === 0
            ? 'Nenhuma vaga nova.'
            : `${result.new} ${result.new === 1 ? 'vaga nova' : 'vagas novas'}.`,
        detalhe: `${vistas} conferidas nas fontes.`,
      })
      // Fonte fora do ar nao impede o resto: avisa sem apagar o que veio.
      if (result.errors.length > 0) {
        toast.mostrar({
          tom: 'bad',
          titulo: 'Uma fonte falhou.',
          detalhe: result.errors.map((falha) => `${falha.source}: ${falha.message}`).join(' | '),
          duracao: null,
        })
      }
    },
    onError: (err) =>
      toast.mostrar({
        tom: 'bad',
        titulo: apiErrorMessage(err, 'Nao deu para buscar vagas novas.'),
        duracao: null,
      }),
    onSettled: () => {
      if (coletando.current !== null) toast.fechar(coletando.current)
      coletando.current = null
    },
  })

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const next = new URLSearchParams()
    // A fila sobrevive ao filtro: ela e a visao, nao um corte. Sem isto,
    // aplicar um filtro dentro de "Descartadas" devolvia para a triagem.
    if (filters.queue) next.set('queue', filters.queue)
    for (const key of ['q', 'source', 'min_score', 'published_after', 'published_before']) {
      const value = String(form.get(key) ?? '').trim()
      if (value) next.set(key, value)
    }
    // Filtro novo comeca da primeira pagina: manter a pagina 9 de um filtro
    // que agora tem 2 paginas cairia direto num 404.
    setParams(next)
  }

  const vazia = jobs.data?.results.length === 0

  return (
    <div className="flex flex-col gap-4">
      <RadarFilters
        filters={filters}
        onSubmit={submitFilters}
        onClear={() => setParams(filters.queue ? new URLSearchParams({ queue: filters.queue }) : new URLSearchParams())}
        onRemover={removerFiltro}
        podeColetar={podeColetar}
        coletando={collect.isPending}
        onColetar={() => collect.mutate()}
        podeTriar={podeTriar}
        onCadastrar={() => setCadastrando(true)}
      />

      {cadastrando && <NovaVagaPanel onClose={() => setCadastrando(false)} />}

      {editando && <EditarVagaPanel job={editando} onClose={() => setEditando(null)} />}

      <div className="min-w-0">
        {error && (
          <div className="mb-3 flex items-start gap-2.5 rounded-[10px] border border-bad bg-card px-4 py-3 text-bad">
            <CircleAlert size={16} className="mt-0.5 shrink-0" />
            <p className="min-w-0">{error}</p>
          </div>
        )}

        {jobs.isPending && <StateMessage>Carregando a fila...</StateMessage>}

        {jobs.isError && (
          <StateMessage tone="bad">
            {apiErrorMessage(jobs.error, 'A API nao respondeu. O backend esta rodando na 8000?')}
          </StateMessage>
        )}

        {vazia && (
          <EmptyState>
            <p className="text-ink">Nada na fila com esses filtros.</p>
            <p className="mt-1">
              Abra a faixa de datas, limpe os filtros
              {podeColetar ? ' ou clique em "buscar vagas novas".' : '.'}
            </p>
          </EmptyState>
        )}

        <div className="flex flex-col gap-2">
          {jobs.data?.results.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              podeTriar={podeTriar}
              onEditar={podeEditar ? setEditando : null}
              onQuero={(alvo) => triar.mutate({ job: alvo, acao: 'quero' })}
              onDescartar={(alvo) => triar.mutate({ job: alvo, acao: 'descartar' })}
              onRestaurar={(alvo) => restaurar.mutate(alvo)}
            />
          ))}
        </div>

        <Pagination page={page} count={encontradas} pageSize={PAGE_SIZE} onChange={goToPage} />
      </div>
    </div>
  )
}
