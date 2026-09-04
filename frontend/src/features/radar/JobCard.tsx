import { Check, Pencil, RotateCcw, X } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { formatJobDate } from '@/lib/format'
import { resumoDaVaga } from '@/lib/vaga'
import type { Job } from '@/types/api'

/** Faixas de score: 30 para cima e boa, 12 para cima e olhavel, abaixo e ruido. */
function scoreTone(score: number): string {
  if (score >= 30) return 'text-ok'
  if (score >= 12) return 'text-warn'
  return 'text-muted'
}

interface Props {
  job: Job
  podeTriar: boolean
  /** Ausente quando quem esta olhando nao tem `vagas.gerenciar`. */
  onEditar: ((job: Job) => void) | null
  onQuero: (job: Job) => void
  onDescartar: (job: Job) => void
  onRestaurar: (job: Job) => void
}

export function JobCard({
  job,
  podeTriar,
  onEditar,
  onQuero,
  onDescartar,
  onRestaurar,
}: Props) {
  const data = job.published_at
    ? `Publicada em: ${formatJobDate(job.published_at)}`
    : `Coletada em: ${formatJobDate(job.created_at)}`
  const apoio = resumoDaVaga(job)

  const titulo = (
    <a
      href={job.url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-ink outline-none hover:text-accent hover:underline focus-visible:underline"
    >
      {job.title}
    </a>
  )

  const corpo = (
    <>
      <h3 className="text-[15px] leading-snug font-semibold">{titulo}</h3>

      <p className="mt-1 text-[12.5px] text-muted">
        {job.location}
        {job.location && data && ' - '}
        {data}
      </p>

      {apoio && <p className="mt-1.5 text-[12.5px] text-muted">{apoio}</p>}
    </>
  )

  // Lapis em vez de rotulo: corrigir vaga e acao rara perto de triar, e um
  // botao escrito ao lado do "quero" competiria com a decisao do dia a dia.
  const editar = onEditar && (
    <IconButton
      type="button"
      aria-label={`Editar a vaga ${job.title}`}
      title="Editar vaga"
      onClick={() => onEditar(job)}
      className="max-lg:h-11 max-lg:w-11"
    >
      <Pencil size={15} />
    </IconButton>
  )

  // Vaga descartada nao se tria de novo: o unico caminho e devolver para a fila.
  const acoes = podeTriar && job.discarded && (
    <Button
      size="sm"
      onClick={() => onRestaurar(job)}
      className="max-lg:h-11 max-lg:flex-1"
    >
      <RotateCcw size={15} />
      devolver para a fila
    </Button>
  )

  const acoesTriagem = podeTriar && !job.discarded && (
    <>
      {/* Sem rotulo visivel, o botao precisa do nome acessivel: um check
          sozinho nao diz nada para quem navega por leitor de tela. */}
      <Button
        variant="primary"
        size="sm"
        aria-label="Quero aplicar"
        title="Quero aplicar"
        onClick={() => onQuero(job)}
        className="max-lg:h-11 max-lg:flex-1"
      >
        <Check size={15} strokeWidth={2.8} />
      </Button>
      <Button
        size="sm"
        aria-label="Descartar vaga"
        title="Descartar vaga"
        onClick={() => onDescartar(job)}
        className="max-lg:h-11 max-lg:flex-1"
      >
        <X size={15} strokeWidth={2.4} />
      </Button>
    </>
  )

  return (
    <article className="rounded-[10px] border border-line bg-card transition-colors hover:border-field">
      {/* Desktop: score, corpo e acoes numa linha so, centrados na vertical. */}
      <div className="hidden items-center gap-3 px-4 py-3.5 lg:flex">
        <div
          className={`w-11 shrink-0 text-center text-[22px] leading-none font-semibold tabular-nums ${scoreTone(job.score)}`}
          title="Score de aderência ao seu perfil"
        >
          {job.score}
        </div>

        <div className="min-w-0 flex-1">{corpo}</div>

        {(podeTriar || editar) && (
          <div className="flex shrink-0 items-center gap-1.5">
            {editar}
            {acoes || acoesTriagem}
          </div>
        )}
      </div>

      {/* Mobile: empilha, com o score na linha do titulo. */}
      <div className="flex flex-col p-3.5 lg:hidden">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">{corpo}</div>
          <span
            className={`shrink-0 text-[21px] leading-none font-semibold tabular-nums ${scoreTone(job.score)}`}
            title="Score de aderência ao seu perfil"
          >
            {job.score}
          </span>
        </div>

        {(podeTriar || editar) && (
          <div className="mt-3 flex items-center gap-2">
            {editar}
            {acoes || acoesTriagem}
          </div>
        )}
      </div>
    </article>
  )
}
