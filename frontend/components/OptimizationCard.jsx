import { CheckCircle, XCircle, Play, ArrowRight } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

export function OptimizationCard({ optimization, onApprove, onReject, onExecute, loading }) {
  const { 
    optimization_id,
    overall_assessment,
    recommendations,
    status,
    guardrail_status
  } = optimization

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-soft hover:border-brand-primary/30 transition-all duration-300">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h3 className="text-xl font-bold text-foreground mb-1">Optimization Proposal</h3>
          <p className="text-sm text-muted font-mono">{optimization_id}</p>
        </div>
        <div className="flex flex-col items-start md:items-end gap-2">
          <StatusBadge status={status} />
          {guardrail_status && guardrail_status.status === "REJECTED" && (
            <span className="text-xs font-bold text-red-600 bg-red-50 dark:bg-red-900/30 dark:text-red-400 px-2.5 py-1 rounded-md">
              GUARDRAIL BLOCKED
            </span>
          )}
        </div>
      </div>

      <p className="text-foreground/80 leading-relaxed mb-6">{overall_assessment}</p>

      <div className="space-y-4 mb-8">
        {recommendations.map((rec, idx) => (
          <div key={idx} className="bg-gray-50/50 dark:bg-gray-900/30 rounded-xl p-5 border border-border/50">
            <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-muted">{rec.type.replace(/_/g, ' ')}</span>
              <span className={`text-xs font-bold px-2.5 py-1 rounded-md uppercase ${
                rec.priority === 'high' 
                  ? 'bg-brand-peach/50 text-brand-coral dark:bg-brand-peach/20' 
                  : 'bg-brand-mint/50 text-brand-teal dark:bg-brand-mint/20'
              }`}>
                {rec.priority} Priority
              </span>
            </div>
            
            <p className="text-foreground font-semibold mb-2 text-lg">{rec.action}</p>
            <p className="text-sm text-muted italic mb-4 border-l-2 border-brand-teal/30 pl-3">"{rec.reason}"</p>
            
            {(rec.current_value !== undefined || rec.recommended_value !== undefined) && (
              <div className="flex items-center flex-wrap gap-3 mt-4 bg-surface p-3 rounded-lg border border-border shadow-sm inline-flex">
                {rec.current_value !== undefined && (
                  <div className="text-sm flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                    <span className="text-muted text-xs uppercase font-bold tracking-wider">Current:</span>
                    <span className="font-semibold line-through text-muted/70">{rec.current_value}</span>
                  </div>
                )}
                {rec.current_value !== undefined && rec.recommended_value !== undefined && (
                  <ArrowRight className="text-brand-teal/50 w-4 h-4 hidden sm:block" />
                )}
                {rec.recommended_value !== undefined && (
                  <div className="text-sm flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                    <span className="text-muted text-xs uppercase font-bold tracking-wider">Recommended:</span>
                    <span className="font-bold text-brand-primary dark:text-brand-teal">{rec.recommended_value}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {guardrail_status && guardrail_status.status === "REJECTED" && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-5 rounded-xl mb-6 text-sm flex items-start gap-3">
          <XCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <strong className="block mb-1.5 text-base">Rejected by Business Rules</strong>
            <p className="leading-relaxed opacity-90">{guardrail_status.reason}</p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 mt-6 pt-6 border-t border-border">
        {status === "GENERATED" && guardrail_status?.status !== "REJECTED" && (
          <>
            <button 
              onClick={() => onApprove(optimization_id)}
              disabled={loading}
              className="flex-1 flex justify-center items-center gap-2 bg-brand-primary hover:bg-brand-teal text-white font-semibold py-3 px-6 rounded-xl transition-colors disabled:opacity-50 shadow-sm"
            >
              <CheckCircle size={18} /> Approve Changes
            </button>
            <button 
              onClick={() => onReject(optimization_id)}
              disabled={loading}
              className="flex-1 flex justify-center items-center gap-2 bg-surface border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 font-semibold py-3 px-6 rounded-xl transition-colors disabled:opacity-50"
            >
              <XCircle size={18} /> Reject
            </button>
          </>
        )}

        {status === "APPROVED" && (
          <button 
            onClick={() => onExecute(optimization_id)}
            disabled={loading}
            className="w-full flex justify-center items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-xl transition-all shadow-md hover:shadow-lg disabled:opacity-50 hover:-translate-y-0.5"
          >
            <Play size={20} fill="currentColor" /> Execute Optimization Live
          </button>
        )}
        
        {(status === "EXECUTED" || status === "REJECTED" || (guardrail_status && guardrail_status.status === "REJECTED")) && (
          <div className="w-full text-center py-3 text-muted font-medium text-sm bg-gray-50/50 dark:bg-gray-900/20 rounded-xl border border-border">
            No further actions available for this proposal.
          </div>
        )}
      </div>
    </div>
  )
}
