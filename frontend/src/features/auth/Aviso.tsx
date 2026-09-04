import { CheckCircle2, CircleAlert } from 'lucide-react'

/** A caixa de erro e a de sucesso das telas de fora, com o mesmo desenho. */
export function Aviso({ tom, children }: { tom: 'bad' | 'ok'; children: React.ReactNode }) {
  const Icone = tom === 'ok' ? CheckCircle2 : CircleAlert
  return (
    <div
      role={tom === 'bad' ? 'alert' : 'status'}
      className={`flex items-start gap-2.5 rounded-lg border px-3.5 py-3 ${
        tom === 'ok' ? 'border-ok/25 bg-ok/5' : 'border-bad/25 bg-bad/5'
      }`}
    >
      <Icone
        size={17}
        className={`mt-px shrink-0 ${tom === 'ok' ? 'text-ok' : 'text-bad'}`}
        aria-hidden
      />
      <p className={`text-sm font-medium ${tom === 'ok' ? 'text-ok' : 'text-bad'}`}>{children}</p>
    </div>
  )
}
