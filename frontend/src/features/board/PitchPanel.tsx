import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Sparkles, TriangleAlert, X } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { StateMessage } from '@/components/ui/StateMessage'
import { useSessao } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { TAMANHO_DE_PITCH_PADRAO, TAMANHOS_DE_PITCH } from '@/lib/pitch'
import { fetchPitches, generatePitch } from '@/services/pitch.service'
import type { Application, Pitch } from '@/types/api'

interface Props {
  application: Application
  onClose: () => void
}

export function PitchPanel({ application, onClose }: Props) {
  const { job } = application
  const queryClient = useQueryClient()

  // Comeca pelo padrao do Perfil. Antes era 1200 fixo aqui, o que deixava a
  // preferencia salva sem efeito nenhum.
  const { perfil } = useSessao()
  const [maxChars, setMaxChars] = useState(
    perfil?.pitch_max_chars ?? TAMANHO_DE_PITCH_PADRAO,
  )
  const [instrucao, setInstrucao] = useState('')
  const [copiado, setCopiado] = useState(false)
  const [error, setError] = useState('')

  const pitches = useQuery({
    queryKey: ['pitches', job.id],
    queryFn: () => fetchPitches(job.id),
  })

  // Esc fecha, como qualquer modal se comporta.
  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [onClose])

  const gerar = useMutation({
    mutationFn: () => generatePitch(job.id, { max_chars: maxChars, instrucao }),
    onMutate: () => setError(''),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['pitches', job.id] })
    },
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para gerar a apresentacao.')),
  })

  async function copiar(texto: string) {
    try {
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      setError('O navegador bloqueou a copia. Selecione o texto e copie na mao.')
    }
  }

  const versoes = pitches.data ?? []

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/45 p-4"
      onClick={onClose}
    >
      {/* Sombra aqui e proposital: o painel esta acima da pagina, ao contrario
          do cartao parado do board, que se resolve com borda. */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pitch-titulo"
        className="mt-6 mb-6 w-full max-w-3xl rounded-[10px] border border-line bg-card p-4 shadow-xl lg:p-5"
        onClick={(evento) => evento.stopPropagation()}
      >
        <div className="mb-4 flex items-start gap-3 border-b border-line pb-3">
          <div className="min-w-0 flex-1">
            <h2 id="pitch-titulo" className="text-[15px] font-semibold">
              Apresente-se
            </h2>
            <p className="mt-0.5 truncate text-xs text-muted">{job.title}</p>
          </div>
          <IconButton
            type="button"
            aria-label="Fechar"
            onClick={onClose}
            className="max-lg:h-11 max-lg:w-11"
          >
            <X size={18} />
          </IconButton>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="w-[190px] shrink-0">
            <Select
              inputSize="sm"
              aria-label="Tamanho do texto"
              className="max-lg:h-11"
              options={TAMANHOS_DE_PITCH.map((tamanho) => ({
                value: String(tamanho),
                label: `${tamanho} Caracteres`,
              }))}
              value={String(maxChars)}
              onChange={(valor) => setMaxChars(Number(valor))}
            />
          </div>

          <div className="min-w-[240px] flex-1">
            <Input
              inputSize="sm"
              className="max-lg:h-11"
              aria-label="Ajuste opcional"
              value={instrucao}
              onChange={(evento) => setInstrucao(evento.target.value)}
              maxLength={300}
              placeholder="ajuste opcional, ex: puxa o lado de dados"
            />
          </div>

          <Button
            type="button"
            variant="primary"
            size="sm"
            className="gap-2 max-lg:h-11"
            disabled={gerar.isPending}
            onClick={() => gerar.mutate()}
          >
            <Sparkles size={16} />
            {gerar.isPending ? 'gerando...' : versoes.length ? 'gerar outra' : 'gerar'}
          </Button>
        </div>

        {gerar.isPending && (
          <StateMessage>
            Escrevendo com base no seu dossie e nesta vaga.
          </StateMessage>
        )}

        {error && (
          <div
            role="alert"
            className="mb-3 flex items-start gap-2 rounded-[10px] border border-bad bg-card px-3.5 py-2.5 text-[13px] text-bad"
          >
            <TriangleAlert size={16} className="mt-px shrink-0" />
            {error}
          </div>
        )}

        {pitches.isPending && <StateMessage>Carregando as versoes...</StateMessage>}

        {!pitches.isPending && versoes.length === 0 && !gerar.isPending && (
          <p className="rounded-[10px] border border-dashed border-line px-4 py-8 text-center text-[13px] text-muted">
            Nenhuma versao ainda. O texto sai do seu dossie cruzado com esta vaga.
          </p>
        )}

        {versoes.map((pitch, indice) => (
          <Versao
            key={pitch.id}
            pitch={pitch}
            atual={indice === 0}
            copiado={copiado}
            onCopiar={() => void copiar(pitch.texto)}
          />
        ))}

        {versoes.length > 0 && (
          <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
            Revise antes de colar. O texto sai do seu dossie, mas quem responde por ele numa
            entrevista e voce.
          </p>
        )}
      </div>
    </div>
  )
}

interface VersaoProps {
  pitch: Pitch
  atual: boolean
  copiado: boolean
  onCopiar: () => void
}

function Versao({ pitch, atual, copiado, onCopiar }: VersaoProps) {
  const acima = pitch.caracteres > pitch.max_chars

  return (
    <article
      className={`mb-3 rounded-[10px] border bg-surface px-3.5 py-3 ${
        atual ? 'border-accent' : 'border-line'
      }`}
    >
      <div className="mb-2 flex flex-wrap items-center gap-2 text-[11.5px] text-muted">
        {/* Estourar o limite nao invalida o texto, so avisa que vai precisar
            de corte, entao a cor fica mesmo sem a pilula em volta. */}
        <span className={acima ? 'font-medium text-warn' : undefined}>
          {pitch.caracteres} de {pitch.max_chars} caracteres
        </span>
        {pitch.instrucao && <span className="truncate">· {pitch.instrucao}</span>}
        <Button
          type="button"
          size="sm"
          className="ml-auto gap-2 max-lg:h-11"
          onClick={onCopiar}
        >
          {copiado ? <Check size={15} /> : <Copy size={15} />}
          {copiado ? 'copiado' : 'copiar'}
        </Button>
      </div>
      <p className="text-[13.5px] leading-relaxed whitespace-pre-wrap text-ink">{pitch.texto}</p>
    </article>
  )
}
