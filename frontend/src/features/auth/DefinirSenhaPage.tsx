import { useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage } from '@/lib/api'
import { conferirLink, redefinirSenha } from '@/services/session.service'
import { Aviso } from './Aviso'
import { CAMPO, Moldura } from './Moldura'

/**
 * Fecha o link de senha: recuperacao e convite caem os dois aqui.
 *
 * Os dois usam o mesmo token do backend, entao a unica diferenca e o texto:
 * quem esqueceu a senha esta trocando uma que tinha, quem foi convidado esta
 * escolhendo a primeira. `convite` decide qual das duas historias contar.
 */
export function DefinirSenhaPage({ convite = false }: { convite?: boolean }) {
  const [params] = useSearchParams()
  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''

  const [nova, setNova] = useState('')
  const [repetida, setRepetida] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [error, setError] = useState('')

  // Confere o link antes de pedir a senha: sem isto a pessoa so descobriria
  // que ele venceu depois de escolher e digitar a senha duas vezes.
  const link = useQuery({
    queryKey: ['link-de-senha', uid, token],
    queryFn: () => conferirLink(uid, token),
    enabled: Boolean(uid && token),
    retry: false,
  })

  const definir = useMutation({
    mutationFn: () => redefinirSenha(uid, token, nova),
    onMutate: () => setError(''),
    onError: (err) => setError(apiErrorMessage(err, 'Nao deu para salvar a senha.')),
  })

  function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!nova) {
      setError('Escolha uma senha.')
      return
    }
    if (nova !== repetida) {
      setError('As duas senhas precisam ser iguais.')
      return
    }
    definir.mutate()
  }

  const titulo = convite ? 'Escolha sua senha' : 'Nova senha'

  if (!uid || !token) {
    return (
      <Moldura titulo="Link incompleto">
        <div className="mt-8 flex flex-col gap-4.5">
          <Aviso tom="bad">
            Este endereço está sem os dados do link. Abra pelo link do e-mail, inteiro.
          </Aviso>
          <Link to="/" className="text-[14px] font-medium text-accent hover:underline">
            Voltar para a entrada
          </Link>
        </div>
      </Moldura>
    )
  }

  if (link.isPending) {
    return (
      <Moldura titulo={titulo}>
        <p className="mt-3 text-[15px] text-muted">Conferindo o link...</p>
      </Moldura>
    )
  }

  if (link.isError || !link.data?.valido) {
    return (
      <Moldura titulo="Esse link não vale mais">
        <div className="mt-8 flex flex-col gap-4.5">
          <p className="text-[15px] leading-relaxed text-muted text-pretty">
            Links de senha valem uma vez só e expiram. Peça um novo e use o mais recente que
            chegar.
          </p>
          <Link
            to="/esqueci-senha"
            className="text-[14px] font-medium text-accent hover:underline"
          >
            Pedir um link novo
          </Link>
        </div>
      </Moldura>
    )
  }

  if (definir.isSuccess) {
    return (
      <Moldura titulo="Senha definida">
        <div className="mt-8 flex flex-col gap-4.5">
          <Aviso tom="ok">Pronto. Agora é só entrar com a senha nova.</Aviso>
          <Link to="/" className="text-[14px] font-medium text-accent hover:underline">
            Ir para a entrada
          </Link>
        </div>
      </Moldura>
    )
  }

  return (
    <Moldura titulo={titulo}>
      <p className="mt-3 text-[15px] leading-relaxed text-muted text-pretty">
        {convite
          ? `Sua conta já existe. Escolha a senha de ${link.data.email} e entre.`
          : `Escolha a senha nova de ${link.data.email}.`}
      </p>

      <form onSubmit={enviar} noValidate className="mt-8 flex flex-col gap-4.5">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3">
            <label htmlFor="nova" className="text-[13px] font-medium">
              Senha
            </label>
            <button
              type="button"
              onClick={() => setMostrar((visivel) => !visivel)}
              aria-pressed={mostrar}
              aria-controls="nova"
              className="cursor-pointer text-[12.5px] font-medium text-accent hover:underline"
            >
              {mostrar ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>
          <input
            id="nova"
            type={mostrar ? 'text' : 'password'}
            value={nova}
            autoComplete="new-password"
            autoFocus
            onChange={(event) => setNova(event.target.value)}
            className={CAMPO}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="repetida" className="text-[13px] font-medium">
            Repita a senha
          </label>
          <input
            id="repetida"
            type={mostrar ? 'text' : 'password'}
            value={repetida}
            autoComplete="new-password"
            onChange={(event) => setRepetida(event.target.value)}
            className={CAMPO}
          />
        </div>

        {error && <Aviso tom="bad">{error}</Aviso>}

        <Button
          type="submit"
          variant="primary"
          className="mt-1 h-12 rounded-lg text-[15px] font-semibold"
          disabled={definir.isPending}
        >
          {definir.isPending ? 'Salvando...' : 'Salvar senha'}
        </Button>
      </form>
    </Moldura>
  )
}
