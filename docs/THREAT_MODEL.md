# Threat Model

## Overview

This document identifies threats to the Telegram Bot Creator platform and describes mitigations.

## Assets

1. **User accounts** - Email, password hash
2. **Telegram bot tokens** - Access to user's bots
3. **Payment data** - Invoice records, transaction signatures
4. **Bot specifications** - User's bot configurations
5. **System secrets** - JWT key, encryption key, API keys
6. **Infrastructure** - Servers, containers, databases

## Threat Actors

1. **External attackers** - Attempting unauthorized access
2. **Malicious users** - Abusing the platform
3. **Compromised dependencies** - Supply chain attacks
4. **Insider threats** - Admin abuse

## Threats and Mitigations

### T1: Authentication Bypass

**Threat**: Attacker gains access to user account without credentials.

**Attack vectors**:
- Session hijacking (XSS stealing cookies)
- JWT token theft
- Weak password

**Mitigations**:
- ✅ HttpOnly cookies prevent JS access
- ✅ SameSite=Lax prevents CSRF
- ✅ CSRF token required for mutations
- ✅ Password minimum length enforced
- ⚠️ Consider: MFA, account lockout, password complexity

### T2: Prompt Injection

**Threat**: User manipulates AI to generate malicious BotSpec.

**Attack vectors**:
- Injecting instructions in description
- Requesting dangerous system prompts

**Mitigations**:
- ✅ BotSpec schema validation
- ✅ System prompt validation (blocks dangerous patterns)
- ✅ AI only outputs JSON, no code execution
- ✅ Limited module set (no arbitrary code)

### T3: Telegram Token Theft

**Threat**: Attacker obtains user's Telegram bot token.

**Attack vectors**:
- Database breach
- Log exposure
- API response leaking token

**Mitigations**:
- ✅ Tokens encrypted at rest (Fernet)
- ✅ Token never returned after initial set
- ✅ Logs sanitized for sensitive data
- ⚠️ Consider: Separate secrets store (Vault)

### T4: Payment Fraud

**Threat**: Attacker activates subscription without paying.

**Attack vectors**:
- Replay attack (reusing transaction)
- Fake transaction submission
- Amount manipulation

**Mitigations**:
- ✅ Unique reference per invoice (not reusable)
- ✅ On-chain verification (can't fake)
- ✅ Amount verified against expected
- ✅ Invoice expiration

### T5: SSRF via Webhooks

**Threat**: Attacker uses webhook feature to scan internal network.

**Attack vectors**:
- Webhook URL pointing to internal services
- Cloud metadata access

**Mitigations**:
- ✅ Private IP ranges blocked
- ✅ Localhost blocked
- ✅ Metadata IPs blocked
- ✅ HTTPS required

### T6: Container Escape

**Threat**: Malicious bot breaks out of container.

**Attack vectors**:
- Exploiting container runtime vulnerability
- Mounting host filesystem
- Privilege escalation

**Mitigations**:
- ✅ Containers run as non-root
- ✅ No volume mounts
- ✅ No privileged mode
- ✅ Resource limits
- ⚠️ Risk: Docker socket access from API

### T7: Docker Socket Abuse

**Threat**: Compromised API uses Docker socket for host access.

**Attack vectors**:
- Create privileged container
- Mount host filesystem
- Execute arbitrary commands

**Mitigations**:
- ⚠️ Socket mounted read-only
- ⚠️ API runs as non-root
- 🔴 Consider: docker-socket-proxy
- 🔴 Consider: Rootless Docker

### T8: Denial of Service

**Threat**: Attacker overwhelms service with requests.

**Attack vectors**:
- API flooding
- AI generation abuse
- Creating many bots

**Mitigations**:
- ✅ AI generation rate limit (10/hour)
- ⚠️ TODO: General API rate limiting
- ⚠️ TODO: Per-user bot limits
- Consider: CDN/WAF for proxy

### T9: Data Breach

**Threat**: Attacker exfiltrates database contents.

**Attack vectors**:
- SQL injection
- Unprotected backup
- Compromised credentials

**Mitigations**:
- ✅ SQLAlchemy parameterized queries
- ✅ Passwords bcrypt hashed
- ✅ Tokens encrypted
- ⚠️ TODO: Database encryption at rest
- ⚠️ TODO: Backup encryption

### T10: Supply Chain Attack

**Threat**: Malicious dependency compromises system.

**Attack vectors**:
- Compromised npm/pip package
- Typosquatting

**Mitigations**:
- ✅ Dependencies pinned to versions
- ⚠️ TODO: Dependabot/Snyk scanning
- ⚠️ TODO: Lock file integrity checks

### T11: Admin Abuse

**Threat**: Admin user misuses access.

**Attack vectors**:
- Viewing user data
- Manipulating subscriptions
- Accessing Telegram tokens

**Mitigations**:
- ✅ Audit logging of admin actions
- ⚠️ TODO: Admin action approval workflow
- ⚠️ TODO: Token access logging

### T12: Log Injection

**Threat**: Attacker injects malicious content into logs.

**Attack vectors**:
- Injecting control characters
- Log forging

**Mitigations**:
- ✅ Structured logging (JSON)
- ✅ Input sanitization
- ⚠️ Log monitoring for anomalies

## Risk Matrix

| Threat | Likelihood | Impact | Risk Level | Status |
|--------|------------|--------|------------|--------|
| T1: Auth Bypass | Medium | High | High | Mitigated |
| T2: Prompt Injection | High | Medium | High | Mitigated |
| T3: Token Theft | Low | High | Medium | Mitigated |
| T4: Payment Fraud | Low | Medium | Low | Mitigated |
| T5: SSRF | Medium | Medium | Medium | Mitigated |
| T6: Container Escape | Low | Critical | Medium | Partial |
| T7: Docker Socket | Low | Critical | High | ⚠️ Needs Work |
| T8: DoS | High | Medium | High | ⚠️ Needs Work |
| T9: Data Breach | Low | Critical | Medium | Partial |
| T10: Supply Chain | Low | Critical | Medium | ⚠️ Needs Work |
| T11: Admin Abuse | Low | High | Medium | Partial |
| T12: Log Injection | Low | Low | Low | Mitigated |

## Recommendations

### High Priority
1. Implement docker-socket-proxy to limit socket access
2. Add API rate limiting middleware
3. Set up dependency vulnerability scanning
4. Enable database encryption at rest

### Medium Priority
5. Add MFA support
6. Implement admin action approval workflow
7. Set up backup encryption
8. Add account lockout after failed logins

### Low Priority
9. Consider rootless Docker
10. Add honeypot endpoints
11. Implement advanced anomaly detection
