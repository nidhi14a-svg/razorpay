'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Target, TrendingUp, IndianRupee, PieChart, Users, Settings, Database, Cpu, Send, CheckCircle2, Check, RefreshCw, BarChart2 } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { MetricCard } from '@/components/MetricCard'

export default function CampaignDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [campaign, setCampaign] = useState(null)
  const [offers, setOffers] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [execution, setExecution] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionState, setExecutionState] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    if (!merchantId) {
      router.push('/login')
      return
    }

    async function fetchData() {
      try {
        const [campRes, offersRes, analyticsRes, executionRes] = await Promise.all([
          fetch(`http://localhost:8000/campaigns/${params.id}?merchant_id=${merchantId}`),
          fetch(`http://localhost:8000/campaigns/${params.id}/offers?merchant_id=${merchantId}`),
          fetch(`http://localhost:8000/campaigns/${params.id}/analytics?merchant_id=${merchantId}`),
          fetch(`http://localhost:8000/campaigns/${params.id}/execution?merchant_id=${merchantId}`)
        ])

        if (!campRes.ok) throw new Error('Campaign not found')
        
        setCampaign(await campRes.json())
        const offersData = offersRes.ok ? await offersRes.json() : null;
        setOffers(offersData?.items || [])
        setAnalytics(analyticsRes.ok ? await analyticsRes.json() : null)
        setExecution(executionRes.ok ? await executionRes.json() : null)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [params.id, router])

  const handleExecuteCampaign = async () => {
    const merchantId = localStorage.getItem('merchantId')
    setIsExecuting(true)
    setError(null)
    
    // Automation Sequence Animation for Demo
    const sequence = [
      'Preparing campaign...',
      'Validating merchant rules...',
      'Selecting eligible customers...',
      'Provisioning personalized offers...',
      'Executing campaign...'
    ]
    
    for (let i = 0; i < sequence.length; i++) {
      setExecutionState(sequence[i])
      await new Promise(r => setTimeout(r, 600)) // 600ms per step
    }

    try {
      const res = await fetch(`http://localhost:8000/campaigns/${params.id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: merchantId })
      })
      
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || 'Failed to execute campaign')
      }
      
      const executionData = await res.json()
      
      setExecutionState('Campaign activated')
      await new Promise(r => setTimeout(r, 1000))
      
      setExecution({ executed: true, ...executionData })
      setCampaign(prev => ({ ...prev, status: 'EXECUTED' }))
      
      // Refresh offers to get coupon codes and analytics for simulated demo results
      const [offersRes, analyticsRes] = await Promise.all([
        fetch(`http://localhost:8000/campaigns/${params.id}/offers?merchant_id=${merchantId}`),
        fetch(`http://localhost:8000/campaigns/${params.id}/analytics?merchant_id=${merchantId}`)
      ])
      
      if (offersRes.ok) {
        const offersData = await offersRes.json()
        setOffers(offersData?.items || [])
      }
      
      if (analyticsRes.ok) {
        setAnalytics(await analyticsRes.json())
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsExecuting(false)
      setExecutionState(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500">
          <ArrowLeft size={16} className="mr-1" /> Back
        </Link>
        <LoadingSkeleton type="card" />
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="space-y-6">
        <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
          <ArrowLeft size={16} className="mr-1" /> Back to Campaigns
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl font-medium shadow-sm">
          <h3 className="font-bold mb-1 text-lg">Campaign Loading Failed</h3>
          <p className="text-sm opacity-90">{error || 'Campaign not found'}</p>
        </div>
      </div>
    )
  }

  const isExecuted = execution?.executed || campaign.status === 'EXECUTED' || campaign.status === 'COMPLETED'
  const hasAnalytics = analytics && analytics.verified_payments > 0

  const steps = [
    {
      id: 1,
      title: "Analyzing Data",
      subtitle: `${campaign.customers_analyzed || "—"} customers`,
      icon: Database,
      completed: !!campaign.customers_analyzed,
      active: !campaign.customers_analyzed
    },
    {
      id: 2,
      title: "Selecting Customers",
      subtitle: `${campaign.eligible_customers || "—"} eligible`,
      icon: Users,
      completed: !!campaign.eligible_customers,
      active: !!campaign.customers_analyzed && !campaign.eligible_customers
    },
    {
      id: 3,
      title: "Generating Offers",
      subtitle: `${campaign.offers_generated || "—"} strategies`,
      icon: Cpu,
      completed: !!campaign.offers_generated,
      active: !!campaign.eligible_customers && !campaign.offers_generated
    },
    {
      id: 4,
      title: "Executing Campaign",
      subtitle: isExecuted ? "Execution Complete" : (isExecuting ? "Executing..." : "Ready to execute"),
      icon: Send,
      completed: isExecuted,
      active: (!isExecuted && campaign.offers_generated) || isExecuting
    },
    {
      id: 5,
      title: "Tracking Results",
      subtitle: hasAnalytics ? "Results available" : (isExecuted ? "Waiting for activity" : "Pending"),
      icon: BarChart2,
      completed: hasAnalytics,
      active: isExecuted && !hasAnalytics
    }
  ]

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12 max-w-[1400px] mx-auto">
      <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors">
        <ArrowLeft size={16} className="mr-1" /> Back to Campaigns
      </Link>

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border pb-6 mb-8">
        <div className="flex-1">
          <div className="text-xs font-bold text-brand-primary dark:text-brand-teal uppercase tracking-wider mb-1">
            Campaign Goal
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground tracking-tight leading-tight">
              {campaign.goal || campaign.campaign_name || "Untitled Campaign"}
            </h2>
            <StatusBadge status={campaign.status} />
          </div>
          <p className="text-muted font-mono text-xs mt-2 uppercase tracking-wide">ID: {campaign.campaign_id}</p>
        </div>
        
        <div className="w-full md:w-auto">
          {!isExecuted ? (
            <div className="relative">
              <button
                onClick={handleExecuteCampaign}
                disabled={isExecuting || !campaign.offers_generated}
                className={`w-full md:w-auto px-6 py-3 rounded-xl font-bold text-white transition-all shadow-sm hover:shadow-soft flex justify-center items-center gap-2
                  ${isExecuting || !campaign.offers_generated
                    ? 'bg-brand-primary/50 cursor-not-allowed opacity-80' 
                    : 'bg-brand-primary hover:bg-brand-teal hover:-translate-y-0.5'
                  }`}
              >
                {isExecuting ? (
                  <><RefreshCw className="w-5 h-5 animate-spin" /> Executing...</>
                ) : (
                  <><Send className="w-5 h-5" /> Execute Campaign</>
                )}
              </button>
              
              {isExecuting && executionState && (
                <div className="absolute top-full left-0 right-0 mt-2 text-center text-xs font-semibold text-brand-primary dark:text-brand-teal animate-pulse whitespace-nowrap">
                  {executionState}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200/60 dark:border-emerald-800/40 text-emerald-700 dark:text-emerald-400 px-5 py-3 rounded-xl shadow-sm flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 shrink-0" />
              <div>
                <span className="font-bold block text-sm">Execution Complete</span>
                <span className="text-xs opacity-90">{execution?.total_offers_sent || analytics?.total_offers || 0} Offers sent. Tracking active.</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Automation Pipeline UI */}
      <div className="bg-surface border border-border rounded-2xl shadow-soft p-8 mb-10">
        <h3 className="text-lg font-bold text-foreground mb-8 flex items-center">
          <Settings className="w-5 h-5 mr-2 text-brand-primary dark:text-brand-teal" />
          Campaign Automation Workflow
        </h3>
        
        {/* Horizontal Stepper for Desktop, Vertical for Mobile */}
        <div className="relative flex flex-col md:flex-row justify-between w-full pb-4">
          {/* Connecting Line Desktop */}
          <div className="hidden md:block absolute top-6 left-[10%] right-[10%] h-1 bg-muted/20 -z-10 rounded-full overflow-hidden">
             <div className="h-full bg-brand-primary transition-all duration-700" style={{ width: `${((steps.filter(s => s.completed).length - 1) / (steps.length - 1)) * 100}%` }}></div>
          </div>
          
          {/* Connecting Line Mobile */}
          <div className="md:hidden absolute top-0 bottom-0 left-6 w-1 bg-muted/20 -z-10 rounded-full overflow-hidden">
             <div className="w-full bg-brand-primary transition-all duration-700" style={{ height: `${((steps.filter(s => s.completed).length - 1) / (steps.length - 1)) * 100}%` }}></div>
          </div>

          {steps.map((step, index) => (
            <div key={step.id} className="flex flex-row md:flex-col items-start md:items-center relative z-10 mb-8 md:mb-0 w-full md:w-1/5">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center border-2 shrink-0 bg-surface transition-all duration-300
                ${step.completed ? 'border-brand-primary text-brand-primary shadow-[0_0_15px_rgba(15,118,110,0.3)] dark:shadow-[0_0_15px_rgba(20,184,166,0.3)] dark:text-brand-teal dark:border-brand-teal' : 
                  (step.active ? 'border-brand-primary text-brand-primary scale-110 shadow-[0_0_20px_rgba(15,118,110,0.4)] dark:shadow-[0_0_20px_rgba(20,184,166,0.4)] dark:text-brand-teal dark:border-brand-teal' : 'border-border text-muted')}
              `}>
                {step.completed ? <Check className="w-6 h-6" /> : (isExecuting && step.id === 4 ? <RefreshCw className="w-5 h-5 animate-spin" /> : <step.icon className="w-5 h-5" />)}
              </div>
              
              <div className="ml-4 md:ml-0 md:mt-4 flex flex-col md:items-center">
                <span className={`text-sm font-bold tracking-tight ${step.active || step.completed ? 'text-foreground' : 'text-muted'}`}>
                  {step.title}
                </span>
                <span className={`text-xs font-medium mt-1 text-left md:text-center uppercase tracking-wider ${step.completed ? 'text-brand-primary dark:text-brand-teal' : 'text-muted/70'}`}>
                  {step.subtitle}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Automation Results */}
      <div className="mb-10">
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-5">Campaign Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <MetricCard title="Customers Analyzed" value={campaign.customers_analyzed || "—"} icon={Database} color="gray" />
          <MetricCard title="Eligible Customers" value={campaign.eligible_customers || "—"} icon={Users} color="blue" />
          <MetricCard title="Offers Generated" value={campaign.offers_generated || "—"} icon={Cpu} color="purple" />
          <MetricCard title="Offers Sent" value={execution?.total_offers_sent || analytics?.total_offers || (isExecuted ? (campaign.offers_generated || "—") : "—")} icon={Send} color="green" />
          <MetricCard title="Conversions" value={analytics?.verified_payments !== undefined ? analytics.verified_payments : "—"} icon={Target} color="orange" />
          <MetricCard title="Revenue" value={analytics?.revenue !== undefined ? `₹${analytics.revenue.toLocaleString()}` : "—"} icon={IndianRupee} color="green" />
          <MetricCard title="Conv. Rate" value={analytics?.conversion_rate !== undefined ? `${analytics.conversion_rate.toFixed(1)}%` : "—"} icon={TrendingUp} color="blue" />
        </div>
      </div>

      {/* AI Segmentation Strategy */}
      {Array.isArray(offers) && offers.length > 0 && (
        <div className="mb-10 space-y-6">
          <h3 className="text-xl font-bold text-foreground">Data-Driven Target Audiences</h3>
          <p className="text-base text-muted max-w-3xl leading-relaxed">The AI analyzed the actual customer dataset and dynamically formed the following segments aligned with your campaign goal.</p>
          
          <div className="grid grid-cols-1 gap-6">
            {Array.from(new Set(offers.map(o => o.customer_segment))).map(segmentName => {
              const segmentOffers = offers.filter(o => o.customer_segment === segmentName);
              const sample = segmentOffers[0];
              
              return (
                <div key={segmentName} className="bg-surface border border-border rounded-2xl p-8 shadow-soft hover:shadow-md transition-shadow">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 pb-6 border-b border-border">
                    <div>
                      <h4 className="text-xl font-bold text-brand-primary dark:text-brand-teal flex items-center tracking-tight">
                        <Users className="w-6 h-6 mr-3 text-brand-primary/80 dark:text-brand-teal/80" />
                        {segmentName.replace(/_/g, ' ')}
                      </h4>
                      <p className="text-sm font-semibold text-muted mt-2 tracking-wide uppercase">Target Segment Profile</p>
                    </div>
                    <div className="mt-4 sm:mt-0 flex flex-col items-end">
                      <span className="bg-brand-primary/10 text-brand-primary dark:bg-brand-teal/10 dark:text-brand-teal text-sm font-bold px-4 py-2 rounded-xl border border-brand-primary/20 dark:border-brand-teal/20">
                        {segmentOffers.length} Eligible Customers
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="bg-background/50 rounded-2xl p-6 border border-border">
                      <h5 className="text-xs font-bold text-muted uppercase tracking-widest mb-6">AI Strategy & Offer</h5>
                      
                      <div className="space-y-6">
                        <div>
                          <span className="text-xs font-bold text-brand-primary dark:text-brand-teal uppercase tracking-widest">Strategy</span>
                          <p className="text-base font-semibold text-foreground mt-2">{sample.recommended_strategy}</p>
                        </div>
                        
                        <div>
                          <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest">Generated Offer</span>
                          <div className="mt-3 flex items-start gap-4">
                            <span className="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-400 text-sm font-bold px-4 py-2 rounded-lg border border-emerald-200 dark:border-emerald-800 shrink-0 mt-0.5">
                              {sample.discount_percentage ?? sample.discount_pct}% OFF
                            </span>
                            <span className="text-base font-semibold text-foreground leading-snug">
                              {sample.offer_description}
                            </span>
                          </div>
                        </div>
                        
                        <div>
                          <span className="text-xs font-bold text-brand-coral uppercase tracking-widest">Expected Objective</span>
                          <p className="text-base text-foreground/80 mt-2 font-medium leading-relaxed">{sample.expected_objective}</p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-background/50 rounded-2xl p-6 border border-border">
                      <h5 className="text-xs font-bold text-muted uppercase tracking-widest mb-6">Reasoning & Rules</h5>
                      
                      <div className="space-y-6">
                        <div>
                          <span className="text-xs font-bold text-amber-600 dark:text-amber-500 uppercase tracking-widest">Why this offer?</span>
                          <p className="text-base text-foreground/80 mt-2 font-medium leading-relaxed">{sample.why_this_offer}</p>
                        </div>
                        
                        <div>
                          <span className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-widest">Data Evidence</span>
                          <p className="text-sm text-foreground/70 mt-2 leading-relaxed">{sample.data_evidence}</p>
                        </div>
                        
                        <div>
                          <span className="text-xs font-bold text-rose-600 dark:text-rose-400 uppercase tracking-widest">Merchant Constraints Applied</span>
                          <p className="text-sm text-foreground/70 mt-2 leading-relaxed">{sample.merchant_constraints}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}


      {/* Offers & Segments Table */}
      <div className="bg-surface border border-border rounded-2xl shadow-soft overflow-hidden mt-8">
        <div className="p-8 border-b border-border">
          <h3 className="text-xl font-bold text-foreground">Customer-Level Offers</h3>
          <p className="text-sm text-muted mt-2">Detailed view of every personalized offer generated and sent by the AI.</p>
        </div>
        
        {(!Array.isArray(offers) || offers.length === 0) ? (
          <div className="p-8 text-center text-muted font-medium">No offers found for this campaign.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead>
                <tr className="bg-background/50 text-muted text-xs font-bold uppercase tracking-widest border-b border-border">
                  <th className="p-5">Customer</th>
                  <th className="p-5">Segment</th>
                  <th className="p-5">Strategy</th>
                  <th className="p-5 w-1/4">Offer</th>
                  <th className="p-5">Code</th>
                  <th className="p-5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {offers.map((offer) => {
                  return (
                    <tr key={offer.offer_id} className="hover:bg-background/80 transition-colors">
                      <td className="p-5">
                        <div className="font-bold text-foreground">{offer.customer_name || 'Unknown'}</div>
                        <div className="text-xs text-muted font-mono mt-1">{offer.customer_id}</div>
                      </td>
                      <td className="p-5 font-bold capitalize text-foreground/80">
                        {offer.customer_segment.replace(/_/g, ' ')}
                      </td>
                      <td className="p-5">
                        <span className="text-xs font-bold bg-brand-primary/10 text-brand-primary dark:text-brand-teal px-3 py-1.5 rounded-lg">
                          {offer.recommended_strategy || 'Standard Engagement'}
                        </span>
                      </td>
                      <td className="p-5">
                        <div className="font-bold text-foreground">
                          {offer.offer_description || `${offer.discount_percentage ?? offer.discount_pct}% OFF`}
                        </div>
                        {offer.why_this_offer && (
                           <div className="text-xs text-muted mt-2 leading-relaxed line-clamp-2 font-medium">{offer.why_this_offer}</div>
                        )}
                      </td>
                      <td className="p-5">
                        {offer.coupon_code ? (
                          <span className="font-mono text-sm font-bold bg-background px-3 py-1.5 rounded-lg text-foreground border border-border">
                            {offer.coupon_code}
                          </span>
                        ) : (
                          <span className="text-muted text-xs italic font-medium">Pending</span>
                        )}
                      </td>
                      <td className="p-5">
                        <span className={`text-xs font-bold px-3 py-1.5 rounded-lg ${offer.status === 'SENT' ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-400' : 'bg-background text-muted border border-border'}`}>
                          {offer.status}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* Feedback Loop */}
      <div className="mt-12 relative overflow-hidden bg-brand-primary text-white rounded-3xl p-10 shadow-soft border border-brand-primary/20">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl pointer-events-none translate-x-1/2 -translate-y-1/2"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-brand-teal/20 rounded-full blur-2xl pointer-events-none -translate-x-1/3 translate-y-1/3"></div>
        
        <div className="relative z-10 flex flex-col md:flex-row items-center gap-8 md:gap-12 max-w-4xl mx-auto">
          <div className="flex-shrink-0 w-20 h-20 bg-white/10 backdrop-blur-md rounded-2xl flex items-center justify-center border border-white/20 shadow-inner">
            <TrendingUp className="w-10 h-10 text-white drop-shadow-md" />
          </div>
          <div className="text-center md:text-left">
            <h3 className="text-2xl font-bold mb-3 tracking-tight">Continuous Learning & Optimization</h3>
            <p className="text-lg text-white/90 leading-relaxed">
              RAZZZ becomes smarter using campaign performance data. Once actual conversions and revenue are collected, this data automatically feeds back into the AI Intelligence engine to continuously optimize future recommendations and segmentation strategies.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
