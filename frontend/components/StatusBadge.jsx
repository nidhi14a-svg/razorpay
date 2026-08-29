export function StatusBadge({ status }) {
  const styles = {
    APPROVED: "bg-green-100 text-green-800 border-green-200",
    EXECUTED: "bg-blue-100 text-blue-800 border-blue-200",
    REJECTED: "bg-red-100 text-red-800 border-red-200",
    REJECTED_BY_GUARDRAILS: "bg-red-100 text-red-800 border-red-200",
    GENERATED: "bg-amber-100 text-amber-800 border-amber-200",
    ACTIVE: "bg-green-100 text-green-800 border-green-200",
    COMPLETED: "bg-gray-100 text-gray-800 border-gray-200",
    FAILED: "bg-red-100 text-red-800 border-red-200",
    PENDING: "bg-amber-100 text-amber-800 border-amber-200"
  }

  const safeStatus = status?.toUpperCase() || "UNKNOWN"
  const defaultStyle = "bg-gray-100 text-gray-800 border-gray-200"
  
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${styles[safeStatus] || defaultStyle}`}>
      {safeStatus.replace(/_/g, " ")}
    </span>
  )
}
