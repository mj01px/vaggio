import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react'

type Size = 'md' | 'sm' | 'xs'

const sizes: Record<Size, string> = {
  md: 'h-11 px-3.5 text-[14.5px]',
  sm: 'h-9 px-3 text-[13.5px]',
  xs: 'h-8 px-2.5 text-[13px]',
}

const MESES = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]
const SEMANA = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S']

/** ISO local (aaaa-mm-dd). `toISOString` daria o dia errado perto da meia-noite. */
function iso(ano: number, mes: number, dia: number): string {
  return `${ano}-${String(mes + 1).padStart(2, '0')}-${String(dia).padStart(2, '0')}`
}

function deIso(valor: string): Date | null {
  if (!valor) return null
  const [a, m, d] = valor.split('-').map(Number)
  if (!a || !m || !d) return null
  return new Date(a, m - 1, d)
}

function curto(valor: string): string {
  const data = deIso(valor)
  if (!data) return ''
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

interface Props {
  value: string
  onChange: (valor: string) => void
  /** Impede escolher antes desta data, para o "ate" nunca ficar antes do "de". */
  min?: string
  max?: string
  placeholder?: string
  inputSize?: Size
  id?: string
  'aria-label'?: string
}

/**
 * Escolha de data pelo calendario.
 *
 * Substitui a janela de recencia em dias ("ultimos 7 dias"): preset responde
 * "o que e recente", mas nao responde "o que saiu naquela terca". Duas datas
 * cobrem os dois casos.
 *
 * Vai para um portal com posicao fixa pelo mesmo motivo do `Select`: os
 * containers do app rolam com `overflow` e cortariam o calendario inline.
 */
export function DateSelect({
  value,
  onChange,
  min,
  max,
  placeholder = 'dd/mm/aa',
  inputSize = 'xs',
  id,
  'aria-label': ariaLabel,
}: Props) {
  const [aberto, setAberto] = useState(false)
  const [caixa, setCaixa] = useState<{ top: number; left: number; largura: number } | null>(null)
  const [vista, setVista] = useState(() => deIso(value) ?? new Date())

  const botao = useRef<HTMLButtonElement>(null)
  const painel = useRef<HTMLDivElement>(null)

  const limiteMin = deIso(min ?? '')
  const limiteMax = deIso(max ?? '')

  const dias = useMemo(() => {
    const ano = vista.getFullYear()
    const mes = vista.getMonth()
    const primeiro = new Date(ano, mes, 1).getDay()
    const total = new Date(ano, mes + 1, 0).getDate()
    // Os nulos da frente alinham o dia 1 na coluna certa da semana.
    return [...Array<null>(primeiro).fill(null), ...Array.from({ length: total }, (_, i) => i + 1)]
  }, [vista])

  useLayoutEffect(() => {
    if (!aberto || !botao.current) return
    const r = botao.current.getBoundingClientRect()
    const altura = 300
    const cabeAbaixo = window.innerHeight - r.bottom > altura
    // A largura e a do proprio campo, e nao um numero fixo: calendario mais
    // largo que o campo nao parece sair dele, parece um cartao solto na tela.
    // O piso de 196px e onde a celula do dia para de ser clicavel.
    const largura = Math.max(r.width, 196)
    setCaixa({
      top: cabeAbaixo ? r.bottom + 6 : Math.max(8, r.top - altura - 6),
      left: Math.max(8, Math.min(r.left, window.innerWidth - largura - 12)),
      largura,
    })
  }, [aberto])

  useEffect(() => {
    if (!aberto) return
    const fora = (evento: MouseEvent) => {
      const alvo = evento.target as Node
      if (botao.current?.contains(alvo) || painel.current?.contains(alvo)) return
      setAberto(false)
    }
    const some = () => setAberto(false)
    document.addEventListener('mousedown', fora)
    window.addEventListener('scroll', some, true)
    window.addEventListener('resize', some)
    return () => {
      document.removeEventListener('mousedown', fora)
      window.removeEventListener('scroll', some, true)
      window.removeEventListener('resize', some)
    }
  }, [aberto])

  function abrir() {
    setVista(deIso(value) ?? new Date())
    setAberto(true)
  }

  function bloqueado(dia: number): boolean {
    const data = new Date(vista.getFullYear(), vista.getMonth(), dia)
    if (limiteMin && data < limiteMin) return true
    if (limiteMax && data > limiteMax) return true
    return false
  }

  const hoje = new Date()
  const escolhida = deIso(value)

  return (
    <>
      <div className="relative">
        <button
          ref={botao}
          id={id}
          type="button"
          aria-label={ariaLabel}
          aria-expanded={aberto}
          onClick={() => (aberto ? setAberto(false) : abrir())}
          onKeyDown={(e) => e.key === 'Escape' && setAberto(false)}
          className={`flex w-full cursor-pointer items-center gap-2 rounded-lg border bg-card text-left outline-none ${
            sizes[inputSize]
          } ${aberto ? 'border-ink' : 'border-field'} ${value ? 'text-ink' : 'text-muted'} ${
            value ? 'pr-7' : ''
          }`}
        >
          <CalendarDays size={15} className="shrink-0 text-muted" />
          <span className="truncate">{value ? curto(value) : placeholder}</span>
        </button>

        {/* O limpar mora fora do botao: botao dentro de botao nao e HTML valido
            e o clique de um comeria o do outro. */}
        {value && (
          <button
            type="button"
            aria-label="Limpar data"
            onClick={() => onChange('')}
            className="absolute top-1/2 right-1.5 -translate-y-1/2 cursor-pointer rounded p-1 text-muted outline-none hover:text-ink focus-visible:border focus-visible:border-ink"
          >
            <X size={13} />
          </button>
        )}
      </div>

      {aberto &&
        caixa &&
        createPortal(
          <div
            ref={painel}
            // O portal perde o escopo do tema claro da raiz do app.
            data-tema="claro"
            style={{ top: caixa.top, left: caixa.left, width: caixa.largura }}
            className="fixed z-50 rounded-[10px] border border-line bg-card p-2.5 shadow-lg shadow-ink/10"
          >
            <div className="mb-2 flex items-center justify-between">
              <button
                type="button"
                aria-label="Mês anterior"
                onClick={() => setVista(new Date(vista.getFullYear(), vista.getMonth() - 1, 1))}
                className="cursor-pointer rounded-md p-1 text-muted outline-none hover:bg-surface hover:text-ink"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-[13px] font-semibold">
                {MESES[vista.getMonth()]} de {vista.getFullYear()}
              </span>
              <button
                type="button"
                aria-label="Próximo mês"
                onClick={() => setVista(new Date(vista.getFullYear(), vista.getMonth() + 1, 1))}
                className="cursor-pointer rounded-md p-1 text-muted outline-none hover:bg-surface hover:text-ink"
              >
                <ChevronRight size={16} />
              </button>
            </div>

            <div className="grid grid-cols-7 gap-0.5">
              {SEMANA.map((letra, indice) => (
                <span
                  key={indice}
                  className="grid h-7 place-items-center text-[11px] font-semibold text-muted"
                >
                  {letra}
                </span>
              ))}

              {dias.map((dia, indice) => {
                if (dia === null) return <span key={`vazio-${indice}`} className="h-8" />

                const data = new Date(vista.getFullYear(), vista.getMonth(), dia)
                const marcada =
                  escolhida !== null && data.toDateString() === escolhida.toDateString()
                const eHoje = data.toDateString() === hoje.toDateString()
                const fora = bloqueado(dia)

                return (
                  <button
                    key={dia}
                    type="button"
                    disabled={fora}
                    onClick={() => {
                      onChange(iso(vista.getFullYear(), vista.getMonth(), dia))
                      setAberto(false)
                    }}
                    className={`grid h-8 cursor-pointer place-items-center rounded-md text-[12.5px] outline-none disabled:cursor-not-allowed disabled:text-line ${
                      marcada
                        ? 'bg-accent font-semibold text-white'
                        : eHoje
                          ? 'font-semibold text-accent hover:bg-surface'
                          : 'text-ink hover:bg-surface'
                    }`}
                  >
                    {dia}
                  </button>
                )
              })}
            </div>

            <button
              type="button"
              onClick={() => {
                const agora = new Date()
                onChange(iso(agora.getFullYear(), agora.getMonth(), agora.getDate()))
                setAberto(false)
              }}
              className="mt-2 w-full cursor-pointer rounded-md py-1.5 text-[12.5px] font-medium text-accent outline-none hover:bg-surface"
            >
              hoje
            </button>
          </div>,
          document.body,
        )}
    </>
  )
}
