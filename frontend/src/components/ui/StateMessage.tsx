/** Carregando e erro com a mesma moldura da lista, para a tela nao pular. */
export function StateMessage({ tone = 'muted', children }: { tone?: 'muted' | 'bad'; children: React.ReactNode }) {
  return (
    <div
      className={`rounded-lg border bg-card p-8 text-center ${
        tone === 'bad' ? 'border-bad text-bad' : 'border-line text-muted'
      }`}
    >
      {children}
    </div>
  )
}
