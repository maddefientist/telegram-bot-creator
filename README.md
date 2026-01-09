# Telegram Bot Creator Platform

A web dashboard for creating and hosting Telegram bots with AI-powered configuration and Solana subscription payments.

## Features

- **AI-Powered Bot Creation**: Describe what you want, get a working bot
- **Safe Execution Model**: AI generates constrained BotSpec JSON, not arbitrary code
- **Solana Payments**: Subscription-based bot hosting paid in SOL
- **Docker Isolation**: Each bot runs in its own container
- **Real-time Monitoring**: View bot status, health, and logs
- **Admin Controls**: Pricing tiers, user management, payment overrides

## Quick Start (Development)

### Prerequisites

- Docker & Docker Compose v2
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local API dev)

### 1. Clone and Configure

```bash
cp .env.example .env
# Edit .env with your values (see Environment Variables section)
```

### 2. Start Services

```bash
# Start all services
docker compose up --build

# Or in detached mode
docker compose up --build -d
```

### 3. Access

- **Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Create Admin User

```bash
docker compose exec api python -m scripts.create_admin --email admin@example.com --password yourpassword
```

## Environment Variables

Create `.env` from `.env.example`. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key for AI generation | Yes |
| `OPENROUTER_MODEL` | Model to use (default: `anthropic/claude-3.5-sonnet`) | No |
| `JWT_SECRET` | Secret for JWT signing (min 32 chars) | Yes |
| `CSRF_SECRET` | Secret for CSRF tokens | Yes |
| `ENCRYPTION_KEY` | Fernet key for encrypting Telegram tokens | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SOLANA_RPC_URL` | Solana RPC endpoint | Yes |
| `SOLANA_TREASURY_ADDRESS` | Treasury wallet for payments | Yes |
| `PRICING_MIN_SOL` | Minimum monthly price | No |
| `PRICING_MAX_SOL` | Maximum monthly price | No |
| `DEFAULT_PRICE_SOL` | Default monthly price | No |
| `GRACE_DAYS` | Grace period after subscription expires | No |
| `RUNNER_SHARED_SECRET` | Secret for runner-API auth | Yes |

### Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│  Caddy/TLS  │────▶│   Next.js   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │   Postgres  │◀────│   FastAPI   │
                    └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │    Redis    │◀────│   Workers   │
                    └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │Docker Daemon│◀────│ Bot Runners │
                    └─────────────┘     └─────────────┘
```

## Bot Hosting Strategy

**Per-Bot Docker Containers** (chosen approach):

- Each bot runs in isolated container
- Better security and resource isolation
- Independent restarts without affecting other bots
- Clear resource limits per container
- Easier debugging and log isolation

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for trade-off analysis.

## Development

### Backend (FastAPI)

```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

### Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd apps/api
pytest

# Frontend lint/typecheck
cd apps/web
npm run lint
npm run typecheck
```

## Production Deployment

See [RUNBOOK.md](docs/RUNBOOK.md) for operational procedures.

```bash
# Use production compose profile
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head
```

### TLS Setup

The included Caddy configuration automatically handles TLS. Set:

```env
APP_DOMAIN=yourdomain.com
```

## Security

See [SECURITY.md](docs/SECURITY.md) for security model and hardening.

Key security features:
- JWT auth with HttpOnly cookies
- CSRF protection (double-submit pattern)
- Telegram tokens encrypted at rest (Fernet)
- BotSpec validation rejects dangerous configs
- Rate limiting on all endpoints
- Webhook URL validation (blocks private IPs)
- Docker socket access minimized

## API Documentation

See [API.md](docs/API.md) for endpoint reference.

Interactive docs available at `/docs` when running.

## License

MIT
