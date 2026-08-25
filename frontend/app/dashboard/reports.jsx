'use client'

import Link from 'next/link'

export default function Reports() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b p-4">
        <Link href="/dashboard" className="text-blue-600 hover:text-blue-800 font-semibold">
          ← Back to Dashboard
        </Link>
      </div>

      <div className="max-w-4xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-2 text-gray-800">📈 Reports</h1>
        <p className="text-gray-600 mb-8">
          View detailed analytics and campaign performance.
        </p>

        <div className="bg-white p-8 rounded-lg shadow-lg">
          <p className="text-gray-600">
            Reports dashboard coming in Day 3...
          </p>
        </div>
      </div>
    </div>
  )
}