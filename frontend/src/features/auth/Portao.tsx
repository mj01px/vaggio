import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Outlet, useNavigate } from 'react-router-dom'
import { StateMessage } from '@/components/ui/StateMessage'
import { SessaoContext } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { fetchSessao, logout } from '@/services/session.service'
import type { Sessao } from '@/types/api'

/**
 * Quem sabe se ha sessao, para todo mundo abaixo.
 *
 * E a rota raiz do roteador, e nao um envelope acima dele, porque entrar e
 * sair agora sao navegacoes: `/` e o login e o resto exige sessao. Quem decide
 * o que fazer com a falta dela sao as guardas em `rotas.tsx`.
 */
export function Portao() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const sessao = useQuery({
    queryKey: ['sessao'],
    queryFn: fetchSessao,
    // A sessao nao muda sozinha, e uma consulta a mais aqui atrasa a primeira
    // pintura de toda tela.
    staleTime: 5 * 60_000,
    retry: false,
  })

  const recarregar = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['sessao'] })
  }, [queryClient])

  const sair = useCallback(() => {
    // A sessao cai aqui antes de a resposta chegar, e nesta ordem: esperar o
    // servidor deixaria o board no ar depois do clique, e navegar antes de
    // zerar o perfil faria a guarda de `/` achar que ainda ha sessao e mandar
    // de volta para o board.
    queryClient.setQueryData<Sessao>(['sessao'], { autenticado: false, perfil: null })
    navigate('/', { replace: true })

    // O `finally` cobre tambem a chamada que falha: ficar logado na tela
    // depois de pedir para sair seria pior que sair. O refetch da sessao no
    // fim e quem tem a ultima palavra.
    void logout().finally(() => {
      // Dado de vaga e de funil na memoria pertence a quem saiu. A chave da
      // sessao escapa da limpeza porque acabou de ser escrita: apagar ela
      // aqui faria a tela de login piscar um "Carregando..." a toa.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'sessao' })
      recarregar()
    })
  }, [queryClient, recarregar, navigate])

  if (sessao.isPending) return <StateMessage>Carregando...</StateMessage>

  if (sessao.isError) {
    return (
      <StateMessage tone="bad">
        {apiErrorMessage(sessao.error, 'A API nao respondeu. O backend esta rodando na 8000?')}
      </StateMessage>
    )
  }

  return (
    <SessaoContext.Provider value={{ perfil: sessao.data?.perfil ?? null, recarregar, sair }}>
      <Outlet />
    </SessaoContext.Provider>
  )
}
