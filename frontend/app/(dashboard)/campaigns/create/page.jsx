'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Sparkles, ArrowLeft, CheckCircle2 } from 'lucide-react'

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
      const response = await fetch('http://localhost:8000/campaigns', {
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
      <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
        <ArrowLeft size={16} className="mr-1" /> Back to Campaigns
      </Link>

      <div>
        <h2 className="text-3xl font-bold text-gray-900 tracking-tight">Create AI Campaign</h2>
        <p className="text-gray-500 mt-1">Set a business goal, and our AI will instantly generate personalized offers for every segment.</p>
      </div>

      {!result ? (
        <form onSubmit={handleCreateCampaign} className="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
          <div className="mb-8">
            <label className="block text-sm font-bold text-gray-700 uppercase tracking-wide mb-3">
              What is your primary goal?
            </label>
            <textarea
              placeholder="e.g., Clear out winter inventory by offering aggressive discounts to price-sensitive buyers, while upselling high-value customers."
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-40 resize-none text-gray-900 placeholder:text-gray-400"
              required
              disabled={loading}
            />
            <p className="text-gray-500 text-sm mt-3">
              Be specific about what you want to achieve. The AI will strictly adhere to your preset business rules (max discounts, minimum margins).
            </p>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg mb-6 text-sm font-medium">
              {error}
            </div>
          )}

          <div className="flex justify-end pt-4 border-t border-gray-100">
            <button
              type="submit"
              disabled={loading || !goal.trim()}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-2.5 rounded-lg transition disabled:opacity-50 shadow-sm"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating Strategy...
                </>
              ) : (
                <>
                  <Sparkles size={18} /> Generate Campaign Offers
                </>
              )}
            </button>
          </div>
        </form>
      ) : (
        <div className="space-y-6">
          <div className="bg-green-50 border border-green-200 p-6 rounded-xl flex items-start gap-4">
            <CheckCircle2 className="w-8 h-8 text-green-600 shrink-0" />
            <div>
              <h3 className="text-lg font-bold text-green-900">Campaign Activated Successfully</h3>
              <p className="text-green-700 text-sm mt-1">Your campaign has been generated and payment links have been automatically provisioned.</p>
              
              <div className="mt-4 flex gap-3">
                <Link href={`/campaigns/${result.campaign_id}`} className="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg text-sm font-medium transition">
                  View Campaign Details
                </Link>
                <button onClick={() => { setGoal(''); setResult(null) }} className="bg-white border border-green-200 text-green-700 hover:bg-green-50 px-4 py-2 rounded-lg text-sm font-medium transition">
                  Create Another
                </button>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-gray-50/80 px-6 py-4 border-b border-gray-200">
              <h4 className="font-bold text-gray-900">AI Generated Offers</h4>
            </div>
            <div className="divide-y divide-gray-100">
              {Object.entries(result.offers).map(([segment, offer]) => (
                <div key={segment} className="p-6">
                  <div className="flex justify-between items-start mb-2">
                    <h5 className="font-bold text-gray-900 capitalize text-lg">
                      {segment.replace(/_/g, ' ')}
                    </h5>
                    <span className="bg-purple-100 text-purple-800 border border-purple-200 px-3 py-1 rounded-full text-sm font-bold">
                      {offer.discount_pct}% OFF
                    </span>
                  </div>
                  <p className="text-gray-900 font-medium mb-3">{offer.offer}</p>
                  <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 border border-gray-100">
                    <strong className="text-gray-700 font-semibold mr-1">AI Reasoning:</strong>
                    {offer.reasoning}
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
