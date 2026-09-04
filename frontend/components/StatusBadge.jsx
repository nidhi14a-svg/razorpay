export function StatusBadge({ status }) {
  const styles = {
    APPROVED: "bg-emerald-50 text-emerald-700 border-emerald-200/60 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800/40",
    EXECUTED: "bg-brand-mint/30 text-brand-primary border-brand-primary/20 dark:bg-brand-mint/10 dark:text-brand-teal dark:border-brand-teal/30",
    REJECTED: "bg-red-50 text-red-700 border-red-200/60 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800/40",
    REJECTED_BY_GUARDRAILS: "bg-red-50 text-red-700 border-red-200/60 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800/40",
    GENERATED: "bg-brand-peach/50 text-brand-coral border-brand-coral/20 dark:bg-amber-900/20 dark:text-amber-500 dark:border-amber-800/30",
    ACTIVE: "bg-emerald-50 text-emerald-700 border-emerald-200/60 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800/40",
    COMPLETED: "bg-gray-100 text-gray-700 border-gray-200/80 dark:bg-gray-800/50 dark:text-gray-300 dark:border-gray-700/50",
    FAILED: "bg-red-50 text-red-700 border-red-200/60 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800/40",
    PENDING: "bg-amber-50 text-amber-700 border-amber-200/60 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800/40"
  }

  const safeStatus = status?.toUpperCase() || "UNKNOWN"
  const defaultStyle = "bg-gray-100 text-gray-700 border-gray-200/80 dark:bg-gray-800/50 dark:text-gray-300 dark:border-gray-700/50"
  
  return (
    <span className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${styles[safeStatus] || defaultStyle} shadow-sm inline-flex items-center justify-center`}>
      {safeStatus.replace(/_/g, " ")}
    </span>
  )
}
