import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check } from 'lucide-react'

export interface Opcao {
  value: string
  label: string
}

type Size = 'md' | 'sm' | 'xs'

const sizes: Record<Size, string> = {
  md: 'h-11 px-3.5 text-[14.5px]',
  sm: 'h-9 px-3 text-[13.5px]',
  // `xs` e do painel de filtro, onde varios campos dividem uma linha so.
  xs: 'h-8 px-2.5 text-[13px]',
}

interface Props {
  options: Opcao[]
  /** Controlado. Sem ele, o componente guarda a escolha e usa `defaultValue`. */
  value?: string
  defaultValue?: string
  /** Com `name`, um input escondido carrega o valor para o FormData do form. */
  name?: string
  onChange?: (value: string) => void
  inputSize?: Size
  disabled?: boolean
  id?: string
  className?: string
  'aria-label'?: string
}

/**
 * A lista suspensa do sistema.
 *
 * Existe porque o `<select>` nativo so aceita estilo enquanto esta fechado: a
 * lista aberta e desenhada pelo sistema operacional e ignora token, raio e
 * fonte. Aqui a lista e nossa dos dois lados.
 *
 * Ela vai para um portal com posicao fixa, e nao inline, porque a coluna do
 * Board e o `main` rolam com `overflow`: inline, a lista seria cortada pela
 * borda do container em vez de flutuar sobre a pagina.
 *
 * O teclado precisa continuar funcionando como no nativo, entao setas andam,
 * Enter e espaco escolhem, Esc fecha e Home/End vao para as pontas.
 */
export function Select({
  options,
  value,
  defaultValue,
  name,
  onChange,
  inputSize = 'md',
  disabled = false,
  id,
  className = '',
  'aria-label': ariaLabel,
}: Props) {
  const controlado = value !== undefined
  const [interno, setInterno] = useState(defaultValue ?? options[0]?.value ?? '')
  const escolhido = controlado ? value : interno

  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(0)
  const [caixa, setCaixa] = useState<{ top: number; left: number; width: number } | null>(null)

  const botao = useRef<HTMLButtonElement>(null)
  const lista = useRef<HTMLUListElement>(null)
  const listaId = useId()

  const selecionada = options.find((opcao) => opcao.value === escolhido)

  function abrir() {
    if (disabled) return
    const indice = options.findIndex((opcao) => opcao.value === escolhido)
    setAtivo(indice < 0 ? 0 : indice)
    setAberto(true)
  }

  function fechar() {
    setAberto(false)
    botao.current?.focus()
  }

  function escolher(opcao: Opcao) {
    if (!controlado) setInterno(opcao.value)
    onChange?.(opcao.value)
    setAberto(false)
    botao.current?.focus()
  }

  // A posicao e medida depois da lista existir, antes da pintura, senao ela
  // aparece por um quadro no canto da tela.
  useLayoutEffect(() => {
    if (!aberto || !botao.current) return
    const r = botao.current.getBoundingClientRect()
    const espacoAbaixo = window.innerHeight - r.bottom
    const altura = Math.min(options.length * 36 + 8, 260)
    // Sem espaco embaixo, abre para cima: no rodape da tela a lista ficaria
    // metade fora da janela.
    const top = espacoAbaixo < altura + 8 && r.top > altura ? r.top - altura - 6 : r.bottom + 6
    setCaixa({ top, left: r.left, width: r.width })
  }, [aberto, options.length])

  // Rolar ou redimensionar move o botao e a lista ficaria orfa no lugar antigo.
  // Fechar e mais honesto do que reposicionar a cada quadro.
  useEffect(() => {
    if (!aberto) return
    const fecharSemFoco = () => setAberto(false)
    window.addEventListener('scroll', fecharSemFoco, true)
    window.addEventListener('resize', fecharSemFoco)
    return () => {
      window.removeEventListener('scroll', fecharSemFoco, true)
      window.removeEventListener('resize', fecharSemFoco)
    }
  }, [aberto])

  useEffect(() => {
    if (!aberto) return
    const clique = (evento: MouseEvent) => {
      const alvo = evento.target as Node
      if (botao.current?.contains(alvo) || lista.current?.contains(alvo)) return
      setAberto(false)
    }
    document.addEventListener('mousedown', clique)
    return () => document.removeEventListener('mousedown', clique)
  }, [aberto])

  useEffect(() => {
    if (aberto) lista.current?.focus()
  }, [aberto])

  function teclado(evento: React.KeyboardEvent) {
    switch (evento.key) {
      case 'ArrowDown':
        evento.preventDefault()
        if (!aberto) abrir()
        else setAtivo((atual) => Math.min(atual + 1, options.length - 1))
        break
      case 'ArrowUp':
        evento.preventDefault()
        if (!aberto) abrir()
        else setAtivo((atual) => Math.max(atual - 1, 0))
        break
      case 'Home':
        if (aberto) {
          evento.preventDefault()
          setAtivo(0)
        }
        break
      case 'End':
        if (aberto) {
          evento.preventDefault()
          setAtivo(options.length - 1)
        }
        break
      case 'Enter':
      case ' ':
        evento.preventDefault()
        if (!aberto) abrir()
        else if (options[ativo]) escolher(options[ativo])
        break
      case 'Escape':
        if (aberto) {
          evento.preventDefault()
          fechar()
        }
        break
      case 'Tab':
        if (aberto) setAberto(false)
        break
    }
  }

  return (
    <>
      {name && <input type="hidden" name={name} value={escolhido} />}

      <button
        ref={botao}
        id={id}
        type="button"
        role="combobox"
        aria-expanded={aberto}
        aria-haspopup="listbox"
        aria-controls={aberto ? listaId : undefined}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => (aberto ? setAberto(false) : abrir())}
        onKeyDown={teclado}
        className={`flex w-full cursor-pointer items-center rounded-lg border bg-card text-left text-ink outline-none disabled:cursor-not-allowed disabled:border-line disabled:bg-surface disabled:text-muted ${
          sizes[inputSize]
        } ${aberto ? 'border-ink' : 'border-field'} ${className}`}
      >
        <span className="truncate">{selecionada?.label ?? ''}</span>
      </button>

      {aberto &&
        caixa &&
        createPortal(
          <ul
            ref={lista}
            id={listaId}
            role="listbox"
            tabIndex={-1}
            aria-activedescendant={`${listaId}-${ativo}`}
            onKeyDown={teclado}
            // O portal sai da arvore do AppLayout, e com ele sai o escopo do
            // `data-tema="claro"`. Sem repetir aqui, a lista le os tokens do
            // `:root` e fica escura para quem esta com o SO no tema escuro.
            data-tema="claro"
            style={{ top: caixa.top, left: caixa.left, width: caixa.width }}
            className="fixed z-50 max-h-[260px] overflow-y-auto rounded-lg border border-line bg-card p-1 shadow-lg shadow-ink/10 outline-none"
          >
            {options.map((opcao, indice) => {
              const marcada = opcao.value === escolhido
              return (
                <li
                  key={opcao.value}
                  id={`${listaId}-${indice}`}
                  role="option"
                  aria-selected={marcada}
                  onMouseEnter={() => setAtivo(indice)}
                  onClick={() => escolher(opcao)}
                  // O realce e cinza, nao azul: quem diz qual esta escolhida e
                  // o check, entao o azul so competia com ele.
                  className={`flex h-9 cursor-pointer items-center gap-2 rounded-md px-2.5 text-[13.5px] text-ink ${
                    indice === ativo ? 'bg-surface' : ''
                  }`}
                >
                  <span className="flex-1 truncate">{opcao.label}</span>
                  {marcada && <Check size={15} className="shrink-0 text-accent" />}
                </li>
              )
            })}
          </ul>,
          document.body,
        )}
    </>
  )
}
