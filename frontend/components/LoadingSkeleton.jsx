export function LoadingSkeleton({ type = "card" }) {
  if (type === "card") {
    return (
      <div className="p-6 bg-surface rounded-2xl border border-border shadow-soft animate-pulse">
        <div className="h-3 bg-muted/20 rounded w-1/3 mb-5"></div>
        <div className="h-8 bg-muted/20 rounded w-1/2 mb-3"></div>
        <div className="h-3 bg-muted/20 rounded w-1/4"></div>
      </div>
    )
  }
  
  if (type === "table") {
    return (
      <div className="animate-pulse bg-surface border border-border rounded-xl p-4 shadow-sm">
        <div className="h-10 bg-muted/10 rounded-lg mb-4"></div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-muted/5 border-b border-border/50 mb-2 rounded-lg"></div>
        ))}
      </div>
    )
  }
  
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-4 bg-muted/20 rounded-md w-3/4"></div>
      <div className="h-4 bg-muted/20 rounded-md w-1/2"></div>
    </div>
  )
}
