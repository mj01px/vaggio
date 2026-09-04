import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { Campo, Input } from '@/components/ui/Input'
import { Select as Lista } from '@/components/ui/Select'
import { useToast } from '@/hooks/useToast'
import { apiErrorMessage } from '@/lib/api'
import { updateApplication } from '@/services/applications.service'
import type { Application } from '@/types/api'

/** 1 e a maior. O modelo valida a faixa, entao a tela nao inventa outra. */
const PRIORIDADES = [1, 2, 3, 4, 5].map((n) => ({
  value: String(n),
  label: n === 1 ? '1 (maior)' : n === 5 ? '5 (menor)' : String(n),
}))

interface Props {
  application: Application
  podeGerenciar: boolean
  onClose: () => void
}

/**
 * Tudo que so dava para editar pelo admin do Django.
 *
 * Notas, contato, prioridade e o proximo passo saem daqui, e o proximo passo e
 * o que alimenta o "atrasadas" do Dashboard: sem esta tela, a promessa central
 * do produto dependia de alguem abrir o /admin.
 *
 * A linha do tempo saiu: o funil ja diz em que etapa a candidatura esta, e
 * anotar evento a evento virava trabalho manual que ninguem repetia. O que
 * precisa de memoria cabe em Notas.
 */
export function DetalhePanel({ application, podeGerenciar, onClose }: Props) {
  const { job } = application
  const queryClient = useQueryClient()
  const toast = useToast()

  const [prioridade, setPrioridade] = useState(String(application.priority))
  const [aplicadaEm, setAplicadaEm] = useState(application.applied_on ?? '')
  const [proximoPasso, setProximoPasso] = useState(application.next_step)
  const [proximoPassoEm, setProximoPassoEm] = useState(application.next_step_on ?? '')
  const [contato, setContato] = useState(application.contact)
  const [indicado, setIndicado] = useState(application.has_referral)
  const [notas, setNotas] = useState(application.notes)

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [onClose])

  const invalidar = () => {
    void queryClient.invalidateQueries({ queryKey: ['board'] })
    void queryClient.invalidateQueries({ queryKey: ['encerradas'] })
  }

  const salvar = useMutation({
    mutationFn: () =>
      updateApplication(application.id, {
        priority: Number(prioridade),
        // String vazia nao e data: o campo aceita nulo, e mandar '' daria 400.
        applied_on: aplicadaEm || null,
        next_step: proximoPasso,
        next_step_on: proximoPassoEm || null,
        contact: contato,
        has_referral: indicado,
        notes: notas,
      }),
    onSuccess: () => {
      invalidar()
      toast.mostrar({ tom: 'ok', titulo: 'Candidatura salva.' })
      onClose()
    },
    onError: (err) =>
      toast.mostrar({
        tom: 'bad',
        titulo: apiErrorMessage(err, 'Nao deu para salvar.'),
        duracao: null,
      }),
  })

  function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    salvar.mutate()
  }

  return (
    <div
      className="fixed inset-0 z-40 flex justify-center overflow-y-auto bg-ink/45 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="detalhe-titulo"
        className="my-6 h-fit w-full max-w-2xl rounded-[10px] border border-line bg-card p-4 shadow-xl lg:p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h2 id="detalhe-titulo" className="text-[15px] font-semibold">
              Detalhes da candidatura
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

        <form onSubmit={enviar} className="flex flex-col gap-3.5">
          <div className="grid gap-3.5 sm:grid-cols-2">
            <Campo label="Prioridade" htmlFor="det-prioridade">
              <Lista
                id="det-prioridade"
                inputSize="sm"
                options={PRIORIDADES}
                value={prioridade}
                disabled={!podeGerenciar}
                onChange={setPrioridade}
              />
            </Campo>

            <Campo label="Aplicada em" htmlFor="det-aplicada">
              <Input
                id="det-aplicada"
                type="date"
                inputSize="sm"
                value={aplicadaEm}
                disabled={!podeGerenciar}
                onChange={(e) => setAplicadaEm(e.target.value)}
              />
            </Campo>

            <Campo label="Próximo passo" htmlFor="det-passo">
              <Input
                id="det-passo"
                inputSize="sm"
                placeholder="Retomar contato com o recrutador"
                value={proximoPasso}
                disabled={!podeGerenciar}
                onChange={(e) => setProximoPasso(e.target.value)}
              />
            </Campo>

            {/* Esta data e o que faz a candidatura virar "atrasada" no
                Dashboard e no filtro das Candidaturas. */}
            <Campo label="Data do próximo passo" htmlFor="det-passo-em">
              <Input
                id="det-passo-em"
                type="date"
                inputSize="sm"
                value={proximoPassoEm}
                disabled={!podeGerenciar}
                onChange={(e) => setProximoPassoEm(e.target.value)}
              />
            </Campo>

            <Campo label="Contato" htmlFor="det-contato">
              <Input
                id="det-contato"
                inputSize="sm"
                placeholder="nome, e-mail ou telefone"
                value={contato}
                disabled={!podeGerenciar}
                onChange={(e) => setContato(e.target.value)}
              />
            </Campo>

            <label className="flex min-h-11 items-center gap-2.5 self-end text-[13.5px]">
              <input
                type="checkbox"
                checked={indicado}
                disabled={!podeGerenciar}
                onChange={(e) => setIndicado(e.target.checked)}
                className="h-4 w-4 accent-current text-accent"
              />
              Tenho indicação
            </label>
          </div>

          <Campo label="Notas" htmlFor="det-notas">
            <textarea
              id="det-notas"
              rows={4}
              value={notas}
              disabled={!podeGerenciar}
              onChange={(e) => setNotas(e.target.value)}
              className="w-full rounded-lg border border-field bg-card px-3.5 py-2.5 text-[13.5px] text-ink outline-none focus:border-ink disabled:bg-surface disabled:text-muted"
            />
          </Campo>

          {podeGerenciar && (
            <div className="flex justify-end gap-2">
              <Button type="button" size="sm" onClick={onClose}>
                cancelar
              </Button>
              <Button type="submit" variant="primary" size="sm" disabled={salvar.isPending}>
                {salvar.isPending ? 'salvando...' : 'salvar'}
              </Button>
            </div>
          )}
        </form>

      </div>
    </div>
  )
}
