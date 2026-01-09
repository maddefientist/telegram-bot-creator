# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Caddy Reverse Proxy                                  │
│                    (TLS termination, routing)                                │
│                           :80, :443                                          │
└──────────────┬───────────────────────────────────┬──────────────────────────┘
               │                                   │
               ▼                                   ▼
┌──────────────────────────┐         ┌──────────────────────────┐
│       Next.js Web        │         │      FastAPI Backend     │
│        (Frontend)        │◄───────►│          (API)           │
│          :3000           │         │          :8000           │
└──────────────────────────┘         └─────────────┬────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────┐
                    │                              │                          │
                    ▼                              ▼                          ▼
         ┌───────────────────┐        ┌───────────────────┐      ┌───────────────────┐
         │    PostgreSQL     │        │       Redis       │      │   Docker Daemon   │
         │     (Database)    │        │  (Cache/Queue)    │      │  (Bot Containers) │
         │       :5432       │        │       :6379       │      │                   │
         └───────────────────┘        └───────────────────┘      └─────────┬─────────┘
                                                                           │
                                                          ┌────────────────┼────────────────┐
                                                          │                │                │
                                                          ▼                ▼                ▼
                                                    ┌──────────┐    ┌──────────┐    ┌──────────┐
                                                    │ Bot #1   │    │ Bot #2   │    │ Bot #N   │
                                                    │ Container│    │ Container│    │ Container│
                                                    └──────────┘    └──────────┘    └──────────┘
```

## Components

### 1. Caddy Reverse Proxy

- **Purpose**: TLS termination, request routing, security headers
- **Port**: 80 (HTTP redirect), 443 (HTTPS)
- **Features**:
  - Automatic HTTPS via Let's Encrypt
  - HTTP/2 support
  - Security headers (HSTS, X-Frame-Options, etc.)

### 2. Next.js Frontend (Web)

- **Purpose**: User interface for bot management
- **Port**: 3000
- **Technology**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Features**:
  - Server-side rendering
  - Authentication UI
  - Bot creation wizard
  - Dashboard and monitoring
  - Admin panel

### 3. FastAPI Backend (API)

- **Purpose**: Core business logic, API endpoints
- **Port**: 8000
- **Technology**: FastAPI, SQLAlchemy, Pydantic
- **Features**:
  - JWT authentication (HttpOnly cookies)
  - CSRF protection
  - BotSpec validation
  - Payment verification
  - Docker container management

### 4. PostgreSQL Database

- **Purpose**: Persistent data storage
- **Port**: 5432
- **Data stored**:
  - Users and authentication
  - Bots and specifications
  - Subscriptions and invoices
  - Audit logs

### 5. Redis

- **Purpose**: Caching and background job queue
- **Port**: 6379
- **Usage**:
  - Rate limiting counters
  - Session cache
  - Background job queue (payment verification)

### 6. Bot Containers

- **Purpose**: Run individual Telegram bots
- **Technology**: Python, python-telegram-bot
- **Isolation**: Each bot runs in its own Docker container
- **Communication**: Containers communicate with API via HTTP

## Bot Hosting Strategy

We chose **per-bot Docker containers** over a multiplexed single service:

### Advantages

1. **Isolation**: Complete process isolation between bots
2. **Resource Control**: Per-container memory/CPU limits
3. **Independent Restarts**: One bot crash doesn't affect others
4. **Debugging**: Easy to tail logs, exec into containers
5. **Security**: No shared memory or state between bots

### Trade-offs

1. **Overhead**: More memory usage per bot (~50MB base)
2. **Startup Time**: Container creation adds ~2-5 seconds
3. **Docker Socket**: API needs socket access (security consideration)

### Scaling Considerations

For 100+ bots, consider:
- Kubernetes/Docker Swarm for orchestration
- Separate runner hosts to isolate Docker socket access
- Container pooling for faster startup

## Data Flow

### Bot Creation Flow

```
User → Web → API → Validate Token → Create DB Records → Return Bot ID
                 ↓
              AI Service → OpenRouter → Generate BotSpec → Validate → Save
                                                                       ↓
User → Web → Select Pricing → Create Invoice → API → Generate Reference
                                                         ↓
User → Wallet → Solana → Transaction with Reference
                              ↓
Background Worker → Poll RPC → Find Transaction → Verify Amount
                                                       ↓
Update Invoice → Activate Subscription → User Notified
```

### Bot Start Flow

```
User → API → Check Subscription Active
           ↓
        Docker API → Create Container → Inject Env Vars
                          ↓
                     Container Starts → Runner Process
                          ↓
                     Fetch BotSpec from API
                          ↓
                     Initialize Modules → Start Telegram Polling
                          ↓
                     Heartbeat Loop → Report to API
```

## Security Model

See [SECURITY.md](SECURITY.md) for detailed security information.

Key points:
- BotSpec is validated, not executed as code
- Telegram tokens encrypted at rest
- JWT in HttpOnly cookies with CSRF protection
- Webhook URLs validated against private networks

## Payment Model

Uses Solana Pay reference key method:

1. Invoice created with unique reference (public key)
2. User sends SOL to treasury with reference in transaction
3. Background worker polls for transactions with reference
4. On match, verify amount and mark paid
5. Subscription activated

See [ASSUMPTIONS.md](../ASSUMPTIONS.md) for payment verification details.
