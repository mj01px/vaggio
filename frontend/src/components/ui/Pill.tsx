import type { ReactNode } from 'react'

/**
 * A pilula do sistema, com tres familias de uso:
 *
 * - `state` e `tag` existem porque na mesma linha convivem dois tipos de
 *   informacao: o estado da vaga, que sai do contrato e vale a leitura, e a
 *   tag, que e ruido util. O contorno separa um do outro sem cor nova.
 * - as semanticas (`ok`, `warn`, `bad`, `accent`) sao para quando a cor
 *   significa alguma coisa. Fora disso, cor vira decoracao e perde o valor.
 */
export type PillTone = 'state' | 'tag' | 'ok' | 'warn' | 'bad' | 'accent'

const tones: Record<PillTone, string> = {
  state: 'border border-line bg-card text-ink font-medium',
  tag: 'border border-transparent bg-surface text-muted',
  ok: 'bg-ok/10 text-ok font-medium',
  warn: 'bg-warn/10 text-warn font-medium',
  bad: 'bg-bad/10 text-bad font-medium',
  accent: 'bg-wash text-accent font-medium',
}

export function Pill({
  tone = 'tag',
  className = '',
  children,
}: {
  tone?: PillTone
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11.5px] leading-[17px] ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  )
}

/** Contador redondo de alerta: o "3" que aparece ao lado de Board. */
export function Contador({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-5 min-w-[22px] items-center justify-center rounded-full bg-bad px-1.5 text-[11px] font-semibold text-white">
      {children}
    </span>
  )
}
