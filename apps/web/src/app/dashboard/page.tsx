'use client';

import Link from 'next/link';
import { useBots } from '@/hooks/use-bots';
import { formatRelativeTime, getStatusColor } from '@/lib/utils';
import {
  Bot,
  Plus,
  Play,
  Square,
  RefreshCw,
  AlertCircle,
  Loader2,
  Clock,
} from 'lucide-react';
import { useStartBot, useStopBot } from '@/hooks/use-bots';
import { toast } from 'sonner';

export default function DashboardPage() {
  const { data: bots, isLoading, error } = useBots();
  const startBot = useStartBot();
  const stopBot = useStopBot();

  const handleStart = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await startBot.mutateAsync(id);
      toast.success('Bot started');
    } catch (err: any) {
      toast.error(err.message || 'Failed to start bot');
    }
  };

  const handleStop = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await stopBot.mutateAsync(id);
      toast.success('Bot stopped');
    } catch (err: any) {
      toast.error(err.message || 'Failed to stop bot');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-danger-200 bg-danger-50 p-4 text-danger-700">
        Failed to load bots: {error.message}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Your Bots</h1>
          <p className="mt-1 text-surface-500">Manage your Telegram bots</p>
        </div>
        <Link href="/dashboard/create" className="btn-primary">
          <Plus className="mr-2 h-4 w-4" />
          Create Bot
        </Link>
      </div>

      {bots?.length === 0 ? (
        <div className="card p-12 text-center">
          <Bot className="mx-auto h-12 w-12 text-surface-400" />
          <h2 className="mt-4 text-lg font-medium text-surface-900">No bots yet</h2>
          <p className="mt-2 text-surface-500">
            Create your first bot to get started
          </p>
          <Link href="/dashboard/create" className="btn-primary mt-6">
            <Plus className="mr-2 h-4 w-4" />
            Create Bot
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {bots?.map((bot) => (
            <Link
              key={bot.id}
              href={`/dashboard/bots/${bot.id}`}
              className="card p-6 transition-shadow hover:shadow-soft"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100">
                    <Bot className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-surface-900">{bot.name}</h3>
                    {bot.telegram_username && (
                      <p className="text-sm text-surface-500">@{bot.telegram_username}</p>
                    )}
                  </div>
                </div>
                <span className={`badge badge-${getStatusColor(bot.status)}`}>
                  {bot.status}
                </span>
              </div>

              {/* Subscription info */}
              {bot.subscription && (
                <div className="mt-4 flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-surface-400" />
                  <span className="text-surface-600">
                    {bot.subscription.state === 'active' && bot.subscription.active_until
                      ? `Active until ${new Date(bot.subscription.active_until).toLocaleDateString()}`
                      : bot.subscription.state === 'pending'
                      ? 'Awaiting payment'
                      : bot.subscription.state}
                  </span>
                </div>
              )}

              {/* Last error */}
              {bot.last_error && (
                <div className="mt-4 flex items-start gap-2 rounded bg-danger-50 p-2 text-sm text-danger-700">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span className="line-clamp-2">{bot.last_error}</span>
                </div>
              )}

              {/* Last heartbeat */}
              {bot.last_heartbeat && (
                <p className="mt-4 text-xs text-surface-400">
                  Last seen {formatRelativeTime(bot.last_heartbeat)}
                </p>
              )}

              {/* Actions */}
              <div className="mt-4 flex gap-2">
                {bot.status === 'running' ? (
                  <button
                    onClick={(e) => handleStop(bot.id, e)}
                    disabled={stopBot.isPending}
                    className="btn-secondary flex-1 text-sm"
                  >
                    <Square className="mr-1 h-3 w-3" />
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={(e) => handleStart(bot.id, e)}
                    disabled={startBot.isPending || bot.subscription?.state !== 'active'}
                    className="btn-primary flex-1 text-sm"
                  >
                    <Play className="mr-1 h-3 w-3" />
                    Start
                  </button>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
