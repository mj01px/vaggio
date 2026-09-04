import { ArrowRight, CircleCheck, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardHeader } from '@/components/ui/Card'
import { Contador } from '@/components/ui/Pill'
import type { Application } from '@/types/api'
import { textoVencimento } from './tempo'

/**
 * Altura de tres itens: a quarta linha aparece cortada de proposito, que e o
 * que faz a pessoa entender que o cartao rola. O contador do cabecalho segue
 * mostrando o total, e nao o que esta visivel.
 */
const LISTA = 'mt-3 flex max-h-[218px] flex-col gap-2 overflow-y-auto pr-1'

/**
 * As candidaturas com follow-up vencido, que e a unica coisa do dashboard que
 * pede acao hoje.
 *
 * Sem nada atrasado o cartao continua na tela, virado em estado positivo: se
 * ele sumisse, o dia sem pendencia ficaria indistinguivel do dia em que a
 * consulta falhou.
 */
export function PrecisaDeVoce({ atrasadas }: { atrasadas: Application[] }) {
  return (
    <Card className="p-4">
      <CardHeader titulo="Precisa de você hoje">
        {atrasadas.length > 0 && <Contador>{atrasadas.length}</Contador>}
        <Link
          to="/candidaturas"
          className="ml-auto inline-flex items-center gap-1 rounded-lg text-[13px] font-medium text-accent outline-none hover:underline focus-visible:border focus-visible:border-ink"
        >
          Candidaturas
          <ArrowRight size={15} aria-hidden />
        </Link>
      </CardHeader>

      {atrasadas.length === 0 ? (
        <div className="mt-4 flex items-center gap-2.5 rounded-lg bg-surface px-3.5 py-4 text-[13px]">
          <CircleCheck size={18} className="shrink-0 text-ok" aria-hidden />
          <span>Nenhum follow-up vencido.</span>
        </div>
      ) : (
        <ul className={LISTA}>
          {atrasadas.map((candidatura) => (
            <li
              key={candidatura.id}
              className="rounded-r-lg border-l-[3px] border-bad bg-surface py-2 pr-3 pl-3"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="truncate text-[13.5px] font-semibold">
                  {candidatura.job.title}
                </span>
                <span className="shrink-0 text-[12px] font-medium text-bad">
                  {textoVencimento(candidatura.next_step_on)}
                </span>
              </div>

              <div className="truncate text-[12.5px] text-muted">
                {candidatura.job.company || 'empresa não informada'}
              </div>

              <div className="mt-0.5 flex items-center gap-1.5 text-[12.5px]">
                <TriangleAlert size={14} className="shrink-0 text-warn" aria-hidden />
                <span className="truncate">
                  {candidatura.next_step || 'sem próximo passo escrito'}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
