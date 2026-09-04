import type { ReactNode } from 'react'

type Tone = 'default' | 'bad'

/**
 * A moldura padrao de bloco de conteudo.
 *
 * Borda, nao sombra: cartao parado nao flutua. Sombra fica reservada para o que
 * realmente esta acima da pagina — menu, modal, cartao sendo arrastado.
 */
const tones: Record<Tone, string> = {
  default: 'border-line bg-card',
  bad: 'border-bad/25 bg-bad/[0.03]',
}

interface Props {
  tone?: Tone
  className?: string
  children: ReactNode
}

export function Card({ tone = 'default', className = '', children }: Props) {
  return (
    <div className={`rounded-[10px] border ${tones[tone]} ${className}`}>{children}</div>
  )
}

/** Cabecalho de cartao: titulo a esquerda, acao ou contador a direita. */
export function CardHeader({
  titulo,
  children,
}: {
  titulo: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-[15px] font-semibold">{titulo}</span>
      {children}
    </div>
  )
}
