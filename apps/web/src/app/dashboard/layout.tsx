'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/use-auth';
import { Bot, LayoutDashboard, Plus, Settings, LogOut, Loader2, Shield } from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isLoading, logout, isAdmin } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/auth/login');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r border-surface-200 bg-white">
        <div className="flex h-16 items-center gap-2 border-b border-surface-200 px-6">
          <Bot className="h-6 w-6 text-primary-600" />
          <span className="font-semibold text-surface-900">Bot Creator</span>
        </div>

        <nav className="p-4 space-y-1">
          <Link
            href="/dashboard"
            className="flex items-center gap-3 rounded px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100"
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Link>
          <Link
            href="/dashboard/create"
            className="flex items-center gap-3 rounded px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100"
          >
            <Plus className="h-4 w-4" />
            Create Bot
          </Link>
          {isAdmin && (
            <Link
              href="/admin"
              className="flex items-center gap-3 rounded px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100"
            >
              <Shield className="h-4 w-4" />
              Admin
            </Link>
          )}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 border-t border-surface-200 p-4">
          <div className="mb-3 px-3">
            <p className="text-sm font-medium text-surface-900 truncate">{user.email}</p>
            <p className="text-xs text-surface-500 capitalize">{user.role}</p>
          </div>
          <button
            onClick={() => logout()}
            className="flex w-full items-center gap-3 rounded px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="pl-64">
        <div className="min-h-screen p-8">{children}</div>
      </main>
    </div>
  );
}
