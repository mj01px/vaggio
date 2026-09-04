import { GripVertical, Pencil, Sparkles } from 'lucide-react'
import { IconButton } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { formatDate } from '@/lib/format'
import { resumoDaVaga } from '@/lib/vaga'
import type { Application, ApplicationStatusKey, Board } from '@/types/api'

/** A partir de quantos dias parada a candidatura merece um aviso no cartao. */
const DIAS_PARA_AVISAR = 7

/** As duas saidas fechadas do funil, que nao tem coluna no board. */
const FECHADAS: ApplicationStatusKey[] = ['rejected', 'withdrawn']

/**
 * O select do cartao lista a etapa atual e as duas saidas fechadas.
 *
 * Andar no funil e arrastar o cartao, entao repetir as seis etapas aqui era
 * oferecer duas vezes o mesmo caminho. Rejeitada e Desisti ficam porque nao
 * tem coluna nenhuma: sao os dois destinos que o arraste nao alcanca.
 */
function opcoes(statuses: Board['statuses'], atual: ApplicationStatusKey) {
  return statuses
    .filter((status) => status.value === atual || FECHADAS.includes(status.value))
    // Aqui o select e um menu de acao, nao um rotulo de estado: quem le esta
    // escolhendo o que fazer. O backend guarda "Desisti", que e como a
    // candidatura aparece depois, na tela de encerradas.
    .map((status) =>
      status.value === 'withdrawn' ? { ...status, label: 'Desistir' } : status,
    )
}

interface Props {
  application: Application
  statuses: Board['statuses']
  /** Falso esconde o select e o botao: quem so ve o funil nao mexe nele. */
  podeGerenciar: boolean
  /** Esta candidatura especifica esta sendo movida agora. */
  movendo: boolean
  onMover: (status: ApplicationStatusKey) => void
  /** Comeco e fim do arraste de mouse, para a coluna saber quem esta vindo. */
  onArrastar: (id: number | null) => void
  /** Aperto no punho de arraste do mobile. */
  onPegar: (evento: React.PointerEvent) => void
  /** Este cartao esta sendo arrastado com o dedo agora. */
  naMao: boolean
  onApresentar: (() => void) | null
  onAbrirDetalhe: () => void
}

/**
 * O cartao de candidatura.
 *
 * Segue a mesma linguagem do cartao do Radar: titulo, uma linha de local e uma
 * de apoio, tudo em texto corrido. Sem pilula, porque numa coluna de 248px uma
 * faixa de badge ocupa mais altura do que informa.
 *
 * A borda esquerda existe nos dois estados, vermelha no atraso e cinza no
 * resto, para o cartao nao mudar de largura quando o follow-up vence: o que
 * muda e a cor, nao a geometria.
 */
export function CandidaturaCard({
  application,
  statuses,
  podeGerenciar,
  movendo,
  onMover,
  onArrastar,
  onPegar,
  naMao,
  onApresentar,
  onAbrirDetalhe,
}: Props) {
  const { job } = application
  const atrasada = application.is_overdue
  const parada = !atrasada && application.days_idle >= DIAS_PARA_AVISAR
  const apoio = resumoDaVaga(job)

  return (
    <article
      // So arrasta quem pode mover. O HTML5 nativo cobre mouse no desktop; no
      // toque e no teclado quem move e o select do rodape, que continua ali.
      draggable={podeGerenciar}
      onDragStart={(evento) => {
        evento.dataTransfer.setData('text/plain', String(application.id))
        evento.dataTransfer.effectAllowed = 'move'
        onArrastar(application.id)
      }}
      onDragEnd={() => onArrastar(null)}
      className={`rounded-[10px] border border-l-[3px] bg-card px-3 py-2.5 ${
        atrasada ? 'border-bad/35 border-l-bad' : 'border-line border-l-line'
      } ${movendo || naMao ? 'opacity-55' : ''} ${podeGerenciar ? 'lg:cursor-grab lg:active:cursor-grabbing' : ''}`}
    >
      <h3 className="text-[13.5px] leading-[18px] font-semibold">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-ink outline-none hover:text-accent hover:underline focus-visible:underline"
        >
          {job.title}
        </a>
      </h3>

      {job.location && <p className="mt-1 truncate text-[12px] text-muted">{job.location}</p>}

      {apoio && <p className="mt-1 truncate text-[12px] text-muted">{apoio}</p>}

      {/* O proximo passo e a promessa do produto, entao ele nunca vira cinza:
          vencido sai em vermelho, e o resto fica no tom normal do texto. */}
      {atrasada ? (
        <p className="mt-2 text-[12px] text-bad">
          <span className="font-semibold">Vencido em {formatDate(application.next_step_on)}</span>
          {application.next_step && ` · ${application.next_step}`}
        </p>
      ) : (
        application.next_step && (
          <p className="mt-2 text-[12px]">
            {application.next_step}
            {application.next_step_on && (
              <span className="text-muted"> · {formatDate(application.next_step_on)}</span>
            )}
          </p>
        )
      )}

      {(application.has_referral || parada) && (
        <p className="mt-1.5 text-[11.5px] text-muted">
          {application.has_referral && 'Indicado'}
          {application.has_referral && parada && ' · '}
          {parada && `Parada há ${application.days_idle} dias`}
        </p>
      )}

      {/* O rodape aparece sempre: ate quem so le o funil abre os detalhes,
          onde as notas e a linha do tempo ficam em modo leitura. */}
      <div className="mt-2.5 flex items-center gap-1.5">
          {/* O punho existe so no toque, e leva `touch-action: none` para o
              deslize sobre ele arrastar o cartao em vez de rolar a coluna.
              Fora dele a coluna rola normal, que e o que se espera do resto. */}
          {podeGerenciar && (
            <button
              type="button"
              aria-label={`Arrastar ${job.title} para outra etapa`}
              onPointerDown={onPegar}
              className="flex h-11 w-9 shrink-0 touch-none items-center justify-center rounded-lg text-muted lg:hidden"
            >
              <GripVertical size={18} />
            </button>
          )}

          {podeGerenciar && (
            <div className="min-w-0 flex-1">
              <Select
                inputSize="sm"
                className="max-lg:h-11 max-lg:text-[14.5px]"
                aria-label={`Mudar o estado de ${job.title}`}
                options={opcoes(statuses, application.status)}
                value={application.status}
                disabled={movendo}
                onChange={(valor) => onMover(valor as ApplicationStatusKey)}
              />
            </div>
          )}

          <IconButton
            type="button"
            title="Detalhes, notas e linha do tempo"
            aria-label={`Abrir detalhes de ${job.title}`}
            onClick={onAbrirDetalhe}
            className="shrink-0"
          >
            <Pencil size={16} />
          </IconButton>

          {onApresentar && (
            <IconButton
              type="button"
              title="Apresente-se"
              aria-label={`Gerar apresentação para ${job.title}`}
              onClick={onApresentar}
              className="shrink-0"
            >
              <Sparkles size={16} />
            </IconButton>
          )}
      </div>
    </article>
  )
}
