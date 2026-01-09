# Telegram Bot Creator

## What is this?
A production-grade web platform for creating and hosting Telegram bots with AI-powered configuration and Solana subscription payments.

## Tech Stack
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Bot Runtime**: Python (python-telegram-bot), Docker containers
- **AI**: OpenRouter API
- **Payments**: Solana (SOL) via Solana Pay reference keys
- **Proxy**: Caddy (auto-TLS)
- **Container**: Docker Compose

## Project Structure
```
/
├── apps/
│   ├── web/          # Next.js frontend
│   ├── api/          # FastAPI backend
│   └── runner/       # Bot runner (Docker image)
├── infra/            # Docker configs, Caddyfile
├── docs/             # Documentation
├── scripts/          # Ops scripts
└── .github/          # CI workflows
```

## How to Run

### Prerequisites
- Docker & Docker Compose v2
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local API dev)

### Quick Start
```bash
# 1. Configure
cp .env.example .env
# Edit .env with your values

# 2. Start
docker compose up --build

# 3. Access
# Dashboard: http://localhost:3000
# API: http://localhost:8000
```

### Create Admin
```bash
docker compose exec api python -m scripts.create_admin --email admin@example.com --password yourpassword
```

## Key Files
- `/apps/api/schemas/botspec.py` - BotSpec validation schema (critical for security)
- `/apps/api/services/bot_service.py` - Bot lifecycle management
- `/apps/api/services/payment_service.py` - Solana payment verification
- `/apps/runner/main.py` - Bot runner entry point
- `/docker-compose.yml` - Service orchestration

## Architecture Decisions
1. **Per-bot Docker containers**: Better isolation vs shared process
2. **BotSpec → Templates**: AI generates JSON config, NOT executable code
3. **Solana Pay reference keys**: Most reliable invoice matching method
4. **JWT in HttpOnly cookies**: Secure auth with CSRF protection

## Recent Changes
- 2024-01-XX: Initial implementation complete
  - Full API with auth, bots, payments, admin
  - Next.js dashboard with bot wizard
  - Docker Compose deployment
  - BotSpec validation with security checks

## Next Steps
- [ ] Add API rate limiting middleware
- [ ] Implement docker-socket-proxy for security
- [ ] Add dependency vulnerability scanning
- [ ] Consider MFA support
- [ ] Production deployment guide

## Environment Variables (Required)
See `.env.example` for full list. Critical ones:
- `JWT_SECRET` - JWT signing (min 32 chars)
- `ENCRYPTION_KEY` - Fernet key for token encryption
- `OPENROUTER_API_KEY` - AI generation
- `SOLANA_TREASURY_ADDRESS` - Payment destination
- `RUNNER_SHARED_SECRET` - Internal auth

## Commands
```bash
# Dev
docker compose up --build

# Prod
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Migrations
docker compose exec api alembic upgrade head

# Tests
cd apps/api && pytest

# Backup
./scripts/backup.sh
```

## Docs
- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [API Reference](docs/API.md)
- [Runbook](docs/RUNBOOK.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Assumptions](ASSUMPTIONS.md)
