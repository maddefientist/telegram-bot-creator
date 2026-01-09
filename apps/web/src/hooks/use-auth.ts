'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { User } from '@/types';

export function useAuth() {
  const queryClient = useQueryClient();
  const router = useRouter();

  const { data: user, isLoading, error } = useQuery<User>({
    queryKey: ['user'],
    queryFn: () => api.getCurrentUser(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(['user'], data.user);
      router.push('/dashboard');
    },
  });

  const registerMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.register(email, password),
    onSuccess: () => {
      router.push('/auth/login?registered=true');
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      queryClient.clear();
      router.push('/auth/login');
    },
  });

  const walletLoginMutation = useMutation({
    mutationFn: async ({
      walletAddress,
      signMessage,
      email,
    }: {
      walletAddress: string;
      signMessage: (message: Uint8Array) => Promise<Uint8Array>;
      email?: string;
    }) => {
      // Step 1: Request nonce
      const { nonce, message } = await api.requestWalletNonce(walletAddress);

      // Step 2: Sign message
      const messageBytes = new TextEncoder().encode(message);
      const signatureBytes = await signMessage(messageBytes);

      // Convert signature to base58
      const bs58 = (await import('bs58')).default;
      const signature = bs58.encode(signatureBytes);

      // Step 3: Try to login
      try {
        const result = await api.loginWallet(walletAddress, signature, nonce);
        return result;
      } catch (error: any) {
        // Step 4: If wallet not registered, auto-register
        if (error.message?.includes('not registered')) {
          const user = await api.registerWallet(walletAddress, signature, nonce, email);
          // After registration, request new nonce and login
          const { nonce: newNonce, message: newMessage } = await api.requestWalletNonce(
            walletAddress
          );
          const newMessageBytes = new TextEncoder().encode(newMessage);
          const newSignatureBytes = await signMessage(newMessageBytes);
          const newSignature = bs58.encode(newSignatureBytes);
          return await api.loginWallet(walletAddress, newSignature, newNonce);
        }
        throw error;
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['user'], data.user);
      router.push('/dashboard');
    },
  });

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    error,
    login: loginMutation.mutate,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutate,
    registerError: registerMutation.error,
    isRegistering: registerMutation.isPending,
    logout: logoutMutation.mutate,
    isLoggingOut: logoutMutation.isPending,
    walletLogin: walletLoginMutation.mutate,
    walletLoginError: walletLoginMutation.error,
    isWalletLoggingIn: walletLoginMutation.isPending,
  };
}
