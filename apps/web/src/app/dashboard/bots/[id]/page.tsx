'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBot, useBotStatus, useBotLogs, useStartBot, useStopBot, useRestartBot, useDeleteBot, useUpdateBotSpec } from '@/hooks/use-bots';
import { api } from '@/lib/api';
import { formatDateTime, formatRelativeTime, getStatusColor } from '@/lib/utils';
import { toast } from 'sonner';
import {
  Bot,
  Play,
  Square,
  RefreshCw,
  Trash2,
  Settings,
  Terminal,
  Clock,
  AlertCircle,
  Loader2,
  Save,
  CreditCard,
} from 'lucide-react';
import type { BotSpec } from '@/types';
import { QRCodeSVG } from 'qrcode.react';

export default function BotDetailPage() {
  const params = useParams();
  const router = useRouter();
  const botId = params.id as string;

  const { data: bot, isLoading, error } = useBot(botId);
  const { data: status } = useBotStatus(botId, bot?.status === 'running');
  const { data: logsData } = useBotLogs(botId);

  const startBot = useStartBot();
  const stopBot = useStopBot();
  const restartBot = useRestartBot();
  const deleteBot = useDeleteBot();
  const updateSpec = useUpdateBotSpec();

  const [activeTab, setActiveTab] = useState<'overview' | 'spec' | 'logs' | 'payment'>('overview');
  const [specJson, setSpecJson] = useState('');
  const [specError, setSpecError] = useState('');
  const [paymentInfo, setPaymentInfo] = useState<any>(null);

  const handleStart = async () => {
    try {
      await startBot.mutateAsync(botId);
      toast.success('Bot started');
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleStop = async () => {
    try {
      await stopBot.mutateAsync(botId);
      toast.success('Bot stopped');
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleRestart = async () => {
    try {
      await restartBot.mutateAsync(botId);
      toast.success('Bot restarted');
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this bot?')) return;
    try {
      await deleteBot.mutateAsync(botId);
      toast.success('Bot deleted');
      router.push('/dashboard');
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleSaveSpec = async () => {
    setSpecError('');
    try {
      const parsed = JSON.parse(specJson);
      await updateSpec.mutateAsync({ id: botId, spec: parsed });
      toast.success('Spec saved');
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        setSpecError('Invalid JSON');
      } else {
        setSpecError(err.message);
      }
    }
  };

  const handleCreateInvoice = async () => {
    try {
      const invoice = await api.createInvoice(botId, 1);
      setPaymentInfo(invoice);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleVerifyPayment = async () => {
    if (!paymentInfo) return;
    try {
      const result = await api.verifyPayment(paymentInfo.invoice_id);
      if (result.status === 'paid') {
        toast.success('Payment confirmed!');
        setPaymentInfo(null);
      } else {
        toast.info(result.message);
      }
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error || !bot) {
    return (
      <div className="rounded-lg border border-danger-200 bg-danger-50 p-4 text-danger-700">
        Bot not found
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100">
            <Bot className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">{bot.name}</h1>
            {bot.telegram_username && (
              <p className="text-surface-500">@{bot.telegram_username}</p>
            )}
          </div>
          <span className={`badge badge-${getStatusColor(bot.status)}`}>
            {bot.status}
          </span>
        </div>

        <div className="flex gap-2">
          {bot.status === 'running' ? (
            <>
              <button onClick={handleStop} disabled={stopBot.isPending} className="btn-secondary">
                <Square className="mr-2 h-4 w-4" />
                Stop
              </button>
              <button onClick={handleRestart} disabled={restartBot.isPending} className="btn-secondary">
                <RefreshCw className="mr-2 h-4 w-4" />
                Restart
              </button>
            </>
          ) : (
            <button
              onClick={handleStart}
              disabled={startBot.isPending || bot.subscription?.state !== 'active'}
              className="btn-primary"
            >
              <Play className="mr-2 h-4 w-4" />
              Start
            </button>
          )}
          <button onClick={handleDelete} disabled={deleteBot.isPending} className="btn-danger">
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-surface-200">
        <nav className="flex gap-8">
          {(['overview', 'spec', 'logs', 'payment'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab);
                if (tab === 'spec' && bot) {
                  setSpecJson(JSON.stringify(bot.spec_json, null, 2));
                }
              }}
              className={`border-b-2 pb-4 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-surface-500 hover:text-surface-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="card p-6">
            <h3 className="mb-4 font-semibold text-surface-900">Status</h3>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm text-surface-500">Current Status</dt>
                <dd className="font-medium capitalize">{bot.status}</dd>
              </div>
              {bot.last_heartbeat && (
                <div>
                  <dt className="text-sm text-surface-500">Last Heartbeat</dt>
                  <dd>{formatRelativeTime(bot.last_heartbeat)}</dd>
                </div>
              )}
              {bot.last_error && (
                <div>
                  <dt className="text-sm text-surface-500">Last Error</dt>
                  <dd className="text-danger-600">{bot.last_error}</dd>
                </div>
              )}
              <div>
                <dt className="text-sm text-surface-500">Created</dt>
                <dd>{formatDateTime(bot.created_at)}</dd>
              </div>
            </dl>
          </div>

          <div className="card p-6">
            <h3 className="mb-4 font-semibold text-surface-900">Subscription</h3>
            {bot.subscription ? (
              <dl className="space-y-4">
                <div>
                  <dt className="text-sm text-surface-500">Status</dt>
                  <dd className={`font-medium capitalize badge badge-${getStatusColor(bot.subscription.state)}`}>
                    {bot.subscription.state}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-surface-500">Price</dt>
                  <dd>{bot.subscription.price_per_month_sol} SOL/month</dd>
                </div>
                {bot.subscription.active_until && (
                  <div>
                    <dt className="text-sm text-surface-500">Active Until</dt>
                    <dd>{formatDateTime(bot.subscription.active_until)}</dd>
                  </div>
                )}
              </dl>
            ) : (
              <p className="text-surface-500">No subscription</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'spec' && (
        <div className="card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-surface-900">Bot Specification</h3>
            <button
              onClick={handleSaveSpec}
              disabled={updateSpec.isPending}
              className="btn-primary"
            >
              {updateSpec.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Changes
            </button>
          </div>
          {specError && (
            <div className="mb-4 rounded bg-danger-50 p-3 text-danger-700">{specError}</div>
          )}
          <textarea
            value={specJson}
            onChange={(e) => setSpecJson(e.target.value)}
            className="input h-96 font-mono text-sm"
            spellCheck={false}
          />
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="card p-6">
          <h3 className="mb-4 font-semibold text-surface-900">Logs</h3>
          <div className="h-96 overflow-auto rounded bg-surface-900 p-4 font-mono text-sm text-surface-100">
            {logsData?.logs.length ? (
              logsData.logs.map((log, i) => (
                <div key={i} className="whitespace-pre-wrap">{log}</div>
              ))
            ) : (
              <p className="text-surface-400">No logs available</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'payment' && (
        <div className="card p-6">
          <h3 className="mb-4 font-semibold text-surface-900">Payment</h3>

          {paymentInfo ? (
            <div className="space-y-6 text-center">
              <div className="mx-auto w-fit rounded-lg bg-white p-4 shadow-soft">
                <QRCodeSVG value={paymentInfo.solana_pay_url} size={200} />
              </div>
              <div>
                <p className="text-2xl font-bold">{paymentInfo.amount_sol} SOL</p>
                <p className="font-mono text-sm text-surface-500 break-all">
                  {paymentInfo.recipient}
                </p>
              </div>
              <button onClick={handleVerifyPayment} className="btn-primary">
                Verify Payment
              </button>
            </div>
          ) : (
            <div className="text-center py-8">
              <CreditCard className="mx-auto h-12 w-12 text-surface-400" />
              <p className="mt-4 text-surface-600">
                Extend your subscription by creating a new invoice
              </p>
              <button onClick={handleCreateInvoice} className="btn-primary mt-6">
                Create Invoice
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
