import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { Campo, Input } from '@/components/ui/Input'
import { useToast } from '@/hooks/useToast'
import { apiErrorMessage } from '@/lib/api'
import { createJob } from '@/services/jobs.service'

/**
 * Cadastro manual de vaga.
 *
 * A coleta cobre GitHub e Gupy. Vaga que voce achou no LinkedIn, num grupo ou
 * por indicacao entra por aqui, e o backend a classifica e pontua igual as
 * outras: fica na mesma fila, com o mesmo score, e nao numa lista a parte.
 */
export function NovaVagaPanel({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const toast = useToast()

  const [titulo, setTitulo] = useState('')
  const [empresa, setEmpresa] = useState('')
  const [local, setLocal] = useState('')
  const [url, setUrl] = useState('')
  const [descricao, setDescricao] = useState('')

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [onClose])

  const criar = useMutation({
    mutationFn: () =>
      createJob({
        title: titulo.trim(),
        company: empresa.trim(),
        location: local.trim(),
        url: url.trim(),
        description: descricao.trim(),
      }),
    onSuccess: (vaga) => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.mostrar({
        tom: 'ok',
        titulo: 'Vaga cadastrada.',
        detalhe: `Entrou na fila com score ${vaga.score}.`,
      })
      onClose()
    },
    // O backend recusa URL repetida com "Essa vaga ja esta no radar", que e
    // uma resposta util: vai inteira para a tela em vez de virar generico.
    onError: (err) =>
      toast.mostrar({
        tom: 'bad',
        titulo: apiErrorMessage(err, 'Nao deu para cadastrar a vaga.'),
        duracao: null,
      }),
  })

  function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    criar.mutate()
  }

  return (
    <div
      className="fixed inset-0 z-40 flex justify-center overflow-y-auto bg-ink/45 p-4"
      onClick={onClose}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="nova-vaga-titulo"
        onSubmit={enviar}
        onClick={(e) => e.stopPropagation()}
        className="my-6 h-fit w-full max-w-xl rounded-[10px] border border-line bg-card p-4 shadow-xl lg:p-5"
      >
        <div className="mb-4 flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h2 id="nova-vaga-titulo" className="text-[15px] font-semibold">
              Cadastrar vaga
            </h2>
            <p className="mt-0.5 text-xs text-muted">
              Para o que a coleta não traz. Ela entra na fila e é pontuada igual às outras.
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
          <Campo label="Título" htmlFor="vaga-titulo">
            <Input
              id="vaga-titulo"
              inputSize="sm"
              autoFocus
              placeholder="Desenvolvedor Python Júnior"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
            />
          </Campo>

          <Campo label="Link da vaga" htmlFor="vaga-url">
            <Input
              id="vaga-url"
              type="url"
              inputSize="sm"
              placeholder="https://..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </Campo>

          <div className="grid gap-3.5 sm:grid-cols-2">
            <Campo label="Empresa" htmlFor="vaga-empresa">
              <Input
                id="vaga-empresa"
                inputSize="sm"
                value={empresa}
                onChange={(e) => setEmpresa(e.target.value)}
              />
            </Campo>

            <Campo label="Local" htmlFor="vaga-local">
              <Input
                id="vaga-local"
                inputSize="sm"
                placeholder="Remoto, Brasil"
                value={local}
                onChange={(e) => setLocal(e.target.value)}
              />
            </Campo>
          </div>

          {/* A descricao e o que o classificador le para dar senioridade,
              modalidade, tags e score. Sem ela a vaga entra com score baixo. */}
          <Campo label="Descrição" htmlFor="vaga-descricao">
            <textarea
              id="vaga-descricao"
              rows={5}
              placeholder="Cole aqui o texto da vaga. É dele que saem o score e as tags."
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              className="w-full rounded-lg border border-field bg-card px-3.5 py-2.5 text-[13.5px] text-ink outline-none focus:border-ink"
            />
          </Campo>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" size="sm" onClick={onClose}>
            cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={!titulo.trim() || !url.trim() || criar.isPending}
          >
            {criar.isPending ? 'cadastrando...' : 'cadastrar'}
          </Button>
        </div>
      </form>
    </div>
  )
}
