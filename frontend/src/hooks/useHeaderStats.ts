import { createContext, useContext, useEffect } from 'react'

export interface HeaderStat {
  label: string
  value: number | string
}

/**
 * Os contadores moram no header, mas quem sabe o numero e a pagina.
 * O layout expoe o setter e cada tela publica os seus ao montar.
 */
export const HeaderStatsContext = createContext<(stats: HeaderStat[]) => void>(() => {})

export function useHeaderStats(stats: HeaderStat[]) {
  const setStats = useContext(HeaderStatsContext)
  // Serializa para nao reagir a um array novo com o mesmo conteudo a cada render.
  const serialized = JSON.stringify(stats)

  useEffect(() => {
    setStats(JSON.parse(serialized) as HeaderStat[])
    return () => setStats([])
  }, [serialized, setStats])
}
