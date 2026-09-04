import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Mail, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useToast } from '@/hooks/useToast'
import { apiErrorMessage } from '@/lib/api'
import {
  confirmarDoisFatores,
  desativarDoisFatores,
  fetchDoisFatores,
  novosCodigosDeReserva,
  pedirTrocaDeEmail,
  prepararDoisFatores,
  trocarSenha,
} from '@/services/session.service'

const MICRO = 'text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase'

const CAMPO =
  'h-9 w-full rounded-lg border border-field bg-card px-3 text-[13.5px] text-ink outline-none ' +
  'focus:border-ink'

function Card({ children }: { children: ReactNode }) {
  return <div className="rounded-[10px] border border-line bg-card p-4 lg:p-5">{children}</div>
}

function Bloco({
  icone,
  titulo,
  descricao,
  acao,
}: {
  icone: ReactNode
  titulo: string
  descricao: string
  acao?: ReactNode
}) {
  return (
    <div className="flex items-center gap-3.5">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface text-muted">
        {icone}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-semibold">{titulo}</p>
        <p className="mt-0.5 text-[12.5px] text-muted">{descricao}</p>
      </div>
      {acao}
    </div>
  )
}

function Campo({
  rotulo,
  id,
  tipo = 'text',
  valor,
  onChange,
  ...resto
}: {
  rotulo: string
  id: string
  tipo?: string
  valor: string
  onChange: (valor: string) => void
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value' | 'id' | 'type'>) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className={MICRO} htmlFor={id}>
        {rotulo}
      </label>
      <input
        id={id}
        type={tipo}
        value={valor}
        onChange={(event) => onChange(event.target.value)}
        className={CAMPO}
        {...resto}
      />
    </div>
  )
}

/** Os codigos de reserva, mostrados a unica vez em que existem em claro. */
function CodigosDeReserva({ codigos }: { codigos: string[] }) {
  return (
    <div className="flex flex-col gap-2.5 rounded-lg border border-warn/30 bg-warn/5 p-3.5">
      <p className="text-[13px] font-semibold text-warn">
        Guarde estes códigos agora. Eles não aparecem de novo.
      </p>
      <p className="text-[12.5px] text-muted">
        Cada um entra uma vez, e servem para quando você não estiver com o celular.
      </p>
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {codigos.map((codigo) => (
          <code
            key={codigo}
            className="rounded border border-line bg-card px-2 py-1.5 text-center text-[13px] tracking-wider tabular-nums"
          >
            {codigo}
          </code>
        ))}
      </div>
    </div>
  )
}

/**
 * Senha, e-mail e segundo fator.
 *
 * Separado do resto do perfil porque o que protege estas acoes nao e cargo, e
 * prova de identidade: a senha atual em todas elas, e o codigo do aplicativo
 * no segundo fator.
 */
export function Seguranca({ email }: { email: string }) {
  const queryClient = useQueryClient()
  const toast = useToast()

  const [abrindo, setAbrindo] = useState<'senha' | 'email' | null>(null)

  return (
    <div className="flex flex-col gap-3">
      <Card>
        {abrindo === 'senha' ? (
          <TrocaDeSenha onFechar={() => setAbrindo(null)} />
        ) : (
          <Bloco
            icone={<KeyRound size={20} />}
            titulo="Senha"
            descricao="Para trocar, você precisa saber a senha de agora."
            acao={
              <Button size="sm" className="shrink-0" onClick={() => setAbrindo('senha')}>
                trocar
              </Button>
            }
          />
        )}
      </Card>

      <Card>
        {abrindo === 'email' ? (
          <TrocaDeEmail atual={email} onFechar={() => setAbrindo(null)} />
        ) : (
          <Bloco
            icone={<Mail size={20} />}
            titulo="E-mail de acesso"
            descricao={`Hoje você entra com ${email}.`}
            acao={
              <Button size="sm" className="shrink-0" onClick={() => setAbrindo('email')}>
                trocar
              </Button>
            }
          />
        )}
      </Card>

      <Card>
        <DoisFatores
          onMudou={() => void queryClient.invalidateQueries({ queryKey: ['2fa'] })}
          toast={toast}
        />
      </Card>
    </div>
  )
}

function TrocaDeSenha({ onFechar }: { onFechar: () => void }) {
  const toast = useToast()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [repetida, setRepetida] = useState('')
  const [erro, setErro] = useState('')

  const trocar = useMutation({
    mutationFn: () => trocarSenha(atual, nova),
    onMutate: () => setErro(''),
    onSuccess: () => {
      toast.mostrar({ tom: 'ok', titulo: 'Senha alterada.' })
      onFechar()
    },
    onError: (err) => setErro(apiErrorMessage(err, 'Nao deu para trocar a senha.')),
  })

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault()
        if (nova !== repetida) return setErro('As duas senhas precisam ser iguais.')
        trocar.mutate()
      }}
    >
      <Bloco
        icone={<KeyRound size={20} />}
        titulo="Trocar a senha"
        descricao="A senha de agora é a prova de que é você."
      />

      <div className="grid gap-3.5 sm:grid-cols-3">
        <Campo
          rotulo="Senha atual"
          id="seg-atual"
          tipo="password"
          valor={atual}
          onChange={setAtual}
          autoComplete="current-password"
          autoFocus
        />
        <Campo
          rotulo="Nova"
          id="seg-nova"
          tipo="password"
          valor={nova}
          onChange={setNova}
          autoComplete="new-password"
        />
        <Campo
          rotulo="Repita a nova"
          id="seg-repetida"
          tipo="password"
          valor={repetida}
          onChange={setRepetida}
          autoComplete="new-password"
        />
      </div>

      {erro && <p className="text-[12.5px] text-bad">{erro}</p>}

      <div className="flex justify-end gap-2">
        <Button type="button" size="sm" onClick={onFechar}>
          cancelar
        </Button>
        <Button
          type="submit"
          size="sm"
          variant="primary"
          disabled={trocar.isPending || !atual || !nova}
        >
          {trocar.isPending ? 'salvando...' : 'salvar senha'}
        </Button>
      </div>
    </form>
  )
}

function TrocaDeEmail({ atual, onFechar }: { atual: string; onFechar: () => void }) {
  const [senha, setSenha] = useState('')
  const [novo, setNovo] = useState('')
  const [erro, setErro] = useState('')

  const pedir = useMutation({
    mutationFn: () => pedirTrocaDeEmail(senha, novo.trim()),
    onMutate: () => setErro(''),
    onError: (err) => setErro(apiErrorMessage(err, 'Nao deu para pedir a troca.')),
  })

  if (pedir.isSuccess) {
    return (
      <div className="flex flex-col gap-3">
        <Bloco
          icone={<Mail size={20} />}
          titulo="Confirme no e-mail novo"
          descricao={pedir.data}
        />
        <p className="text-[12.5px] text-muted">
          Até você abrir aquele link, sua entrada continua sendo {atual}.
        </p>
        <div className="flex justify-end">
          <Button size="sm" onClick={onFechar}>
            fechar
          </Button>
        </div>
      </div>
    )
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault()
        pedir.mutate()
      }}
    >
      {/* O link vai para o endereco NOVO: e o unico jeito de provar que ele
          existe e e seu antes de virar a sua credencial de entrada. */}
      <Bloco
        icone={<Mail size={20} />}
        titulo="Trocar o e-mail de acesso"
        descricao="Mandamos um link para o endereço novo. Nada muda até você abrir esse link."
      />

      <div className="grid gap-3.5 sm:grid-cols-2">
        <Campo
          rotulo="Senha atual"
          id="seg-email-senha"
          tipo="password"
          valor={senha}
          onChange={setSenha}
          autoComplete="current-password"
          autoFocus
        />
        <Campo
          rotulo="E-mail novo"
          id="seg-email-novo"
          tipo="email"
          valor={novo}
          onChange={setNovo}
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
        />
      </div>

      {erro && <p className="text-[12.5px] text-bad">{erro}</p>}

      <div className="flex justify-end gap-2">
        <Button type="button" size="sm" onClick={onFechar}>
          cancelar
        </Button>
        <Button
          type="submit"
          size="sm"
          variant="primary"
          disabled={pedir.isPending || !senha || !novo.includes('@')}
        >
          {pedir.isPending ? 'enviando...' : 'mandar o link'}
        </Button>
      </div>
    </form>
  )
}

type Toast = ReturnType<typeof useToast>

function DoisFatores({ onMudou, toast }: { onMudou: () => void; toast: Toast }) {
  const [passo, setPasso] = useState<'fechado' | 'ligando' | 'desligando'>('fechado')
  const [codigo, setCodigo] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [codigos, setCodigos] = useState<string[]>([])

  const estado = useQuery({ queryKey: ['2fa'], queryFn: fetchDoisFatores })

  const preparar = useMutation({
    mutationFn: prepararDoisFatores,
    onMutate: () => {
      setErro('')
      setCodigos([])
      setPasso('ligando')
    },
    onError: (err) => setErro(apiErrorMessage(err, 'Nao deu para comecar a ativacao.')),
  })

  const confirmar = useMutation({
    mutationFn: () => confirmarDoisFatores(codigo.trim()),
    onMutate: () => setErro(''),
    onSuccess: (novos) => {
      setCodigos(novos)
      setCodigo('')
      setPasso('fechado')
      onMudou()
      toast.mostrar({ tom: 'ok', titulo: 'Segundo fator ativado.' })
    },
    onError: (err) => setErro(apiErrorMessage(err, 'Codigo incorreto.')),
  })

  const desativar = useMutation({
    mutationFn: () => desativarDoisFatores(senha),
    onMutate: () => setErro(''),
    onSuccess: () => {
      setSenha('')
      setPasso('fechado')
      setCodigos([])
      onMudou()
      toast.mostrar({ tom: 'ok', titulo: 'Segundo fator desativado.' })
    },
    onError: (err) => setErro(apiErrorMessage(err, 'Nao deu para desativar.')),
  })

  const renovar = useMutation({
    mutationFn: () => novosCodigosDeReserva(senha),
    onMutate: () => setErro(''),
    onSuccess: (novos) => {
      setCodigos(novos)
      setSenha('')
      setPasso('fechado')
      onMudou()
    },
    onError: (err) => setErro(apiErrorMessage(err, 'Nao deu para gerar codigos novos.')),
  })

  const ativo = estado.data?.ativo ?? false

  return (
    <div className="flex flex-col gap-4">
      <Bloco
        icone={<ShieldCheck size={20} />}
        titulo="Verificação em duas etapas"
        descricao={
          ativo
            ? `Ativa. Restam ${estado.data?.codigos_restantes ?? 0} códigos de reserva.`
            : 'Pede um código do seu celular além da senha, a cada entrada.'
        }
        acao={
          passo === 'fechado' ? (
            <div className="flex shrink-0 gap-2">
              {ativo ? (
                <>
                  <Button size="sm" onClick={() => setPasso('desligando')}>
                    desativar
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="primary"
                  disabled={preparar.isPending}
                  onClick={() => preparar.mutate()}
                >
                  ativar
                </Button>
              )}
            </div>
          ) : undefined
        }
      />

      {/* Preparar nao liga nada: quem desiste no meio nao fica trancado fora. */}
      {passo === 'ligando' && preparar.data && (
        <div className="flex flex-col gap-4 sm:flex-row">
          <img
            src={preparar.data.qr}
            alt="QR code para o aplicativo autenticador"
            className="h-40 w-40 shrink-0 self-center rounded-lg border border-line sm:self-start"
          />
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <p className="text-[13px] leading-relaxed text-muted">
              Leia o código com o Google Authenticator, o Authy ou o gerenciador de senhas que
              você usa. Se a câmera não ajudar, digite esta chave:
            </p>
            <code className="rounded border border-line bg-surface px-2.5 py-1.5 text-[12.5px] break-all">
              {preparar.data.segredo}
            </code>

            <form
              className="flex flex-col gap-3"
              onSubmit={(event) => {
                event.preventDefault()
                confirmar.mutate()
              }}
            >
              <Campo
                rotulo="Código do aplicativo"
                id="seg-2fa-codigo"
                valor={codigo}
                onChange={setCodigo}
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
              />
              {erro && <p className="text-[12.5px] text-bad">{erro}</p>}
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    setPasso('fechado')
                    setCodigo('')
                    setErro('')
                  }}
                >
                  cancelar
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  variant="primary"
                  disabled={confirmar.isPending || !codigo.trim()}
                >
                  {confirmar.isPending ? 'conferindo...' : 'ativar'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {passo === 'desligando' && (
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            desativar.mutate()
          }}
        >
          <p className="text-[13px] text-muted">
            Confirme com a senha da conta. Sem o segundo fator, sua senha volta a ser a única
            barreira.
          </p>
          <div className="sm:max-w-xs">
            <Campo
              rotulo="Senha atual"
              id="seg-2fa-senha"
              tipo="password"
              valor={senha}
              onChange={setSenha}
              autoComplete="current-password"
              autoFocus
            />
          </div>
          {erro && <p className="text-[12.5px] text-bad">{erro}</p>}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => {
                setPasso('fechado')
                setSenha('')
                setErro('')
              }}
            >
              cancelar
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={renovar.isPending || !senha}
              onClick={() => renovar.mutate()}
            >
              só gerar códigos novos
            </Button>
            <Button
              type="submit"
              size="sm"
              variant="destrutivo"
              disabled={desativar.isPending || !senha}
            >
              desativar
            </Button>
          </div>
        </form>
      )}

      {codigos.length > 0 && <CodigosDeReserva codigos={codigos} />}
    </div>
  )
}
