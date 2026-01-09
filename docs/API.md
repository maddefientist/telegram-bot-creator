# API Documentation

Base URL: `http://localhost:8000` (development) or `https://yourdomain.com/api` (production)

## Authentication

All authenticated endpoints require:
- `access_token` cookie (set by login)
- `X-CSRF-Token` header for mutating requests

## Endpoints

### Authentication

#### Register
```
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response: 201 Created
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Login
```
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response: 200 OK
Set-Cookie: access_token=<jwt>; HttpOnly; SameSite=Lax
{
  "message": "Login successful",
  "csrf_token": "token",
  "user": { ... }
}
```

#### Logout
```
POST /auth/logout

Response: 200 OK
Set-Cookie: access_token=; Max-Age=0
```

#### Get Current User
```
GET /auth/me
Cookie: access_token=<jwt>

Response: 200 OK
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "user",
  ...
}
```

### Bots

#### List Bots
```
GET /bots
Cookie: access_token=<jwt>

Response: 200 OK
[
  {
    "id": "uuid",
    "name": "My Bot",
    "telegram_username": "mybot",
    "status": "running",
    "subscription": { ... },
    ...
  }
]
```

#### Get Bot
```
GET /bots/{bot_id}
Cookie: access_token=<jwt>

Response: 200 OK
{
  "id": "uuid",
  "name": "My Bot",
  "spec_json": { ... },
  "status": "running",
  ...
}
```

#### Create Bot
```
POST /bots
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{
  "name": "My Bot",
  "telegram_token": "123456:ABC...",
  "description": "A helpful bot",
  "price_per_month_sol": 0.1
}

Response: 201 Created
{ ... bot object ... }
```

#### Update Bot Spec
```
PUT /bots/{bot_id}/spec
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{
  "name": "My Bot",
  "enabled_modules": ["basic_commands", "ai_chat"],
  ...
}

Response: 200 OK
{ ... updated bot ... }
```

#### Start Bot
```
POST /bots/{bot_id}/start
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>

Response: 200 OK
{
  "message": "Container started successfully",
  "status": "running"
}
```

#### Stop Bot
```
POST /bots/{bot_id}/stop
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>

Response: 200 OK
{
  "message": "Container stopped",
  "status": "stopped"
}
```

#### Get Bot Status
```
GET /bots/{bot_id}/status
Cookie: access_token=<jwt>

Response: 200 OK
{
  "id": "uuid",
  "status": "running",
  "last_heartbeat": "2024-01-01T00:00:00Z",
  "last_error": null,
  "container_id": "abc123",
  "logs": ["line1", "line2", ...]
}
```

#### Get Bot Logs
```
GET /bots/{bot_id}/logs?tail=100
Cookie: access_token=<jwt>

Response: 200 OK
{
  "bot_id": "uuid",
  "logs": ["line1", "line2", ...]
}
```

#### Delete Bot
```
DELETE /bots/{bot_id}
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>

Response: 204 No Content
```

### AI Generation

#### Generate BotSpec
```
POST /ai/generate-botspec
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{
  "description": "A customer support bot that answers FAQs",
  "bot_name": "Support Bot",
  "enabled_modules": ["basic_commands", "ai_chat"],
  "constraints": "Keep responses under 200 words"
}

Response: 200 OK
{
  "success": true,
  "spec": { ... BotSpec ... },
  "errors": [],
  "tokens_used": 500,
  "retries": 0
}
```

### Payments

#### Get Pricing
```
GET /payments/pricing

Response: 200 OK
{
  "min_sol": 0.01,
  "max_sol": 10.0,
  "default_sol": 0.1,
  "tiers": [
    {
      "id": "starter",
      "name": "Starter",
      "price_sol": 0.05,
      "features": [...],
      "recommended": false
    },
    ...
  ]
}
```

#### Create Invoice
```
POST /payments/invoices
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{
  "bot_id": "uuid",
  "months": 1
}

Response: 201 Created
{
  "invoice_id": "uuid",
  "amount_sol": 0.1,
  "recipient": "TreasuryAddress...",
  "reference": "ReferenceKey...",
  "expires_at": "2024-01-02T00:00:00Z",
  "solana_pay_url": "solana:..."
}
```

#### Verify Payment
```
POST /payments/verify
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{
  "invoice_id": "uuid"
}

Response: 200 OK
{
  "invoice_id": "uuid",
  "status": "paid",
  "message": "Payment confirmed: 0.1 SOL",
  "subscription_active_until": "2024-02-01T00:00:00Z"
}
```

### Admin (Admin Role Required)

#### Get Stats
```
GET /admin/stats
Cookie: access_token=<jwt>

Response: 200 OK
{
  "total_users": 100,
  "total_bots": 50,
  "active_bots": 30,
  "total_invoices": 200,
  "paid_invoices": 180,
  "total_revenue_sol": 18.0,
  "active_subscriptions": 45
}
```

#### Override Bot State
```
POST /admin/bots/{bot_id}/override
Cookie: access_token=<jwt>
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{
  "action": "extend",
  "reason": "Customer support request",
  "extend_days": 30
}

Response: 200 OK
{
  "message": "Extended by 30 days",
  "action": "extend"
}
```

### Health

#### Health Check
```
GET /health

Response: 200 OK
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "api"
}
```

#### Readiness Check
```
GET /health/ready

Response: 200 OK
{
  "status": "ready",
  "timestamp": "2024-01-01T00:00:00Z",
  "checks": {
    "database": "healthy"
  }
}
```

## Error Responses

All errors return JSON:
```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `400` - Bad request (validation error)
- `401` - Unauthorized (not logged in)
- `403` - Forbidden (missing permission)
- `404` - Not found
- `429` - Rate limited
- `500` - Internal server error
