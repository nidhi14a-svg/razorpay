import { CheckCircle, XCircle, Play } from 'lucide-react'
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
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">Optimization Proposal</h3>
          <p className="text-sm text-gray-500 font-mono">{optimization_id}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusBadge status={status} />
          {guardrail_status && guardrail_status.status === "REJECTED" && (
            <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-1 rounded">GUARDRAIL BLOCKED</span>
          )}
        </div>
      </div>

      <p className="text-gray-700 mb-6">{overall_assessment}</p>

      <div className="space-y-4 mb-6">
        {recommendations.map((rec, idx) => (
          <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <div className="flex justify-between mb-2">
              <span className="text-sm font-semibold uppercase text-gray-500">{rec.type.replace(/_/g, ' ')}</span>
              <span className={`text-xs font-bold px-2 py-1 rounded uppercase ${rec.priority === 'high' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                {rec.priority} Priority
              </span>
            </div>
            
            <p className="text-gray-900 font-medium mb-2">{rec.action}</p>
            <p className="text-sm text-gray-600 italic mb-3">"{rec.reason}"</p>
            
            {(rec.current_value !== undefined || rec.recommended_value !== undefined) && (
              <div className="flex items-center gap-4 mt-3 bg-white p-2 rounded border border-gray-200 inline-flex">
                {rec.current_value !== undefined && (
                  <div className="text-sm">
                    <span className="text-gray-500 mr-1">Current:</span>
                    <span className="font-semibold line-through text-gray-400">{rec.current_value}</span>
                  </div>
                )}
                {rec.current_value !== undefined && rec.recommended_value !== undefined && (
                  <span className="text-gray-300">→</span>
                )}
                {rec.recommended_value !== undefined && (
                  <div className="text-sm">
                    <span className="text-gray-500 mr-1">Recommended:</span>
                    <span className="font-semibold text-blue-600">{rec.recommended_value}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {guardrail_status && guardrail_status.status === "REJECTED" && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-6 text-sm flex items-start gap-2">
          <XCircle className="w-5 h-5 shrink-0" />
          <div>
            <strong className="block mb-1">Rejected by Business Rules</strong>
            {guardrail_status.reason}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 mt-6 pt-4 border-t border-gray-100">
        {status === "GENERATED" && guardrail_status?.status !== "REJECTED" && (
          <>
            <button 
              onClick={() => onApprove(optimization_id)}
              disabled={loading}
              className="flex-1 flex justify-center items-center gap-2 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 font-semibold py-2 px-4 rounded-lg transition disabled:opacity-50"
            >
              <CheckCircle size={18} /> Approve
            </button>
            <button 
              onClick={() => onReject(optimization_id)}
              disabled={loading}
              className="flex-1 flex justify-center items-center gap-2 bg-white border border-red-200 text-red-600 hover:bg-red-50 font-semibold py-2 px-4 rounded-lg transition disabled:opacity-50"
            >
              <XCircle size={18} /> Reject
            </button>
          </>
        )}

        {status === "APPROVED" && (
          <button 
            onClick={() => onExecute(optimization_id)}
            disabled={loading}
            className="w-full flex justify-center items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition shadow-sm disabled:opacity-50"
          >
            <Play size={18} /> Execute Optimization
          </button>
        )}
      </div>
    </div>
  )
}
