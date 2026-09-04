import { Navigate, useLocation } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { useSessao } from '@/hooks/useSessao'
import { LoginPage } from './LoginPage'

/** Onde quem entra cai, e para onde volta quem sai de uma rota protegida. */
const INICIO = '/dashboard'

/** O que estava sendo tentado antes de cair no login. */
interface Origem {
  de?: string
}

/**
 * A rota `/`: o login, ou o app se ja houver sessao.
 *
 * Quem ja entrou nao pode ficar olhando a tela de login: ou ele acha que
 * precisa entrar de novo, ou entra de novo e cicla a sessao a toa.
 */
export function RotaDeEntrada() {
  const { perfil, recarregar } = useSessao()
  const { state } = useLocation()

  if (perfil) {
    return <Navigate to={(state as Origem | null)?.de ?? INICIO} replace />
  }

  return <LoginPage onEntrou={recarregar} />
}

/**
 * Tudo que nao e o login.
 *
 * Sem sessao a rota nem monta: volta para `/` guardando aonde a pessoa queria
 * ir, para o login devolver ela ao lugar certo em vez de despejar no board.
 * Isto e conveniencia de navegacao, nao seguranca: quem decide e o backend,
 * que responde 403 em toda chamada sem sessao.
 */
export function RotaProtegida() {
  const { perfil } = useSessao()
  const location = useLocation()

  if (!perfil) {
    return <Navigate to="/" replace state={{ de: location.pathname + location.search }} />
  }

  return <AppLayout />
}
