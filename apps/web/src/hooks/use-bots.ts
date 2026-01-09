'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Bot, BotSpec } from '@/types';

export function useBots() {
  return useQuery<Bot[]>({
    queryKey: ['bots'],
    queryFn: () => api.getBots(),
  });
}

export function useBot(id: string) {
  return useQuery<Bot>({
    queryKey: ['bot', id],
    queryFn: () => api.getBot(id),
    enabled: !!id,
  });
}

export function useBotStatus(id: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['bot-status', id],
    queryFn: () => api.getBotStatus(id),
    enabled: enabled && !!id,
    refetchInterval: 5000, // Poll every 5 seconds
  });
}

export function useBotLogs(id: string, tail: number = 100) {
  return useQuery({
    queryKey: ['bot-logs', id, tail],
    queryFn: () => api.getBotLogs(id, tail),
    enabled: !!id,
    refetchInterval: 10000, // Poll every 10 seconds
  });
}

export function useCreateBot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      telegram_token: string;
      description: string;
      price_per_month_sol: number;
    }) => api.createBot(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] });
    },
  });
}

export function useUpdateBotSpec() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, spec }: { id: string; spec: BotSpec }) =>
      api.updateBotSpec(id, spec),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['bot', id] });
      queryClient.invalidateQueries({ queryKey: ['bots'] });
    },
  });
}

export function useStartBot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.startBot(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['bot', id] });
      queryClient.invalidateQueries({ queryKey: ['bot-status', id] });
      queryClient.invalidateQueries({ queryKey: ['bots'] });
    },
  });
}

export function useStopBot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.stopBot(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['bot', id] });
      queryClient.invalidateQueries({ queryKey: ['bot-status', id] });
      queryClient.invalidateQueries({ queryKey: ['bots'] });
    },
  });
}

export function useRestartBot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.restartBot(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['bot', id] });
      queryClient.invalidateQueries({ queryKey: ['bot-status', id] });
      queryClient.invalidateQueries({ queryKey: ['bots'] });
    },
  });
}

export function useDeleteBot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteBot(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bots'] });
    },
  });
}
