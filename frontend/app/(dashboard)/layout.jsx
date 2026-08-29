'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, Users, Megaphone, Brain, TrendingUp, LogOut, Settings } from 'lucide-react'

export default function DashboardLayout({ children }) {
  const pathname = usePathname()
  const router = useRouter()
  const [businessName, setBusinessName] = useState('Loading...')

  useEffect(() => {
    const id = localStorage.getItem('merchantId')
    const name = localStorage.getItem('businessName')
    
    if (!id) {
      router.push('/login')
    } else {
      setBusinessName(name || 'Your Business')
    }
  }, [router])

  const handleLogout = () => {
    localStorage.removeItem('merchantId')
    localStorage.removeItem('businessName')
    router.push('/login')
  }

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Customers', href: '/customers', icon: Users },
    { name: 'Campaigns', href: '/campaigns', icon: Megaphone },
    { name: 'AI Intelligence', href: '/intelligence', icon: Brain },
    { name: 'Optimizations', href: '/optimizations', icon: TrendingUp },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col hidden md:flex fixed h-full z-10">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">R</div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900">RAZZZ</h1>
          </div>
          <p className="text-sm font-medium text-gray-500 mt-2 truncate">{businessName}</p>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${
                  isActive 
                    ? 'bg-blue-50 text-blue-700' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <item.icon size={20} className={isActive ? 'text-blue-600' : 'text-gray-400'} />
                {item.name}
              </Link>
            )
          })}
        </nav>
        
        <div className="p-4 border-t border-gray-100">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 px-3 py-2 text-sm font-medium text-gray-600 rounded-lg hover:bg-gray-50 hover:text-red-600 transition-colors"
          >
            <LogOut size={20} className="text-gray-400" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        {/* Mobile Header (simplified) */}
        <header className="md:hidden bg-white border-b border-gray-200 p-4 flex justify-between items-center sticky top-0 z-20">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">R</div>
            <h1 className="text-lg font-bold">RAZZZ</h1>
          </div>
          <button onClick={handleLogout} className="text-sm text-gray-600 font-medium">Sign out</button>
        </header>

        {/* Topbar for Desktop (Optional utility bar) */}
        <header className="hidden md:flex bg-white h-16 border-b border-gray-200 items-center justify-end px-8 sticky top-0 z-20">
           <div className="flex items-center gap-4">
             <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm">
               {businessName.charAt(0).toUpperCase()}
             </span>
           </div>
        </header>

        <main className="flex-1 p-4 md:p-8 lg:p-10 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  )
}
