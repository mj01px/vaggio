import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { apiErrorMessage } from '@/lib/api'
import { confirmarEmail } from '@/services/session.service'
import { Aviso } from './Aviso'
import { Moldura } from './Moldura'

/**
 * Aplica a troca de e-mail que o link autoriza.
 *
 * Nao tem formulario: a decisao ja foi tomada quando a troca foi pedida, e o
 * clique no link e a prova de que o endereco novo e mesmo da pessoa. A tela
 * so mostra o resultado.
 *
 * `useQuery` e nao `useMutation` de proposito: a confirmacao acontece ao abrir
 * a pagina, sem um botao no meio do caminho.
 */
export function ConfirmarEmailPage() {
  const [params] = useSearchParams()
  const codigo = params.get('codigo') ?? ''

  const confirmacao = useQuery({
    queryKey: ['confirmar-email', codigo],
    queryFn: () => confirmarEmail(codigo),
    enabled: Boolean(codigo),
    retry: false,
  })

  if (!codigo) {
    return (
      <Moldura titulo="Link incompleto">
        <div className="mt-8 flex flex-col gap-4.5">
          <Aviso tom="bad">Abra pelo link do e-mail, inteiro.</Aviso>
          <Link to="/" className="text-[14px] font-medium text-accent hover:underline">
            Voltar para a entrada
          </Link>
        </div>
      </Moldura>
    )
  }

  return (
    <Moldura titulo="Troca de e-mail">
      <div className="mt-8 flex flex-col gap-4.5">
        {confirmacao.isPending && <p className="text-[15px] text-muted">Confirmando...</p>}

        {confirmacao.isError && (
          <>
            <Aviso tom="bad">
              {apiErrorMessage(confirmacao.error, 'Esse link nao vale mais.')}
            </Aviso>
            <p className="text-[14.5px] leading-relaxed text-muted">
              Peça a troca de novo pelo seu perfil, e abra o link mais recente que chegar.
            </p>
          </>
        )}

        {confirmacao.isSuccess && <Aviso tom="ok">{confirmacao.data}</Aviso>}

        <Link to="/" className="text-[14px] font-medium text-accent hover:underline">
          Ir para a entrada
        </Link>
      </div>
    </Moldura>
  )
}
