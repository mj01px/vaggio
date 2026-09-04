import {
  Archive,
  Columns3,
  LayoutDashboard,
  RefreshCw,
  ShieldCheck,
  Target,
  Users,
  type LucideIcon,
} from 'lucide-react'
import type { PermissaoKey } from '@/types/api'

export interface ItemNav {
  para: string
  rotulo: string
  icone: LucideIcon
  /** A linha de apoio que a topbar mostra sob o titulo. */
  descricao: string
  exige?: PermissaoKey
}

export interface GrupoNav {
  titulo: string
  itens: ItemNav[]
}

/**
 * A navegacao inteira, com a permissao que cada item exige.
 *
 * O item some quando o cargo nao libera, mas isso e conveniencia: quem decide e
 * o backend, que checa de novo em toda chamada.
 *
 * Agrupado em vez de lista unica porque a administracao tende a crescer, e
 * misturada com o trabalho do dia ela empurra Board e Radar para baixo.
 */
export const GRUPOS: GrupoNav[] = [
  {
    titulo: 'Trabalho',
    itens: [
      {
        para: '/dashboard',
        rotulo: 'Dashboard',
        icone: LayoutDashboard,
        descricao: 'O estado do dia: o que venceu, onde está o funil e se a coleta rodou',
      },
      // Radar antes de Candidaturas porque essa e a ordem do fluxo: a vaga
      // chega na fila, e so depois de um "quero" ela vira candidatura.
      {
        para: '/radar',
        rotulo: 'Radar',
        icone: Target,
        descricao: 'A fila de vagas coletadas, ordenada pelo score do seu perfil',
        exige: 'vagas.ver',
      },
      {
        para: '/candidaturas',
        rotulo: 'Candidaturas',
        icone: Columns3,
        descricao: 'Onde cada candidatura está, de "quero aplicar" até a proposta',
        exige: 'funil.ver',
      },
      {
        para: '/encerradas',
        rotulo: 'Encerradas',
        icone: Archive,
        descricao: 'O que já acabou: onde você não passou e de onde desistiu',
        exige: 'funil.ver',
      },
    ],
  },
  {
    titulo: 'Administração',
    itens: [
      {
        para: '/coletas',
        rotulo: 'Coletas',
        icone: RefreshCw,
        descricao: 'Histórico de execução das fontes, com o que cada uma trouxe',
        exige: 'coleta.ver',
      },
      {
        para: '/usuarios',
        rotulo: 'Usuários',
        icone: Users,
        descricao: 'Quem tem acesso ao Vaggio e com qual cargo',
        exige: 'usuarios.ver',
      },
      {
        para: '/cargos',
        rotulo: 'Cargos',
        icone: ShieldCheck,
        descricao: 'Os cargos e o que cada permissão libera',
        exige: 'cargos.ver',
      },
    ],
  },
]

export interface Cabecalho {
  titulo: string
  descricao: string
  /**
   * Classe de largura da coluna de conteudo, aplicada ao cabecalho junto.
   *
   * Vazio e a largura toda, que e o que lista e tabela querem. Tela de
   * formulario pede coluna estreita, e ai o titulo tem de acompanhar: coluna
   * centralizada com titulo grudado na esquerda fica torta.
   */
  largura?: string
}

/** O que a topbar mostra, a partir da rota atual. */
export function cabecalhoDaRota(pathname: string): Cabecalho {
  const item = GRUPOS.flatMap((g) => g.itens).find(
    (i) => pathname === i.para || pathname.startsWith(`${i.para}/`),
  )
  if (item) return { titulo: item.rotulo, descricao: item.descricao }
  if (pathname.startsWith('/perfil')) {
    return {
      titulo: 'Perfil',
      descricao: 'Seu dossiê e as preferências que alimentam o score',
      largura: 'mx-auto w-full max-w-3xl',
    }
  }
  return { titulo: 'Vaggio', descricao: '' }
}
