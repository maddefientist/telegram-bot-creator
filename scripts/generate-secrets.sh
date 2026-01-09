#!/bin/bash
# Generate secure secrets for production deployment

set -e

echo "========================================"
echo "Generating Production Secrets"
echo "========================================"
echo ""
echo "Add these to your .env file or environment:"
echo ""

# Generate JWT Secret (64 chars hex)
JWT_SECRET=$(openssl rand -hex 32)
echo "JWT_SECRET=$JWT_SECRET"

# Generate CSRF Secret (64 chars hex)
CSRF_SECRET=$(openssl rand -hex 32)
echo "CSRF_SECRET=$CSRF_SECRET"

# Generate Runner Shared Secret (64 chars hex)
RUNNER_SHARED_SECRET=$(openssl rand -hex 32)
echo "RUNNER_SHARED_SECRET=$RUNNER_SHARED_SECRET"

# Generate Fernet key for encryption
# Fernet requires a 32-byte base64-encoded key
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"

# Generate Postgres password
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"

echo ""
echo "========================================"
echo "Important: Store these securely!"
echo "========================================"
