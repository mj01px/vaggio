import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage } from '@/lib/api'
import { pedirRecuperacao } from '@/services/session.service'
import { Aviso } from './Aviso'
import { CAMPO, Moldura } from './Moldura'

/**
 * Pedir o link de recuperacao.
 *
 * A resposta e a mesma exista ou nao a conta, e a tela repete isso em vez de
 * dizer "enviado": prometer envio para um e-mail que nao existe seria mentira,
 * e dizer que nao existe entregaria quais contas existem para quem estiver
 * tentando adivinhar.
 */
export function EsqueciSenhaPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')

  const pedir = useMutation({
    mutationFn: () => pedirRecuperacao(email.trim()),
    onMutate: () => setError(''),
    onError: (err) =>
      setError(
        apiErrorMessage(
          err,
          'Nao deu para pedir o link agora. Espere um pouco e tente de novo.',
        ),
      ),
  })

  function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email.trim().includes('@')) {
      setError('Digite o e-mail da sua conta.')
      return
    }
    pedir.mutate()
  }

  if (pedir.isSuccess) {
    return (
      <Moldura titulo="Confira seu e-mail">
        <div className="mt-8 flex flex-col gap-4.5">
          <Aviso tom="ok">{pedir.data}</Aviso>
          <p className="text-[14.5px] leading-relaxed text-muted">
            O link vale por 2 horas e só funciona uma vez. Se não chegar, veja no spam e confira
            se o endereço está certo.
          </p>
          <Link to="/" className="text-[14px] font-medium text-accent hover:underline">
            Voltar para a entrada
          </Link>
        </div>
      </Moldura>
    )
  }

  return (
    <Moldura titulo="Esqueci minha senha">
      <p className="mt-3 text-[15px] leading-relaxed text-muted text-pretty">
        Diga o e-mail da sua conta e mandamos um link para você escolher uma senha nova.
      </p>

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

        {error && <Aviso tom="bad">{error}</Aviso>}

        <Button
          type="submit"
          variant="primary"
          className="mt-1 h-12 rounded-lg text-[15px] font-semibold"
          disabled={pedir.isPending}
        >
          {pedir.isPending ? 'Enviando...' : 'Mandar o link'}
        </Button>

        <Link
          to="/"
          className="text-center text-[14px] font-medium text-accent hover:underline"
        >
          Voltar para a entrada
        </Link>
      </form>
    </Moldura>
  )
}
