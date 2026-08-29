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
    
    async function fetchCustomers() {
      try {
        const res = await fetch(`http://localhost:8000/customers?merchant_id=${merchantId}`)
        if (!res.ok) {
          throw new Error(`Failed to load customers (Status: ${res.status})`)
        }
        
        const json = await res.json()
        setCustomers(json.items || [])
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
  const segments = customers.reduce((acc, customer) => {
    const seg = customer.segment || 'Unknown'
    if (!acc[seg]) {
      acc[seg] = { count: 0, customers: [] }
    }
    acc[seg].count += 1
    acc[seg].customers.push(customer)
    return acc
  }, {})

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Customer Segments</h2>
          <p className="text-gray-500">Loading your customer data...</p>
        </div>
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
        Failed to load customers. Please try again.
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Customer Segments</h2>
          <p className="text-gray-500 mt-1">View your audience broken down by behavior.</p>
        </div>
        <div className="bg-white border border-gray-200 px-4 py-2 rounded-lg text-sm font-medium text-gray-700 flex items-center gap-2">
          <Users size={16} className="text-gray-400" />
          {customers.length} Total Customers
        </div>
      </div>

      {customers.length === 0 ? (
        <EmptyState 
          title="No customers found" 
          description="You don't have any customer data available for segmentation yet."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(segments).map(([segment, data]) => (
            <div key={segment} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition">
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-gray-900 capitalize text-lg">{segment.replace(/_/g, ' ')}</h3>
                <span className="bg-blue-50 text-blue-700 font-bold px-2.5 py-1 rounded-lg text-sm">
                  {data.count}
                </span>
              </div>
              <p className="text-sm text-gray-500">
                {Math.round((data.count / customers.length) * 100)}% of your total audience
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
