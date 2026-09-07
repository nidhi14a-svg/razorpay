'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Eye, EyeOff, Mail, Lock, ShieldCheck, ArrowRight } from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [requiresVerification, setRequiresVerification] = useState(false)
  const [resendStatus, setResendStatus] = useState('')
  
  const router = useRouter()

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setRequiresVerification(false)
    setResendStatus('')

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (response.ok) {
        if (data.requires_verification) {
          setRequiresVerification(true)
          setError(data.detail)
        } else {
          localStorage.setItem('merchantId', data.merchant_id)
          if (data.business_name) localStorage.setItem('businessName', data.business_name)
          if (data.full_name) localStorage.setItem('fullName', data.full_name)
          if (data.email) localStorage.setItem('email', data.email)
          if (data.token) {
            localStorage.setItem('token', data.token)
          }
          if (data.onboarding_completed) {
            localStorage.setItem('onboardingCompleted', 'true')
            router.push('/dashboard')
          } else {
            localStorage.setItem('onboardingCompleted', 'false')
            router.push('/onboarding')
          }
        }
      } else {
        setError(data.detail || 'Login failed')
      }
    } catch (error) {
      setError('Error: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleResendVerification = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/auth/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await response.json()
      if (response.ok) {
        setResendStatus("Verification email sent! Check your inbox.")
      } else {
        setError(data.detail || "Failed to resend verification")
      }
    } catch (err) {
      setError("Error: " + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex">
      {/* Left side: Login form */}
      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:flex-none lg:w-1/2 xl:px-24">
        <div className="mx-auto w-full max-w-sm lg:w-96">
          <div className="flex items-center gap-2 mb-8">
            <div className="w-10 h-10 bg-brand-primary rounded-xl flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-xl">R</span>
            </div>
            <h1 className="text-3xl font-extrabold text-foreground tracking-tight">RAZZZ</h1>
          </div>
          
          <h2 className="text-3xl font-bold text-foreground tracking-tight mb-2">
            Welcome back
          </h2>
          <p className="text-muted text-sm mb-8">
            Automate revenue campaigns and grow your business with AI.
          </p>

          <form className="space-y-6" onSubmit={handleLogin}>
            
            {error && (
              <div className={`p-4 rounded-xl text-sm border flex flex-col gap-3 ${requiresVerification ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-red-50 border-red-200 text-red-700'}`}>
                <div>{error}</div>
                {requiresVerification && (
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={loading}
                    className="inline-flex items-center justify-center px-4 py-2 border border-amber-300 shadow-sm text-sm font-bold rounded-lg text-amber-700 bg-white hover:bg-amber-50 focus:outline-none"
                  >
                    <Mail className="w-4 h-4 mr-2" />
                    Resend Verification Email
                  </button>
                )}
              </div>
            )}
            
            {resendStatus && (
              <div className="p-4 rounded-xl text-sm border bg-brand-mint/20 border-brand-mint/50 text-brand-teal flex items-center gap-2 font-medium">
                <ShieldCheck className="w-4 h-4 text-brand-teal" />
                {resendStatus}
              </div>
            )}

            <div>
              <label className="block text-sm font-bold text-foreground mb-2">Email address</label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-muted" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-11 pr-4 py-3 bg-background border border-border rounded-xl focus:ring-2 focus:ring-brand-primary/50 focus:border-transparent transition-shadow text-foreground placeholder:text-muted"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-foreground mb-2">Password</label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-muted" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-11 pr-10 py-3 bg-background border border-border rounded-xl focus:ring-2 focus:ring-brand-primary/50 focus:border-transparent transition-shadow text-foreground placeholder:text-muted"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-muted hover:text-foreground transition-colors" />
                  ) : (
                    <Eye className="h-5 w-5 text-muted hover:text-foreground transition-colors" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-brand-primary focus:ring-brand-primary border-border rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm font-medium text-foreground">
                  Remember me
                </label>
              </div>

              <div className="text-sm">
                <Link href="/forgot-password" className="font-bold text-brand-primary hover:text-brand-teal transition-colors">
                  Forgot your password?
                </Link>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 rounded-xl shadow-sm hover:shadow-md text-sm font-bold text-white bg-brand-primary hover:bg-brand-teal focus:outline-none transition-all disabled:opacity-50 hover:-translate-y-0.5"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </div>
          </form>

          <div className="mt-8">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-surface text-muted font-medium">New to RAZZZ?</span>
              </div>
            </div>

            <div className="mt-8">
              <Link
                href="/register"
                className="w-full flex justify-center py-3 px-4 border border-border rounded-xl shadow-sm text-sm font-bold text-foreground bg-background hover:bg-gray-50 focus:outline-none transition-all hover:border-brand-primary/50"
              >
                Create your account
              </Link>
            </div>
          </div>

          {/* Demo Credentials Box */}
          <div className="mt-10 bg-brand-primary/5 border border-brand-primary/20 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck className="w-5 h-5 text-brand-primary" />
              <h3 className="text-sm font-bold text-brand-primary">Demo Access</h3>
            </div>
            <p className="text-xs text-muted mb-4 font-medium leading-relaxed">
              Use these credentials to view the pre-populated demo dataset and explore all features immediately.
            </p>
            <div className="bg-background rounded-xl p-4 text-sm font-mono text-foreground space-y-2 border border-border shadow-inner">
              <div className="flex justify-between items-center">
                <span className="text-muted font-bold text-xs uppercase tracking-wider">Email:</span>
                <span className="select-all font-semibold">demo@example.com</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-border">
                <span className="text-muted font-bold text-xs uppercase tracking-wider">Password:</span>
                <span className="select-all font-semibold">demo123</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Right side: Illustration & Branding */}
      <div className="hidden lg:block relative w-0 flex-1 bg-surface border-l border-border overflow-hidden">
        {/* Background gradient & blob */}
        <div className="absolute inset-0 bg-gradient-to-br from-brand-primary/5 via-brand-teal/5 to-transparent pointer-events-none"></div>
        <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-brand-primary/10 rounded-full blur-[120px] pointer-events-none"></div>
        
        <div className="absolute inset-0 flex flex-col items-center justify-center p-12 relative z-10">
          <div className="max-w-md text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-primary/10 text-brand-primary font-bold text-sm tracking-wide uppercase mb-6 border border-brand-primary/20">
              <ArrowRight size={16} />
              AI Revenue Agent
            </div>
            <h2 className="text-4xl font-extrabold text-foreground tracking-tight leading-tight mb-4">
              Smarter Growth. <br/>
              <span className="text-brand-coral">On Autopilot.</span>
            </h2>
            <p className="text-lg text-muted">
              Turn your customer data into revenue with intelligent, personalized campaign strategies.
            </p>
          </div>
          
          <img 
            src="/hero_illustration.jpg" 
            alt="Growth Illustration" 
            className="w-full max-w-[450px] rounded-3xl shadow-2xl border-8 border-white dark:border-gray-800 rotate-2 hover:rotate-0 transition-transform duration-700 object-cover"
          />
        </div>
      </div>
    </div>
  )
}