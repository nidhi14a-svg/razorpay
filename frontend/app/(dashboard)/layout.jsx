'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, Users, Megaphone, Brain, TrendingUp, LogOut, BarChart3, Menu, X, Sliders } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'
import { getApiUrl } from '@/lib/api'

export default function DashboardLayout({ children }) {
  const pathname = usePathname()
  const router = useRouter()
  const [businessName, setBusinessName] = useState('Loading...')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isAuthorized, setIsAuthorized] = useState(false)
  const [missingGuardrails, setMissingGuardrails] = useState(false)

  useEffect(() => {
    const id = localStorage.getItem('merchantId')
    const token = localStorage.getItem('token')
    const name = localStorage.getItem('businessName')
    const onboardingCompleted = localStorage.getItem('onboardingCompleted')
    
    if (!id || !token) {
      router.replace('/login')
      return
    }
    
    setBusinessName(name || 'Your Business')

    fetch(getApiUrl(`/merchants/${id}/onboarding-status`), {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error('Status check failed')
        return res.json()
      })
      .then(status => {
        if (status.onboarding_completed) {
          localStorage.setItem('onboardingCompleted', 'true')
          setIsAuthorized(true)
          if (!status.has_guardrails) {
            setMissingGuardrails(true)
          } else {
            setMissingGuardrails(false)
          }
        } else {
          localStorage.setItem('onboardingCompleted', 'false')
          router.replace('/onboarding')
        }
      })
      .catch(err => {
        console.error("Failed to check onboarding status:", err)
        // If network error but we have local authorization flag, allow grace
        if (onboardingCompleted === 'true') {
          setIsAuthorized(true)
        } else {
          router.replace('/onboarding')
        }
      })
  }, [router, pathname])

  const handleLogout = () => {
    localStorage.removeItem('merchantId')
    localStorage.removeItem('businessName')
    localStorage.removeItem('token')
    localStorage.removeItem('onboardingCompleted')
    router.push('/login')
  }

  if (!isAuthorized) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-brand-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-muted font-medium">Loading workspace...</p>
        </div>
      </div>
    )
  }

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Customers', href: '/customers', icon: Users },
    { name: 'Campaigns', href: '/campaigns', icon: Megaphone },
    { name: 'AI Intelligence', href: '/intelligence', icon: Brain },
    { name: 'Optimizations', href: '/optimizations', icon: TrendingUp },
  ]

  const SidebarContent = () => (
    <>
      <div className="p-6 border-b border-border bg-surface">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="bg-brand-primary p-2 rounded-lg flex items-center justify-center shadow-soft">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">RAZZZ</h1>
        </Link>
        <p className="text-xs font-semibold tracking-wider uppercase text-muted mt-4 mb-2 px-1">
          Revenue Agent
        </p>
        <div className="bg-gray-50 dark:bg-gray-800/50 border border-border px-3 py-2 rounded-lg inline-flex items-center w-full">
          <span className="text-sm font-medium text-foreground truncate">{businessName}</span>
        </div>
      </div>
      
      <nav className="flex-1 py-4 space-y-1 overflow-y-auto bg-surface pr-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-3 px-4 py-3 rounded-r-lg font-medium transition-all border-l-4 group ${
                isActive 
                  ? 'border-brand-primary bg-brand-primary/10 text-brand-primary dark:text-brand-primary' 
                  : 'border-transparent text-muted hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:text-foreground'
              }`}
            >
              <item.icon size={20} className={isActive ? 'text-brand-primary dark:text-brand-primary' : 'text-muted transition-transform group-hover:scale-110'} />
              {item.name}
            </Link>
          )
        })}
      </nav>
      
      <div className="p-4 border-t border-border bg-surface">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-medium text-muted rounded-lg hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition-colors"
        >
          <LogOut size={20} className="text-inherit opacity-70" />
          Sign out
        </button>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row text-foreground font-sans">
      
      {/* Desktop Sidebar */}
      <aside className="w-64 border-r border-border flex-col hidden md:flex fixed h-full z-10 bg-surface shadow-soft">
        <SidebarContent />
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        
        {/* Mobile Header */}
        <header className="md:hidden bg-surface border-b border-border p-4 flex justify-between items-center sticky top-0 z-20 shadow-sm">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="bg-brand-primary p-1.5 rounded-lg">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-foreground">RAZZZ</h1>
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-muted hover:text-foreground hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </header>

        {/* Mobile Menu Overlay */}
        {mobileMenuOpen && (
          <div className="md:hidden fixed inset-0 top-[73px] z-50 bg-background flex flex-col border-t border-border overflow-y-auto">
            <SidebarContent />
          </div>
        )}

        {/* Desktop Topbar */}
        <header className="hidden md:flex bg-surface/80 backdrop-blur-md h-16 border-b border-border items-center justify-end px-8 sticky top-0 z-20 shadow-sm transition-all">
           <div className="flex items-center gap-6">
             <ThemeToggle />
             <div className="h-6 w-px bg-border"></div>
             <div className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity">
               <span className="text-sm font-semibold text-foreground">{businessName}</span>
               <span className="w-9 h-9 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center font-bold text-sm border border-brand-primary/20 shadow-sm">
                 {businessName.charAt(0).toUpperCase()}
               </span>
             </div>
           </div>
        </header>

        <main className="flex-1 p-4 md:p-8 lg:p-10 max-w-7xl mx-auto w-full">
          {missingGuardrails && (
            <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm animate-in fade-in duration-300">
              <div className="flex items-center gap-3 text-amber-800 dark:text-amber-300">
                <div className="w-9 h-9 rounded-lg bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center shrink-0">
                  <Sliders className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-sm font-bold">Complete your merchant settings before generating campaigns.</p>
                  <p className="text-xs text-amber-700/90 dark:text-amber-400/90">Merchant guardrail rules are required so that AI campaigns strictly follow your discount caps and order limits.</p>
                </div>
              </div>
              <Link
                href="/onboarding?step=guardrails"
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg transition-colors shrink-0 text-center shadow-sm"
              >
                Configure Guardrails
              </Link>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  )
}
