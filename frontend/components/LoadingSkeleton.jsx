export function LoadingSkeleton({ type = "card" }) {
  if (type === "card") {
    return (
      <div className="p-6 bg-white rounded-xl border border-gray-100 shadow-sm animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-1/4"></div>
      </div>
    )
  }
  
  if (type === "table") {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-100 rounded mb-4"></div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-white border-b border-gray-100 mb-2 rounded"></div>
        ))}
      </div>
    )
  }
  
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-4 bg-gray-200 rounded w-3/4"></div>
      <div className="h-4 bg-gray-200 rounded w-1/2"></div>
    </div>
  )
}
