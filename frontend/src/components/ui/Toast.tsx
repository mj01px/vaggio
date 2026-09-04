import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { CircleAlert, CircleCheck, LoaderCircle, X } from 'lucide-react'
import { ToastContext, type Aviso, type Toast, type ToastTom } from '@/hooks/useToast'

const DURACAO_PADRAO = 6000

const estilos: Record<ToastTom, { borda: string; icone: ReactNode }> = {
  carregando: {
    borda: 'border-line',
    icone: <LoaderCircle size={17} className="animate-spin text-accent" />,
  },
  ok: { borda: 'border-line', icone: <CircleCheck size={17} className="text-ok" /> },
  bad: { borda: 'border-bad/30', icone: <CircleAlert size={17} className="text-bad" /> },
}

/**
 * Avisos no canto inferior direito.
 *
 * Existe para tirar da tela o bloco que empurrava a lista para baixo a cada
 * coleta: a fila e o conteudo, e o andamento de uma acao nao deveria mover o
 * que a pessoa esta lendo.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Toast[]>([])
  const proximo = useRef(1)

  const fechar = useCallback((id: number) => {
    setAvisos((atuais) => atuais.filter((aviso) => aviso.id !== id))
  }, [])

  const mostrar = useCallback((aviso: Aviso) => {
    const id = proximo.current++
    setAvisos((atuais) => [
      ...atuais,
      {
        id,
        tom: aviso.tom ?? 'ok',
        titulo: aviso.titulo,
        detalhe: aviso.detalhe,
        duracao: aviso.duracao === undefined ? DURACAO_PADRAO : aviso.duracao,
      },
    ])
    return id
  }, [])

  const api = useMemo(() => ({ mostrar, fechar }), [mostrar, fechar])

  return (
    <ToastContext.Provider value={api}>
      {children}
      {createPortal(
        // O portal sai da arvore do AppLayout e perde o escopo do tema claro;
        // sem repetir aqui, o aviso sai escuro para quem usa o SO no escuro.
        <div
          data-tema="claro"
          className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[calc(100vw-2rem)] max-w-[360px] flex-col gap-2"
        >
          {avisos.map((aviso) => (
            <Cartao key={aviso.id} aviso={aviso} onFechar={fechar} />
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}

function Cartao({ aviso, onFechar }: { aviso: Toast; onFechar: (id: number) => void }) {
  useEffect(() => {
    if (aviso.duracao === null) return
    const relogio = setTimeout(() => onFechar(aviso.id), aviso.duracao)
    return () => clearTimeout(relogio)
  }, [aviso.id, aviso.duracao, onFechar])

  const { borda, icone } = estilos[aviso.tom]

  return (
    <div
      // `status` e nao `alert`: o aviso e complemento do que a tela ja mostra,
      // e `alert` interromperia a leitura de quem usa leitor de tela.
      role="status"
      aria-live="polite"
      className={`pointer-events-auto flex items-start gap-2.5 rounded-[10px] border ${borda} bg-card px-3.5 py-3 shadow-lg shadow-ink/10`}
    >
      <span className="mt-px shrink-0">{icone}</span>

      <div className="min-w-0 flex-1">
        <p className="text-[13.5px] font-medium text-ink">{aviso.titulo}</p>
        {aviso.detalhe && <p className="mt-0.5 text-[12.5px] text-muted">{aviso.detalhe}</p>}
      </div>

      <button
        type="button"
        aria-label="Fechar aviso"
        onClick={() => onFechar(aviso.id)}
        className="-mt-0.5 -mr-1 shrink-0 cursor-pointer rounded-md p-1 text-muted outline-none hover:text-ink focus-visible:border focus-visible:border-ink"
      >
        <X size={15} />
      </button>
    </div>
  )
}
