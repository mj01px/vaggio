import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Inbox, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Contador } from '@/components/ui/Pill'
import { StateMessage } from '@/components/ui/StateMessage'
import { usePode } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { fetchBoard, updateApplication } from '@/services/applications.service'
import type { Application, ApplicationStatusKey, Board, BoardColumn } from '@/types/api'
import { BoardColuna, ColunaVazia } from './BoardColuna'
import { CandidaturaCard } from './CandidaturaCard'
import { DetalhePanel } from './DetalhePanel'
import { PitchPanel } from './PitchPanel'
import { contarAtrasadas, moverNoBoard } from './board.utils'
import { useArrasteToque } from './useArrasteToque'

/**
 * A largura da coluna no kanban.
 *
 * Elastica com piso e teto em vez de fixa: em tela larga as seis colunas
 * ocupam o espaco todo sem sobra, e quando o piso de 248px nao cabe mais o
 * board rola na horizontal em vez de espremer o titulo da vaga.
 */
const LARGURA_COLUNA = 'flex-1 min-w-[248px] max-w-[340px]'

interface Mover {
  id: number
  status: ApplicationStatusKey
}

export function BoardPage() {
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  // A candidatura com o painel de apresentacao aberto, ou nenhuma.
  const [apresentando, setApresentando] = useState<Application | null>(null)
  // A candidatura com o painel de detalhes aberto, ou nenhuma.
  const [detalhando, setDetalhando] = useState<Application | null>(null)
  // Ligado, o board mostra so quem esta com follow-up vencido.
  const [soAtrasadas, setSoAtrasadas] = useState(false)
  // A etapa aberta no mobile. Nula ate a pessoa escolher, e ai vale a primeira.
  const [etapa, setEtapa] = useState<ApplicationStatusKey | null>(null)
  // A candidatura sendo arrastada agora, ou nenhuma.
  const [arrastando, setArrastando] = useState<number | null>(null)

  const podeGerenciar = usePode('funil.gerenciar')
  const podeApresentar = usePode('apresentacao.gerar')

  const board = useQuery({ queryKey: ['board'], queryFn: fetchBoard })

  const move = useMutation({
    mutationFn: ({ id, status }: Mover) => updateApplication(id, { status }),
    // Mutacao otimista: o cartao troca de coluna na hora e volta sozinho se a
    // API recusar. Sem isso o board parece travado a cada mudanca de etapa.
    onMutate: async ({ id, status }) => {
      setError('')
      await queryClient.cancelQueries({ queryKey: ['board'] })
      const anterior = queryClient.getQueryData<Board>(['board'])
      if (anterior) {
        queryClient.setQueryData<Board>(['board'], moverNoBoard(anterior, id, status))
      }
      return { anterior }
    },
    onError: (err, _variaveis, contexto) => {
      if (contexto?.anterior) queryClient.setQueryData(['board'], contexto.anterior)
      setError(apiErrorMessage(err, 'Nao deu para mover a candidatura.'))
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['board'] })
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  // O toque solta em cima do chip de etapa; o mouse solta na coluna. Os dois
  // caem na mesma mutacao otimista.
  const toque = useArrasteToque((id, status) => {
    const atual = board.data?.columns.find((coluna) =>
      coluna.items.some((item) => item.id === id),
    )
    if (atual?.status === status) return
    move.mutate({ id, status })
  })

  const data = board.data
  const atrasadas = data?.overdue.length ?? 0
  // O filtro so vale enquanto existir atraso: sem esta guarda, mover a ultima
  // atrasada deixaria o board vazio com o botao do filtro ja fora da tela.
  const filtrando = soAtrasadas && atrasadas > 0

  const colunas: BoardColumn[] = useMemo(() => {
    if (!data) return []
    if (!filtrando) return data.columns
    return data.columns.map((coluna) => ({
      ...coluna,
      items: coluna.items.filter((item) => item.is_overdue),
    }))
  }, [data, filtrando])

  if (board.isPending) return <StateMessage>Carregando as candidaturas...</StateMessage>

  if (board.isError || !data) {
    return (
      <StateMessage tone="bad">
        {apiErrorMessage(board.error, 'A API nao respondeu. O backend esta rodando na 8000?')}
      </StateMessage>
    )
  }

  const { statuses } = data
  const vazio = data.columns.every((coluna) => coluna.total === 0)
  const movendoId = move.isPending ? move.variables.id : null
  const colunaAberta = colunas.find((coluna) => coluna.status === etapa) ?? colunas[0]

  /**
   * Soltar na coluna move a candidatura para a etapa dela.
   *
   * Soltar na propria coluna de origem nao dispara nada: o backend aceitaria,
   * mas seria uma escrita a toa e um piscar de lista sem motivo.
   */
  function soltarEm(status: ApplicationStatusKey) {
    const id = arrastando
    setArrastando(null)
    if (id === null) return
    const atual = colunas.find((coluna) => coluna.items.some((item) => item.id === id))
    if (atual?.status === status) return
    move.mutate({ id, status })
  }

  /** O mesmo cartao serve o kanban e a lista do mobile. */
  function cartoes(coluna: BoardColumn) {
    if (coluna.items.length === 0) return <ColunaVazia filtrando={filtrando} />
    return coluna.items.map((application) => (
      <CandidaturaCard
        key={application.id}
        application={application}
        statuses={statuses}
        podeGerenciar={podeGerenciar}
        movendo={movendoId === application.id}
        onMover={(status) => move.mutate({ id: application.id, status })}
        onArrastar={setArrastando}
        onPegar={(evento) => toque.comecar(evento, application.id, application.job.title)}
        naMao={toque.arraste?.id === application.id}
        onApresentar={podeApresentar ? () => setApresentando(application) : null}
        onAbrirDetalhe={() => setDetalhando(application)}
      />
    ))
  }

  return (
    // h-full com min-h-0 e o que deixa a rolagem dentro das colunas: a pagina
    // fica parada e cada etapa rola por conta propria.
    <div className="flex h-full min-h-0 flex-col gap-3">
      {/* O cartao fantasma segue o dedo. Sem ele o arraste no toque nao tem
          retorno nenhum: a pessoa segura, move e nao ve nada sair do lugar. */}
      {toque.arraste && (
        <div
          aria-hidden
          style={{ left: toque.arraste.x, top: toque.arraste.y }}
          className="pointer-events-none fixed z-50 max-w-[220px] -translate-x-1/2 -translate-y-1/2 truncate rounded-lg border border-accent bg-card px-3 py-2 text-[12.5px] font-semibold shadow-lg shadow-ink/20"
        >
          {toque.arraste.titulo}
        </div>
      )}

      {apresentando && (
        <PitchPanel application={apresentando} onClose={() => setApresentando(null)} />
      )}

      {detalhando && (
        <DetalhePanel
          application={detalhando}
          podeGerenciar={podeGerenciar}
          onClose={() => setDetalhando(null)}
        />
      )}

      {error && (
        <div
          role="alert"
          className="flex shrink-0 items-start gap-2 rounded-[10px] border border-bad bg-card px-3.5 py-2.5 text-[13px] text-bad"
        >
          <TriangleAlert size={16} className="mt-px shrink-0" />
          {error}
        </div>
      )}

      {!vazio && (
        <FiltroAtrasadas
          atrasadas={atrasadas}
          ligado={filtrando}
          onAlternar={() => setSoAtrasadas((atual) => !atual)}
        />
      )}

      {vazio ? (
        <EmptyState>
          <Inbox size={22} className="mx-auto mb-2 text-muted" />
          <p className="text-[14.5px] font-medium text-ink">Nenhuma candidatura no funil</p>
          <p className="mt-1 text-[13px]">
            Esta tela enche a partir do{' '}
            <Link to="/radar" className="text-accent underline">
              Radar
            </Link>
            : marque "quero" numa vaga e ela entra em Quero aplicar.
          </p>
        </EmptyState>
      ) : (
        <>
          {/* Mobile: seis colunas lado a lado nao cabem, entao o board vira uma
              etapa por vez com este seletor no lugar do scroll horizontal. */}
          <SeletorEtapa
            colunas={colunas}
            colunasReais={data.columns}
            aberta={colunaAberta?.status ?? null}
            alvo={toque.alvo}
            onEscolher={setEtapa}
          />

          {colunaAberta && (
            <BoardColuna
              key={colunaAberta.status}
              label={colunaAberta.label}
              total={colunaAberta.total}
              visiveis={colunaAberta.items.length}
              filtrando={filtrando}
              comCabecalho={false}
              className="min-h-0 flex-1 lg:hidden"
            >
              {cartoes(colunaAberta)}
            </BoardColuna>
          )}

          {/* Desktop: o kanban de verdade, rolando na horizontal se faltar espaco. */}
          <div className="hidden min-h-0 flex-1 gap-3 overflow-x-auto pb-1 lg:flex">
            {colunas.map((coluna) => (
              <BoardColuna
                key={coluna.status}
                label={coluna.label}
                total={coluna.total}
                visiveis={coluna.items.length}
                filtrando={filtrando}
                arrastando={arrastando !== null}
                onSoltar={podeGerenciar ? () => soltarEm(coluna.status) : null}
                className={LARGURA_COLUNA}
              >
                {cartoes(coluna)}
              </BoardColuna>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * A faixa das atrasadas.
 *
 * Nao perder follow-up e a promessa do produto, entao o numero fica fixo no
 * topo do board e um clique isola as vencidas nas seis colunas de uma vez.
 * Uma lista solta em cima, como era antes, repetia cartao e empurrava o
 * kanban para fora da tela justo nos dias em que ha mais o que fazer.
 */
function FiltroAtrasadas({
  atrasadas,
  ligado,
  onAlternar,
}: {
  atrasadas: number
  ligado: boolean
  onAlternar: () => void
}) {
  // Sem atraso, nada aparece: o Dashboard ja abre dizendo que esta tudo em dia,
  // e repetir aqui gasta uma linha da barra para nao informar nada novo.
  if (atrasadas === 0) return null

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      <Button
        type="button"
        size="sm"
        aria-pressed={ligado}
        onClick={onAlternar}
        // O `!` e proposital: ligado precisa vencer a borda e o fundo que a
        // variante neutra ja aplica, sem depender da ordem das classes.
        className={`max-lg:h-11 ${ligado ? 'border-ink! bg-surface!' : ''}`}
      >
        <TriangleAlert size={16} className="text-bad" />
        Follow-up vencido
        <Contador>{atrasadas}</Contador>
      </Button>
      <span className="text-[12.5px] text-muted">
        {ligado ? 'mostrando so as atrasadas' : 'clique para ver so as atrasadas'}
      </span>
    </div>
  )
}

/**
 * O seletor de etapa do mobile.
 *
 * Cada etapa carrega o proprio contador e o numero de atrasadas, senao a
 * pessoa teria de abrir uma por uma para descobrir onde esta o atraso.
 */
function SeletorEtapa({
  colunas,
  colunasReais,
  aberta,
  alvo,
  onEscolher,
}: {
  colunas: BoardColumn[]
  colunasReais: BoardColumn[]
  aberta: ApplicationStatusKey | null
  /** A etapa sob o dedo durante um arraste, ou nula. */
  alvo: ApplicationStatusKey | null
  onEscolher: (status: ApplicationStatusKey) => void
}) {
  return (
    <div
      role="group"
      aria-label="Etapa do funil"
      className="-mx-1 flex shrink-0 gap-1.5 overflow-x-auto px-1 pb-1 lg:hidden"
    >
      {colunas.map((coluna) => {
        const ativa = coluna.status === aberta
        const recebendo = coluna.status === alvo
        const real = colunasReais.find((item) => item.status === coluna.status)
        const vencidas = contarAtrasadas(real?.items ?? [])
        return (
          <button
            key={coluna.status}
            type="button"
            data-etapa={coluna.status}
            aria-pressed={ativa}
            onClick={() => onEscolher(coluna.status)}
            className={`inline-flex h-11 shrink-0 cursor-pointer items-center gap-2 rounded-lg border px-3 text-[13.5px] outline-none focus-visible:border-ink ${
              recebendo
                ? 'border-accent bg-wash font-semibold text-accent'
                : ativa
                  ? 'border-ink bg-card font-semibold text-ink'
                  : 'border-line bg-card text-muted'
            }`}
          >
            {coluna.label}
            <span className="tabular-nums">{coluna.items.length}</span>
            {vencidas > 0 && <Contador>{vencidas}</Contador>}
          </button>
        )
      })}
    </div>
  )
}
