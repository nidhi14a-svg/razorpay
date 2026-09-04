'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { UploadCloud, CheckCircle2, AlertCircle, Loader2, Database, HelpCircle, RefreshCcw } from 'lucide-react'
import Link from 'next/link'

export default function Onboarding() {
  const router = useRouter()
  const [file, setFile] = useState(null)
  
  // Loading states
  const [uploadLoading, setUploadLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)
  
  const [error, setError] = useState(null)
  
  // Success states
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [demoSuccess, setDemoSuccess] = useState(false)
  const [demoStats, setDemoStats] = useState(null)
  
  const [showHelp, setShowHelp] = useState(false)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (!selectedFile.name.endsWith('.csv')) {
        setError('Please upload a valid CSV file.')
        setFile(null)
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploadLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)
    
    const merchantId = localStorage.getItem('merchantId') || 'onboarded_merchant_' + Math.floor(Math.random() * 1000)
    formData.append('merchant_id', merchantId)

    try {
      const response = await fetch('http://localhost:8000/customers/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to upload dataset')
      }

      setUploadSuccess(true)
      localStorage.setItem('merchantId', merchantId)
      localStorage.setItem('businessName', 'My Business')
      
      setTimeout(() => {
        router.push('/dashboard')
      }, 1500)
      
    } catch (err) {
      if (err instanceof TypeError || (err.message && (err.message.toLowerCase().includes('fetch') || err.message.toLowerCase().includes('network')))) {
        setError('Could not connect to the backend. Make sure the FastAPI server is running.');
      } else {
        setError(err.message || 'An unknown error occurred');
      }
    } finally {
      setUploadLoading(false)
    }
  }

  const handleUseDemo = async () => {
    setDemoLoading(true)
    setError(null)
    setDemoSuccess(false)
    setDemoStats(null)

    try {
      const response = await fetch('http://localhost:8000/customers/demo', {
        method: 'POST'
      })
      
      let data;
      try {
        data = await response.json()
      } catch (e) {
        throw new Error('Could not connect to the backend. Make sure the FastAPI server is running.')
      }

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load demo data')
      }
      
      localStorage.setItem('merchantId', 'demo_merchant_001')
      localStorage.setItem('businessName', 'Summer Store (Demo)')
      
      setDemoStats({
        customers: data.customers_count,
        segments: data.segments_count
      })
      setDemoSuccess(true)
      
      setTimeout(() => {
        router.push('/dashboard')
      }, 2500)
      
    } catch (err) {
      if (err instanceof TypeError || (err.message && (err.message.toLowerCase().includes('fetch') || err.message.toLowerCase().includes('network')))) {
        setError('Could not connect to the backend. Make sure the FastAPI server is running.');
      } else {
        setError(err.message || 'An unknown error occurred');
      }
    } finally {
      setDemoLoading(false)
    }
  }

  const handleResetDemo = async () => {
    setResetLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/customers/demo/reset', {
        method: 'POST'
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to reset demo data')
      }
      
      setDemoSuccess(false)
      setDemoStats(null)
      alert("Demo data successfully reset.")
    } catch (err) {
      if (err instanceof TypeError || (err.message && (err.message.toLowerCase().includes('fetch') || err.message.toLowerCase().includes('network')))) {
        setError('Could not connect to the backend. Make sure the FastAPI server is running.');
      } else {
        setError(err.message || 'An unknown error occurred');
      }
    } finally {
      setResetLoading(false)
    }
  }

  const isLoading = uploadLoading || demoLoading || resetLoading;
  const isSuccess = uploadSuccess || demoSuccess;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center py-20 px-4">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-foreground mb-3">Upload Customer Dataset</h1>
          <p className="text-muted">
            Upload your customer data so RAZZZ can understand behavior, identify segments and generate personalized campaign strategies.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-2xl shadow-sm p-8 mb-6 relative">
          
          {/* File Dropzone */}
          <div 
            className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
              file ? 'border-brand-teal bg-brand-mint/10' : 'border-gray-300 dark:border-gray-700 hover:border-brand-primary hover:bg-gray-50 dark:hover:bg-gray-800/50'
            }`}
          >
            {file ? (
              <div className="flex flex-col items-center justify-center">
                <CheckCircle2 className="w-12 h-12 text-brand-teal mb-3" />
                <p className="font-semibold text-foreground">{file.name}</p>
                <p className="text-sm text-muted mt-1 mb-4">{(file.size / 1024).toFixed(1)} KB</p>
                <button 
                  onClick={() => setFile(null)}
                  className="text-sm text-brand-coral hover:underline"
                  disabled={isLoading || isSuccess}
                >
                  Remove and select another file
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center">
                <UploadCloud className="w-12 h-12 text-muted mb-4" />
                <p className="text-foreground font-medium mb-1">Drag & drop your CSV file here</p>
                <p className="text-muted text-sm mb-4">or</p>
                <label className="bg-brand-primary hover:bg-brand-teal text-white px-5 py-2.5 rounded-lg cursor-pointer transition-colors text-sm font-medium shadow-sm">
                  Browse Files
                  <input 
                    type="file" 
                    accept=".csv" 
                    className="hidden" 
                    onChange={handleFileChange}
                    disabled={isLoading || isSuccess}
                  />
                </label>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-5 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-xl flex items-start gap-3 text-sm font-medium">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p>{error}</p>
            </div>
          )}

          {uploadSuccess && (
            <div className="mt-5 p-4 bg-brand-mint/50 dark:bg-brand-mint/20 border border-brand-teal/30 text-brand-primary dark:text-brand-teal rounded-xl flex items-center justify-center gap-3 font-bold text-lg">
              <CheckCircle2 className="w-6 h-6" />
              Data Successfully Imported! Redirecting...
            </div>
          )}

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="text-sm text-muted hover:text-foreground flex items-center gap-1.5 transition-colors font-medium"
            >
              <HelpCircle className="w-4 h-4" />
              What data should my CSV contain?
            </button>
            <button
              onClick={handleUpload}
              disabled={!file || isLoading || isSuccess}
              className={`w-full sm:w-auto px-6 py-3 rounded-xl font-bold transition-all shadow-sm flex items-center justify-center gap-2 ${
                !file || isLoading || isSuccess 
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed shadow-none' 
                  : 'bg-brand-primary hover:bg-brand-teal text-white hover:shadow-md'
              }`}
            >
              {uploadLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
              {uploadLoading ? 'Uploading & Analyzing...' : 'Import Customers'}
            </button>
          </div>

          {showHelp && (
            <div className="mt-6 p-5 bg-gray-50 dark:bg-gray-900/30 rounded-xl border border-border text-sm">
              <h4 className="font-bold text-foreground mb-2">Expected CSV format:</h4>
              <p className="text-muted mb-4">Your CSV should ideally contain headers matching these names (missing ones will default to 0/empty):</p>
              <ul className="list-disc pl-5 space-y-2 text-muted/80 font-mono text-xs">
                <li><strong className="text-brand-primary font-bold">name</strong> - Customer Name</li>
                <li><strong className="text-brand-primary font-bold">email</strong> - Email address</li>
                <li><strong className="text-brand-primary font-bold">purchase_count</strong> - Total historical orders (e.g., 5)</li>
                <li><strong className="text-brand-primary font-bold">days_since_last_purchase</strong> - Days since last order</li>
                <li><strong className="text-brand-primary font-bold">lifetime_value</strong> - Total revenue from customer</li>
                <li><strong className="text-brand-primary font-bold">cart_status</strong> - "abandoned" or "browsing" or empty</li>
              </ul>
            </div>
          )}
        </div>

        {/* Demo Fallback */}
        <div className="text-center bg-surface/50 border border-border rounded-2xl p-8 shadow-sm">
          <div className="mb-6">
            <h3 className="text-lg font-bold text-foreground mb-2">Want to test the platform first?</h3>
            <p className="text-muted text-sm">Generate a realistic synthetic dataset with diverse customer behaviors to see how the AI Revenue Agent operates.</p>
          </div>
          
          <div className="flex flex-col items-center justify-center gap-4">
            <button 
              onClick={handleUseDemo}
              disabled={isLoading || isSuccess}
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-background border-2 border-border hover:border-brand-primary/50 text-foreground rounded-xl transition-all font-bold shadow-sm hover:shadow-md disabled:opacity-50"
            >
              {demoLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-brand-teal" />
                  Preparing your demo workspace...
                </>
              ) : (
                <>
                  <Database className="w-5 h-5 text-brand-coral" />
                  Generate & Use Demo Dataset
                </>
              )}
            </button>
            
            <button 
              onClick={handleResetDemo}
              disabled={isLoading || isSuccess}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-brand-coral transition-colors disabled:opacity-50"
            >
              <RefreshCcw className="w-3.5 h-3.5" />
              Reset Demo Data
            </button>
          </div>
          
          {demoSuccess && demoStats && (
             <div className="mt-6 p-5 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800/30 rounded-xl text-left animate-in zoom-in duration-300">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-500 font-bold text-lg mb-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Demo data loaded successfully
                </div>
                <ul className="text-sm text-green-800/80 dark:text-green-400/80 space-y-1 ml-7 font-medium">
                  <li>• {demoStats.customers} customers imported</li>
                  <li>• {demoStats.segments} customer segments identified</li>
                </ul>
                <div className="mt-4 text-center">
                  <p className="text-sm text-green-700 dark:text-green-500 font-bold animate-pulse">Navigating to Dashboard...</p>
                </div>
             </div>
          )}
        </div>

      </div>
    </div>
  )
}
