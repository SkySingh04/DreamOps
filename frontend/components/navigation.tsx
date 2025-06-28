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
  Home,
  LogOut,
  User as UserIcon
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useRouter } from 'next/navigation';
import { User } from '@/lib/db/schema';
import useSWR, { mutate } from 'swr';
import { AccountTierBadge } from '@/components/ui/account-tier-badge';

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
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { data: user, error, isLoading } = useSWR<User>('/api/user', fetcher);

  const handleLogout = async () => {
    try {
      await fetch('/api/logout', { method: 'POST' });
      mutate('/api/user', null, false);
      router.push('/sign-in');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Left side - Logo and nav items */}
          <div className="flex">
            {/* Logo */}
            <Link href="/" className="flex items-center">
              <Bot className="h-8 w-8 text-orange-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">DreamOps</span>
            </Link>

            {/* Desktop navigation */}
            <div className="hidden md:ml-8 md:flex md:space-x-8">
              {navItems.map((item) => {
                if (item.hideWhenLoggedOut && !user) return null;
                
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`
                      inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium
                      ${isActive
                        ? 'border-orange-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }
                    `}
                  >
                    <item.icon className="h-4 w-4 mr-2" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right side - User menu */}
          <div className="flex items-center space-x-4">
            {user && (
              <>
                <AccountTierBadge tier={user.accountTier || 'free'} />
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src="/avatar.png" alt={user.name || ''} />
                        <AvatarFallback>
                          {user.name?.charAt(0).toUpperCase() || 'U'}
                        </AvatarFallback>
                      </Avatar>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-56" align="end" forceMount>
                    <DropdownMenuItem className="flex flex-col items-start">
                      <div className="text-sm font-medium">{user.name || 'User'}</div>
                      <div className="text-xs text-gray-500">{user.email}</div>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link href="/dashboard/general">
                        <UserIcon className="mr-2 h-4 w-4" />
                        <span>Account</span>
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link href="/settings">
                        <Settings className="mr-2 h-4 w-4" />
                        <span>Settings</span>
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout}>
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Log out</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )}

            {/* Mobile menu button */}
            <div className="md:hidden">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              >
                {isMobileMenuOpen ? (
                  <X className="h-6 w-6" />
                ) : (
                  <Menu className="h-6 w-6" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile navigation menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="pt-2 pb-3 space-y-1">
            {navItems.map((item) => {
              if (item.hideWhenLoggedOut && !user) return null;
              
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    block pl-3 pr-4 py-2 border-l-4 text-base font-medium
                    ${isActive
                      ? 'bg-orange-50 border-orange-500 text-orange-700'
                      : 'border-transparent text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800'
                    }
                  `}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <div className="flex items-center">
                    <item.icon className="h-5 w-5 mr-3" />
                    {item.label}
                  </div>
                </Link>
              );
            })}
            {user && (
              <>
                <div className="border-t pt-2">
                  <Link
                    href="/dashboard/general"
                    className="block pl-3 pr-4 py-2 border-l-4 border-transparent text-base font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <div className="flex items-center">
                      <UserIcon className="h-5 w-5 mr-3" />
                      Account
                    </div>
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout();
                      setIsMobileMenuOpen(false);
                    }}
                    className="block w-full text-left pl-3 pr-4 py-2 border-l-4 border-transparent text-base font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800"
                  >
                    <div className="flex items-center">
                      <LogOut className="h-5 w-5 mr-3" />
                      Log out
                    </div>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}