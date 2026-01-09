# Security Documentation

## Overview

This document describes the security model and hardening measures for the Telegram Bot Creator platform.

## Authentication & Authorization

### JWT Authentication

- Tokens stored in **HttpOnly cookies** (not accessible to JavaScript)
- **SameSite=Lax** to prevent CSRF on cross-origin requests
- **Secure flag** enabled in production (HTTPS only)
- Token expiration: 24 hours (configurable)
- Tokens contain: user_id, role, CSRF token, expiration

### CSRF Protection

- Double-submit cookie pattern
- CSRF token embedded in JWT, must match X-CSRF-Token header
- Required for all mutating requests (POST, PUT, DELETE, PATCH)
- Exempt paths: /auth/login, /auth/register, /runner/* (internal)

### Role-Based Access Control

- **User role**: Can manage own bots, create invoices
- **Admin role**: Can manage all users/bots, override subscriptions

## Secrets Management

### Encryption at Rest

- **Telegram tokens**: Encrypted with Fernet (AES-128-CBC)
- Master encryption key from environment variable
- Key rotation: Generate new key, re-encrypt all tokens, update env

### Environment Variables

Sensitive variables that MUST be set and kept secret:
- `JWT_SECRET`: JWT signing key (min 32 chars)
- `CSRF_SECRET`: CSRF token generation
- `ENCRYPTION_KEY`: Fernet key for token encryption
- `RUNNER_SHARED_SECRET`: Internal runner-API auth
- `OPENROUTER_API_KEY`: AI generation service

### Secrets in Logs

- All logging sanitizes sensitive fields
- Tokens, passwords, API keys replaced with `[REDACTED]`
- See `core/security.py:sanitize_log_data()`

## Input Validation

### BotSpec Validation

The BotSpec schema rejects:
- Unknown fields (prevents injection)
- Dangerous system prompts (prompt injection attempts)
- Private/internal webhook URLs
- Reserved command names
- Values outside allowed bounds

### Webhook URL Validation

Blocked URLs:
- `localhost`, `127.0.0.1`, `0.0.0.0`
- Private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Cloud metadata endpoints (169.254.169.254)
- Non-HTTPS URLs

### Rate Limiting

- **AI Generation**: 10 requests/hour/user (configurable)
- **API General**: 100 requests/minute/IP (TODO: implement middleware)
- **Bot Messages**: Configured in BotSpec limits

## Docker Security

### Socket Access

The API container mounts Docker socket read-only:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

**Risks**:
- Socket access = root equivalent on host
- Malicious container escape could compromise host

**Mitigations**:
- API runs as non-root user
- Socket mounted read-only where possible
- Consider Docker socket proxy (docker-socket-proxy) in production
- Network isolation for bot containers

### Container Isolation

Bot containers are isolated:
- Separate network namespace
- Resource limits (memory, CPU)
- No volume mounts (stateless)
- No privileged mode
- Run as non-root user

### Image Security

- Base images from official sources (python:3.11-slim)
- Dependencies pinned to specific versions
- No secrets in images (passed as env vars at runtime)

## Network Security

### Internal Communication

- All services on private Docker network
- Only proxy exposed to public internet
- API ↔ Runner communication via internal network
- Database/Redis not exposed externally

### TLS

- Caddy handles TLS termination
- Auto-provisions certificates via Let's Encrypt
- HTTP redirected to HTTPS
- HSTS header in production

## Solana Payment Security

### Invoice Verification

- Unique reference key per invoice (unforgeable)
- Amount verified on-chain
- Treasury address verified
- Transaction must be confirmed (not just submitted)

### Treasury Wallet

- Controlled by admin (private key NOT stored in app)
- Consider multi-sig for production
- Automated sweep to cold storage recommended

## Hardening Checklist

### Before Production

- [ ] Change all default secrets
- [ ] Use strong, unique passwords
- [ ] Enable TLS (set APP_DOMAIN)
- [ ] Review Caddyfile security headers
- [ ] Set up firewall (only 80, 443 open)
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Review Docker daemon config
- [ ] Consider docker-socket-proxy
- [ ] Set up database backups
- [ ] Enable PostgreSQL SSL

### Regular Maintenance

- [ ] Rotate JWT_SECRET quarterly
- [ ] Review audit logs
- [ ] Update dependencies
- [ ] Review rate limit settings
- [ ] Monitor for unusual activity

## Incident Response

### If Credentials Leaked

1. Rotate affected secret immediately
2. If JWT_SECRET: All sessions invalidated
3. If ENCRYPTION_KEY: Re-encrypt all Telegram tokens
4. Review audit logs for suspicious activity
5. Notify affected users if data compromised

### If Bot Token Compromised

1. User should revoke token via @BotFather
2. Update token in platform
3. Investigate how token was exposed

### If Database Compromised

1. Take system offline
2. Assess scope of breach
3. Telegram tokens are encrypted (attacker needs ENCRYPTION_KEY)
4. Passwords are hashed (bcrypt)
5. Notify users, force password resets
6. Review and patch vulnerability
