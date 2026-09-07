'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Sparkles, ArrowLeft, CheckCircle2 } from 'lucide-react'
import { getApiUrl } from '@/lib/api'

export default function CreateCampaignPage() {
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const router = useRouter()

  const handleCreateCampaign = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    const merchantId = localStorage.getItem('merchantId')

    try {
      const response = await fetch(getApiUrl('/campaigns'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          merchant_id: merchantId,
          campaign_name: goal,
          target_segment: 'all'
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setResult(data)
      } else {
        setError(data.detail || 'Failed to create campaign')
      }
    } catch (error) {
      setError('Connection error: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500 pb-12">
      <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-muted hover:text-foreground transition-colors">
        <ArrowLeft size={16} className="mr-1" /> Back to Campaigns
      </Link>

      <div className="mb-10">
        <h2 className="text-3xl font-bold text-foreground tracking-tight mb-2">Create AI Campaign</h2>
        <p className="text-muted text-lg">Define your objective and let RAZZZ generate the optimal strategy.</p>
      </div>

      {/* Workflow Stepper */}
      <div className="flex items-center gap-2 mb-10 overflow-hidden">
        <div className={`flex items-center gap-3 ${!result ? 'text-brand-primary dark:text-brand-teal' : 'text-muted'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${!result ? 'bg-brand-primary text-white' : 'bg-surface border border-border'}`}>1</div>
          <span className="font-semibold text-sm uppercase tracking-wide">Define Objective</span>
        </div>
        <div className={`h-px bg-border flex-1 mx-2 ${result ? 'bg-brand-primary/50' : ''}`}></div>
        <div className={`flex items-center gap-3 ${loading ? 'text-brand-primary animate-pulse' : (result ? 'text-brand-primary dark:text-brand-teal' : 'text-muted')}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${loading || result ? 'bg-brand-primary text-white' : 'bg-surface border border-border'}`}>2</div>
          <span className="font-semibold text-sm uppercase tracking-wide">AI Analysis</span>
        </div>
        <div className={`h-px bg-border flex-1 mx-2 ${result ? 'bg-brand-primary/50' : ''}`}></div>
        <div className={`flex items-center gap-3 ${result ? 'text-brand-primary dark:text-brand-teal' : 'text-muted opacity-50'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${result ? 'bg-brand-primary text-white' : 'bg-surface border border-border'}`}>3</div>
          <span className="font-semibold text-sm uppercase tracking-wide">Execute</span>
        </div>
      </div>

      {!result ? (
        <form onSubmit={handleCreateCampaign} className="bg-surface border border-border rounded-3xl p-8 md:p-10 shadow-soft hover:border-brand-primary/20 transition-all duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/5 rounded-full blur-3xl pointer-events-none -translate-y-1/2 translate-x-1/2 group-hover:bg-brand-primary/10 transition-colors duration-700"></div>
          
          <div className="mb-10 relative z-10">
            <label className="block text-sm font-bold text-foreground uppercase tracking-widest mb-4 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-brand-primary"></div>
              What do you want to achieve?
            </label>
            <textarea
              placeholder="e.g., Increase weekend revenue by moving overstocked inventory without hurting margins for our most loyal customers."
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="w-full px-6 py-5 bg-background/50 border border-border rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-primary/50 focus:border-transparent transition-all h-40 resize-none text-foreground placeholder:text-muted/70 text-lg shadow-inner"
              required
              disabled={loading}
            />
            <div className="flex items-center gap-2 mt-4 px-2">
              <Sparkles size={16} className="text-brand-primary animate-pulse" />
              <p className="text-muted text-sm font-medium">
                RAZZZ will analyze your customer data and merchant rules before recommending a strategy.
              </p>
            </div>
          </div>

          {error && (
            <div className="p-5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-2xl mb-8 text-sm font-medium flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-red-600 shrink-0"></div>
                <span>{error}</span>
              </div>
              {(error.toLowerCase().includes('guardrail') || error.toLowerCase().includes('rules')) && (
                <Link
                  href="/onboarding?step=guardrails"
                  className="shrink-0 inline-flex items-center justify-center gap-2 bg-brand-primary hover:bg-brand-teal text-white text-xs font-bold px-4 py-2 rounded-xl transition-colors"
                >
                  Configure Guardrails
                </Link>
              )}
            </div>
          )}

          <div className="flex justify-end pt-8 border-t border-border/60 relative z-10">
            <button
              type="submit"
              disabled={loading || !goal.trim()}
              className="inline-flex items-center justify-center gap-3 bg-brand-primary hover:bg-brand-teal text-white font-bold px-8 py-4 rounded-xl transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:hover:shadow-sm w-full md:w-auto hover:-translate-y-0.5"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Analyzing Data...
                </>
              ) : (
                <>
                  <Sparkles size={20} /> Generate AI Strategy
                </>
              )}
            </button>
          </div>
        </form>
      ) : (
        <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-500">
          <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200/60 dark:border-emerald-900/30 p-8 rounded-3xl flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-soft relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-400/10 rounded-full blur-2xl pointer-events-none -translate-y-1/2 translate-x-1/2"></div>
            <div className="flex items-start gap-4 relative z-10">
              <div className="bg-emerald-100 dark:bg-emerald-900/40 p-2 rounded-full shrink-0">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-emerald-900 dark:text-emerald-400 mb-1">Campaign Strategy Generated</h3>
                <p className="text-emerald-700/90 dark:text-emerald-500/80 text-base">Your campaign has been generated and payment links have been automatically provisioned.</p>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-3 shrink-0 relative z-10">
              <Link href={`/campaigns/${result.campaign_id}`} className="bg-emerald-600 text-white hover:bg-emerald-700 px-6 py-3 rounded-xl text-sm font-bold transition-all shadow-sm hover:shadow-md text-center">
                Review & Execute
              </Link>
              <button onClick={() => { setGoal(''); setResult(null) }} className="bg-white dark:bg-surface border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/40 px-6 py-3 rounded-xl text-sm font-bold transition-colors">
                Start Over
              </button>
            </div>
          </div>

          <div className="bg-surface border border-border rounded-3xl overflow-hidden shadow-soft">
            <div className="bg-background px-8 py-6 border-b border-border flex items-center gap-3">
              <div className="bg-brand-primary/10 p-2 rounded-lg">
                <Sparkles size={20} className="text-brand-primary" />
              </div>
              <h4 className="font-bold text-foreground text-lg">Recommended AI Offers</h4>
            </div>
            <div className="divide-y divide-border">
              {Object.entries(result.offers).map(([segment, offer]) => (
                <div key={segment} className="p-8 hover:bg-gray-50/50 dark:hover:bg-gray-900/20 transition-colors flex flex-col md:flex-row gap-6">
                  <div className="w-full md:w-1/3">
                    <h5 className="font-bold text-muted uppercase tracking-wider text-xs mb-2">Target Audience</h5>
                    <div className="font-bold text-foreground capitalize text-lg mb-4">
                      {segment.replace(/_/g, ' ')}
                    </div>
                    
                    <h5 className="font-bold text-muted uppercase tracking-wider text-xs mb-2">Constraint</h5>
                    <span className="inline-block bg-amber-50 dark:bg-amber-900/20 text-amber-700 border border-amber-200/50 px-3 py-1.5 rounded-lg text-sm font-semibold">
                      Max discount: {offer.discount_pct}%
                    </span>
                  </div>
                  
                  <div className="w-full md:w-2/3 space-y-4">
                    <div>
                      <h5 className="font-bold text-brand-primary dark:text-brand-teal uppercase tracking-wider text-xs mb-2">Generated Offer</h5>
                      <p className="text-foreground font-semibold text-xl leading-snug">{offer.offer}</p>
                    </div>
                    
                    <div className="bg-gray-50 dark:bg-black/20 rounded-2xl p-5 border border-border/80">
                      <h5 className="font-bold text-muted uppercase tracking-wider text-xs mb-2">AI Reasoning</h5>
                      <p className="text-sm text-foreground/80 leading-relaxed">{offer.reasoning}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
