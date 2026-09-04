import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="rounded-lg border border-line bg-card p-8 text-center text-muted">
      <p>Pagina nao encontrada.</p>
      <Link to="/candidaturas" className="text-accent underline">
        Voltar para as candidaturas
      </Link>
    </div>
  )
}
