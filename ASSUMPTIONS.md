# Assumptions

This document lists assumptions made during implementation. Review and adjust as needed.

## Infrastructure

1. **Linux VM with Docker**: Target deployment is a Linux VM with Docker and Docker Compose v2 installed.

2. **Single-Server Deployment**: MVP assumes single-server deployment. Multi-server scaling requires additional orchestration (Kubernetes, Docker Swarm).

3. **Docker Socket Access**: The API container needs access to Docker socket for managing bot containers. This is a security trade-off documented in SECURITY.md.

4. **Public Solana RPC**: Payment verification uses public Solana RPC endpoints. For production, consider dedicated RPC providers (Helius, QuickNode) for reliability.

5. **DNS/TLS Later**: Local development uses HTTP. Production TLS via Caddy requires domain configuration.

## Authentication & Security

1. **Email-Based Auth**: Users authenticate with email/password. OAuth providers not included in MVP.

2. **Single Tenant**: One organization/deployment. Multi-tenancy not implemented.

3. **Admin Bootstrap**: First admin created via CLI script. No self-service admin registration.

4. **Session Duration**: JWT tokens expire after 24 hours. Refresh token rotation not implemented (consider for production).

## Payments

1. **SOL Only**: Payments accepted only in SOL (not SPL tokens). Adding token support requires schema changes.

2. **Reference Key Method**: Using Solana Pay reference keys for invoice matching. This is the most reliable method that doesn't require memo support.

3. **Manual Treasury**: Treasury address is a standard wallet. For production, consider:
   - Multi-sig treasury
   - Automated sweep to cold storage
   - Payment processor integration

4. **No Refunds**: Refunds are manual admin actions. Automated refund flow not implemented.

5. **Price in SOL**: Prices stored in SOL, not USD. No automatic USD conversion.

6. **Polling Verification**: Payment verification polls Solana RPC. Webhook-based verification (via Helius etc.) would be more efficient at scale.

## Bot Runtime

1. **Polling Mode**: Bots use Telegram polling, not webhooks. This simplifies deployment (no public URL per bot) but is less efficient.

2. **No Persistent State**: Bot state is ephemeral. If a bot needs persistence, it should use the API or external storage.

3. **Resource Limits**: Default container limits (256MB RAM, 0.5 CPU). Adjustable but not per-user configurable in MVP.

4. **Single Region**: All bots run on the same VM. Geo-distribution not implemented.

5. **Python Runtime**: Bots use Python runtime only. Other languages not supported.

## AI Integration

1. **OpenRouter Only**: AI generation uses OpenRouter. Direct provider integrations not included.

2. **Model Selection**: Users cannot select AI model. Admin configures default model.

3. **No Fine-Tuning**: Uses base models with prompt engineering. No custom fine-tuned models.

4. **English Primary**: System prompts and validation optimized for English. Other languages may work but aren't specifically tested.

5. **Rate Limits**: Per-user AI generation limits (10/hour default). Consider cost implications.

## BotSpec Constraints

1. **Predefined Modules**: Bots can only use predefined modules:
   - BasicCommands
   - StaticReplies
   - AIChat
   - Moderation
   - WebhookForward

2. **No Custom Code**: Users cannot write custom Python code. All behavior is configured through BotSpec JSON.

3. **No File Access**: Bots cannot access filesystem, network (except Telegram API and configured webhooks), or system resources.

4. **Webhook Restrictions**: Webhook URLs must be public HTTPS endpoints. Private IPs, localhost, and metadata URLs blocked.

## Database

1. **PostgreSQL**: Postgres is the only supported database. SQLite for local dev not supported due to async SQLAlchemy.

2. **UTC Timestamps**: All timestamps stored in UTC.

3. **Soft Deletes**: Bots are soft-deleted (status='deleted'). Hard delete requires manual DB operation.

## Frontend

1. **Modern Browsers**: Supports modern browsers only (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+).

2. **No Mobile App**: Web dashboard only. Native mobile apps not included.

3. **English UI**: Interface is English only. i18n not implemented.

## Operations

1. **Manual Backups**: Backup scripts provided but not automated. Set up cron jobs for production.

2. **No Alerting**: Monitoring endpoints provided but no alerting integration. Connect to your preferred alerting system.

3. **Log Rotation**: Docker handles log rotation. Configure Docker daemon for production log limits.

## Scaling Considerations

For scaling beyond MVP:

1. **Database**: Add read replicas, connection pooling (PgBouncer)
2. **Redis**: Switch to Redis Cluster or managed Redis
3. **Bot Hosting**: Kubernetes or Docker Swarm for container orchestration
4. **Payments**: Integrate Sphere, Helio, or similar payment processor
5. **CDN**: Add CDN for static assets
6. **Queue**: Consider dedicated message broker (RabbitMQ) for complex workflows

## Third-Party Dependencies

1. **OpenRouter**: Requires active OpenRouter account with credits
2. **Telegram**: Requires Telegram Bot API (BotFather tokens)
3. **Solana**: Requires working Solana RPC endpoint
4. **Docker Hub**: Base images pulled from Docker Hub

## Compliance

1. **No PII Handling**: System stores minimal PII (email). GDPR/CCPA compliance requires additional work.

2. **No Content Moderation**: User-generated bot descriptions not moderated beyond BotSpec validation.

3. **Telegram ToS**: Users responsible for their bots' Telegram ToS compliance.

4. **No Audit Export**: Audit logs stored in DB but no export functionality in MVP.
