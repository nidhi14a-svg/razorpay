'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { 
  UploadCloud, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Database, 
  HelpCircle, 
  ArrowRight, 
  ArrowLeft,
  Sparkles, 
  LogOut, 
  BarChart3,
  ShieldCheck,
  Building2,
  Sliders,
  Users,
  Target,
  IndianRupee,
  Check,
  Percent,
  Clock,
  Truck,
  FileText,
  Info,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileSpreadsheet,
  Layers,
  Trash2,
  RefreshCw,
  X,
  FileCheck,
  ShoppingBag,
  PackageCheck
} from 'lucide-react'
import { getApiUrl } from '@/lib/api'
import Link from 'next/link'
import { ThemeToggle } from '@/components/ThemeToggle'

function OnboardingContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  // Logical Steps: 1: Business Information, 2: Guardrail Rules, 3: Customer Data Upload
  const [currentStep, setCurrentStep] = useState(1)
  const [merchantId, setMerchantId] = useState('')
  const [token, setToken] = useState('')
  const [email, setEmail] = useState('')

  // Step 1: Business Information
  const [fullName, setFullName] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [businessCategory, setBusinessCategory] = useState('E-commerce')
  const [businessDescription, setBusinessDescription] = useState('')
  const [businessLoading, setBusinessLoading] = useState(false)

  // Step 2: Guardrail Rules
  const [guardrails, setGuardrails] = useState({
    max_discount_percentage: 25,
    min_margin_percentage: 30,
    min_order_value: 500,
    free_shipping_allowed: true,
    max_campaign_budget: 50000,
    high_value_customer_protection: true,
    contact_frequency_days: 7
  })
  const [showAdvancedGuardrails, setShowAdvancedGuardrails] = useState(false)
  const [guardrailErrors, setGuardrailErrors] = useState({})
  const [guardrailsLoading, setGuardrailsLoading] = useState(false)

  // Step 3: Customer Data Upload & Preview (Mode A: Single Transaction, Mode B: Multiple Related)
  const [uploadMode, setUploadMode] = useState('multiple') // 'multiple' | 'single'
  const [singleFile, setSingleFile] = useState(null)
  const [customersFile, setCustomersFile] = useState(null)
  const [ordersFile, setOrdersFile] = useState(null)
  const [orderItemsFile, setOrderItemsFile] = useState(null)
  
  const [csvPreview, setCsvPreview] = useState(null)
  const [validatingCsv, setValidatingCsv] = useState(false)
  const [importMode, setImportMode] = useState('replace') // 'replace' | 'append'
  const [uploadLoading, setUploadLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [showCsvGuide, setShowCsvGuide] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState(null)
  const [demoSuccess, setDemoSuccess] = useState(false)

  // General state
  const [error, setError] = useState(null)
  const [isAlreadyOnboarded, setIsAlreadyOnboarded] = useState(false)
  const [loadingInitial, setLoadingInitial] = useState(true)

  useEffect(() => {
    const id = localStorage.getItem('merchantId')
    const tok = localStorage.getItem('token')
    const storedName = localStorage.getItem('businessName')
    const storedFullName = localStorage.getItem('fullName')
    const storedEmail = localStorage.getItem('email')
    
    if (!id || !tok) {
      router.push('/login')
      return
    }

    setMerchantId(id)
    setToken(tok)
    if (storedName) setBusinessName(storedName)
    if (storedFullName) setFullName(storedFullName)
    if (storedEmail) setEmail(storedEmail)

    // Handle step override via query parameter
    const stepParam = searchParams.get('step')
    if (stepParam === 'guardrails') {
      setCurrentStep(2)
    } else if (stepParam === 'data') {
      setCurrentStep(3)
    } else if (stepParam === 'business') {
      setCurrentStep(1)
    }

    // Fetch onboarding status & existing profile & guardrails from backend
    fetch(getApiUrl(`/merchants/${id}/onboarding-status`), {
      headers: { 'Authorization': `Bearer ${tok}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch onboarding status')
        return res.json()
      })
      .then(status => {
        if (status.onboarding_completed) {
          setIsAlreadyOnboarded(true)
        }
        if (status.full_name) setFullName(status.full_name)
        if (status.business_name) setBusinessName(status.business_name)
        if (status.email) setEmail(status.email)
        
        if (status.has_guardrails && status.rules) {
          setGuardrails(prev => ({
            ...prev,
            ...status.rules
          }))
        }

        // Only auto-advance step if not manually navigated via stepParam
        if (!stepParam && !status.onboarding_completed) {
          if (status.onboarding_step === 'guardrails_setup') {
            setCurrentStep(2)
          } else if (status.onboarding_step === 'data_setup') {
            setCurrentStep(3)
          }
        }
      })
      .catch(err => {
        console.error("Status fetch error:", err)
      })
      .finally(() => {
        setLoadingInitial(false)
      })

    // Fetch full profile if available
    fetch(getApiUrl(`/merchants/${id}/profile`))
      .then(res => res.ok ? res.json() : null)
      .then(prof => {
        if (prof) {
          if (prof.full_name) setFullName(prof.full_name)
          if (prof.business_name) setBusinessName(prof.business_name)
          if (prof.email) setEmail(prof.email)
          if (prof.business_category) setBusinessCategory(prof.business_category)
          if (prof.business_description) setBusinessDescription(prof.business_description)
        }
      })
      .catch(() => {})

  }, [router, searchParams])

  const handleLogout = () => {
    localStorage.removeItem('merchantId')
    localStorage.removeItem('businessName')
    localStorage.removeItem('fullName')
    localStorage.removeItem('email')
    localStorage.removeItem('token')
    localStorage.removeItem('onboardingCompleted')
    router.push('/login')
  }

  // --- Step 1: Save Business Information ---
  const handleSaveBusiness = async (e) => {
    e.preventDefault()
    if (!businessName.trim()) {
      setError("Please enter your business name.")
      return
    }

    setBusinessLoading(true)
    setError(null)

    try {
      const res = await fetch(getApiUrl(`/merchants/${merchantId}/profile`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          full_name: fullName.trim(),
          business_name: businessName.trim(),
          business_category: businessCategory,
          business_description: businessDescription.trim()
        })
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save business profile')
      }

      localStorage.setItem('businessName', businessName.trim())
      if (fullName.trim()) localStorage.setItem('fullName', fullName.trim())
      
      setCurrentStep(2)
    } catch (err) {
      setError(err.message || 'Failed to save business information')
    } finally {
      setBusinessLoading(false)
    }
  }

  // --- Step 2: Validate & Save Guardrail Rules ---
  const validateGuardrails = () => {
    const errs = {}
    const maxDiscount = parseFloat(guardrails.max_discount_percentage)
    if (isNaN(maxDiscount) || maxDiscount < 0 || maxDiscount > 100) {
      errs.max_discount_percentage = "Maximum discount percentage must be between 0% and 100%."
    }

    const minMargin = parseFloat(guardrails.min_margin_percentage)
    if (isNaN(minMargin) || minMargin < 0 || minMargin > 100) {
      errs.min_margin_percentage = "Minimum margin percentage must be between 0% and 100%."
    }

    const minOrder = parseFloat(guardrails.min_order_value)
    if (isNaN(minOrder) || minOrder < 0) {
      errs.min_order_value = "Minimum order value cannot be negative."
    }

    if (guardrails.max_campaign_budget !== '' && guardrails.max_campaign_budget !== null) {
      const budget = parseFloat(guardrails.max_campaign_budget)
      if (isNaN(budget) || budget < 0) {
        errs.max_campaign_budget = "Campaign budget cannot be negative."
      }
    }

    if (guardrails.contact_frequency_days !== '' && guardrails.contact_frequency_days !== null) {
      const freq = parseInt(guardrails.contact_frequency_days)
      if (isNaN(freq) || freq < 0) {
        errs.contact_frequency_days = "Contact frequency cannot be negative."
      }
    }

    setGuardrailErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSaveGuardrails = async (e) => {
    e.preventDefault()
    if (!validateGuardrails()) {
      return
    }

    setGuardrailsLoading(true)
    setError(null)

    try {
      const payload = {
        max_discount_percentage: parseFloat(guardrails.max_discount_percentage),
        min_margin_percentage: parseFloat(guardrails.min_margin_percentage),
        min_order_value: parseFloat(guardrails.min_order_value || 0),
        free_shipping_allowed: Boolean(guardrails.free_shipping_allowed),
        max_campaign_budget: guardrails.max_campaign_budget ? parseFloat(guardrails.max_campaign_budget) : null,
        high_value_customer_protection: Boolean(guardrails.high_value_customer_protection),
        contact_frequency_days: guardrails.contact_frequency_days ? parseInt(guardrails.contact_frequency_days) : null
      }

      const res = await fetch(getApiUrl(`/merchants/${merchantId}/guardrails`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save merchant guardrails')
      }

      setCurrentStep(3)
    } catch (err) {
      setError(err.message || 'Failed to save guardrails')
    } finally {
      setGuardrailsLoading(false)
    }
  }

  // --- Step 3: Customer Data Upload & Preview Handlers ---
  const handleSingleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
        setError('Please select a valid CSV file (.csv extension required).')
        setSingleFile(null)
        setCsvPreview(null)
        return
      }
      setSingleFile(selectedFile)
      setError(null)
      setCsvPreview(null)
    }
  }

  const handleCustomersFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0]
      if (!f.name.toLowerCase().endsWith('.csv')) {
        setError('Customers file must be a CSV file (.csv extension required).')
        setCustomersFile(null)
        setCsvPreview(null)
        return
      }
      setCustomersFile(f)
      setError(null)
      setCsvPreview(null)
    }
  }

  const handleOrdersFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0]
      if (!f.name.toLowerCase().endsWith('.csv')) {
        setError('Orders file must be a CSV file (.csv extension required).')
        setOrdersFile(null)
        setCsvPreview(null)
        return
      }
      setOrdersFile(f)
      setError(null)
      setCsvPreview(null)
    }
  }

  const handleOrderItemsFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0]
      if (!f.name.toLowerCase().endsWith('.csv')) {
        setError('Order Items file must be a CSV file (.csv extension required).')
        setOrderItemsFile(null)
        setCsvPreview(null)
        return
      }
      setOrderItemsFile(f)
      setError(null)
      setCsvPreview(null)
    }
  }

  // Explicit user action: Process Data
  const handleProcessData = async () => {
    setError(null)
    setValidatingCsv(true)
    setCsvPreview(null)

    try {
      if (uploadMode === 'single') {
        if (!singleFile) {
          throw new Error('Please select a Transaction CSV file first.')
        }
        const formData = new FormData()
        formData.append('file', singleFile)

        const res = await fetch(getApiUrl('/customers/validate-csv'), {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
          body: formData
        })
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.detail || 'Single CSV validation failed.')
        }
        setCsvPreview(data)
      } else {
        // Mode B: Multiple related CSVs
        if (!customersFile || !ordersFile || !orderItemsFile) {
          throw new Error('Please upload all 3 files (Customers, Orders, and Order Items) before processing.')
        }

        const formData = new FormData()
        formData.append('customers_file', customersFile)
        formData.append('orders_file', ordersFile)
        formData.append('order_items_file', orderItemsFile)

        const res = await fetch(getApiUrl('/customers/validate-multi-csv'), {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
          body: formData
        })
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.detail || 'Relational CSV validation failed.')
        }
        setCsvPreview(data)
      }
    } catch (err) {
      setError(err.message || 'Error processing dataset.')
      setCsvPreview(null)
    } finally {
      setValidatingCsv(false)
    }
  }

  // Explicit user action: Confirm and Import
  const handleConfirmImport = async () => {
    if (!csvPreview) return

    setUploadLoading(true)
    setError(null)

    try {
      if (uploadMode === 'single') {
        if (!singleFile) return
        const formData = new FormData()
        formData.append('file', singleFile)
        formData.append('mode', importMode)

        const response = await fetch(getApiUrl('/customers/upload'), {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
          body: formData,
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to upload customer CSV.')
        }

        localStorage.setItem('onboardingCompleted', 'true')
        setUploadSuccess({
          imported: data.rows_imported,
          segments: data.segments_calculated ? Object.keys(data.segments_calculated).length : 0
        })

        setTimeout(() => {
          router.push('/dashboard')
        }, 1500)
      } else {
        // Mode B
        if (!customersFile || !ordersFile || !orderItemsFile) return
        const formData = new FormData()
        formData.append('customers_file', customersFile)
        formData.append('orders_file', ordersFile)
        formData.append('order_items_file', orderItemsFile)
        formData.append('mode', importMode)

        const response = await fetch(getApiUrl('/customers/upload-multi'), {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
          body: formData,
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to import relational customer dataset.')
        }

        localStorage.setItem('onboardingCompleted', 'true')
        setUploadSuccess({
          imported: data.rows_imported,
          segments: data.segments_calculated ? Object.keys(data.segments_calculated).length : 0,
          orders: data.total_orders,
          matched: data.matched_customers
        })

        setTimeout(() => {
          router.push('/dashboard')
        }, 1500)
      }
    } catch (err) {
      setError(err.message || 'An error occurred during dataset import.')
    } finally {
      setUploadLoading(false)
    }
  }

  const handleUseDemo = async () => {
    setDemoLoading(true)
    setError(null)

    try {
      const response = await fetch(getApiUrl('/customers/demo'), {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load demo data.')
      }

      localStorage.setItem('onboardingCompleted', 'true')
      setDemoSuccess(true)

      setTimeout(() => {
        router.push('/dashboard')
      }, 1500)
    } catch (err) {
      setError(err.message || 'An error occurred setting up demo data.')
    } finally {
      setDemoLoading(false)
    }
  }

  const steps = [
    { num: 1, label: "Business Information", short: "Business" },
    { num: 2, label: "Guardrail Rules", short: "Guardrails" },
    { num: 3, label: "Customer Data", short: "Customer Data" }
  ]

  if (loadingInitial) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
          <p className="text-sm font-medium text-muted">Loading merchant configuration...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans selection:bg-brand-primary selection:text-white">
      {/* Header */}
      <header className="w-full border-b border-border bg-surface/80 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-brand-primary p-1.5 rounded-lg shadow-sm">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-foreground">RAZZZ</span>
          </div>
          
          <div className="flex items-center gap-4">
            {businessName && (
              <span className="text-sm font-semibold text-foreground hidden sm:inline px-2.5 py-1 bg-surface border border-border rounded-lg">
                {businessName}
              </span>
            )}
            <ThemeToggle />
            <div className="h-5 w-px bg-border"></div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-sm text-muted hover:text-red-500 font-medium transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center py-8 px-4 sm:px-6">
        <div className="max-w-3xl w-full">

          {/* Stepper Navigation */}
          <div className="mb-8">
            <div className="flex items-center justify-between relative">
              <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-border -translate-y-1/2 z-0"></div>
              {steps.map((s) => {
                const isPassed = currentStep > s.num
                const isCurrent = currentStep === s.num
                return (
                  <div 
                    key={s.num} 
                    className="relative z-10 flex flex-col items-center cursor-pointer"
                    onClick={() => {
                      if (s.num < currentStep || isAlreadyOnboarded) {
                        setCurrentStep(s.num)
                      }
                    }}
                  >
                    <div 
                      className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                        isPassed 
                          ? 'bg-emerald-600 text-white shadow-sm' 
                          : isCurrent 
                            ? 'bg-brand-primary text-white ring-4 ring-brand-primary/20 font-extrabold shadow-sm' 
                            : 'bg-surface border border-border text-muted hover:border-brand-primary/50'
                      }`}
                    >
                      {isPassed ? <Check className="w-5 h-5" /> : s.num}
                    </div>
                    <span className={`text-xs mt-2 font-medium hidden sm:block ${
                      isCurrent 
                        ? 'text-brand-primary font-bold' 
                        : isPassed 
                          ? 'text-emerald-600 font-semibold' 
                          : 'text-muted'
                    }`}>
                      {s.label}
                    </span>
                    <span className={`text-xs mt-2 font-medium sm:hidden ${
                      isCurrent ? 'text-brand-primary font-bold' : 'text-muted'
                    }`}>
                      {s.short}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Already Onboarded Notice */}
          {isAlreadyOnboarded && (
            <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300 text-sm font-medium">
                <ShieldCheck className="w-5 h-5 shrink-0 text-emerald-600" />
                <span>Your account onboarding is complete. You can update your settings or return to Dashboard.</span>
              </div>
              <Link 
                href="/dashboard"
                className="text-sm font-bold text-emerald-700 dark:text-emerald-400 hover:underline flex items-center gap-1 shrink-0 ml-3"
              >
                Go to Dashboard <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-xl flex items-start gap-3 text-sm font-medium">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p>{error}</p>
            </div>
          )}

          {/* ======================================================== */}
          {/* STEP 1: BUSINESS INFORMATION                             */}
          {/* ======================================================== */}
          {currentStep === 1 && (
            <div className="bg-surface border border-border rounded-2xl shadow-soft p-6 sm:p-10 animate-in fade-in duration-300">
              {/* Authenticated Identity Badge */}
              <div className="mb-6 p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-brand-primary/10 text-brand-primary dark:text-brand-teal">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider text-muted">
                      Authenticated Account
                    </div>
                    <div className="text-sm font-mono font-medium text-foreground">
                      ID: <span className="font-bold text-brand-primary">{merchantId}</span>
                    </div>
                  </div>
                </div>
                {email && (
                  <div className="text-xs text-muted font-medium bg-surface px-3 py-1.5 rounded-lg border border-border">
                    {email}
                  </div>
                )}
              </div>

              <div className="mb-6">
                <h2 className="text-2xl font-bold text-foreground tracking-tight">Step 1: Business Information</h2>
                <p className="text-sm text-muted mt-1">
                  Confirm your personal and business details to set up your merchant profile.
                </p>
              </div>

              <form onSubmit={handleSaveBusiness} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-foreground mb-1.5">
                    Full Name <span className="text-brand-coral">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g., Alice Founder"
                    className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-brand-primary/50 text-sm transition-all"
                  />
                  <p className="text-xs text-muted mt-1">Primary owner or manager for this merchant account.</p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-foreground mb-1.5">
                    Business Name <span className="text-brand-coral">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="e.g., Acme Goods Co."
                    className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-brand-primary/50 text-sm transition-all"
                  />
                  <p className="text-xs text-muted mt-1">The brand or store name displayed on offers and campaigns.</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                  <div>
                    <label className="block text-sm font-semibold text-foreground mb-1.5">
                      Business Category
                    </label>
                    <select
                      value={businessCategory}
                      onChange={(e) => setBusinessCategory(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-brand-primary/50 text-sm transition-all"
                    >
                      <option value="E-commerce">E-commerce / Retail</option>
                      <option value="Apparel & Fashion">Apparel & Fashion</option>
                      <option value="Electronics">Consumer Electronics</option>
                      <option value="Beauty & Wellness">Beauty & Wellness</option>
                      <option value="Home & Living">Home & Living</option>
                      <option value="Food & Beverage">Food & Beverage</option>
                      <option value="SaaS & Digital">SaaS & Digital Products</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-foreground mb-1.5">
                      Description (Optional)
                    </label>
                    <input
                      type="text"
                      value={businessDescription}
                      onChange={(e) => setBusinessDescription(e.target.value)}
                      placeholder="e.g., Premium handcrafted essentials"
                      className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-brand-primary/50 text-sm transition-all"
                    />
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <button
                    type="submit"
                    disabled={businessLoading}
                    className="flex items-center gap-2 px-6 py-3 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl font-semibold text-sm shadow-sm transition-all disabled:opacity-50"
                  >
                    {businessLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Saving Business Info...</span>
                      </>
                    ) : (
                      <>
                        <span>Continue to Guardrail Rules</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ======================================================== */}
          {/* STEP 2: GUARDRAIL RULES                                  */}
          {/* ======================================================== */}
          {currentStep === 2 && (
            <div className="bg-surface border border-border rounded-2xl shadow-soft p-6 sm:p-10 animate-in fade-in duration-300">
              <div className="mb-6">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-primary/10 text-brand-primary text-xs font-bold uppercase tracking-wider mb-2">
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Merchant-Specific Economics</span>
                </div>
                <h2 className="text-2xl font-bold text-foreground tracking-tight">Step 2: Guardrail Rules</h2>
                <p className="text-sm text-muted mt-1">
                  Configure the business boundaries for your store. The AI engine will strictly enforce these rules across all campaigns and offers.
                </p>
              </div>

              <form onSubmit={handleSaveGuardrails} className="space-y-6">
                {/* Core Rule 1: Maximum Discount */}
                <div className="p-5 rounded-xl border border-border bg-background/50 hover:border-brand-primary/40 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <label className="text-sm font-bold text-foreground flex items-center gap-1.5">
                        <Percent className="w-4 h-4 text-brand-primary" />
                        Maximum Discount Percentage
                      </label>
                      <p className="text-xs text-muted mt-0.5">
                        AI will never offer discounts above this threshold to protect brand equity.
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={guardrails.max_discount_percentage}
                        onChange={(e) => setGuardrails({ ...guardrails, max_discount_percentage: e.target.value })}
                        className="w-20 px-3 py-1.5 rounded-lg border border-border bg-surface text-foreground font-bold text-right text-base focus:ring-2 focus:ring-brand-primary/50"
                      />
                      <span className="text-foreground font-bold text-sm">%</span>
                    </div>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={guardrails.max_discount_percentage || 0}
                    onChange={(e) => setGuardrails({ ...guardrails, max_discount_percentage: e.target.value })}
                    className="w-full accent-brand-primary cursor-pointer h-2 bg-slate-200 dark:bg-slate-700 rounded-lg mt-2"
                  />

                  <div className="flex justify-between items-center text-xs text-muted mt-2">
                    <span>Conservative (5-15%)</span>
                    <span>Standard (20-25%)</span>
                    <span>Aggressive (30-50%)</span>
                  </div>

                  {guardrailErrors.max_discount_percentage && (
                    <p className="text-xs font-semibold text-red-500 mt-2">{guardrailErrors.max_discount_percentage}</p>
                  )}
                </div>

                {/* Core Rule 2: Minimum Margin */}
                <div className="p-5 rounded-xl border border-border bg-background/50 hover:border-brand-primary/40 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <label className="text-sm font-bold text-foreground flex items-center gap-1.5">
                        <Target className="w-4 h-4 text-emerald-600" />
                        Minimum Margin Percentage
                      </label>
                      <p className="text-xs text-muted mt-0.5">
                        Every generated campaign will protect at least this gross profit margin after discounts.
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={guardrails.min_margin_percentage}
                        onChange={(e) => setGuardrails({ ...guardrails, min_margin_percentage: e.target.value })}
                        className="w-20 px-3 py-1.5 rounded-lg border border-border bg-surface text-foreground font-bold text-right text-base focus:ring-2 focus:ring-brand-primary/50"
                      />
                      <span className="text-foreground font-bold text-sm">%</span>
                    </div>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={guardrails.min_margin_percentage || 0}
                    onChange={(e) => setGuardrails({ ...guardrails, min_margin_percentage: e.target.value })}
                    className="w-full accent-emerald-600 cursor-pointer h-2 bg-slate-200 dark:bg-slate-700 rounded-lg mt-2"
                  />

                  <div className="flex justify-between items-center text-xs text-muted mt-2">
                    <span>10% Low Margin</span>
                    <span>25-30% Recommended</span>
                    <span>50%+ High Margin</span>
                  </div>

                  {guardrailErrors.min_margin_percentage && (
                    <p className="text-xs font-semibold text-red-500 mt-2">{guardrailErrors.min_margin_percentage}</p>
                  )}
                </div>

                {/* Advanced Guardrails Accordion */}
                <div className="border border-border rounded-xl overflow-hidden bg-background/30">
                  <button
                    type="button"
                    onClick={() => setShowAdvancedGuardrails(!showAdvancedGuardrails)}
                    className="w-full p-4 flex items-center justify-between text-left hover:bg-surface/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-muted" />
                      <span className="text-sm font-semibold text-foreground">Advanced Business Constraints</span>
                      <span className="text-xs text-muted">(Optional)</span>
                    </div>
                    {showAdvancedGuardrails ? (
                      <ChevronUp className="w-4 h-4 text-muted" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-muted" />
                    )}
                  </button>

                  {showAdvancedGuardrails && (
                    <div className="p-4 pt-0 space-y-4 border-t border-border mt-2">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-foreground mb-1">
                            Minimum Order Value (₹)
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={guardrails.min_order_value}
                            onChange={(e) => setGuardrails({ ...guardrails, min_order_value: e.target.value })}
                            className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-foreground text-sm"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-foreground mb-1">
                            Max Campaign Budget (₹)
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={guardrails.max_campaign_budget || ''}
                            onChange={(e) => setGuardrails({ ...guardrails, max_campaign_budget: e.target.value })}
                            placeholder="e.g., 50000"
                            className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-foreground text-sm"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-foreground mb-1">
                            Contact Frequency (Days between touches)
                          </label>
                          <input
                            type="number"
                            min="1"
                            value={guardrails.contact_frequency_days || ''}
                            onChange={(e) => setGuardrails({ ...guardrails, contact_frequency_days: e.target.value })}
                            className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-foreground text-sm"
                          />
                        </div>

                        <div className="flex flex-col justify-end space-y-2">
                          <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground">
                            <input
                              type="checkbox"
                              checked={guardrails.free_shipping_allowed}
                              onChange={(e) => setGuardrails({ ...guardrails, free_shipping_allowed: e.target.checked })}
                              className="rounded border-border text-brand-primary focus:ring-brand-primary"
                            />
                            <span>Allow Free Shipping Offers</span>
                          </label>

                          <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground">
                            <input
                              type="checkbox"
                              checked={guardrails.high_value_customer_protection}
                              onChange={(e) => setGuardrails({ ...guardrails, high_value_customer_protection: e.target.checked })}
                              className="rounded border-border text-brand-primary focus:ring-brand-primary"
                            />
                            <span>Protect High-Value Customers from Heavy Discounts</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="pt-4 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(1)}
                    className="flex items-center gap-1.5 px-4 py-2.5 text-muted hover:text-foreground text-sm font-medium transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back to Business Info</span>
                  </button>

                  <button
                    type="submit"
                    disabled={guardrailsLoading}
                    className="flex items-center gap-2 px-6 py-3 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl font-semibold text-sm shadow-sm transition-all disabled:opacity-50"
                  >
                    {guardrailsLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Saving Guardrails...</span>
                      </>
                    ) : (
                      <>
                        <span>Save & Continue to Customer Data</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ======================================================== */}
          {/* STEP 3: CUSTOMER DATA UPLOAD                             */}
          {/* ======================================================== */}
          {currentStep === 3 && (
            <div className="bg-surface border border-border rounded-2xl shadow-soft p-6 sm:p-10 animate-in fade-in duration-300">
              <div className="mb-6">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-primary/10 text-brand-primary text-xs font-bold uppercase tracking-wider mb-2">
                  <Database className="w-3.5 h-3.5" />
                  <span>Customer Intelligence</span>
                </div>
                <h2 className="text-2xl font-bold text-foreground tracking-tight">Step 3: Customer Data</h2>
                <p className="text-sm text-muted mt-1">
                  Upload customer transaction history to calculate metrics, discover segments, and power AI revenue campaigns.
                </p>
              </div>

              {/* Merchant Isolation Notice */}
              <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800/50 rounded-xl flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                <div className="text-xs text-blue-900 dark:text-blue-200 leading-relaxed">
                  All customer records are strictly isolated under your merchant account (<span className="font-mono font-bold">{merchantId}</span>). No cross-merchant access is permitted.
                </div>
              </div>

              {/* Success Banners */}
              {uploadSuccess && (
                <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center gap-3 animate-in fade-in">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div className="text-sm font-medium text-emerald-900 dark:text-emerald-200">
                    Successfully imported <strong>{uploadSuccess.imported}</strong> customers into {uploadSuccess.segments} segments! Redirecting to Dashboard...
                  </div>
                </div>
              )}

              {demoSuccess && (
                <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center gap-3 animate-in fade-in">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div className="text-sm font-medium text-emerald-900 dark:text-emerald-200">
                    Demo dataset loaded successfully! Redirecting to Dashboard...
                  </div>
                </div>
              )}

              {/* Mode Selection Tabs */}
              <div className="mb-8">
                <div className="text-xs font-bold uppercase tracking-wider text-muted mb-3">Choose Dataset Format</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setUploadMode('multiple')
                      setCsvPreview(null)
                      setError(null)
                    }}
                    className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                      uploadMode === 'multiple'
                        ? 'border-brand-primary bg-brand-primary/5 ring-2 ring-brand-primary/20 shadow-sm'
                        : 'border-border bg-background/50 hover:bg-surface hover:border-border/80'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Layers className={`w-4 h-4 ${uploadMode === 'multiple' ? 'text-brand-primary' : 'text-muted'}`} />
                        <span className="text-sm font-bold text-foreground">Mode B: Relational Datasets</span>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-primary/10 text-brand-primary">
                        Recommended for Olist
                      </span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Upload 3 separate relational files: Customers, Orders, and Order Items. Automatically joined via customer and order IDs.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUploadMode('single')
                      setCsvPreview(null)
                      setError(null)
                    }}
                    className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                      uploadMode === 'single'
                        ? 'border-brand-primary bg-brand-primary/5 ring-2 ring-brand-primary/20 shadow-sm'
                        : 'border-border bg-background/50 hover:bg-surface hover:border-border/80'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className={`w-4 h-4 ${uploadMode === 'single' ? 'text-brand-primary' : 'text-muted'}`} />
                        <span className="text-sm font-bold text-foreground">Mode A: Single Transaction CSV</span>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface border border-border text-muted">
                        Flat Table
                      </span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Upload one combined CSV file containing customer IDs, invoice/order IDs, purchase dates, and monetary amounts.
                    </p>
                  </button>
                </div>
              </div>

              {/* MODE B: 3-FILE RELATIONAL UPLOAD */}
              {uploadMode === 'multiple' && (
                <div className="space-y-6">
                  <div className="p-4 rounded-xl bg-background/60 border border-border">
                    <div className="flex items-center gap-2 mb-1">
                      <Info className="w-4 h-4 text-brand-primary" />
                      <span className="text-xs font-bold text-foreground">Relational Dataset Requirements</span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Select all three CSV files from the Olist E-Commerce dataset (or similar relational store schema). The engine joins <code className="text-brand-primary font-mono font-bold">customer_id</code> and <code className="text-brand-primary font-mono font-bold">order_id</code> to calculate lifetime value, purchase count, average order value, and recency.
                    </p>
                  </div>

                  {/* 3 Upload Cards Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Card 1: Customers CSV */}
                    <div className={`p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                      customersFile ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-border bg-background/50'
                    }`}>
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="w-9 h-9 rounded-xl bg-brand-primary/10 text-brand-primary flex items-center justify-center">
                            <Users className="w-4 h-4" />
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            customersFile 
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300' 
                              : 'bg-surface border border-border text-muted'
                          }`}>
                            {customersFile ? '✓ Selected' : 'Required'}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-foreground mb-1">1. Customers Data</h3>
                        <p className="text-xs text-muted mb-2">
                          Demographic records containing <code className="font-mono text-foreground font-semibold">customer_id</code>.
                        </p>
                        <div className="text-[11px] text-muted italic mb-4">
                          e.g., olist_customers_dataset.csv
                        </div>
                      </div>

                      <div>
                        {customersFile ? (
                          <div className="p-2.5 rounded-xl bg-surface border border-border flex items-center justify-between gap-2">
                            <div className="truncate">
                              <div className="text-xs font-bold text-foreground truncate">{customersFile.name}</div>
                              <div className="text-[10px] text-muted">{(customersFile.size / 1024).toFixed(1)} KB</div>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setCustomersFile(null)
                                setCsvPreview(null)
                              }}
                              className="p-1 rounded-lg text-muted hover:text-red-500 transition-colors"
                              title="Remove file"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <label className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-dashed border-brand-primary/40 bg-brand-primary/5 hover:bg-brand-primary/10 text-brand-primary text-xs font-bold cursor-pointer transition-colors text-center">
                            <UploadCloud className="w-4 h-4" />
                            <span>Select Customers CSV</span>
                            <input
                              type="file"
                              accept=".csv"
                              onChange={handleCustomersFileChange}
                              className="hidden"
                            />
                          </label>
                        )}
                      </div>
                    </div>

                    {/* Card 2: Orders CSV */}
                    <div className={`p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                      ordersFile ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-border bg-background/50'
                    }`}>
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="w-9 h-9 rounded-xl bg-brand-teal/10 text-brand-teal flex items-center justify-center">
                            <ShoppingBag className="w-4 h-4" />
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            ordersFile 
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300' 
                              : 'bg-surface border border-border text-muted'
                          }`}>
                            {ordersFile ? '✓ Selected' : 'Required'}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-foreground mb-1">2. Orders Data</h3>
                        <p className="text-xs text-muted mb-2">
                          Order timestamps linking <code className="font-mono text-foreground font-semibold">order_id</code> and <code className="font-mono text-foreground font-semibold">customer_id</code>.
                        </p>
                        <div className="text-[11px] text-muted italic mb-4">
                          e.g., olist_orders_dataset.csv
                        </div>
                      </div>

                      <div>
                        {ordersFile ? (
                          <div className="p-2.5 rounded-xl bg-surface border border-border flex items-center justify-between gap-2">
                            <div className="truncate">
                              <div className="text-xs font-bold text-foreground truncate">{ordersFile.name}</div>
                              <div className="text-[10px] text-muted">{(ordersFile.size / 1024).toFixed(1)} KB</div>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setOrdersFile(null)
                                setCsvPreview(null)
                              }}
                              className="p-1 rounded-lg text-muted hover:text-red-500 transition-colors"
                              title="Remove file"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <label className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-dashed border-brand-teal/40 bg-brand-teal/5 hover:bg-brand-teal/10 text-brand-teal text-xs font-bold cursor-pointer transition-colors text-center">
                            <UploadCloud className="w-4 h-4" />
                            <span>Select Orders CSV</span>
                            <input
                              type="file"
                              accept=".csv"
                              onChange={handleOrdersFileChange}
                              className="hidden"
                            />
                          </label>
                        )}
                      </div>
                    </div>

                    {/* Card 3: Order Items CSV */}
                    <div className={`p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                      orderItemsFile ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-border bg-background/50'
                    }`}>
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="w-9 h-9 rounded-xl bg-brand-coral/10 text-brand-coral flex items-center justify-center">
                            <PackageCheck className="w-4 h-4" />
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            orderItemsFile 
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300' 
                              : 'bg-surface border border-border text-muted'
                          }`}>
                            {orderItemsFile ? '✓ Selected' : 'Required'}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-foreground mb-1">3. Order Items Data</h3>
                        <p className="text-xs text-muted mb-2">
                          Item prices and values with <code className="font-mono text-foreground font-semibold">order_id</code> and <code className="font-mono text-foreground font-semibold">price</code>.
                        </p>
                        <div className="text-[11px] text-muted italic mb-4">
                          e.g., olist_order_items_dataset.csv
                        </div>
                      </div>

                      <div>
                        {orderItemsFile ? (
                          <div className="p-2.5 rounded-xl bg-surface border border-border flex items-center justify-between gap-2">
                            <div className="truncate">
                              <div className="text-xs font-bold text-foreground truncate">{orderItemsFile.name}</div>
                              <div className="text-[10px] text-muted">{(orderItemsFile.size / 1024).toFixed(1)} KB</div>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setOrderItemsFile(null)
                                setCsvPreview(null)
                              }}
                              className="p-1 rounded-lg text-muted hover:text-red-500 transition-colors"
                              title="Remove file"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <label className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-dashed border-brand-coral/40 bg-brand-coral/5 hover:bg-brand-coral/10 text-brand-coral text-xs font-bold cursor-pointer transition-colors text-center">
                            <UploadCloud className="w-4 h-4" />
                            <span>Select Order Items CSV</span>
                            <input
                              type="file"
                              accept=".csv"
                              onChange={handleOrderItemsFileChange}
                              className="hidden"
                            />
                          </label>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Multi-file status & process trigger */}
                  <div className="p-4 rounded-xl bg-surface border border-border flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3 text-xs text-muted">
                      <span className="font-semibold text-foreground">Required Files:</span>
                      <span className={`inline-flex items-center gap-1 ${customersFile ? 'text-emerald-600 font-bold' : 'text-muted'}`}>
                        {customersFile ? '✓' : '○'} Customers
                      </span>
                      <span>•</span>
                      <span className={`inline-flex items-center gap-1 ${ordersFile ? 'text-emerald-600 font-bold' : 'text-muted'}`}>
                        {ordersFile ? '✓' : '○'} Orders
                      </span>
                      <span>•</span>
                      <span className={`inline-flex items-center gap-1 ${orderItemsFile ? 'text-emerald-600 font-bold' : 'text-muted'}`}>
                        {orderItemsFile ? '✓' : '○'} Order Items
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={handleProcessData}
                      disabled={validatingCsv || !customersFile || !ordersFile || !orderItemsFile}
                      className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl font-bold text-xs shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {validatingCsv ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Joining Datasets & Calculating Metrics...</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          <span>Process Related Datasets</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* MODE A: SINGLE TRANSACTION CSV UPLOAD */}
              {uploadMode === 'single' && (
                <div className="space-y-6">
                  <div className="p-6 rounded-2xl border-2 border-dashed border-border hover:border-brand-primary/50 transition-colors bg-background/50 text-center">
                    <input
                      type="file"
                      id="singleCsvUpload"
                      accept=".csv"
                      onChange={handleSingleFileChange}
                      className="hidden"
                    />
                    <label htmlFor="singleCsvUpload" className="cursor-pointer flex flex-col items-center">
                      <div className="w-12 h-12 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary mb-3">
                        <UploadCloud className="w-6 h-6" />
                      </div>
                      <span className="text-sm font-bold text-foreground mb-1">
                        {singleFile ? singleFile.name : "Choose or drag & drop a single Transaction CSV file"}
                      </span>
                      <span className="text-xs text-muted">
                        {singleFile ? `${(singleFile.size / 1024).toFixed(1)} KB selected` : "Supports transactional or customer-summary CSV files"}
                      </span>
                    </label>
                  </div>

                  {/* CSV Format Helper Toggle */}
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => setShowCsvGuide(!showCsvGuide)}
                      className="text-xs text-brand-primary font-semibold hover:underline inline-flex items-center gap-1"
                    >
                      <Info className="w-3.5 h-3.5" />
                      <span>{showCsvGuide ? "Hide CSV schema guide" : "View supported single CSV columns & auto-mapping"}</span>
                    </button>

                    {showCsvGuide && (
                      <div className="mt-3 p-4 rounded-xl bg-surface border border-border text-left text-xs text-muted space-y-2">
                        <p className="font-semibold text-foreground">Auto-Detected Columns (Transactional or Summary):</p>
                        <ul className="list-disc list-inside space-y-1">
                          <li><code className="text-brand-primary font-mono font-bold">Customer ID</code>: customer_id, CustomerID, id, cust_id, client_id</li>
                          <li><code className="font-mono font-bold">Orders / Invoices</code>: InvoiceNo, invoice_id, order_id, transaction_id</li>
                          <li><code className="font-mono font-bold">Dates</code>: InvoiceDate, purchase_date, date, order_purchase_timestamp</li>
                          <li><code className="font-mono font-bold">Price & Quantity</code>: UnitPrice, price, unit_price AND Quantity, qty</li>
                          <li><code className="font-mono font-bold">Revenue / Total</code>: Amount, revenue, total, payment_value</li>
                          <li><code className="font-mono font-bold">Pre-calculated</code>: purchase_count, lifetime_value, days_since_last_purchase</li>
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={handleProcessData}
                      disabled={validatingCsv || !singleFile}
                      className="flex items-center gap-2 px-6 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl font-bold text-xs shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {validatingCsv ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Analyzing Columns & Grouping Transactions...</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          <span>Process Transaction Data</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* DATASET VALIDATION & PROCESSING PREVIEW CARD */}
              {csvPreview && (
                <div className="mt-8 space-y-6 p-6 rounded-2xl bg-surface border border-border shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-4">
                    <div>
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs font-bold uppercase mb-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Processing Succeeded ({csvPreview.dataset_type})</span>
                      </div>
                      <h3 className="text-lg font-bold text-foreground">Dataset Behavioral Preview</h3>
                    </div>
                    {csvPreview.filenames ? (
                      <div className="text-[11px] text-muted space-x-2">
                        <span>{csvPreview.filenames.customers}</span>
                        <span>•</span>
                        <span>{csvPreview.filenames.orders}</span>
                        <span>•</span>
                        <span>{csvPreview.filenames.order_items}</span>
                      </div>
                    ) : (
                      <span className="text-xs font-medium text-muted">{csvPreview.filename}</span>
                    )}
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-3.5 rounded-xl bg-background border border-border">
                      <div className="text-xs text-muted font-medium">Customer Rows</div>
                      <div className="text-xl font-extrabold text-foreground mt-0.5">
                        {(csvPreview.total_customer_rows ?? csvPreview.total_rows_detected ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3.5 rounded-xl bg-background border border-border">
                      <div className="text-xs text-muted font-medium">Unique Customers</div>
                      <div className="text-xl font-extrabold text-brand-primary mt-0.5">
                        {csvPreview.total_unique_customers.toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3.5 rounded-xl bg-background border border-border">
                      <div className="text-xs text-muted font-medium">
                        {csvPreview.total_orders !== undefined ? 'Total Orders' : 'Total Transactions'}
                      </div>
                      <div className="text-xl font-extrabold text-brand-teal mt-0.5">
                        {(csvPreview.total_orders ?? csvPreview.total_transactions ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3.5 rounded-xl bg-background border border-border">
                      <div className="text-xs text-muted font-medium">
                        {csvPreview.matched_customers_count !== undefined ? 'Active Buyers' : 'Invalid Rows'}
                      </div>
                      <div className="text-xl font-extrabold text-emerald-600 mt-0.5">
                        {(csvPreview.matched_customers_count ?? csvPreview.invalid_rows_count ?? 0).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {/* Relational specific statistics */}
                  {csvPreview.total_order_items !== undefined && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="p-3.5 rounded-xl bg-background border border-border flex items-center justify-between">
                        <span className="text-xs text-muted">Total Order Items Joined:</span>
                        <span className="text-sm font-bold text-foreground">{csvPreview.total_order_items.toLocaleString()} items</span>
                      </div>
                      <div className="p-3.5 rounded-xl bg-background border border-border flex items-center justify-between">
                        <span className="text-xs text-muted">Customers without Orders:</span>
                        <span className="text-sm font-bold text-amber-600">{csvPreview.unmatched_customers_count.toLocaleString()} (segmented as inactive)</span>
                      </div>
                    </div>
                  )}

                  {/* Segment Distribution Badges */}
                  {csvPreview.segment_distribution && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted mb-2">Calculated Customer Segments</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(csvPreview.segment_distribution).map(([seg, count]) => (
                          <span key={seg} className="inline-flex items-center gap-1.5 px-3 py-1 bg-brand-primary/10 text-brand-primary border border-brand-primary/20 rounded-xl text-xs font-bold uppercase tracking-wide">
                            <span>{seg.replace('_', ' ')}:</span>
                            <span>{count.toLocaleString()}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Preview Table */}
                  {csvPreview.preview && csvPreview.preview.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted mb-2">
                        Customer Records Preview ({csvPreview.preview.length} Sample Profiles)
                      </h4>
                      <div className="overflow-x-auto border border-border rounded-xl">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-background border-b border-border text-muted font-semibold">
                              <th className="p-2.5">Customer ID</th>
                              <th className="p-2.5 text-right">Purchases</th>
                              <th className="p-2.5 text-right">Lifetime Value</th>
                              <th className="p-2.5 text-right">Avg Order</th>
                              <th className="p-2.5 text-right">Days Since Last</th>
                              <th className="p-2.5 text-center">Segment</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/60">
                            {csvPreview.preview.map((c, i) => (
                              <tr key={i} className="hover:bg-background/50">
                                <td className="p-2.5 font-mono font-medium">
                                  {c.customer_id.length > 18 ? `${c.customer_id.slice(0, 12)}...` : c.customer_id}
                                </td>
                                <td className="p-2.5 text-right font-semibold">{c.purchase_count}</td>
                                <td className="p-2.5 text-right font-semibold">₹{c.lifetime_value.toLocaleString()}</td>
                                <td className="p-2.5 text-right font-medium">₹{c.average_order_value.toLocaleString()}</td>
                                <td className="p-2.5 text-right text-muted">{c.days_since_last_purchase}d</td>
                                <td className="p-2.5 text-center">
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-brand-primary/10 text-brand-primary border border-brand-primary/20">
                                    {c.segment}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Database Import Mode Option */}
                  <div className="p-4 rounded-xl bg-background border border-border">
                    <div className="text-xs font-bold uppercase tracking-wider text-muted mb-2">Database Import Strategy</div>
                    <div className="flex flex-col sm:flex-row gap-4">
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground">
                        <input
                          type="radio"
                          name="importMode"
                          value="replace"
                          checked={importMode === 'replace'}
                          onChange={() => setImportMode('replace')}
                          className="text-brand-primary focus:ring-brand-primary"
                        />
                        <span>Replace existing records for this merchant (Recommended)</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground">
                        <input
                          type="radio"
                          name="importMode"
                          value="append"
                          checked={importMode === 'append'}
                          onChange={() => setImportMode('append')}
                          className="text-brand-primary focus:ring-brand-primary"
                        />
                        <span>Append / Update existing customer records</span>
                      </label>
                    </div>
                  </div>

                  {/* Confirm & Import Button */}
                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={handleConfirmImport}
                      disabled={uploadLoading}
                      className="flex items-center gap-2 px-8 py-3 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl font-bold text-sm shadow-md transition-all disabled:opacity-50"
                    >
                      {uploadLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Importing & Finalizing Onboarding...</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          <span>Confirm & Import Dataset ({csvPreview.total_unique_customers.toLocaleString()} Customers)</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Alternative: Demo Data */}
              <div className="mt-8 pt-6 border-t border-border">
                <div className="p-5 rounded-xl border border-border bg-background/50 hover:border-brand-primary/30 transition-all flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="w-4 h-4 text-brand-coral" />
                      <h3 className="text-sm font-bold text-foreground">Explore with Demo Data</h3>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">
                      Don't have your CSV files right now? Load a pre-segmented sample dataset to evaluate AI recommendations instantly.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleUseDemo}
                    disabled={demoLoading || uploadLoading}
                    className="shrink-0 flex items-center justify-center gap-2 px-5 py-2.5 border border-border bg-surface hover:bg-surface/80 text-foreground rounded-xl text-xs font-bold transition-all disabled:opacity-50"
                  >
                    {demoLoading ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Setting up Demo Data...</span>
                      </>
                    ) : (
                      <>
                        <Database className="w-3.5 h-3.5 text-brand-primary" />
                        <span>Load Demo Dataset</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Back to Guardrails */}
              <div className="mt-6 flex items-center justify-start">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-muted hover:text-foreground text-sm font-medium transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Guardrails</span>
                </button>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}

export default function Onboarding() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
          <p className="text-sm font-medium text-muted">Loading merchant onboarding...</p>
        </div>
      </div>
    }>
      <OnboardingContent />
    </Suspense>
  )
}

