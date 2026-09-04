import type { ReactNode } from 'react'

type Tone = 'tag' | 'state'

/**
 * Pilula do cartao de vaga.
 *
 * Existe ao lado do Badge porque na mesma linha convivem dois tipos de
 * informacao: o estado da vaga (senioridade, modalidade, fonte), que sai do
 * contrato e vale a leitura, e a tag, que e ruido util. O contorno separa um
 * do outro sem precisar de cor nova, e o espacamento fica com o flex do pai
 * em vez de margem propria.
 */
const tones: Record<Tone, string> = {
  state: 'border-line bg-card text-ink font-medium',
  tag: 'border-transparent bg-surface text-muted',
}

export function Chip({ tone = 'tag', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-px text-[11px] leading-5 ${tones[tone]}`}
    >
      {children}
    </span>
  )
}
