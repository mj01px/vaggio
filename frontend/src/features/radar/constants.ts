/** Opcoes e padroes dos filtros da fila, fora do componente para o fast refresh. */

export const SOURCES = [
  { value: 'github', label: 'GitHub Issues' },
  { value: 'gupy', label: 'Gupy' },
  { value: 'manual', label: 'Cadastro manual' },
]

export interface RadarFilterValues {
  /**
   * '' | discarded | all, direto no parametro `queue` da API.
   *
   * Sem controle na tela: sai da URL e volta para ela. `?queue=discarded` e o
   * caminho para rever o que foi descartado e devolver para a fila.
   */
  queue: string
  q: string
  source: string
  min_score: string
  /** Datas ISO locais (aaaa-mm-dd). Vazias trazem a fila inteira. */
  published_after: string
  published_before: string
}
