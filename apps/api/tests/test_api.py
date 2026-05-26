"""API smoke tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# We need to mock settings before importing app
import os
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-only")
os.environ.setdefault("CSRF_SECRET", "test-csrf-secret-only")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-only")  # base64
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("SOLANA_RPC_URL", "https://api.devnet.solana.com")
os.environ.setdefault("SOLANA_TREASURY_ADDRESS", "11111111111111111111111111111111")  # Valid base58, 32 bytes
os.environ.setdefault("RUNNER_SHARED_SECRET", "test-runner-secret-only")


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test basic health endpoint."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/auth/login",
                json={"email": "nonexistent@example.com", "password": "wrongpassword"},
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_unauthorized(self):
        """Test /me endpoint without auth."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/auth/me")
            assert response.status_code == 401


class TestPaymentEndpoints:
    """Test payment endpoints."""

    @pytest.mark.asyncio
    async def test_get_pricing(self):
        """Test pricing endpoint."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/payments/pricing")
            assert response.status_code == 200
            data = response.json()
            assert "min_sol" in data
            assert "max_sol" in data
            assert "tiers" in data
            assert len(data["tiers"]) > 0


class TestBotSpecValidation:
    """Test BotSpec validation endpoint."""

    @pytest.mark.asyncio
    async def test_validate_spec_unauthorized(self):
        """Test spec validation requires auth."""
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/bots/validate-spec",
                json={"spec": {"name": "Test"}},
            )
            assert response.status_code == 401
