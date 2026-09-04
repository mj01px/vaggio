import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage } from '@/lib/api'
import { entrarComCodigo, login } from '@/services/session.service'
import { Aviso } from './Aviso'
import { CAMPO, Moldura } from './Moldura'

interface Props {
  onEntrou: () => void
}

export function LoginPage({ onEntrou }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [lembrar, setLembrar] = useState(true)
  const [error, setError] = useState('')

  // Com segundo fator, a senha certa ainda nao e entrar: a tela troca para o
  // passo do codigo e a sessao so existe depois dele.
  const [pedindoCodigo, setPedindoCodigo] = useState(false)
  const [codigo, setCodigo] = useState('')

  const entrar = useMutation({
    mutationFn: () => login(email, password, lembrar),
    onMutate: () => setError(''),
    onSuccess: (resposta) => {
      if (resposta.precisa_codigo) {
        setPedindoCodigo(true)
        return
      }
      onEntrou()
    },
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para entrar.')),
  })

  const conferir = useMutation({
    mutationFn: () => entrarComCodigo(codigo.trim()),
    onMutate: () => setError(''),
    onSuccess: onEntrou,
    onError: (err) => setError(apiErrorMessage(err, 'Codigo incorreto.')),
  })

  /**
   * O botao fica sempre clicavel: botao apagado nao explica o que falta, e
   * quem chega sem entender por que nao entra fica sem resposta nenhuma.
   *
   * A checagem e daqui e nao da API de proposito. O DRF responde "Este campo
   * nao pode ser em branco" sem dizer qual campo, o que na tela nao ajuda -
   * e ainda gastaria uma ida ao servidor para algo que da para saber aqui.
   * O `trim` acompanha o CharField do DRF, que ja corta espaco nas pontas.
   *
   * O formulario vai com `noValidate` pelo mesmo motivo: o balao nativo do
   * type="email" seria uma terceira voz dizendo a mesma coisa de outro jeito.
   * O type continua ali pelo teclado do celular e pelo autofill.
   */
  function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const faltando: string[] = []
    if (!email.trim()) faltando.push('o e-mail')
    if (!password.trim()) faltando.push('a senha')

    if (faltando.length > 0) {
      setError(`Preencha ${faltando.join(' e ')}.`)
      return
    }

    if (!email.includes('@')) {
      setError('Digite o e-mail da sua conta.')
      return
    }

    entrar.mutate()
  }

  function enviarCodigo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!codigo.trim()) {
      setError('Digite o código.')
      return
    }
    conferir.mutate()
  }

  if (pedindoCodigo) {
    return (
      <Moldura titulo="Confirme que é você">
        <p className="mt-3 text-[15px] leading-relaxed text-muted text-pretty">
          Digite o código de seis dígitos do seu aplicativo autenticador. Se você não estiver com
          o celular, use um dos códigos de reserva.
        </p>

        <form onSubmit={enviarCodigo} noValidate className="mt-8 flex flex-col gap-4.5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="codigo" className="text-[13px] font-medium">
              Código
            </label>
            <input
              id="codigo"
              value={codigo}
              // `one-time-code` e o que faz o iOS e o Android oferecerem o
              // codigo direto do teclado, sem passear pelo app autenticador.
              autoComplete="one-time-code"
              inputMode="numeric"
              autoFocus
              onChange={(event) => setCodigo(event.target.value)}
              className={`${CAMPO} tracking-[0.3em] tabular-nums`}
            />
          </div>

          {error && <Aviso tom="bad">{error}</Aviso>}

          <Button
            type="submit"
            variant="primary"
            className="mt-1 h-12 rounded-lg text-[15px] font-semibold"
            disabled={conferir.isPending}
          >
            {conferir.isPending ? 'Conferindo...' : 'Entrar'}
          </Button>

          <button
            type="button"
            onClick={() => {
              setPedindoCodigo(false)
              setCodigo('')
              setPassword('')
              setError('')
            }}
            className="cursor-pointer text-center text-[14px] font-medium text-accent hover:underline"
          >
            Voltar
          </button>
        </form>
      </Moldura>
    )
  }

  return (
    <Moldura titulo="Entrar na sua conta">
      <form onSubmit={enviar} noValidate className="mt-8 flex flex-col gap-4.5">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-[13px] font-medium">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            value={email}
            autoComplete="email"
            autoCapitalize="none"
            spellCheck={false}
            autoFocus
            onChange={(event) => setEmail(event.target.value)}
            className={CAMPO}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3">
            <label htmlFor="password" className="text-[13px] font-medium">
              Senha
            </label>
            <button
              type="button"
              onClick={() => setMostrarSenha((visivel) => !visivel)}
              aria-pressed={mostrarSenha}
              aria-controls="password"
              className="cursor-pointer text-[12.5px] font-medium text-accent hover:underline"
            >
              {mostrarSenha ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>
          <input
            id="password"
            type={mostrarSenha ? 'text' : 'password'}
            value={password}
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            className={CAMPO}
          />
        </div>

        {/* Mesmo checkbox nativo do resto do app (accent-current), so
            maior: aqui ele e alvo de toque, nao item de lista densa. */}
        <label className="flex min-h-11 cursor-pointer items-center gap-2.5 text-[13.5px] text-accent lg:min-h-0">
          <input
            type="checkbox"
            checked={lembrar}
            onChange={(event) => setLembrar(event.target.checked)}
            className="h-4 w-4 accent-current"
          />
          <span className="text-ink">Continuar conectado</span>
        </label>

        {error && <Aviso tom="bad">{error}</Aviso>}

        <Button
          type="submit"
          variant="primary"
          className="mt-1 h-12 rounded-lg text-[15px] font-semibold"
          disabled={entrar.isPending}
        >
          {entrar.isPending ? 'Entrando...' : 'Entrar'}
        </Button>

        <Link
          to="/esqueci-senha"
          className="text-center text-[14px] font-medium text-accent hover:underline"
        >
          Esqueci minha senha
        </Link>
      </form>
    </Moldura>
  )
}
