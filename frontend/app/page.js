'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, BarChart3, Target, Zap, CheckCircle2 } from 'lucide-react'

export default function LandingPage() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  useEffect(() => {
    setMounted(true)
    const merchantId = localStorage.getItem('merchantId')
    if (merchantId) {
      setIsLoggedIn(true)
    }
  }, [])

  if (!mounted) return null

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-brand-teal selection:text-white font-sans">
      
      {/* Navigation */}
      <nav className="border-b border-border bg-surface/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-brand-coral p-1.5 rounded-lg">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-foreground">RAZZZ</span>
          </div>
          <div className="flex items-center gap-4">
            {isLoggedIn ? (
              <Link href="/dashboard" className="text-sm font-medium hover:text-brand-primary transition-colors">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link href="/login" className="text-sm font-medium hover:text-brand-primary transition-colors">
                  Log in
                </Link>
                <Link 
                  href="/onboarding" 
                  className="bg-brand-primary hover:bg-brand-teal text-white px-4 py-2 rounded-full text-sm font-medium transition-all shadow-sm hover:shadow-md"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="bg-surface relative pb-24 overflow-hidden">
        {/* Wavy Background Graphic for full width hero */}
        <div className="absolute top-0 left-0 w-full h-[600px] z-0 overflow-hidden pointer-events-none">
          {/* We'll use a CSS wave or large SVG for the background */}
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-brand-mint/20 to-transparent"></div>
          <svg className="absolute bottom-0 w-full h-64 text-brand-teal/80 dark:text-brand-teal/20 transform scale-x-110" preserveAspectRatio="none" viewBox="0 0 1440 320">
            <path fill="currentColor" fillOpacity="1" d="M0,192L48,181.3C96,171,192,149,288,144C384,139,480,149,576,165.3C672,181,768,203,864,197.3C960,192,1056,160,1152,149.3C1248,139,1344,149,1392,154.7L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path>
          </svg>
          <svg className="absolute bottom-0 w-full h-48 text-brand-primary dark:text-brand-primary transform scale-x-105" preserveAspectRatio="none" viewBox="0 0 1440 320">
            <path fill="currentColor" fillOpacity="1" d="M0,256L48,229.3C96,203,192,149,288,154.7C384,160,480,224,576,218.7C672,213,768,139,864,128C960,117,1056,171,1152,197.3C1248,224,1344,224,1392,224L1440,224L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path>
          </svg>
        </div>

        <section className="relative z-10 pt-24 pb-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center gap-12 lg:gap-20">
            <div className="flex-1 space-y-8">
              <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold text-brand-primary dark:text-white tracking-tight leading-tight">
                AI Revenue Agent <br/>
                <span className="text-brand-coral">for Smarter Growth</span>
              </h1>
              
              <p className="text-xl text-foreground/80 max-w-xl leading-relaxed">
                RAZZZ analyzes customer data, campaign performance and business goals to recommend the next best action that drives real revenue.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center gap-4 pt-4">
                <Link 
                  href={isLoggedIn ? "/dashboard" : "/onboarding"}
                  className="w-full sm:w-auto bg-brand-primary hover:bg-brand-teal text-white px-8 py-4 rounded-xl text-lg font-bold transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5 flex items-center justify-center gap-2"
                >
                  {isLoggedIn ? "Go to Dashboard" : "Get Started"}
                </Link>
              </div>
            </div>
            
            <div className="flex-1 flex justify-center md:justify-end w-full relative">
              <img 
                src="/hero_illustration.jpg" 
                alt="Marketing Strategy Growth" 
                className="w-full max-w-[450px] relative z-10 rounded-2xl shadow-2xl"
              />
            </div>
          </div>
        </section>

        {/* Feature Columns */}
        <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-surface/90 backdrop-blur-sm p-8 rounded-2xl border border-border shadow-sm flex flex-col sm:flex-row items-start gap-4 hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-brand-primary/10 text-brand-primary rounded-xl flex items-center justify-center shrink-0">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-foreground text-lg mb-2">Understand Customers</h3>
                <p className="text-muted text-sm leading-relaxed">Identify high-value segments and opportunities.</p>
              </div>
            </div>
            
            <div className="bg-surface/90 backdrop-blur-sm p-8 rounded-2xl border border-border shadow-sm flex flex-col sm:flex-row items-start gap-4 hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-brand-coral/10 text-brand-coral rounded-xl flex items-center justify-center shrink-0">
                <Target className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-foreground text-lg mb-2">Launch Smart Campaigns</h3>
                <p className="text-muted text-sm leading-relaxed">Personalize offers that drive engagement and sales.</p>
              </div>
            </div>
            
            <div className="bg-surface/90 backdrop-blur-sm p-8 rounded-2xl border border-border shadow-sm flex flex-col sm:flex-row items-start gap-4 hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-brand-teal/10 text-brand-teal rounded-xl flex items-center justify-center shrink-0">
                <BarChart3 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-foreground text-lg mb-2">Optimize & Grow</h3>
                <p className="text-muted text-sm leading-relaxed">Continuously optimize for maximum revenue impact.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-background py-12 border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center gap-2 mb-4 md:mb-0 opacity-80">
            <BarChart3 className="w-5 h-5 text-brand-primary" />
            <span className="font-bold text-lg">RAZZZ</span>
          </div>
          <p className="text-muted text-sm">© {new Date().getFullYear()} RAZZZ Intelligence. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}