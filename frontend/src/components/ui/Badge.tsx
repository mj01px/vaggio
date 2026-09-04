export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="mr-1 inline-block rounded-full border border-line bg-surface px-2 py-px text-[11px] text-muted">
      {children}
    </span>
  )
}
