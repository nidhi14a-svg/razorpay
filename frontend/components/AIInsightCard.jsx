import { Sparkles, AlertTriangle } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

export function AIInsightCard({ title, recommendation, reason, evidence, confidence, limitations }) {
  const confidenceColor = {
    high: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-800/30",
    medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 border-amber-200/50 dark:border-amber-800/30",
    low: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 border-red-200/50 dark:border-red-800/30"
  }

  const safeConfidence = (confidence || "low").toLowerCase()

  return (
    <div className="bg-surface rounded-2xl p-7 shadow-soft border border-border relative overflow-hidden group hover:border-brand-primary/40 transition-colors duration-300">
      {/* Decorative top border */}
      <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-brand-primary via-brand-teal to-brand-mint opacity-80"></div>
      
      {/* Decorative background element */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-brand-primary/5 rounded-full blur-3xl pointer-events-none group-hover:bg-brand-primary/10 transition-colors duration-500"></div>
      
      <div className="flex items-center gap-4 mb-8 relative z-10">
        <div className="p-3 bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/20 dark:text-brand-teal rounded-xl shadow-sm border border-brand-primary/20">
          <Sparkles size={22} className="animate-pulse-slow" />
        </div>
        <div>
          <h4 className="text-xs font-bold text-brand-primary uppercase tracking-wider mb-0.5">AI Revenue Agent</h4>
          <h3 className="text-xl font-bold text-foreground tracking-tight">{title || "Strategic Insight"}</h3>
        </div>
        <span className={`ml-auto text-[10px] font-bold px-3 py-1.5 rounded-full border tracking-wide uppercase ${confidenceColor[safeConfidence]}`}>
          {safeConfidence} CONFIDENCE
        </span>
      </div>

      <div className="bg-background/50 dark:bg-black/20 rounded-xl p-6 border border-border/60 mb-6 relative z-10">
        <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wider mb-3">Current Recommendation</h4>
        <p className="text-xl font-medium text-foreground leading-snug mb-5">{recommendation}</p>
        
        {reason && (
          <div className="mt-5 pt-5 border-t border-border/50">
            <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wider mb-2">Strategy & Reasoning</h4>
            <p className="text-sm text-foreground/80 leading-relaxed">{reason}</p>
          </div>
        )}
      </div>

      {evidence && evidence.length > 0 && (
        <div className="mb-6 relative z-10">
          <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wider mb-3 pl-1">Data Evidence</h4>
          <ul className="space-y-3 bg-surface p-5 rounded-xl border border-border/40 shadow-sm">
            {evidence.map((item, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm text-foreground/80">
                <div className="mt-1 w-1.5 h-1.5 rounded-full bg-brand-primary flex-shrink-0"></div>
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {limitations && limitations.length > 0 && (
        <div className="bg-amber-50/50 dark:bg-amber-900/10 rounded-xl p-4 border border-amber-100 dark:border-amber-900/30 relative z-10 flex gap-3">
          <AlertTriangle size={18} className="text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" /> 
          <div>
            <h4 className="text-xs font-bold text-amber-800 dark:text-amber-500 uppercase tracking-wider mb-2">Constraints</h4>
            <ul className="space-y-1.5">
              {limitations.map((item, idx) => (
                <li key={idx} className="text-sm text-amber-700/90 dark:text-amber-400/90 flex items-start gap-2">
                  <span className="mt-0.5 opacity-50 text-[10px]">■</span> {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
