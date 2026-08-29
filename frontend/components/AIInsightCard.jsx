import { Sparkles, AlertTriangle } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

export function AIInsightCard({ title, recommendation, reason, evidence, confidence, limitations }) {
  const confidenceColor = {
    high: "bg-green-100 text-green-800",
    medium: "bg-amber-100 text-amber-800",
    low: "bg-red-100 text-red-800"
  }

  const safeConfidence = (confidence || "low").toLowerCase()

  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-100 rounded-xl p-6 shadow-sm relative overflow-hidden">
      {/* Decorative background element */}
      <div className="absolute -top-10 -right-10 w-40 h-40 bg-purple-200/40 rounded-full blur-3xl"></div>
      
      <div className="flex items-center gap-2 mb-4 relative z-10">
        <div className="p-2 bg-purple-100 rounded-lg text-purple-600">
          <Sparkles size={20} />
        </div>
        <h3 className="text-xl font-bold text-gray-900">{title || "AI Insight"}</h3>
        <span className={`ml-auto text-xs font-medium px-2.5 py-1 rounded-full ${confidenceColor[safeConfidence]}`}>
          {safeConfidence.toUpperCase()} CONFIDENCE
        </span>
      </div>

      <div className="bg-white/80 backdrop-blur-sm rounded-lg p-5 border border-white/40 mb-4 relative z-10">
        <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Recommendation</h4>
        <p className="text-lg font-medium text-gray-900">{recommendation}</p>
        
        {reason && (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-1">Reasoning</h4>
            <p className="text-sm text-gray-700">{reason}</p>
          </div>
        )}
      </div>

      {evidence && evidence.length > 0 && (
        <div className="mb-4 relative z-10">
          <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Supporting Evidence</h4>
          <ul className="space-y-2">
            {evidence.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-purple-500 mt-0.5">•</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {limitations && limitations.length > 0 && (
        <div className="bg-amber-50/80 rounded-lg p-4 border border-amber-100 mt-4 relative z-10">
          <div className="flex items-center gap-2 text-amber-800 font-medium text-sm mb-2">
            <AlertTriangle size={16} /> Limitations
          </div>
          <ul className="space-y-1">
            {limitations.map((item, idx) => (
              <li key={idx} className="text-xs text-amber-700 flex items-start gap-2">
                <span className="mt-0.5">-</span> {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
