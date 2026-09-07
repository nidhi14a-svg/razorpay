'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { EmptyState } from '@/components/EmptyState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { 
  Users, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  ChevronsLeft, 
  ChevronsRight, 
  Filter, 
  X,
  TrendingUp,
  ShoppingBag,
  Clock,
  DollarSign,
  UploadCloud
} from 'lucide-react'
import { getApiUrl } from '@/lib/api'

export default function CustomersPage() {
  const [customers, setCustomers] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(20)
  const [totalPages, setTotalPages] = useState(1)
  const [segments, setSegments] = useState({})
  const [selectedSegment, setSelectedSegment] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [jumpPage, setJumpPage] = useState('')
  const [loading, setLoading] = useState(true)
  const [pageLoading, setPageLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchCustomers = useCallback(async (isInitial = false) => {
    const merchantId = localStorage.getItem('merchantId')
    if (!merchantId) {
      window.location.href = '/login'
      return
    }

    if (isInitial) {
      setLoading(true)
    } else {
      setPageLoading(true)
    }
    setError(null)

    try {
      const params = new URLSearchParams({
        merchant_id: merchantId,
        page: page.toString(),
        limit: limit.toString()
      })

      if (selectedSegment && selectedSegment !== 'all') {
        params.append('segment', selectedSegment)
      }

      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim())
      }

      const res = await fetch(getApiUrl(`/customers?${params.toString()}`))
      if (!res.ok) {
        throw new Error(`Failed to load customers (Status: ${res.status})`)
      }

      const json = await res.json()
      const items = Array.isArray(json.customers) ? json.customers : (Array.isArray(json.items) ? json.items : [])
      setCustomers(items)
      setTotal(typeof json.total === 'number' ? json.total : items.length)
      setTotalPages(typeof json.total_pages === 'number' ? json.total_pages : Math.max(1, Math.ceil((json.total || 0) / limit)))
      
      if (json.segments && Object.keys(json.segments).length > 0) {
        setSegments(json.segments)
      }
    } catch (err) {
      console.error("Customers fetch error:", err)
      setError(err.message || "Failed to load customers. Please try again.")
    } finally {
      setLoading(false)
      setPageLoading(false)
    }
  }, [page, limit, selectedSegment, searchQuery])

  // Initial load and dependency trigger
  useEffect(() => {
    fetchCustomers(page === 1 && !selectedSegment && !searchQuery)
  }, [fetchCustomers])

  // Handle Search submit
  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setPage(1)
    setSearchQuery(searchInput)
  }

  const handleClearSearch = () => {
    setSearchInput('')
    setSearchQuery('')
    setPage(1)
  }

  // Handle segment filter toggle
  const handleSegmentClick = (seg) => {
    if (selectedSegment === seg) {
      setSelectedSegment('all')
    } else {
      setSelectedSegment(seg)
    }
    setPage(1)
  }

  // Handle direct page jump
  const handleJumpPage = (e) => {
    e.preventDefault()
    const target = parseInt(jumpPage, 10)
    if (!isNaN(target) && target >= 1 && target <= totalPages) {
      setPage(target)
      setJumpPage('')
    }
  }

  // Calculate smart pagination window
  const getPageNumbers = () => {
    const pages = []
    const maxVisible = 5

    if (totalPages <= maxVisible + 2) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
      return pages
    }

    pages.push(1)

    let start = Math.max(2, page - 1)
    let end = Math.min(totalPages - 1, page + 1)

    if (page <= 3) {
      end = Math.min(totalPages - 1, 4)
    } else if (page >= totalPages - 2) {
      start = Math.max(2, totalPages - 3)
    }

    if (start > 2) {
      pages.push('...')
    }

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (end < totalPages - 1) {
      pages.push('...')
    }

    pages.push(totalPages)
    return pages
  }

  // Segment badge color mapping
  const getSegmentBadgeStyle = (seg) => {
    const s = (seg || '').toLowerCase()
    if (s.includes('loyal') || s.includes('vip')) {
      return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60'
    }
    if (s.includes('high') || s.includes('value')) {
      return 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800/60'
    }
    if (s.includes('price') || s.includes('deal') || s.includes('sensitive')) {
      return 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800/60'
    }
    if (s.includes('dormant') || s.includes('inactive') || s.includes('churn')) {
      return 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800/60'
    }
    return 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800/60'
  }

  const startRecord = total > 0 ? (page - 1) * limit + 1 : 0
  const endRecord = Math.min(page * limit, total)

  if (loading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div>
          <h2 className="text-3xl font-bold text-foreground tracking-tight">Customer Intelligence</h2>
          <p className="text-muted text-lg mt-1">Analyzing customer dataset and segments...</p>
        </div>
        <LoadingSkeleton type="table" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-6 rounded-2xl flex flex-col items-start gap-4">
        <h3 className="font-bold text-lg">Unable to load customers</h3>
        <p className="text-sm">{error}</p>
        <button
          onClick={() => fetchCustomers(true)}
          className="bg-red-600 hover:bg-red-700 text-white font-semibold text-xs px-4 py-2 rounded-xl transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border pb-6">
        <div>
          <h2 className="text-3xl font-bold text-foreground tracking-tight">Customer Intelligence</h2>
          <p className="text-muted mt-1 text-base">
            Explore customer behavioral metrics and dynamic segmentation with server-side pagination.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/onboarding?step=data"
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary rounded-xl text-xs font-bold transition-all border border-brand-primary/20 shadow-sm"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Import / Update Data</span>
          </Link>
          <div className="bg-surface border border-border px-5 py-3 rounded-2xl text-sm font-bold text-foreground flex items-center gap-3 shadow-soft">
            <div className="p-2 bg-brand-primary/10 text-brand-primary dark:text-brand-teal rounded-xl">
              <Users size={20} />
            </div>
            <div>
              <div className="text-xs text-muted font-normal uppercase tracking-wider">Total Audience</div>
              <div className="text-xl font-extrabold text-foreground">{total.toLocaleString()} Customers</div>
            </div>
          </div>
        </div>
      </div>

      {/* Segment Breakdown Cards (Server-side aggregated) */}
      {Object.keys(segments).length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted flex items-center gap-2">
              <Filter size={14} /> Segment Breakdown
              {selectedSegment !== 'all' && (
                <button 
                  onClick={() => handleSegmentClick('all')}
                  className="ml-2 text-xs font-semibold text-brand-primary hover:underline lowercase"
                >
                  (clear filter)
                </button>
              )}
            </h3>
            <span className="text-xs text-muted">Click a segment card to filter table</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(segments).map(([segment, count]) => {
              const isSelected = selectedSegment === segment
              const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0

              return (
                <button
                  key={segment}
                  onClick={() => handleSegmentClick(segment)}
                  className={`text-left bg-surface border rounded-2xl p-5 shadow-soft transition-all duration-200 relative overflow-hidden group hover:shadow-md ${
                    isSelected 
                      ? 'border-brand-primary ring-2 ring-brand-primary/20 bg-brand-primary/[0.02]' 
                      : 'border-border hover:border-brand-primary/40'
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="font-bold text-foreground capitalize text-base tracking-tight truncate mr-2">
                      {segment.replace(/_/g, ' ')}
                    </h4>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getSegmentBadgeStyle(segment)}`}>
                      {count.toLocaleString()}
                    </span>
                  </div>

                  <div className="w-full bg-background border border-border/80 rounded-full h-2 mb-2 overflow-hidden">
                    <div 
                      className="bg-brand-primary dark:bg-brand-teal h-full rounded-full transition-all duration-700 ease-out" 
                      style={{ width: `${Math.min(100, Math.max(3, parseFloat(pct)))}%` }}
                    />
                  </div>

                  <div className="flex justify-between items-center text-xs text-muted">
                    <span>{pct}% of audience</span>
                    {isSelected && (
                      <span className="text-brand-primary font-bold text-[11px] uppercase tracking-wide">Active</span>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Search and Control Bar */}
      <div className="bg-surface border border-border p-4 rounded-2xl shadow-soft flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search by ID, Name, or Email..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full pl-10 pr-10 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-brand-primary/40 focus:border-transparent transition-all"
          />
          {searchInput && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground p-0.5"
            >
              <X size={16} />
            </button>
          )}
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          {/* Segment Selector Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted hidden sm:inline">Segment:</span>
            <select
              value={selectedSegment}
              onChange={(e) => {
                setSelectedSegment(e.target.value)
                setPage(1)
              }}
              className="bg-background border border-border rounded-xl text-xs font-semibold px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-brand-primary/40"
            >
              <option value="all">All Segments ({total.toLocaleString()})</option>
              {Object.entries(segments).map(([seg, count]) => (
                <option key={seg} value={seg}>
                  {seg.replace(/_/g, ' ')} ({count.toLocaleString()})
                </option>
              ))}
            </select>
          </div>

          {/* Page Limit Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted hidden sm:inline">Rows:</span>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(parseInt(e.target.value, 10))
                setPage(1)
              }}
              className="bg-background border border-border rounded-xl text-xs font-semibold px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-brand-primary/40"
            >
              <option value={20}>20 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Customers Table Container */}
      {customers.length === 0 ? (
        <EmptyState 
          title="No customers match your criteria" 
          description="Try clearing your search query or selecting 'All Segments'."
          actionLabel="Clear Filters"
          onAction={() => {
            setSelectedSegment('all')
            setSearchInput('')
            setSearchQuery('')
            setPage(1)
          }}
        />
      ) : (
        <div className="space-y-4">
          <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-soft relative">
            {pageLoading && (
              <div className="absolute inset-0 bg-background/50 backdrop-blur-[1px] flex items-center justify-center z-10">
                <div className="w-8 h-8 border-3 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin"></div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-background/80 border-b border-border text-muted text-xs uppercase tracking-wider font-semibold">
                    <th className="py-4 px-6">Customer ID</th>
                    <th className="py-4 px-6">Segment</th>
                    <th className="py-4 px-6 text-right">Purchases</th>
                    <th className="py-4 px-6 text-right">Avg Order Value</th>
                    <th className="py-4 px-6 text-right">Lifetime Value</th>
                    <th className="py-4 px-6 text-right">Last Purchase</th>
                    <th className="py-4 px-6 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 text-sm">
                  {customers.map((c, index) => {
                    const custId = c.id || c.customer_id || `cust_${index}`
                    const displayId = custId.length > 16 ? `${custId.slice(0, 8)}...${custId.slice(-6)}` : custId
                    const aov = typeof c.average_order_value === 'number' ? c.average_order_value : 0
                    const ltv = typeof c.lifetime_value === 'number' ? c.lifetime_value : 0
                    const purchases = typeof c.purchase_count === 'number' ? c.purchase_count : 0
                    const daysAgo = typeof c.days_since_last_purchase === 'number' ? c.days_since_last_purchase : 0

                    return (
                      <tr 
                        key={custId} 
                        className="hover:bg-brand-primary/[0.02] dark:hover:bg-brand-teal/[0.02] transition-colors group"
                      >
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center font-bold text-xs shrink-0">
                              {c.name ? c.name.charAt(0).toUpperCase() : 'C'}
                            </div>
                            <div>
                              <div className="font-mono text-xs font-bold text-foreground" title={custId}>
                                {displayId}
                              </div>
                              {c.name && (
                                <div className="text-xs text-muted truncate max-w-[160px]">{c.name}</div>
                              )}
                              {c.email && (
                                <div className="text-[11px] text-muted/80 truncate max-w-[160px]">{c.email}</div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border capitalize ${getSegmentBadgeStyle(c.segment)}`}>
                            {(c.segment || 'Unknown').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right font-semibold text-foreground">
                          {purchases}
                        </td>
                        <td className="py-4 px-6 text-right font-medium text-foreground">
                          ₹{aov.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-4 px-6 text-right font-bold text-foreground">
                          ₹{ltv.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-4 px-6 text-right text-muted text-xs">
                          {daysAgo === 0 ? 'Today' : `${daysAgo}d ago`}
                        </td>
                        <td className="py-4 px-6 text-center">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                            c.cart_status === 'purchased'
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400'
                              : c.cart_status === 'abandoned'
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400'
                              : 'bg-muted/20 text-muted'
                          }`}>
                            {c.cart_status || 'active'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Controls Bar */}
          <div className="flex flex-col lg:flex-row items-center justify-between gap-4 px-2 py-3">
            {/* Range Text */}
            <div className="text-sm text-muted font-medium text-center lg:text-left">
              Showing <strong className="text-foreground">{startRecord.toLocaleString()}</strong>–<strong className="text-foreground">{endRecord.toLocaleString()}</strong> of <strong className="text-foreground">{total.toLocaleString()}</strong> customers
            </div>

            {/* Numeric & Direction Controls */}
            <div className="flex items-center gap-1.5 flex-wrap justify-center">
              {/* First Page */}
              <button
                onClick={() => setPage(1)}
                disabled={page === 1 || pageLoading}
                title="First Page"
                className="p-2 rounded-xl border border-border text-muted hover:text-foreground hover:bg-surface disabled:opacity-40 disabled:pointer-events-none transition-colors"
              >
                <ChevronsLeft size={16} />
              </button>

              {/* Previous Page */}
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1 || pageLoading}
                title="Previous Page"
                className="inline-flex items-center gap-1 px-3 py-2 rounded-xl border border-border text-xs font-semibold text-muted hover:text-foreground hover:bg-surface disabled:opacity-40 disabled:pointer-events-none transition-colors"
              >
                <ChevronLeft size={16} />
                <span className="hidden sm:inline">Previous</span>
              </button>

              {/* Number Buttons */}
              <div className="flex items-center gap-1 mx-1">
                {getPageNumbers().map((pNum, idx) => {
                  if (pNum === '...') {
                    return (
                      <span key={`dots_${idx}`} className="px-2 text-muted text-xs">
                        ...
                      </span>
                    )
                  }

                  const isCurrent = pNum === page
                  return (
                    <button
                      key={`page_${pNum}`}
                      onClick={() => setPage(pNum)}
                      disabled={pageLoading}
                      className={`min-w-[36px] h-9 px-3 rounded-xl text-xs font-bold transition-all ${
                        isCurrent
                          ? 'bg-brand-primary text-white shadow-sm'
                          : 'border border-border text-foreground hover:bg-surface'
                      }`}
                    >
                      {pNum}
                    </button>
                  )
                })}
              </div>

              {/* Next Page */}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || pageLoading}
                title="Next Page"
                className="inline-flex items-center gap-1 px-3 py-2 rounded-xl border border-border text-xs font-semibold text-muted hover:text-foreground hover:bg-surface disabled:opacity-40 disabled:pointer-events-none transition-colors"
              >
                <span className="hidden sm:inline">Next</span>
                <ChevronRight size={16} />
              </button>

              {/* Last Page */}
              <button
                onClick={() => setPage(totalPages)}
                disabled={page === totalPages || pageLoading}
                title="Last Page"
                className="p-2 rounded-xl border border-border text-muted hover:text-foreground hover:bg-surface disabled:opacity-40 disabled:pointer-events-none transition-colors"
              >
                <ChevronsRight size={16} />
              </button>
            </div>

            {/* Direct Jump to Page Form */}
            <form onSubmit={handleJumpPage} className="flex items-center gap-2 text-xs text-muted">
              <span>Go to page:</span>
              <input
                type="number"
                min={1}
                max={totalPages}
                placeholder={page.toString()}
                value={jumpPage}
                onChange={(e) => setJumpPage(e.target.value)}
                className="w-16 px-2.5 py-1.5 bg-surface border border-border rounded-lg text-center text-foreground font-semibold focus:outline-none focus:ring-1 focus:ring-brand-primary"
              />
              <span className="text-muted/80">/ {totalPages.toLocaleString()}</span>
              <button
                type="submit"
                disabled={!jumpPage.trim()}
                className="bg-surface hover:bg-background border border-border font-bold px-2.5 py-1.5 rounded-lg text-foreground transition-colors disabled:opacity-40"
              >
                Go
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
