import type { ReactNode } from 'react'

const PROMESSA = 'Muita vaga entra. Só as certas chegam até você.'

/**
 * A moldura das telas de fora: login, recuperacao, convite, confirmacao.
 *
 * Extraida do login quando as telas publicas apareceram. Sao cinco telas que a
 * pessoa ve antes de ter sessao, e todas precisam parecer o mesmo produto: com
 * o layout copiado em cada uma, a terceira ja divergiria.
 *
 * `data-tema="claro"` fixa os tokens claros neste ramo da arvore: e a primeira
 * impressao do produto e nao deve depender do tema do SO de quem abre. Por isso
 * tambem nao ha `dark:invert` na logo aqui.
 */
export function Moldura({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div data-tema="claro" className="flex min-h-screen bg-card text-ink">
      <div className="flex w-full flex-col lg:w-160 lg:shrink-0">
        {/* No mobile a marca vira faixa: o painel da direita nao cabe, mas a
            promessa do produto ainda precisa aparecer antes do formulario. */}
        <div className="border-b border-line bg-wash px-6 pt-14 pb-6 lg:hidden">
          <img src="/logo-mark.png" alt="" className="mb-4 w-24" />
          <h2 className="text-[19px] leading-snug font-semibold tracking-tight text-accent text-pretty">
            {PROMESSA}
          </h2>
        </div>

        <div className="flex flex-1 flex-col px-6 py-7 sm:px-10 lg:px-22 lg:py-11">
          <div className="hidden items-center gap-2.5 lg:flex">
            <img src="/logo-mark.png" alt="" className="h-[26px] w-auto" />
            <span className="text-[15px] font-semibold tracking-[0.08em] uppercase">Vaggio</span>
          </div>

          <div className="flex flex-1 flex-col justify-center lg:py-10">
            <h1 className="text-[30px] font-semibold tracking-tight text-pretty">{titulo}</h1>
            {children}
          </div>

          <p className="mt-8 text-xs text-muted lg:mt-0">© 2026 Vaggio</p>
        </div>
      </div>

      <div className="hidden flex-1 flex-col justify-center border-l border-line bg-wash px-18 lg:flex">
        <img src="/logo-mark.png" alt="" className="mb-10 w-42" />

        <h2 className="max-w-115 text-[34px] leading-tight font-semibold tracking-tight text-accent text-pretty">
          {PROMESSA}
        </h2>

        <p className="mt-4.5 max-w-107 text-[15.5px] leading-relaxed text-muted text-pretty">
          O Vaggio coleta vagas de fontes públicas, pontua cada uma pelo seu perfil e não deixa
          nenhum follow-up passar.
        </p>
      </div>
    </div>
  )
}

/** Campo das telas de fora: maior que o do app, sem halo azul no foco. */
export const CAMPO =
  'h-[46px] w-full rounded-lg border border-field bg-card px-3.5 text-[15px] text-ink ' +
  'outline-none focus:border-ink'
