'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useCreateBot } from '@/hooks/use-bots';
import { toast } from 'sonner';
import {
  Bot,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Sparkles,
  Check,
  Copy,
} from 'lucide-react';
import type { BotSpec, ModuleType, PricingTier, GenerateBotSpecResponse } from '@/types';
import { QRCodeSVG } from 'qrcode.react';

const STEPS = [
  { id: 1, title: 'Basic Info', description: 'Name and Telegram token' },
  { id: 2, title: 'Describe', description: 'What should it do?' },
  { id: 3, title: 'Modules', description: 'Choose capabilities' },
  { id: 4, title: 'Generate', description: 'AI creates your spec' },
  { id: 5, title: 'Pricing', description: 'Choose your plan' },
  { id: 6, title: 'Payment', description: 'Pay to activate' },
];

const MODULES: { id: ModuleType; name: string; description: string }[] = [
  { id: 'basic_commands', name: 'Basic Commands', description: '/start and /help' },
  { id: 'static_replies', name: 'Static Replies', description: 'Custom command responses' },
  { id: 'ai_chat', name: 'AI Chat', description: 'Conversational AI responses' },
  { id: 'moderation', name: 'Moderation', description: 'Filter messages' },
  { id: 'webhook_forward', name: 'Webhooks', description: 'Forward events to URL' },
];

export default function CreateBotPage() {
  const router = useRouter();
  const createBot = useCreateBot();
  const [step, setStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Form data
  const [name, setName] = useState('');
  const [telegramToken, setTelegramToken] = useState('');
  const [description, setDescription] = useState('');
  const [selectedModules, setSelectedModules] = useState<ModuleType[]>(['basic_commands']);
  const [constraints, setConstraints] = useState('');
  const [generatedSpec, setGeneratedSpec] = useState<BotSpec | null>(null);
  const [specErrors, setSpecErrors] = useState<string[]>([]);
  const [pricing, setPricing] = useState<{ tiers: PricingTier[]; min: number; max: number } | null>(null);
  const [selectedTier, setSelectedTier] = useState<PricingTier | null>(null);
  const [customPrice, setCustomPrice] = useState<number>(0.1);
  const [paymentInfo, setPaymentInfo] = useState<any>(null);
  const [createdBotId, setCreatedBotId] = useState<string | null>(null);

  const toggleModule = (id: ModuleType) => {
    if (id === 'basic_commands') return; // Always required
    setSelectedModules((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setSpecErrors([]);

    try {
      const response: GenerateBotSpecResponse = await api.generateBotSpec({
        description,
        bot_name: name,
        enabled_modules: selectedModules,
        constraints,
      });

      if (response.success && response.spec) {
        setGeneratedSpec(response.spec);
        setStep(5);
        // Load pricing
        const pricingConfig = await api.getPricing();
        setPricing({
          tiers: pricingConfig.tiers,
          min: pricingConfig.min_sol,
          max: pricingConfig.max_sol,
        });
        setCustomPrice(pricingConfig.default_sol);
      } else {
        setSpecErrors(response.errors || ['Failed to generate spec']);
      }
    } catch (err: any) {
      toast.error(err.message || 'Generation failed');
      setSpecErrors([err.message || 'Generation failed']);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateAndPay = async () => {
    if (!generatedSpec) return;
    setIsCreating(true);

    const price = selectedTier?.price_sol || customPrice;

    try {
      // Create bot
      const bot = await createBot.mutateAsync({
        name,
        telegram_token: telegramToken,
        description,
        price_per_month_sol: price,
      });

      setCreatedBotId(bot.id);

      // Update spec
      await api.updateBotSpec(bot.id, generatedSpec);

      // Create invoice
      const invoice = await api.createInvoice(bot.id, 1);
      setPaymentInfo(invoice);
      setStep(6);
    } catch (err: any) {
      toast.error(err.message || 'Failed to create bot');
    } finally {
      setIsCreating(false);
    }
  };

  const handleVerifyPayment = async () => {
    if (!paymentInfo) return;

    try {
      const result = await api.verifyPayment(paymentInfo.invoice_id);
      if (result.status === 'paid') {
        toast.success('Payment confirmed!');
        router.push(`/dashboard/bots/${createdBotId}`);
      } else {
        toast.info(result.message);
      }
    } catch (err: any) {
      toast.error(err.message || 'Verification failed');
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return name.trim().length > 0 && telegramToken.trim().length >= 40;
      case 2:
        return description.trim().length >= 10;
      case 3:
        return selectedModules.length > 0;
      case 4:
        return generatedSpec !== null;
      case 5:
        return selectedTier !== null || customPrice > 0;
      default:
        return true;
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* Progress */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium ${
                  step >= s.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-surface-200 text-surface-500'
                }`}
              >
                {step > s.id ? <Check className="h-4 w-4" /> : s.id}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`mx-2 h-0.5 w-8 ${
                    step > s.id ? 'bg-primary-600' : 'bg-surface-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="mt-4">
          <h2 className="text-lg font-semibold text-surface-900">
            {STEPS[step - 1].title}
          </h2>
          <p className="text-sm text-surface-500">{STEPS[step - 1].description}</p>
        </div>
      </div>

      {/* Step content */}
      <div className="card p-6">
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <label className="label mb-2 block">Bot Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                placeholder="My Awesome Bot"
              />
            </div>
            <div>
              <label className="label mb-2 block">Telegram Bot Token</label>
              <input
                type="password"
                value={telegramToken}
                onChange={(e) => setTelegramToken(e.target.value)}
                className="input font-mono"
                placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
              />
              <p className="mt-2 text-sm text-surface-500">
                Get this from @BotFather on Telegram
              </p>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <div>
              <label className="label mb-2 block">Describe Your Bot</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="input min-h-[150px]"
                placeholder="A customer support bot that answers questions about our product, handles FAQs, and escalates complex issues..."
              />
              <p className="mt-2 text-sm text-surface-500">
                Be specific about what you want your bot to do
              </p>
            </div>
            <div>
              <label className="label mb-2 block">Additional Constraints (optional)</label>
              <textarea
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                className="input"
                placeholder="Only respond in English, keep responses under 200 words..."
              />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            {MODULES.map((module) => (
              <label
                key={module.id}
                className={`flex cursor-pointer items-center gap-4 rounded-lg border p-4 transition-colors ${
                  selectedModules.includes(module.id)
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-surface-200 hover:border-surface-300'
                } ${module.id === 'basic_commands' ? 'opacity-60' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={selectedModules.includes(module.id)}
                  onChange={() => toggleModule(module.id)}
                  disabled={module.id === 'basic_commands'}
                  className="h-4 w-4 rounded border-surface-300 text-primary-600"
                />
                <div>
                  <p className="font-medium text-surface-900">{module.name}</p>
                  <p className="text-sm text-surface-500">{module.description}</p>
                </div>
              </label>
            ))}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-6">
            {specErrors.length > 0 && (
              <div className="rounded bg-danger-50 p-4 text-danger-700">
                <p className="font-medium">Generation errors:</p>
                <ul className="mt-2 list-inside list-disc">
                  {specErrors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {generatedSpec ? (
              <div>
                <div className="mb-4 flex items-center gap-2 text-success-700">
                  <Check className="h-5 w-5" />
                  <span className="font-medium">Spec generated successfully</span>
                </div>
                <pre className="max-h-96 overflow-auto rounded bg-surface-100 p-4 text-sm">
                  {JSON.stringify(generatedSpec, null, 2)}
                </pre>
              </div>
            ) : (
              <div className="text-center py-8">
                <Sparkles className="mx-auto h-12 w-12 text-primary-400" />
                <p className="mt-4 text-surface-600">
                  Ready to generate your bot configuration with AI
                </p>
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="btn-primary mt-6"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate BotSpec
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {step === 5 && pricing && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              {pricing.tiers.map((tier) => (
                <button
                  key={tier.id}
                  onClick={() => setSelectedTier(tier)}
                  className={`rounded-lg border p-4 text-left transition-colors ${
                    selectedTier?.id === tier.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-surface-200 hover:border-surface-300'
                  }`}
                >
                  {tier.recommended && (
                    <span className="badge badge-info mb-2">Recommended</span>
                  )}
                  <p className="font-semibold text-surface-900">{tier.name}</p>
                  <p className="text-2xl font-bold text-primary-600">
                    {tier.price_sol} SOL<span className="text-sm font-normal">/mo</span>
                  </p>
                  <ul className="mt-4 space-y-2 text-sm text-surface-600">
                    {tier.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <Check className="h-4 w-4 text-success-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </button>
              ))}
            </div>

            <div className="border-t pt-6">
              <label className="label mb-2 block">Or set custom price</label>
              <div className="flex items-center gap-4">
                <input
                  type="number"
                  value={customPrice}
                  onChange={(e) => {
                    setCustomPrice(parseFloat(e.target.value) || 0);
                    setSelectedTier(null);
                  }}
                  min={pricing.min}
                  max={pricing.max}
                  step={0.01}
                  className="input w-32"
                />
                <span className="text-surface-600">SOL/month</span>
              </div>
              <p className="mt-2 text-sm text-surface-500">
                Range: {pricing.min} - {pricing.max} SOL
              </p>
            </div>
          </div>
        )}

        {step === 6 && paymentInfo && (
          <div className="space-y-6 text-center">
            <div className="mx-auto w-fit rounded-lg bg-white p-4 shadow-soft">
              <QRCodeSVG value={paymentInfo.solana_pay_url} size={200} />
            </div>

            <div>
              <p className="text-2xl font-bold text-surface-900">
                {paymentInfo.amount_sol} SOL
              </p>
              <p className="text-surface-500">Send to activate your bot</p>
            </div>

            <div className="rounded bg-surface-100 p-4 text-left">
              <p className="text-sm text-surface-500">Recipient</p>
              <p className="font-mono text-sm break-all">{paymentInfo.recipient}</p>

              <p className="mt-4 text-sm text-surface-500">Reference</p>
              <div className="flex items-center gap-2">
                <p className="font-mono text-sm break-all">{paymentInfo.reference}</p>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(paymentInfo.reference);
                    toast.success('Copied');
                  }}
                  className="text-primary-600 hover:text-primary-700"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
            </div>

            <button onClick={handleVerifyPayment} className="btn-primary">
              I&apos;ve Paid - Verify Payment
            </button>

            <p className="text-sm text-surface-500">
              Payment expires: {new Date(paymentInfo.expires_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="mt-6 flex justify-between">
        <button
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 1}
          className="btn-secondary"
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back
        </button>

        {step < 4 && (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canProceed()}
            className="btn-primary"
          >
            Next
            <ChevronRight className="ml-2 h-4 w-4" />
          </button>
        )}

        {step === 4 && generatedSpec && (
          <button
            onClick={() => setStep(5)}
            className="btn-primary"
          >
            Continue to Pricing
            <ChevronRight className="ml-2 h-4 w-4" />
          </button>
        )}

        {step === 5 && (
          <button
            onClick={handleCreateAndPay}
            disabled={isCreating || !canProceed()}
            className="btn-primary"
          >
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                Create & Pay
                <ChevronRight className="ml-2 h-4 w-4" />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
