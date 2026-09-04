'use client'

import { useEffect, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { Users } from 'lucide-react'

export default function CustomersPage() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const merchantId = localStorage.getItem('merchantId')
    
    if (!merchantId) {
      window.location.href = '/login'
      return
    }
    
    async function fetchCustomers() {
      try {
        const res = await fetch(`http://localhost:8000/customers?merchant_id=${merchantId}`)
        if (!res.ok) {
          throw new Error(`Failed to load customers (Status: ${res.status})`)
        }
        
        const json = await res.json()
        setCustomers(Array.isArray(json.items) ? json.items : [])
      } catch (err) {
        console.error("Customers fetch error:", err)
        setError(err.message || "Failed to load customers. Please try again.")
      } finally {
        setLoading(false)
      }
    }
    
    if (merchantId) fetchCustomers()
  }, [])

  // Aggregate segments
  const segments = Array.isArray(customers) ? customers.reduce((acc, customer) => {
    const seg = customer.segment || 'Unknown'
    if (!acc[seg]) {
      acc[seg] = { count: 0, customers: [] }
    }
    acc[seg].count += 1
    acc[seg].customers.push(customer)
    return acc
  }, {}) : {}

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Customer Intelligence</h2>
          <p className="text-muted">Analyzing your customer database...</p>
        </div>
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-xl">
        Failed to load customers. Please try again.
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-6 mb-8">
        <div>
          <h2 className="text-3xl font-bold text-foreground tracking-tight">Customer Intelligence</h2>
          <p className="text-muted mt-2 text-lg">View your audience broken down by behavior and segment.</p>
        </div>
        <div className="bg-surface border border-border px-5 py-3 rounded-xl text-sm font-bold text-foreground flex items-center gap-3 shadow-soft">
          <div className="p-1.5 bg-brand-primary/10 rounded-lg">
            <Users size={18} className="text-brand-primary dark:text-brand-teal" />
          </div>
          {customers.length} Total Customers
        </div>
      </div>

      {customers.length === 0 ? (
        <EmptyState 
          title="No customers found" 
          description="Upload a CSV dataset to start analyzing your customers."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(segments).map(([segment, data]) => (
            <div key={segment} className="bg-surface border border-border rounded-2xl p-8 shadow-soft hover:shadow-md hover:border-brand-primary/30 transition-all duration-300 group">
              <div className="flex justify-between items-start mb-6">
                <h3 className="font-bold text-foreground capitalize text-xl tracking-tight">{segment.replace(/_/g, ' ')}</h3>
                <span className="bg-brand-primary/10 text-brand-primary dark:bg-brand-teal/10 dark:text-brand-teal font-bold px-4 py-1.5 rounded-lg text-sm border border-brand-primary/20 dark:border-brand-teal/20 group-hover:scale-105 transition-transform">
                  {data.count}
                </span>
              </div>
              
              <div className="w-full bg-background border border-border rounded-full h-3 mb-3 overflow-hidden">
                <div 
                  className="bg-brand-primary dark:bg-brand-teal h-full rounded-full transition-all duration-1000 ease-out" 
                  style={{ width: `${Math.round((data.count / customers.length) * 100)}%` }}
                ></div>
              </div>
              <p className="text-sm font-medium text-muted">
                <strong className="text-foreground">{Math.round((data.count / customers.length) * 100)}%</strong> of your total audience
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
