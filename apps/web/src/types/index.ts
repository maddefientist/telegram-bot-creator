export interface User {
  id: string;
  email: string | null;
  wallet_address: string | null;
  auth_method: 'email' | 'wallet';
  role: 'user' | 'admin';
  is_active: boolean;
  created_at: string;
}

export interface Bot {
  id: string;
  name: string;
  telegram_username: string | null;
  spec_json: BotSpec;
  status: BotStatus;
  last_heartbeat: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  subscription: Subscription | null;
}

export type BotStatus = 'stopped' | 'starting' | 'running' | 'stopping' | 'error' | 'deleted';

export interface Subscription {
  id: string;
  bot_id: string;
  price_per_month_sol: number;
  state: SubscriptionState;
  active_until: string | null;
  grace_until: string | null;
  created_at: string;
}

export type SubscriptionState = 'pending' | 'active' | 'grace' | 'expired' | 'cancelled';

export interface Invoice {
  id: string;
  bot_id: string;
  amount_sol: number;
  treasury_address: string;
  reference: string;
  status: InvoiceStatus;
  tx_signature: string | null;
  paid_at: string | null;
  expires_at: string;
  created_at: string;
}

export type InvoiceStatus = 'pending' | 'confirming' | 'paid' | 'expired' | 'cancelled';

export interface PaymentInfo {
  invoice_id: string;
  amount_sol: number;
  recipient: string;
  reference: string;
  expires_at: string;
  solana_pay_url: string;
  qr_data?: string;
}

export interface PricingTier {
  id: string;
  name: string;
  description: string;
  price_sol: number;
  features: string[];
  recommended: boolean;
}

export interface PricingConfig {
  min_sol: number;
  max_sol: number;
  default_sol: number;
  tiers: PricingTier[];
}

export interface BotSpec {
  name: string;
  description: string;
  enabled_modules: ModuleType[];
  commands: CommandConfig[];
  ai_chat: AIChatConfig;
  moderation: ModerationConfig;
  webhook: WebhookConfig;
  limits: LimitsConfig;
  welcome_message: string;
  help_footer: string;
}

export type ModuleType = 'basic_commands' | 'static_replies' | 'ai_chat' | 'moderation' | 'webhook_forward';

export interface CommandConfig {
  command: string;
  description: string;
  response_type: 'text' | 'markdown' | 'html';
  response_payload: string;
}

export interface AIChatConfig {
  enabled: boolean;
  system_prompt: string;
  allowed_topics: string[];
  disallowed_topics: string[];
  max_tokens: number;
  temperature: number;
  max_context_messages: number;
}

export interface ModerationConfig {
  enabled: boolean;
  blocked_words: string[];
  block_links: boolean;
  block_forwards: boolean;
  warn_before_ban: number;
  auto_delete_violations: boolean;
}

export interface WebhookConfig {
  enabled: boolean;
  url: string;
  secret: string;
  events: string[];
}

export interface LimitsConfig {
  max_messages_per_user_per_minute: number;
  max_messages_per_chat_per_minute: number;
  max_ai_requests_per_user_per_day: number;
  cooldown_seconds: number;
}

export interface GenerateBotSpecRequest {
  description: string;
  bot_name: string;
  enabled_modules: ModuleType[];
  constraints: string;
}

export interface GenerateBotSpecResponse {
  success: boolean;
  spec: BotSpec | null;
  errors: string[];
  tokens_used: number;
  retries: number;
}

export interface ApiError {
  detail: string;
}
