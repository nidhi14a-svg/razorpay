export function MetricCard({ title, value, subtitle, trend, icon: Icon, color = "teal" }) {
  const colorMap = {
    primary: "bg-brand-mint/50 dark:bg-brand-mint/20 text-brand-primary dark:text-brand-teal",
    teal: "bg-brand-mint/30 dark:bg-brand-mint/10 text-brand-teal",
    coral: "bg-brand-peach/50 dark:bg-brand-peach/20 text-brand-coral",
    gray: "bg-gray-100 dark:bg-gray-800 text-muted",
  }

  return (
    <div className="bg-surface p-6 rounded-2xl border border-border shadow-soft flex items-center justify-between hover:border-brand-primary/30 dark:hover:border-brand-primary/50 transition-all duration-300 group cursor-default">
      <div>
        <p className="text-sm font-medium text-muted mb-1 tracking-wide uppercase text-[11px]">{title}</p>
        <div className="flex items-baseline space-x-2">
          <h4 className="text-3xl font-bold text-foreground tracking-tight">{value}</h4>
          {trend && (
            <span className={`text-sm font-semibold flex items-center ${trend > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-brand-coral"}`}>
              {trend > 0 ? "+" : ""}{trend}%
            </span>
          )}
        </div>
        {subtitle && <p className="text-xs text-muted mt-1">{subtitle}</p>}
      </div>
      {Icon && (
        <div className={`p-4 rounded-xl transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3 ${colorMap[color] || colorMap.teal}`}>
          <Icon size={24} />
        </div>
      )}
    </div>
  )
}
