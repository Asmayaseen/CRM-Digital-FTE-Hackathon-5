import './globals.css';
import { ThemeProvider } from '@/components/ThemeProvider';
import ThemeToggle from '@/components/ThemeToggle';
import Link from 'next/link';

export const metadata = {
  title: 'CloudSync Pro — AI Customer Support',
  description: '24/7 AI-powered customer support for CloudSync Pro',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-300">
        <ThemeProvider>
          {/* Navbar */}
          <header className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-gray-100 dark:border-slate-700/50 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
              {/* Logo */}
              <Link href="/" className="flex items-center gap-3 group">
                <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-md group-hover:shadow-blue-200 dark:group-hover:shadow-blue-900 transition-shadow">
                  <span className="text-white font-bold text-lg">C</span>
                </div>
                <div>
                  <h1 className="font-bold text-gray-900 dark:text-white text-base leading-tight">CloudSync Pro</h1>
                  <p className="text-xs text-gray-400 dark:text-gray-500">AI Customer Support</p>
                </div>
              </Link>

              {/* Nav Links */}
              <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
                <Link href="/#features" className="text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Features</Link>
                <Link href="/#how-it-works" className="text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">How it works</Link>
                <Link href="/#channels" className="text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Channels</Link>
                <Link href="/dashboard" className="text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Dashboard</Link>
              </nav>

              {/* Right side */}
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse-slow"></span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">AI Online</span>
                </div>
                <ThemeToggle />
                <Link href="/support" className="btn-primary text-sm py-2 px-4">
                  Get Support
                </Link>
              </div>
            </div>
          </header>

          {/* Page content */}
          <main>{children}</main>

          {/* Footer */}
          <footer className="border-t border-gray-100 dark:border-slate-700/50 bg-white dark:bg-slate-900 mt-20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-sm">C</span>
                  </div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">CloudSync Pro</span>
                </div>
                <p className="text-sm text-gray-400 dark:text-gray-500">
                  © 2026 CloudSync Pro · AI-powered support available 24/7
                </p>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse-slow"></span>
                  <span className="text-xs text-gray-400 dark:text-gray-500">All systems operational</span>
                </div>
              </div>
            </div>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  );
}
