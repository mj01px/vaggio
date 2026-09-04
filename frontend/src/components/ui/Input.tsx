import type { InputHTMLAttributes, ReactNode } from 'react'

type Size = 'md' | 'sm' | 'xs'

/** `md` no formulario, `sm` na barra de ferramentas. */
const sizes: Record<Size, string> = {
  md: 'h-11 px-3.5 text-[14.5px]',
  sm: 'h-9 px-3 text-[13.5px]',
  // `xs` e do painel de filtro, onde varios campos dividem uma linha so.
  xs: 'h-8 px-2.5 text-[13px]',
}

/**
 * O foco escurece a borda e nao pinta halo: o halo azul saiu do login e a
 * regra vale para o app inteiro. Mas alguma marca tem de existir — com
 * `outline-none` e nada no lugar, quem navega de Tab anda as cegas.
 */
const base =
  'w-full rounded-lg border bg-card text-ink outline-none placeholder:text-muted ' +
  'disabled:cursor-not-allowed disabled:border-line disabled:bg-surface disabled:text-muted'

const borda = (invalido: boolean) =>
  invalido ? 'border-bad' : 'border-field focus:border-ink'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  inputSize?: Size
  invalido?: boolean
}

export function Input({
  inputSize = 'md',
  invalido = false,
  className = '',
  ...props
}: InputProps) {
  return (
    <input
      className={`${base} ${sizes[inputSize]} ${borda(invalido)} ${className}`}
      {...props}
    />
  )
}

/** Rotulo + campo + erro, que e o trio que todo formulario repete. */
export function Campo({
  label,
  htmlFor,
  erro,
  acao,
  children,
}: {
  label: string
  htmlFor?: string
  erro?: string
  acao?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={htmlFor} className="text-[13px] font-medium">
          {label}
        </label>
        {acao}
      </div>
      {children}
      {erro && <span className="text-[12.5px] text-bad">{erro}</span>}
    </div>
  )
}
