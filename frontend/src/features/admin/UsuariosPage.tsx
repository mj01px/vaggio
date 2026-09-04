import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MailPlus } from 'lucide-react'
import { Button, IconButton } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { usePode, useSessao } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { formatDate } from '@/lib/format'
import {
  atualizarUsuario,
  criarUsuario,
  enviarConvite,
  fetchCargos,
  fetchUsuarios,
} from '@/services/admin.service'

const CABECALHO =
  'px-4 py-2.5 text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase lg:px-5'
const CELULA = 'px-4 py-3 lg:px-5'

/** Pilula de situacao: sem borda, so fundo lavado e o texto na cor do estado. */
const PILULA = 'rounded-full px-2.5 py-1 text-[10px] font-bold uppercase'

export function UsuariosPage() {
  const queryClient = useQueryClient()
  const { perfil } = useSessao()
  const podeGerenciar = usePode('usuarios.gerenciar')

  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [criando, setCriando] = useState(false)

  const usuarios = useQuery({ queryKey: ['usuarios'], queryFn: fetchUsuarios })
  const cargos = useQuery({ queryKey: ['cargos'], queryFn: fetchCargos })

  const recarregar = () => {
    void queryClient.invalidateQueries({ queryKey: ['usuarios'] })
  }

  const convidar = useMutation({
    mutationFn: (usuario: { id: number }) => enviarConvite(usuario.id),
    onMutate: () => {
      setError('')
      setAviso('')
    },
    onSuccess: (detalhe: string) => setAviso(detalhe),
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para enviar o convite.')),
  })

  const editar = useMutation({
    mutationFn: ({ id, mudancas }: { id: number; mudancas: Record<string, unknown> }) =>
      atualizarUsuario(id, mudancas),
    onMutate: () => {
      setError('')
      setAviso('')
    },
    onSuccess: recarregar,
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para salvar.')),
  })

  return (
    <div>
      {podeGerenciar && (
        <div className="mb-3 flex justify-end">
          <Button variant="primary" size="sm" onClick={() => setCriando(true)}>
            novo usuário
          </Button>
        </div>
      )}

      {aviso && (
        <div className="mb-3 rounded-lg border border-line bg-card px-3.5 py-2.5 text-sm">
          {aviso}
        </div>
      )}
      {error && (
        <div className="mb-3 rounded-lg border border-bad bg-card px-3.5 py-2.5 text-sm text-bad">
          {error}
        </div>
      )}

      {criando && (
        <FormularioNovo
          cargos={cargos.data ?? []}
          onFechar={() => setCriando(false)}
          onCriado={(nome) => {
            setCriando(false)
            setAviso(`Conta de ${nome} criada. O convite foi para o e-mail dela.`)
            recarregar()
          }}
          onErro={setError}
        />
      )}

      {/* Mesma moldura da tabela de Coletas: o `overflow-hidden` e o que faz a
          faixa cinza do cabecalho respeitar os cantos arredondados. */}
      <div className="overflow-hidden rounded-[10px] border border-line bg-card">
        {usuarios.isPending && <p className="p-8 text-center text-muted">Carregando...</p>}

        {usuarios.isError && (
          <p className="p-8 text-center text-bad">
            {apiErrorMessage(usuarios.error, 'Nao deu para carregar os usuarios.')}
          </p>
        )}

        {usuarios.data && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] table-fixed text-left text-[13.5px]">
              <thead className="bg-surface">
                <tr>
                  <th className={`w-[28%] ${CABECALHO}`}>Usuário</th>
                  <th className={`w-[18%] ${CABECALHO}`}>Cargo</th>
                  <th className={`w-[12%] text-center ${CABECALHO}`}>Permissões</th>
                  <th className={`w-[16%] text-center ${CABECALHO}`}>Último acesso</th>
                  <th className={`w-[12%] text-center ${CABECALHO}`}>Situação</th>
                  <th className={`w-[14%] text-center ${CABECALHO}`}>Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {usuarios.data.map((usuario) => {
                  const souEu = usuario.email === perfil?.email
                  const bloqueado = editar.isPending || !podeGerenciar

                  return (
                    <tr
                      key={usuario.id}
                      // Altura fixa: sem ela a linha de quem tem nome curto
                      // fica mais baixa que a das outras e a tabela serrilha.
                      className={`h-16 transition-colors hover:bg-surface ${
                        usuario.is_active ? '' : 'opacity-60'
                      }`}
                    >
                      <td className={CELULA}>
                        <div className="truncate font-semibold">
                          {usuario.nome || usuario.email}
                          {souEu && <span className="ml-1.5 text-[11px] text-muted">(você)</span>}
                        </div>
                        <div className="truncate text-[12px] text-muted">{usuario.email}</div>
                      </td>

                      <td className={`${CELULA} truncate`}>
                        {usuario.cargo ? (
                          usuario.cargo.nome
                        ) : (
                          <span className="text-muted">sem cargo</span>
                        )}
                      </td>

                      {/* Zero permissoes e o caso que importa ver de longe: a
                          pessoa entra e nao consegue fazer nada. */}
                      <td
                        className={`${CELULA} text-center tabular-nums ${
                          usuario.permissoes.length === 0 ? 'text-bad' : ''
                        }`}
                      >
                        {usuario.permissoes.length}
                      </td>

                      <td className={`${CELULA} text-center whitespace-nowrap text-muted tabular-nums`}>
                        {usuario.last_login ? formatDate(usuario.last_login) : 'nunca entrou'}
                      </td>

                      <td className={`${CELULA} text-center`}>
                        <span
                          className={
                            usuario.is_active
                              ? `${PILULA} bg-ok/10 text-ok`
                              : `${PILULA} bg-surface text-muted`
                          }
                        >
                          {usuario.is_active ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>

                      <td className={`${CELULA} text-center`}>
                        {podeGerenciar && (
                          <div className="flex items-center justify-center gap-1.5">
                            {/* Reenviar e util quando o convite venceu, foi
                                para o spam, ou a pessoa perdeu o e-mail. */}
                            <IconButton
                              type="button"
                              aria-label={`Reenviar o convite para ${usuario.email}`}
                              title="Reenviar convite para definir a senha"
                              disabled={convidar.isPending || !usuario.is_active}
                              onClick={() => convidar.mutate(usuario)}
                            >
                              <MailPlus size={16} />
                            </IconButton>
                            <Button
                              size="sm"
                              disabled={bloqueado || souEu || usuario.is_superuser}
                              onClick={() =>
                                editar.mutate({
                                  id: usuario.id,
                                  mudancas: { is_active: !usuario.is_active },
                                })
                              }
                            >
                              {usuario.is_active ? 'desativar' : 'reativar'}
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
        Conta não se apaga, desativa: candidatura e apresentação ficam penduradas em quem as
        criou, e apagar levaria o histórico junto.
      </p>
    </div>
  )
}

interface NovoProps {
  cargos: { slug: string; nome: string }[]
  onFechar: () => void
  onCriado: (nome: string) => void
  onErro: (mensagem: string) => void
}

function FormularioNovo({ cargos, onFechar, onCriado, onErro }: NovoProps) {
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [cargo, setCargo] = useState('')

  // Sem campo de senha de proposito: a conta nasce sem senha utilizavel e a
  // pessoa escolhe a dela pelo link do convite. Assim ninguem, nem quem
  // cadastrou, chega a saber a senha de outra pessoa.
  const criar = useMutation({
    mutationFn: () => criarUsuario({ nome, email, cargo: cargo || null }),
    onSuccess: () => onCriado(nome || email),
    onError: (err) => onErro(apiErrorMessage(err, 'Nao deu para criar a conta.')),
  })

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        criar.mutate()
      }}
      className="mb-4 rounded-lg border border-accent bg-card p-4"
    >
      <h2 className="mb-3 text-[14px] font-semibold">Novo usuário</h2>
      <div className="mb-3 flex flex-wrap gap-2">
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="e-mail"
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          className="w-[230px] rounded-md border border-line bg-surface px-2.5 py-1.5 text-ink"
        />
        <input
          value={nome}
          onChange={(event) => setNome(event.target.value)}
          placeholder="nome"
          className="w-[170px] rounded-md border border-line bg-surface px-2.5 py-1.5 text-ink"
        />
        <div className="w-[170px]">
          <Select
            inputSize="sm"
            aria-label="Cargo da conta nova"
            options={[
              { value: '', label: 'sem cargo' },
              ...cargos.map((c) => ({ value: c.slug, label: c.nome })),
            ]}
            value={cargo}
            onChange={setCargo}
          />
        </div>
      </div>
      <div className="flex gap-1.5">
        <Button type="submit" variant="primary" disabled={criar.isPending || !email}>
          {criar.isPending ? 'criando...' : 'criar e convidar'}
        </Button>
        <Button type="button" onClick={onFechar}>
          cancelar
        </Button>
      </div>
      <p className="mt-2 text-[11.5px] text-muted">
        A pessoa recebe um e-mail para escolher a própria senha, então ninguém além dela vai
        saber essa senha. Sem cargo ela entra e não consegue fazer nada: escolha um.
      </p>
    </form>
  )
}
