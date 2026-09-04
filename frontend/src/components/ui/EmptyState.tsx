export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-line bg-card p-8 text-center text-muted">
      {children}
    </div>
  )
}
