'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { 
  CircleIcon, 
  LayoutDashboard, 
  AlertTriangle, 
  Plug, 
  Settings, 
  Menu,
  Bot,
  BarChart3,
  Activity,
  Shield,
  X,
  Home
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { signOut } from '@/app/(login)/actions';
import { useRouter } from 'next/navigation';
import { User } from '@/lib/db/schema';
import useSWR, { mutate } from 'swr';
import { LogOut } from 'lucide-react';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

const navItems = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', hideWhenLoggedOut: true },
  { href: '/ai-control', icon: Bot, label: 'AI Agents', hideWhenLoggedOut: true },
  { href: '/incidents', icon: AlertTriangle, label: 'Incidents', hideWhenLoggedOut: true },
  { href: '/integrations', icon: Plug, label: 'Integrations', hideWhenLoggedOut: true },
  { href: '/settings', icon: Settings, label: 'Settings', hideWhenLoggedOut: true }
];

export function Navigation() {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const { data: user } = useSWR<User>('/api/user', fetcher);
  const router = useRouter();

  async function handleSignOut() {
    await signOut();
    mutate('/api/user');
    router.push('/');
  }

  const visibleNavItems = navItems.filter(item => 
    user || !item.hideWhenLoggedOut
  );

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center">
              <CircleIcon className="h-8 w-8 text-orange-500" />
              <span className="ml-2 text-xl font-semibold text-gray-900">Oncall AI</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex md:items-center md:space-x-6">
            {visibleNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm font-medium transition-colors hover:text-orange-600 ${
                  pathname === item.href
                    ? 'text-orange-600'
                    : 'text-gray-700'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* User Menu / Auth Buttons */}
          <div className="flex items-center space-x-4">
            {!user ? (
              <>
                <Link
                  href="/pricing"
                  className="hidden md:inline-block text-sm font-medium text-gray-700 hover:text-gray-900"
                >
                  Pricing
                </Link>
                <Button asChild variant="outline" size="sm">
                  <Link href="/sign-in">Sign In</Link>
                </Button>
                <Button asChild size="sm" className="hidden sm:inline-flex">
                  <Link href="/sign-up">Get Started</Link>
                </Button>
              </>
            ) : (
              <DropdownMenu open={isUserMenuOpen} onOpenChange={setIsUserMenuOpen}>
                <DropdownMenuTrigger>
                  <Avatar className="cursor-pointer size-8">
                    <AvatarImage alt={user.name || ''} />
                    <AvatarFallback>
                      {user.email
                        .split(' ')
                        .map((n) => n[0])
                        .join('')
                        .toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem asChild>
                    <Link href="/dashboard" className="w-full cursor-pointer">
                      <LayoutDashboard className="mr-2 h-4 w-4" />
                      Dashboard
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/settings" className="w-full cursor-pointer">
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-red-600">
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200">
          <nav className="px-4 py-2 space-y-1">
            {visibleNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block py-2 px-3 text-base font-medium rounded-md transition-colors ${
                  pathname === item.href
                    ? 'bg-orange-50 text-orange-600'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center">
                  <item.icon className="h-5 w-5 mr-2" />
                  {item.label}
                </div>
              </Link>
            ))}
            {!user && (
              <>
                <Link
                  href="/pricing"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="block py-2 px-3 text-base font-medium text-gray-700 hover:bg-gray-50 hover:text-gray-900 rounded-md"
                >
                  Pricing
                </Link>
                <div className="pt-2 space-y-2">
                  <Button asChild variant="outline" className="w-full">
                    <Link href="/sign-in" onClick={() => setIsMobileMenuOpen(false)}>
                      Sign In
                    </Link>
                  </Button>
                  <Button asChild className="w-full">
                    <Link href="/sign-up" onClick={() => setIsMobileMenuOpen(false)}>
                      Get Started
                    </Link>
                  </Button>
                </div>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}