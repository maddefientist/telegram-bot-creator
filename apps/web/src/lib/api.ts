import type {
  User,
  Bot,
  Invoice,
  PaymentInfo,
  PricingConfig,
  BotSpec,
  GenerateBotSpecRequest,
  GenerateBotSpecResponse,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

class ApiClient {
  private csrfToken: string | null = null;

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add CSRF token for mutating requests
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method || '')) {
      if (this.csrfToken) {
        (headers as Record<string, string>)['X-CSRF-Token'] = this.csrfToken;
      }
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Request failed');
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  setCsrfToken(token: string) {
    this.csrfToken = token;
  }

  // Auth
  async register(email: string, password: string): Promise<User> {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async login(email: string, password: string): Promise<{ user: User; csrf_token: string }> {
    const response = await this.request<{ message: string; csrf_token: string; user: User }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    );
    this.csrfToken = response.csrf_token;
    return response;
  }

  async logout(): Promise<void> {
    await this.request<void>('/auth/logout', { method: 'POST' });
    this.csrfToken = null;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async refreshToken(): Promise<{ csrf_token: string }> {
    const response = await this.request<{ message: string; csrf_token: string }>(
      '/auth/refresh',
      { method: 'POST' }
    );
    this.csrfToken = response.csrf_token;
    return response;
  }

  // Wallet Auth
  async requestWalletNonce(walletAddress: string): Promise<{
    nonce: string;
    message: string;
    expires_in: number;
  }> {
    return this.request('/auth/wallet/nonce', {
      method: 'POST',
      body: JSON.stringify({ wallet_address: walletAddress }),
    });
  }

  async registerWallet(
    walletAddress: string,
    signature: string,
    nonce: string,
    email?: string
  ): Promise<User> {
    return this.request<User>('/auth/wallet/register', {
      method: 'POST',
      body: JSON.stringify({
        wallet_address: walletAddress,
        signature,
        nonce,
        email,
      }),
    });
  }

  async loginWallet(
    walletAddress: string,
    signature: string,
    nonce: string
  ): Promise<{ user: User; csrf_token: string }> {
    const response = await this.request<{ message: string; csrf_token: string; user: User }>(
      '/auth/wallet/login',
      {
        method: 'POST',
        body: JSON.stringify({
          wallet_address: walletAddress,
          signature,
          nonce,
        }),
      }
    );
    this.csrfToken = response.csrf_token;
    return response;
  }

  // Bots
  async getBots(): Promise<Bot[]> {
    return this.request<Bot[]>('/bots');
  }

  async getBot(id: string): Promise<Bot> {
    return this.request<Bot>(`/bots/${id}`);
  }

  async createBot(data: {
    name: string;
    telegram_token: string;
    description: string;
    price_per_month_sol: number;
  }): Promise<Bot> {
    return this.request<Bot>('/bots', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateBotSpec(id: string, spec: BotSpec): Promise<Bot> {
    return this.request<Bot>(`/bots/${id}/spec`, {
      method: 'PUT',
      body: JSON.stringify(spec),
    });
  }

  async startBot(id: string): Promise<{ message: string; status: string }> {
    return this.request(`/bots/${id}/start`, { method: 'POST' });
  }

  async stopBot(id: string): Promise<{ message: string; status: string }> {
    return this.request(`/bots/${id}/stop`, { method: 'POST' });
  }

  async restartBot(id: string): Promise<{ message: string; status: string }> {
    return this.request(`/bots/${id}/restart`, { method: 'POST' });
  }

  async getBotStatus(id: string): Promise<{
    id: string;
    status: string;
    last_heartbeat: string | null;
    last_error: string | null;
    container_id: string | null;
    logs: string[];
  }> {
    return this.request(`/bots/${id}/status`);
  }

  async getBotLogs(id: string, tail: number = 100): Promise<{ bot_id: string; logs: string[] }> {
    return this.request(`/bots/${id}/logs?tail=${tail}`);
  }

  async deleteBot(id: string): Promise<void> {
    return this.request(`/bots/${id}`, { method: 'DELETE' });
  }

  async validateBotSpec(spec: object): Promise<{
    valid: boolean;
    errors: string[];
    validated_spec: BotSpec | null;
  }> {
    return this.request('/bots/validate-spec', {
      method: 'POST',
      body: JSON.stringify({ spec }),
    });
  }

  // AI
  async generateBotSpec(data: GenerateBotSpecRequest): Promise<GenerateBotSpecResponse> {
    return this.request<GenerateBotSpecResponse>('/ai/generate-botspec', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Payments
  async getPricing(): Promise<PricingConfig> {
    return this.request<PricingConfig>('/payments/pricing');
  }

  async createInvoice(botId: string, months: number = 1): Promise<PaymentInfo> {
    return this.request<PaymentInfo>('/payments/invoices', {
      method: 'POST',
      body: JSON.stringify({ bot_id: botId, months }),
    });
  }

  async getInvoice(id: string): Promise<Invoice> {
    return this.request<Invoice>(`/payments/invoices/${id}`);
  }

  async getInvoices(botId?: string): Promise<Invoice[]> {
    const query = botId ? `?bot_id=${botId}` : '';
    return this.request<Invoice[]>(`/payments/invoices${query}`);
  }

  async verifyPayment(invoiceId: string): Promise<{
    invoice_id: string;
    status: string;
    message: string;
    subscription_active_until: string | null;
  }> {
    return this.request('/payments/verify', {
      method: 'POST',
      body: JSON.stringify({ invoice_id: invoiceId }),
    });
  }
}

export const api = new ApiClient();
