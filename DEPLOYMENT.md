# Deployment Guide

## GitHub Repository
**URL:** https://github.com/maddefientist/telegram-bot-creator

## Deployments

### 1. Local Development
**Location:** `/Users/admin/telegrambotcreator`
**Purpose:** Local testing and development

**Status:** ✅ Synced with GitHub (commit: bad3593)

**Running Services:**
```bash
cd /Users/admin/telegrambotcreator
docker compose up -d
```

**Accessing:**
- API: http://localhost:8000
- Web: http://localhost:3000
- Docs: http://localhost:8000/docs

### 2. Production (webvm)
**Location:** `/opt/telegrambotcreator`
**Purpose:** Production deployment

**Status:** ✅ Deployed and synced with GitHub (commit: bad3593)

**Running Services:**
```bash
ssh webvm "cd /opt/telegrambotcreator && docker compose ps"
```

- ✅ API (healthy) - Internal port 8000
- ✅ Database (healthy) - PostgreSQL 16
- ✅ Redis (healthy)
- ✅ Docker Proxy (healthy)
- ✅ Web (running) - Internal port 3000

**Accessing:** Configure Cloudflare Tunnel or Caddy to expose services

## Keeping Deployments Synced

### Update Local from GitHub
```bash
cd /Users/admin/telegrambotcreator
git pull origin main
docker compose down && docker compose up -d --build
```

### Update Production (webvm) from GitHub
```bash
ssh webvm "cd /opt/telegrambotcreator && \
  git pull origin main && \
  docker compose down && \
  docker compose up -d --build"
```

### Push Changes to GitHub
```bash
cd /Users/admin/telegrambotcreator
git add -A
git commit -m "Your commit message"
git push origin main
```

## Environment Configuration

Both deployments require a `.env` file. Copy from `.env.example` and configure:

**Required Variables:**
- `JWT_SECRET` - JWT token signing key (generate with `openssl rand -hex 32`)
- `CSRF_SECRET` - CSRF protection key
- `ENCRYPTION_KEY` - Fernet key for encrypting Telegram tokens
- `RUNNER_SHARED_SECRET` - Shared secret for runner auth
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `SOLANA_TREASURY_ADDRESS` - Your Solana wallet for receiving payments

**Database:**
- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_USER/PASSWORD/DB` - Database credentials

**Solana:**
- `SOLANA_RPC_URL` - Solana RPC endpoint (mainnet/devnet)

## Database Migrations

After pulling updates that include database changes:

```bash
# Local
docker compose exec api alembic upgrade head

# Production (webvm)
ssh webvm "cd /opt/telegrambotcreator && docker compose exec api alembic upgrade head"
```

## Current Features

### ✅ Wallet Authentication (Latest)
- Solana wallet sign-in (Phantom, Solflare)
- Ed25519 signature verification
- Separate wallet-based accounts
- Optional email collection
- Auto-registration on first connect

### Core Features
- Email/password authentication
- JWT-based session management
- Telegram bot creation and management
- AI-powered bot spec generation (OpenRouter)
- Solana payment integration
- Docker-based bot runtime
- Admin dashboard

## Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs -f

# Restart specific service
docker compose restart api

# Full restart
docker compose down && docker compose up -d
```

### Database issues
```bash
# Reset database (⚠️ destructive)
docker compose down -v
docker compose up -d
docker compose exec api alembic upgrade head
```

### Port conflicts
If port 80 is already in use (Caddy running), the proxy service won't start. This is expected. Access services via their internal ports or configure Caddy to proxy to them.

## Monitoring

### Check service health
```bash
# Local
docker compose ps

# Production
ssh webvm "cd /opt/telegrambotcreator && docker compose ps"
```

### View logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api

# Last 100 lines
docker compose logs --tail 100 api
```

## Backup

Database backups can be created with:
```bash
./scripts/backup.sh
```

Backups are stored in `./backups/` directory.

## Next Steps

1. **Configure Production Environment:**
   - Add real OpenRouter API key
   - Add real Solana treasury wallet address
   - Update SOLANA_RPC_URL to mainnet endpoint

2. **Expose Services:**
   - Configure Cloudflare Tunnel on mypi
   - Or update Caddy config to proxy to services
   - Set up domain/subdomain

3. **Security:**
   - Enable HTTPS/TLS
   - Configure rate limiting
   - Set up monitoring/alerts
   - Review security settings in production

4. **Testing:**
   - Test wallet auth flow end-to-end
   - Test bot creation and deployment
   - Test payment flow with Solana
