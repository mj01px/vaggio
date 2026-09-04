import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { Campo, Input } from '@/components/ui/Input'
import { Select as Lista } from '@/components/ui/Select'
import { StateMessage } from '@/components/ui/StateMessage'
import { useToast } from '@/hooks/useToast'
import { apiErrorMessage } from '@/lib/api'
import { fetchJob, updateJob } from '@/services/jobs.service'
import type { Job, JobDetalhe } from '@/types/api'

const SENIORIDADES = [
  { value: 'unknown', label: 'Não informado' },
  { value: 'internship', label: 'Estágio' },
  { value: 'junior', label: 'Júnior' },
  { value: 'mid', label: 'Pleno' },
  { value: 'senior', label: 'Sênior' },
]

const MODALIDADES = [
  { value: 'unknown', label: 'Não informado' },
  { value: 'remote', label: 'Remoto' },
  { value: 'hybrid', label: 'Híbrido' },
  { value: 'onsite', label: 'Presencial' },
]

/**
 * Correcao de uma vaga ja coletada.
 *
 * A coleta le HTML de terceiros e erra: titulo truncado, empresa vazia,
 * senioridade lida errado. Isso so se consertava pelo admin do Django, que nao
 * existe mais. Score e tags entram junto porque sao eles que decidem a ordem
 * da fila: uma vaga boa com score baixo some no fim da lista.
 */
export function EditarVagaPanel({ job, onClose }: { job: Job; onClose: () => void }) {
  const queryClient = useQueryClient()
  const toast = useToast()

  // A lista nao carrega a descricao (e o maior campo da vaga), entao a vaga
  // inteira e buscada ao abrir. O resto do formulario ja pode ser preenchido.
  const detalhe = useQuery<JobDetalhe>({
    queryKey: ['job', job.id],
    queryFn: () => fetchJob(job.id),
  })

  const [titulo, setTitulo] = useState(job.title)
  const [empresa, setEmpresa] = useState(job.company)
  const [local, setLocal] = useState(job.location)
  const [url, setUrl] = useState(job.url)
  const [senioridade, setSenioridade] = useState<string>(job.seniority)
  const [modalidade, setModalidade] = useState<string>(job.work_mode)
  const [score, setScore] = useState(String(job.score))
  const [tags, setTags] = useState(job.tags.join(', '))
  // A descricao chega depois dos outros campos, entao o estado guarda so o que
  // foi digitado: `null` significa "ainda vale o que veio do servidor". Copiar
  // a resposta para o estado num efeito daria um render a mais e, pior, salvar
  // antes de ela chegar mandaria string vazia e apagaria o texto da vaga.
  const [rascunho, setRascunho] = useState<string | null>(null)
  const descricao = rascunho ?? detalhe.data?.description ?? ''
  const descricaoPronta = detalhe.data !== undefined

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [onClose])

  const salvar = useMutation({
    mutationFn: () =>
      updateJob(job.id, {
        title: titulo.trim(),
        company: empresa.trim(),
        location: local.trim(),
        url: url.trim(),
        seniority: senioridade,
        work_mode: modalidade,
        // Campo vazio nao vira zero: sai do PATCH e o score fica como esta.
        ...(score.trim() === '' ? {} : { score: Number(score) }),
        tags: tags
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
        description: descricao,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['job', job.id] })
      // O cartao da candidatura mostra o titulo da vaga: corrigir aqui e
      // deixar o board com o titulo velho seria o mesmo erro em outra tela.
      void queryClient.invalidateQueries({ queryKey: ['board'] })
      void queryClient.invalidateQueries({ queryKey: ['encerradas'] })
      toast.mostrar({ tom: 'ok', titulo: 'Vaga atualizada.' })
      onClose()
    },
    // O backend recusa URL que ja e de outra vaga com um texto proprio, que
    // diz mais do que qualquer mensagem generica daqui.
    onError: (err) =>
      toast.mostrar({
        tom: 'bad',
        titulo: apiErrorMessage(err, 'Nao deu para salvar a vaga.'),
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
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="editar-vaga-titulo"
        onSubmit={enviar}
        onClick={(e) => e.stopPropagation()}
        className="my-6 h-fit w-full max-w-2xl rounded-[10px] border border-line bg-card p-4 shadow-xl lg:p-5"
      >
        <div className="mb-4 flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h2 id="editar-vaga-titulo" className="text-[15px] font-semibold">
              Editar vaga
            </h2>
            <p className="mt-0.5 text-xs text-muted">
              Corrige o que a coleta trouxe errado. O score e as tags mandam na ordem da fila.
            </p>
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

        <div className="flex flex-col gap-3.5">
          <Campo label="Título" htmlFor="edit-titulo">
            <Input
              id="edit-titulo"
              inputSize="sm"
              autoFocus
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
            />
          </Campo>

          {/* Trocar a URL troca a identidade da vaga na deduplicacao: o backend
              recusa se a nova ja for de outra vaga. */}
          <Campo label="Link da vaga" htmlFor="edit-url">
            <Input
              id="edit-url"
              type="url"
              inputSize="sm"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </Campo>

          <div className="grid gap-3.5 sm:grid-cols-2">
            <Campo label="Empresa" htmlFor="edit-empresa">
              <Input
                id="edit-empresa"
                inputSize="sm"
                value={empresa}
                onChange={(e) => setEmpresa(e.target.value)}
              />
            </Campo>

            <Campo label="Local" htmlFor="edit-local">
              <Input
                id="edit-local"
                inputSize="sm"
                value={local}
                onChange={(e) => setLocal(e.target.value)}
              />
            </Campo>

            <Campo label="Senioridade" htmlFor="edit-senioridade">
              <Lista
                id="edit-senioridade"
                inputSize="sm"
                options={SENIORIDADES}
                value={senioridade}
                onChange={setSenioridade}
              />
            </Campo>

            <Campo label="Modalidade" htmlFor="edit-modalidade">
              <Lista
                id="edit-modalidade"
                inputSize="sm"
                options={MODALIDADES}
                value={modalidade}
                onChange={setModalidade}
              />
            </Campo>

            <Campo label="Score" htmlFor="edit-score">
              <Input
                id="edit-score"
                type="number"
                inputSize="sm"
                min={-100}
                max={100}
                value={score}
                onChange={(e) => setScore(e.target.value)}
              />
            </Campo>

            <Campo label="Tags" htmlFor="edit-tags">
              <Input
                id="edit-tags"
                inputSize="sm"
                placeholder="python, django, remoto"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
              />
            </Campo>
          </div>

          <Campo label="Descrição" htmlFor="edit-descricao">
            <textarea
              id="edit-descricao"
              rows={6}
              value={descricao}
              disabled={!descricaoPronta}
              onChange={(e) => setRascunho(e.target.value)}
              className="w-full rounded-lg border border-field bg-card px-3.5 py-2.5 text-[13.5px] text-ink outline-none focus:border-ink disabled:bg-surface disabled:text-muted"
            />
          </Campo>

          {detalhe.isError && (
            <StateMessage tone="bad">
              {apiErrorMessage(detalhe.error, 'Nao deu para carregar a descrição da vaga.')}
            </StateMessage>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" size="sm" onClick={onClose}>
            cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={!titulo.trim() || !url.trim() || !descricaoPronta || salvar.isPending}
          >
            {salvar.isPending ? 'salvando...' : 'salvar'}
          </Button>
        </div>
      </form>
    </div>
  )
}
