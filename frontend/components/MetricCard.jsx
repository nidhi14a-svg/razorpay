export function MetricCard({ title, value, subtitle, trend, icon: Icon, color = "blue" }) {
  const colorMap = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    purple: "bg-purple-50 text-purple-600",
    amber: "bg-amber-50 text-amber-600",
    gray: "bg-gray-50 text-gray-600",
  }

  return (
    <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
        <div className="flex items-baseline space-x-2">
          <h4 className="text-3xl font-bold text-gray-900">{value}</h4>
          {trend && (
            <span className={`text-sm font-medium ${trend > 0 ? "text-green-600" : "text-red-600"}`}>
              {trend > 0 ? "+" : ""}{trend}%
            </span>
          )}
        </div>
        {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
      </div>
      {Icon && (
        <div className={`p-4 rounded-lg ${colorMap[color] || colorMap.blue}`}>
          <Icon size={24} />
        </div>
      )}
    </div>
  )
}
