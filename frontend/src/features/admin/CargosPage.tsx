import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { usePode } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import {
  apagarCargo,
  atualizarCargo,
  criarCargo,
  fetchCargos,
  fetchPermissoes,
} from '@/services/admin.service'
import type { Cargo, Permissao, PermissaoKey } from '@/types/api'

const CABECALHO =
  'px-4 py-2.5 text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase lg:px-5'
const CELULA = 'px-4 py-3 lg:px-5'

/** O prefixo do slug ("vagas.ver" -> "vagas") escrito por extenso. */
const AREAS: Record<string, string> = {
  vagas: 'Vagas',
  funil: 'Funil',
  coleta: 'Coleta',
  apresentacao: 'Apresentação',
  perfil: 'Perfil',
  usuarios: 'Usuários',
  cargos: 'Cargos',
}

/** Agrupa as permissoes pelo prefixo do slug, na ordem em que o catalogo vem. */
function porArea(permissoes: Permissao[]): [string, Permissao[]][] {
  const mapa = new Map<string, Permissao[]>()
  for (const permissao of permissoes) {
    const area = permissao.slug.split('.')[0]
    mapa.set(area, [...(mapa.get(area) ?? []), permissao])
  }
  return [...mapa.entries()]
}

/**
 * Quem pode o que, numa matriz.
 *
 * Antes era um cartao por cargo, cada um repetindo o catalogo inteiro em
 * pilulas: para responder "quem pode rodar a coleta" era preciso varrer os
 * cartoes um a um. Com permissao na linha e cargo na coluna, a resposta e
 * olhar uma linha.
 */
export function CargosPage() {
  const queryClient = useQueryClient()
  const podeGerenciar = usePode('cargos.gerenciar')

  const [error, setError] = useState('')
  const [criando, setCriando] = useState(false)

  const cargos = useQuery({ queryKey: ['cargos'], queryFn: fetchCargos })
  const permissoes = useQuery({ queryKey: ['permissoes'], queryFn: fetchPermissoes })

  const recarregar = () => {
    void queryClient.invalidateQueries({ queryKey: ['cargos'] })
    void queryClient.invalidateQueries({ queryKey: ['usuarios'] })
    void queryClient.invalidateQueries({ queryKey: ['sessao'] })
  }

  const alternar = useMutation({
    mutationFn: ({ cargo, slug }: { cargo: Cargo; slug: PermissaoKey }) => {
      const tem = cargo.permissoes.includes(slug)
      const proximas = tem
        ? cargo.permissoes.filter((p) => p !== slug)
        : [...cargo.permissoes, slug]
      return atualizarCargo(cargo.id, { permissoes: proximas })
    },
    onMutate: () => setError(''),
    onSuccess: recarregar,
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para mudar a permissao.')),
  })

  const remover = useMutation({
    mutationFn: (cargo: Cargo) => apagarCargo(cargo.id),
    onMutate: () => setError(''),
    onSuccess: recarregar,
    // O backend recusa apagar cargo em uso dizendo quantas pessoas o usam,
    // que e a resposta util: vai inteira para a tela.
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para apagar o cargo.')),
  })

  const catalogo = permissoes.data ?? []
  const lista = cargos.data ?? []

  return (
    <div>
      {podeGerenciar && (
        <div className="mb-3 flex justify-end">
          <Button variant="primary" size="sm" onClick={() => setCriando(true)}>
            novo cargo
          </Button>
        </div>
      )}

      {error && (
        <div className="mb-3 rounded-lg border border-bad bg-card px-3.5 py-2.5 text-sm text-bad">
          {error}
        </div>
      )}

      {criando && (
        <FormularioNovo
          onFechar={() => setCriando(false)}
          onCriado={() => {
            setCriando(false)
            recarregar()
          }}
          onErro={setError}
        />
      )}

      <div className="overflow-hidden rounded-[10px] border border-line bg-card">
        {(cargos.isPending || permissoes.isPending) && (
          <p className="p-8 text-center text-muted">Carregando...</p>
        )}

        {cargos.isError && (
          <p className="p-8 text-center text-bad">
            {apiErrorMessage(cargos.error, 'Nao deu para carregar os cargos.')}
          </p>
        )}

        {cargos.data && lista.length === 0 && (
          <div className="p-8 text-center text-muted">
            <p className="text-[14.5px] font-medium text-ink">Nenhum cargo ainda</p>
            <p className="mt-1 text-[13px]">
              Acesso total sai do superusuário. Cargo serve para dar menos que isso.
            </p>
          </div>
        )}

        {cargos.data && permissoes.data && lista.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] table-fixed text-left text-[13.5px]">
              <thead className="bg-surface">
                <tr>
                  <th className={`w-[38%] ${CABECALHO}`}>Permissão</th>
                  {lista.map((cargo) => (
                    <th key={cargo.id} className={`text-center ${CABECALHO}`}>
                      <div className="flex items-center justify-center gap-1">
                        <span className="truncate" title={cargo.descricao || cargo.slug}>
                          {cargo.nome}
                        </span>
                        {podeGerenciar && (
                          <IconButton
                            type="button"
                            aria-label={`Apagar o cargo ${cargo.nome}`}
                            title="Apagar cargo"
                            disabled={remover.isPending}
                            onClick={() => remover.mutate(cargo)}
                            className="h-6 w-6 shrink-0 hover:text-bad"
                          >
                            <Trash2 size={13} />
                          </IconButton>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>

              {porArea(catalogo).map(([area, doArea]) => (
                <tbody key={area} className="divide-y divide-line border-t border-line">
                  {/* A area separa a matriz em blocos legiveis. Sem ela sao 13
                      linhas seguidas e some a noção de onde uma parte acaba. */}
                  <tr>
                    <td
                      colSpan={lista.length + 1}
                      className="bg-surface/60 px-4 py-1.5 text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase lg:px-5"
                    >
                      {AREAS[area] ?? area}
                    </td>
                  </tr>

                  {doArea.map((permissao) => (
                    <tr key={permissao.slug} className="transition-colors hover:bg-surface">
                      <td className={CELULA}>
                        <div className="font-medium">{permissao.nome}</div>
                        <div className="text-[12px] text-muted">{permissao.descricao}</div>
                      </td>

                      {lista.map((cargo) => (
                        <td key={cargo.id} className={`${CELULA} text-center`}>
                          <input
                            type="checkbox"
                            aria-label={`${permissao.nome} para ${cargo.nome}`}
                            checked={cargo.permissoes.includes(permissao.slug)}
                            disabled={!podeGerenciar || alternar.isPending}
                            onChange={() => alternar.mutate({ cargo, slug: permissao.slug })}
                            className="h-4 w-4 accent-current text-accent"
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              ))}
            </table>
          </div>
        )}
      </div>

      <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
        Permissão nova nasce em <code className="rounded bg-surface px-1">permissoes.py</code> e
        entra com <code className="rounded bg-surface px-1">manage.py sync_permissoes</code>: cada
        slug precisa de código que o respeite.
      </p>
    </div>
  )
}

interface NovoProps {
  onFechar: () => void
  onCriado: () => void
  onErro: (mensagem: string) => void
}

function FormularioNovo({ onFechar, onCriado, onErro }: NovoProps) {
  const [slug, setSlug] = useState('')
  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')

  const criar = useMutation({
    mutationFn: () => criarCargo({ slug, nome, descricao, permissoes: [] }),
    onSuccess: onCriado,
    onError: (err) => onErro(apiErrorMessage(err, 'Nao deu para criar o cargo.')),
  })

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        criar.mutate()
      }}
      className="mb-4 rounded-lg border border-accent bg-card p-4"
    >
      <h2 className="mb-3 text-[14px] font-semibold">Novo cargo</h2>
      <div className="mb-3 flex flex-wrap gap-2">
        <input
          value={slug}
          onChange={(event) => setSlug(event.target.value.toLowerCase().replace(/\s+/g, '-'))}
          placeholder="chave, ex: triador"
          className="w-[170px] rounded-md border border-line bg-surface px-2.5 py-1.5 text-ink"
        />
        <input
          value={nome}
          onChange={(event) => setNome(event.target.value)}
          placeholder="nome"
          className="w-[170px] rounded-md border border-line bg-surface px-2.5 py-1.5 text-ink"
        />
        <input
          value={descricao}
          onChange={(event) => setDescricao(event.target.value)}
          placeholder="descrição (opcional)"
          className="min-w-[220px] flex-1 rounded-md border border-line bg-surface px-2.5 py-1.5 text-ink"
        />
      </div>
      <div className="flex gap-1.5">
        <Button type="submit" variant="primary" disabled={criar.isPending || !slug || !nome}>
          {criar.isPending ? 'criando...' : 'criar'}
        </Button>
        <Button type="button" onClick={onFechar}>
          cancelar
        </Button>
      </div>
      <p className="mt-2 text-[11.5px] text-muted">
        O cargo nasce sem permissão nenhuma. Marque as caixas depois de criar.
      </p>
    </form>
  )
}
