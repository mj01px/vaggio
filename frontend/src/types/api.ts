/** Tipos do contrato da API, espelhando os serializers do backend. */

export type JobSourceKey = 'github' | 'gupy' | 'manual'
export type SeniorityKey = 'internship' | 'junior' | 'mid' | 'senior' | 'unknown'
export type WorkModeKey = 'remote' | 'hybrid' | 'onsite' | 'unknown'

export type ApplicationStatusKey =
  | 'interest'
  | 'applied'
  | 'screening'
  | 'challenge'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn'

export interface Job {
  id: number
  title: string
  company: string
  location: string
  url: string
  source: JobSourceKey
  source_display: string
  seniority: SeniorityKey
  seniority_display: string
  work_mode: WorkModeKey
  work_mode_display: string
  score: number
  tags: string[]
  discarded: boolean
  has_application: boolean
  published_at: string | null
  created_at: string
}

/** A vaga aberta sozinha: traz a descricao, que a lista nao carrega. */
export interface JobDetalhe extends Job {
  description: string
  source_id: string
  updated_at: string
}

export interface Application {
  id: number
  job: Job
  status: ApplicationStatusKey
  status_display: string
  priority: number
  applied_on: string | null
  next_step: string
  next_step_on: string | null
  contact: string
  has_referral: boolean
  notes: string
  is_overdue: boolean
  days_idle: number
  created_at: string
  updated_at: string
}

export interface BoardColumn {
  status: ApplicationStatusKey
  label: string
  total: number
  items: Application[]
}

export interface Board {
  columns: BoardColumn[]
  overdue: Application[]
  stats: {
    in_funnel: number
    overdue: number
    radar_queue: number
    closed: number
  }
  statuses: { value: ApplicationStatusKey; label: string }[]
}

/** O que /applications/closed/ devolve: quem saiu do funil, e como saiu. */
export interface Encerradas {
  results: Application[]
  stats: {
    rejected: number
    withdrawn: number
  }
}

/** Uma acao que o cargo pode liberar. Os slugs vem do backend. */
export type PermissaoKey =
  | 'vagas.ver'
  | 'vagas.triar'
  | 'vagas.gerenciar'
  | 'funil.ver'
  | 'funil.gerenciar'
  | 'coleta.ver'
  | 'coleta.rodar'
  | 'apresentacao.gerar'
  | 'perfil.editar'
  | 'usuarios.ver'
  | 'usuarios.gerenciar'
  | 'cargos.ver'
  | 'cargos.gerenciar'

export interface Cargo {
  id: number
  slug: string
  nome: string
  descricao: string
  permissoes: PermissaoKey[]
}

/** Tudo que o app sabe sobre quem esta usando. */
export interface Perfil {
  id: number
  /** A credencial de login. */
  email: string
  nome: string
  cargo: Cargo | null
  permissoes: PermissaoKey[]
  dossie: string
  tem_dossie: boolean
  termos: Record<string, { weight: number; terms: string[] }>
  pitch_max_chars: number
  created_at: string
  updated_at: string
}

export interface Permissao {
  id: number
  slug: PermissaoKey
  nome: string
  descricao: string
}

/** Uma pessoa com acesso, na tela de usuarios. */
export interface Usuario {
  id: number
  email: string
  nome: string
  cargo: Cargo | null
  permissoes: PermissaoKey[]
  perfil_id: number | null
  tem_dossie: boolean
  is_active: boolean
  /**
   * So vem para quem tem `usuarios.gerenciar`.
   *
   * Quem so pode VER usuarios nao precisa saber quais contas passam por cima de
   * todo o controle de acesso, e a API deixou de mandar. Opcional aqui, e nao
   * `boolean`, para o TypeScript cobrar o tratamento de quando ele nao vem: o
   * unico uso e desabilitar o botao de desativar, que so aparece para quem
   * gerencia e portanto recebe o campo.
   */
  is_superuser?: boolean
  last_login: string | null
  date_joined: string
}

/**
 * O que o POST de entrada devolve.
 *
 * Com segundo fator ligado, a senha certa ainda nao e uma sessao: vem
 * `precisa_codigo` e a entrada so fecha no `/sessao/codigo/`.
 */
export interface Entrada {
  autenticado: boolean
  perfil?: Perfil | null
  precisa_codigo?: boolean
}

export interface Sessao {
  autenticado: boolean
  perfil: Perfil | null
}

/** Uma versao gerada do "Apresente-se" da Gupy. */
export interface Pitch {
  id: number
  texto: string
  caracteres: number
  modelo: string
  instrucao: string
  max_chars: number
  tokens_entrada: number
  tokens_saida: number
  tokens_pensamento: number
  created_at: string
}

/** Contadores de /jobs/stats/: a fila inteira, sem filtro de tela. */
export interface JobStats {
  triage: number
  discarded: number
  total: number
}

/** Resultado de uma rodada de coleta, por fonte. */
export interface CollectionSourceResult {
  source: JobSourceKey
  found: number
  new: number
  old: number
  low_score: number
  duplicate: number
  error: string
}

export interface CollectionResult {
  new: number
  sources: CollectionSourceResult[]
  errors: { source: string; message: string }[]
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
