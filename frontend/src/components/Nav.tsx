'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

const navLinks = [
  { href: '/dashboard', label: 'Dashboard', icon: '◆' },
  { href: '/upload', label: 'Upload', icon: '↑' },
  { href: '/jobs', label: 'Jobs', icon: '⚡' },
];

export default function Nav() {
  const router = useRouter();
  const pathname = usePathname();

  function logout() {
    localStorage.removeItem('token');
    router.push('/login');
  }

  return (
    <nav className="sticky top-0 z-50 animate-fade-in-down">
      <div className="bg-slate-950/80 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            {/* Logo */}
            <Link href="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm shadow-glow-brand transition-all duration-300 group-hover:shadow-lg group-hover:scale-105">
                X
              </div>
              <span className="font-bold text-lg tracking-tight">
                <span className="text-white">Xeno</span>
                <span className="text-brand-400 ml-1">Validate</span>
              </span>
            </Link>

            {/* Nav Links */}
            <div className="hidden sm:flex items-center gap-1">
              {navLinks.map((link) => {
                const isActive = pathname === link.href || pathname?.startsWith(link.href + '/');
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? 'text-white bg-white/[0.08]'
                        : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                    }`}
                  >
                    <span className="mr-1.5 opacity-60">{link.icon}</span>
                    {link.label}
                    {isActive && (
                      <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-gradient-to-r from-brand-500 to-purple-500 rounded-full" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right side */}
          <button
            onClick={logout}
            className="text-sm text-slate-500 hover:text-red-400 transition-colors duration-200 flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
