/** Formatacao compartilhada de data e numero, sempre em pt-BR. */

export function formatDate(value: string | null | undefined): string {
  if (!value) return ''
  return new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

/**
 * Data curta de vaga: dia e mes, com o ano so quando nao e o corrente.
 *
 * Com o periodo em "qualquer data" a fila mistura vaga desta semana com vaga do
 * ano passado, e "12/08" nas duas esconde justamente o que importa decidir.
 */
export function formatJobDate(value: string | null | undefined): string {
  if (!value) return ''
  const data = new Date(value)
  const mesmoAno = data.getFullYear() === new Date().getFullYear()
  return data.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    ...(mesmoAno ? {} : { year: '2-digit' }),
  })
}
