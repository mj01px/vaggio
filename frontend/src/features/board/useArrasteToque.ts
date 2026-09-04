import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApplicationStatusKey } from '@/types/api'

/** O que esta na mao agora: a candidatura e onde o dedo esta. */
interface Arraste {
  id: number
  titulo: string
  x: number
  y: number
}

/** Quanto o dedo pode andar antes de a gente desistir e deixar rolar a lista. */
const TOLERANCIA = 10

/** Quanto tempo segurando ate o arraste comecar. */
const ESPERA = 220

/**
 * Arrastar cartao com o dedo.
 *
 * O `draggable` do HTML5 nao existe no toque, entao o mobile precisa de eventos
 * de ponteiro. E como no celular o board mostra uma etapa por vez, nao ha outra
 * coluna para receber o cartao: o alvo passa a ser o proprio chip de etapa la
 * em cima, marcado com `data-etapa`.
 *
 * O arraste so comeca depois de segurar. Sem essa espera, todo deslize para
 * rolar a coluna viraria um movimento de candidatura sem querer.
 */
export function useArrasteToque(
  onSoltar: (id: number, status: ApplicationStatusKey) => void,
) {
  const [arraste, setArraste] = useState<Arraste | null>(null)
  const [alvo, setAlvo] = useState<ApplicationStatusKey | null>(null)

  const relogio = useRef<number | null>(null)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  const ativo = useRef(false)

  const limpar = useCallback(() => {
    if (relogio.current !== null) clearTimeout(relogio.current)
    relogio.current = null
    inicio.current = null
    ativo.current = false
    setArraste(null)
    setAlvo(null)
  }, [])

  /** Qual chip de etapa esta embaixo do dedo, se houver. */
  const etapaSob = useCallback((x: number, y: number): ApplicationStatusKey | null => {
    const elemento = document.elementFromPoint(x, y)
    const chip = elemento?.closest<HTMLElement>('[data-etapa]')
    return (chip?.dataset.etapa as ApplicationStatusKey | undefined) ?? null
  }, [])

  const comecar = useCallback(
    (evento: React.PointerEvent, id: number, titulo: string) => {
      // Mouse ja tem o arraste nativo do HTML5; aqui e so o dedo e a caneta.
      if (evento.pointerType === 'mouse') return

      const { clientX: x, clientY: y } = evento
      inicio.current = { x, y }

      relogio.current = window.setTimeout(() => {
        ativo.current = true
        setArraste({ id, titulo, x, y })
        // Sem o feedback tatil, segurar e nao ver nada acontecer parece travado.
        navigator.vibrate?.(12)
      }, ESPERA)
    },
    [],
  )

  useEffect(() => {
    if (inicio.current === null && arraste === null) return

    function mover(evento: PointerEvent) {
      const partida = inicio.current
      if (partida === null) return

      // Antes do arraste comecar, andar demais quer dizer que a pessoa esta
      // rolando a coluna: cancela e deixa o navegador cuidar do scroll.
      if (!ativo.current) {
        const andou =
          Math.abs(evento.clientX - partida.x) + Math.abs(evento.clientY - partida.y)
        if (andou > TOLERANCIA) limpar()
        return
      }

      evento.preventDefault()
      setArraste((atual) =>
        atual === null ? atual : { ...atual, x: evento.clientX, y: evento.clientY },
      )
      setAlvo(etapaSob(evento.clientX, evento.clientY))
    }

    function soltar(evento: PointerEvent) {
      if (ativo.current) {
        const destino = etapaSob(evento.clientX, evento.clientY)
        const atual = arraste
        if (destino !== null && atual !== null) onSoltar(atual.id, destino)
      }
      limpar()
    }

    // `passive: false` no move: sem isso o `preventDefault` e ignorado e a
    // pagina rola junto com o cartao.
    document.addEventListener('pointermove', mover, { passive: false })
    document.addEventListener('pointerup', soltar)
    document.addEventListener('pointercancel', limpar)
    return () => {
      document.removeEventListener('pointermove', mover)
      document.removeEventListener('pointerup', soltar)
      document.removeEventListener('pointercancel', limpar)
    }
  }, [arraste, etapaSob, limpar, onSoltar])

  return { arraste, alvo, comecar }
}
