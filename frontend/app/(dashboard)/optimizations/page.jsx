'use client'

import { useEffect, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { OptimizationCard } from '@/components/OptimizationCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'

export default function OptimizationsPage() {
  const [optimizations, setOptimizations] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState(null)

  const merchantId = typeof window !== 'undefined' ? localStorage.getItem('merchantId') : null

  useEffect(() => {
    async function fetchData() {
      try {
        const optRes = await fetch(`http://localhost:8000/optimizations?merchant_id=${merchantId}`)
        if (!optRes.ok) {
          throw new Error(`Failed to fetch optimizations (Status: ${optRes.status})`)
        }
        
        const allOpts = await optRes.json()
        setOptimizations(allOpts)
      } catch (err) {
        console.error("Optimizations fetch error:", err)
        setError(err.message || "Failed to load optimizations")
      } finally {
        setLoading(false)
      }
    }
    
    if (merchantId) fetchData()
  }, [merchantId])

  const handleAction = async (optId, action) => {
    setActionLoading(true)
    try {
      const url = `http://localhost:8000/optimizations/${optId}/${action}?merchant_id=${merchantId}`
      
      const body = action === 'reject' ? JSON.stringify({ reason: "Rejected by merchant" }) : null
      const headers = action === 'reject' ? { 'Content-Type': 'application/json' } : {}

      const res = await fetch(url, {
        method: 'POST',
        headers,
        body
      })
      
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Failed to ${action} optimization`)
      
      // Update local state to reflect new status
      setOptimizations(prev => prev.map(opt => {
        if (opt.optimization_id === optId) {
           return { 
             ...opt, 
             status: action === 'approve' ? 'APPROVED' : action === 'reject' ? 'REJECTED' : 'EXECUTED' 
           }
        }
        return opt
      }))
      
    } catch (err) {
      alert(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Campaign Optimizations</h2>
          <p className="text-gray-500">Loading AI proposals...</p>
        </div>
        <div className="grid gap-6">
          <LoadingSkeleton type="card" />
          <LoadingSkeleton type="card" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Campaign Optimizations</h2>
        <p className="text-gray-500 mt-1">Review, approve, and execute AI-generated strategies to improve live campaigns.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
          {error}
        </div>
      )}

      {optimizations.length === 0 && !error ? (
        <EmptyState 
          title="No optimizations available" 
          description="The AI hasn't generated any optimization proposals yet. Ensure you have active campaigns with sufficient data."
        />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {optimizations.map((opt) => (
            <OptimizationCard 
              key={opt.optimization_id} 
              optimization={opt} 
              loading={actionLoading}
              onApprove={(id) => handleAction(id, 'approve')}
              onReject={(id) => handleAction(id, 'reject')}
              onExecute={(id) => handleAction(id, 'execute')}
            />
          ))}
        </div>
      )}
    </div>
  )
}
