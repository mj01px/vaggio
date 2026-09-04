import { createBrowserRouter } from 'react-router-dom'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { BoardPage } from '@/features/board/BoardPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { EncerradasPage } from '@/features/encerradas/EncerradasPage'
import { ConfirmarEmailPage } from '@/features/auth/ConfirmarEmailPage'
import { DefinirSenhaPage } from '@/features/auth/DefinirSenhaPage'
import { EsqueciSenhaPage } from '@/features/auth/EsqueciSenhaPage'
import { Portao } from '@/features/auth/Portao'
import { RotaDeEntrada, RotaProtegida } from '@/features/auth/rotas'
import { CargosPage } from '@/features/admin/CargosPage'
import { ColetasPage } from '@/features/admin/ColetasPage'
import { PerfilPage } from '@/features/admin/PerfilPage'
import { UsuariosPage } from '@/features/admin/UsuariosPage'
import { RadarPage } from '@/features/radar/RadarPage'

/**
 * `/` e o login. Todo o resto vive atras da `RotaProtegida`, que devolve para
 * `/` quem chega sem sessao, inclusive numa URL colada direto na barra.
 *
 * Dentro do app, o dashboard e a home (`/dashboard`), a fila de triagem fica em
 * `/radar` e a administracao mora em rotas normais: nao ha painel separado.
 *
 * As rotas de dentro ficam abertas entre si de proposito: quem chega numa tela
 * que o cargo nao libera ve o erro que a API devolveu, em vez de um 404 que
 * faria parecer que a pagina nao existe.
 *
 * As quatro rotas publicas sao as unicas alcancaveis sem sessao alem do login,
 * e todas nascem de um link mandado por e-mail.
 */
export const router = createBrowserRouter([
  {
    element: <Portao />,
    children: [
      { path: '/', element: <RotaDeEntrada /> },

      // Publicas: quem chega aqui vem de um link do e-mail e por definicao
      // nao tem sessao. Ficam fora da `RotaProtegida`, mas dentro do `Portao`,
      // que e quem planta o cookie de CSRF que estes POSTs precisam.
      { path: '/esqueci-senha', element: <EsqueciSenhaPage /> },
      { path: '/redefinir-senha', element: <DefinirSenhaPage /> },
      { path: '/definir-senha', element: <DefinirSenhaPage convite /> },
      { path: '/confirmar-email', element: <ConfirmarEmailPage /> },
      {
        element: <RotaProtegida />,
        children: [
          { path: '/dashboard', element: <DashboardPage /> },
          { path: '/candidaturas', element: <BoardPage /> },
          { path: '/encerradas', element: <EncerradasPage /> },
          { path: '/radar', element: <RadarPage /> },
          { path: '/perfil', element: <PerfilPage /> },
          { path: '/usuarios', element: <UsuariosPage /> },
          { path: '/cargos', element: <CargosPage /> },
          { path: '/coletas', element: <ColetasPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
])
