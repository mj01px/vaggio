import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'neutral' | 'destrutivo' | 'texto'
type Size = 'md' | 'sm'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

const base =
  'inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg font-medium ' +
  'outline-none focus-visible:border-ink disabled:cursor-not-allowed disabled:opacity-45'

/**
 * `md` e o botao de formulario, `sm` o de barra de ferramentas. Mesma borda,
 * mesmo raio, mesma cor: so a densidade muda.
 */
const sizes: Record<Size, string> = {
  md: 'h-10 px-4 text-sm',
  sm: 'h-9 px-3 text-[13.5px]',
}

const variants: Record<Variant, string> = {
  primary: 'border border-accent bg-accent font-semibold text-white hover:opacity-90',
  neutral: 'border border-field bg-card text-ink hover:border-ink hover:bg-surface',
  destrutivo: 'border border-bad bg-card font-semibold text-bad hover:bg-bad/5',
  texto: 'border border-transparent bg-transparent text-accent hover:underline',
}

export function Button({
  variant = 'neutral',
  size = 'md',
  className = '',
  ...props
}: Props) {
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props} />
  )
}

/** Botao quadrado que carrega so um icone. */
export function IconButton({
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg text-muted outline-none hover:bg-surface hover:text-ink focus-visible:border focus-visible:border-ink disabled:cursor-not-allowed disabled:opacity-45 ${className}`}
      {...props}
    />
  )
}
