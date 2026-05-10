'use client'

import React, { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import Logo from './Logo'
import { Brain, Activity, LogIn, LogOut, Menu, X, User, LayoutDashboard, MessageCircle, BookOpen, BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './ui/button'
import { useAuth } from '@/contexts/AuthContext'

const Navigation = () => {
  const pathname = usePathname()
  const { userRole, isAuthenticated, logout } = useAuth()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Don't show navigation on login/signup pages
  if (pathname === '/login' || pathname === '/signup') {
    return null
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProfileDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const navItems = [
    { href: '/', label: 'Home', icon: Brain, show: true },
    { href: '/detection', label: 'Detection', icon: Activity, show: isAuthenticated && userRole === 'doctor' },
    { href: '/companion', label: 'Companion', icon: MessageCircle, show: isAuthenticated && userRole !== 'doctor' },

  ].filter(item => item.show)

  const getDashboardLink = () => {
    if (userRole === 'doctor') return '/doctor-dashboard'
    if (userRole === 'patient') return '/patient-dashboard'
    return '/'
  }

  const handleLogout = async () => {
    await logout()
    setIsProfileDropdownOpen(false)
  }

  return (
    <nav
      className={cn(
        "sticky top-0 z-50 backdrop-blur-xl border-b",
        "bg-[rgba(17,21,30,0.78)] border-white/[0.07]",
        "shadow-[0_8px_32px_-12px_rgba(0,0,0,0.55)]"
      )}
    >
      {/* subtle neon accent line */}
      <div className="absolute inset-x-0 -bottom-px h-px bg-gradient-to-r from-transparent via-[#4ADE80]/40 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-3 group">
            <Logo />
            <span className="text-2xl font-bold gradient-text-brand tracking-tight">
              DementiaNext
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-3">
            <div className="flex items-center space-x-1">
              {navItems.map((item) => {
                const active = pathname === item.href
                return (
                  <Link key={item.href} href={item.href}>
                    <div
                      className={cn(
                        "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 border",
                        active
                          ? "bg-[rgba(74,222,128,0.10)] text-[#4ADE80] border-[rgba(74,222,128,0.30)] shadow-[0_0_18px_-6px_rgba(74,222,128,0.50)]"
                          : "text-foreground/75 border-transparent hover:bg-white/[0.04] hover:text-foreground hover:border-white/[0.07]"
                      )}
                    >
                      <item.icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </div>
                  </Link>
                )
              })}
            </div>

            <div className="ml-2">
              {isAuthenticated ? (
                <div className="relative" ref={dropdownRef}>
                  <button
                    onClick={() => setIsProfileDropdownOpen(!isProfileDropdownOpen)}
                    className={cn(
                      "p-2 rounded-full transition-all duration-200",
                      "bg-[rgba(74,222,128,0.10)] text-[#4ADE80] border border-[rgba(74,222,128,0.30)]",
                      "hover:bg-[rgba(74,222,128,0.18)] hover:shadow-[0_0_18px_-4px_rgba(74,222,128,0.50)]"
                    )}
                  >
                    <User className="w-5 h-5" />
                  </button>

                  {isProfileDropdownOpen && (
                    <div className="absolute right-0 mt-2 w-52 rounded-xl py-2 z-50 bg-[rgba(24,29,40,0.96)] backdrop-blur-xl border border-white/[0.08] shadow-[0_18px_40px_-12px_rgba(0,0,0,0.65),0_0_28px_-12px_rgba(74,222,128,0.22)]">
                      <Link
                        href={getDashboardLink()}
                        className="flex items-center px-4 py-2.5 text-sm text-foreground/85 hover:bg-white/[0.05] hover:text-[#4ADE80] transition-colors"
                        onClick={() => setIsProfileDropdownOpen(false)}
                      >
                        <LayoutDashboard className="w-4 h-4 mr-3" />
                        Dashboard
                      </Link>
                      {userRole !== 'doctor' && (
                        <Link
                          href="/companion/life-story"
                          className="flex items-center px-4 py-2.5 text-sm text-foreground/85 hover:bg-white/[0.05] hover:text-[#4ADE80] transition-colors"
                          onClick={() => setIsProfileDropdownOpen(false)}
                        >
                          <BookOpen className="w-4 h-4 mr-3" />
                          Life Story
                        </Link>
                      )}
                      <div className="my-1 h-px bg-white/[0.06]" />
                      <button
                        onClick={handleLogout}
                        className="flex items-center w-full px-4 py-2.5 text-sm text-foreground/85 hover:bg-white/[0.05] hover:text-[#FF7080] transition-colors"
                      >
                        <LogOut className="w-4 h-4 mr-3" />
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <Link href="/login">
                  <Button>
                    <LogIn className="w-4 h-4 mr-2" />
                    Login
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-lg text-foreground/80 border border-white/[0.07] bg-white/[0.03] hover:bg-white/[0.06]"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-white/[0.07] py-4">
            <div className="space-y-2">
              {navItems.map((item) => {
                const active = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center space-x-2 px-4 py-3 rounded-lg text-sm font-medium transition-all border",
                      active
                        ? "bg-[rgba(74,222,128,0.10)] text-[#4ADE80] border-[rgba(74,222,128,0.30)]"
                        : "text-foreground/75 border-transparent hover:bg-white/[0.04]"
                    )}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <item.icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}

              {isAuthenticated ? (
                <>
                  <Link
                    href={getDashboardLink()}
                    className="flex items-center space-x-2 px-4 py-3 rounded-lg text-sm font-medium text-foreground/75 hover:bg-white/[0.04]"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    <span>Dashboard</span>
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout()
                      setIsMobileMenuOpen(false)
                    }}
                    className="flex items-center space-x-2 w-full px-4 py-3 rounded-lg text-sm font-medium text-foreground/75 hover:bg-white/[0.04]"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Logout</span>
                  </button>
                </>
              ) : (
                <Link
                  href="/login"
                  className="flex items-center space-x-2 px-4 py-3 rounded-lg text-sm font-semibold bg-brand-gradient text-[#0E1320]"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <LogIn className="w-4 h-4" />
                  <span>Login</span>
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}

export default Navigation
