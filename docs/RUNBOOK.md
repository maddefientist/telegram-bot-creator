# Operations Runbook

## Common Operations

### Starting the Stack

```bash
# Development
docker compose up --build

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Build runner image (required for bot containers)
docker compose build runner
```

### Stopping the Stack

```bash
docker compose down

# Also remove volumes (WARNING: deletes data)
docker compose down -v
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api
```

### Database Operations

#### Run Migrations

```bash
docker compose exec api alembic upgrade head
```

#### Create Migration

```bash
docker compose exec api alembic revision --autogenerate -m "description"
```

#### Rollback Migration

```bash
docker compose exec api alembic downgrade -1
```

#### Database Shell

```bash
docker compose exec db psql -U postgres -d botcreator
```

### User Management

#### Create Admin User

```bash
docker compose exec api python -m scripts.create_admin \
  --email admin@example.com \
  --password "SecurePassword123"
```

### Bot Container Operations

#### List Running Bot Containers

```bash
docker ps --filter "label=botcreator.managed=true"
```

#### View Bot Container Logs

```bash
# By container name (bot-{first 8 chars of bot_id})
docker logs -f bot-abc12345

# By bot ID
docker logs -f $(docker ps -q --filter "label=botcreator.bot_id=<bot-uuid>")
```

#### Stop All Bot Containers

```bash
docker stop $(docker ps -q --filter "label=botcreator.managed=true")
```

#### Remove All Bot Containers

```bash
docker rm -f $(docker ps -aq --filter "label=botcreator.managed=true")
```

## Backups

### Database Backup

```bash
# Create backup
docker compose exec db pg_dump -U postgres botcreator > backup_$(date +%Y%m%d).sql

# With compression
docker compose exec db pg_dump -U postgres botcreator | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Database Restore

```bash
# Stop API first to prevent connections
docker compose stop api

# Restore
docker compose exec -T db psql -U postgres botcreator < backup.sql

# Restart API
docker compose start api
```

### Automated Backups (Cron)

Add to crontab:
```bash
# Daily backup at 3am
0 3 * * * cd /path/to/project && docker compose exec -T db pg_dump -U postgres botcreator | gzip > /backups/botcreator_$(date +\%Y\%m\%d).sql.gz

# Keep last 7 days
0 4 * * * find /backups -name "botcreator_*.sql.gz" -mtime +7 -delete
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# API readiness (includes DB check)
curl http://localhost:8000/health/ready

# Metrics
curl http://localhost:8000/metrics
```

### Resource Usage

```bash
# All containers
docker stats

# Specific service
docker stats botcreator-api-1
```

## Troubleshooting

### API Won't Start

1. Check logs: `docker compose logs api`
2. Verify database is healthy: `docker compose ps db`
3. Check environment variables
4. Verify database connection

### Database Connection Failed

```bash
# Check if postgres is running
docker compose ps db

# Check postgres logs
docker compose logs db

# Test connection
docker compose exec db pg_isready
```

### Bot Container Won't Start

1. Check API logs for Docker errors
2. Verify runner image exists: `docker images | grep runner`
3. Rebuild if needed: `docker compose build runner`
4. Check bot status in database

### Payment Not Detected

1. Check invoice status in admin panel
2. Verify transaction on Solana explorer
3. Check reference key matches
4. Check background worker logs
5. Manually trigger verification via API

### SSL Certificate Issues

```bash
# Check Caddy logs
docker compose logs proxy

# Force certificate renewal
docker compose exec proxy caddy reload --config /etc/caddy/Caddyfile
```

## Key Rotation

### JWT Secret Rotation

1. Set new JWT_SECRET in .env
2. Restart API: `docker compose restart api`
3. All existing sessions will be invalidated
4. Users will need to log in again

### Encryption Key Rotation

This requires re-encrypting all Telegram tokens:

```bash
# 1. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Create migration script to re-encrypt tokens
# (You'll need to implement this based on your needs)

# 3. Update ENCRYPTION_KEY in .env
# 4. Run migration
# 5. Restart API
```

## Scaling

### Horizontal Scaling (Multiple API Instances)

1. Use external PostgreSQL (managed service)
2. Use external Redis (managed service)
3. Configure load balancer
4. Ensure all instances share secrets

### Vertical Scaling

Adjust resource limits in `docker-compose.prod.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
```

## Emergency Procedures

### Complete System Shutdown

```bash
# Stop everything gracefully
docker compose down

# Stop all bot containers
docker stop $(docker ps -q --filter "label=botcreator.managed=true")
```

### Database Emergency Access

```bash
# Direct database access bypassing API
docker compose exec db psql -U postgres -d botcreator

# Emergency: disable all bots
UPDATE bots SET status = 'stopped';
UPDATE subscriptions SET state = 'expired';
```

### Recovery from Backup

```bash
# 1. Stop all services
docker compose down

# 2. Remove existing database volume
docker volume rm telegrambotcreator_postgres_data

# 3. Start database only
docker compose up -d db
sleep 10

# 4. Restore backup
docker compose exec -T db psql -U postgres botcreator < backup.sql

# 5. Start remaining services
docker compose up -d
```
