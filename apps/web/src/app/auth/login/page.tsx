'use client';

import { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Loader2, Bot, ChevronDown, ChevronUp } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';

function LoginForm() {
  const searchParams = useSearchParams();
  const { login, isLoggingIn, loginError, walletLogin, isWalletLoggingIn, walletLoginError } = useAuth();
  const { publicKey, signMessage } = useWallet();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [walletEmail, setWalletEmail] = useState('');
  const [showWalletEmail, setShowWalletEmail] = useState(false);

  const registered = searchParams.get('registered') === 'true';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login({ email, password });
  };

  const handleWalletLogin = async () => {
    if (!publicKey || !signMessage) return;

    walletLogin({
      walletAddress: publicKey.toBase58(),
      signMessage,
      email: walletEmail || undefined,
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary-100">
              <Bot className="h-6 w-6 text-primary-600" />
            </div>
            <h1 className="text-2xl font-bold text-surface-900">Welcome back</h1>
            <p className="mt-2 text-surface-500">Sign in to your account</p>
          </div>

          {registered && (
            <div className="mb-6 rounded bg-success-50 p-3 text-sm text-success-700">
              Account created successfully. Please sign in.
            </div>
          )}

          {loginError && (
            <div className="mb-6 rounded bg-danger-50 p-3 text-sm text-danger-700">
              {loginError.message}
            </div>
          )}

          {walletLoginError && (
            <div className="mb-6 rounded bg-danger-50 p-3 text-sm text-danger-700">
              {walletLoginError.message}
            </div>
          )}

          {/* Wallet Login Section */}
          <div className="mb-6 space-y-4">
            <div className="flex flex-col items-center gap-3">
              <WalletMultiButton className="!bg-primary-600 !hover:bg-primary-700" />

              {publicKey && (
                <>
                  <p className="text-xs text-surface-500">
                    Connected: {publicKey.toBase58().slice(0, 4)}...{publicKey.toBase58().slice(-4)}
                  </p>

                  {/* Optional email input */}
                  <button
                    type="button"
                    onClick={() => setShowWalletEmail(!showWalletEmail)}
                    className="flex items-center gap-1 text-xs text-surface-500 hover:text-surface-700"
                  >
                    {showWalletEmail ? 'Hide' : 'Add'} email (optional)
                    {showWalletEmail ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  </button>

                  {showWalletEmail && (
                    <input
                      type="email"
                      value={walletEmail}
                      onChange={(e) => setWalletEmail(e.target.value)}
                      className="input w-full"
                      placeholder="your@email.com (for notifications)"
                    />
                  )}

                  <button
                    type="button"
                    onClick={handleWalletLogin}
                    disabled={isWalletLoggingIn}
                    className="btn-primary w-full"
                  >
                    {isWalletLoggingIn ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      'Sign in with Wallet'
                    )}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-white px-2 text-surface-500">Or continue with email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="label mb-1 block">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="label mb-1 block">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Enter your password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoggingIn}
              className="btn-primary w-full"
            >
              {isLoggingIn ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-surface-500">
            Don&apos;t have an account?{' '}
            <Link href="/auth/register" className="text-primary-600 hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
