"""Docker service for managing bot containers."""
import asyncio
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx

from config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Docker socket path (fallback if DOCKER_HOST not set)
DOCKER_SOCKET = "/var/run/docker.sock"
DOCKER_API_VERSION = "v1.43"


class DockerService:
    """Service for managing bot containers via Docker API."""

    def __init__(self):
        self.network = settings.docker_network
        self.runner_image = settings.runner_image
        self.memory_limit = settings.bot_memory_limit
        self.cpu_limit = settings.bot_cpu_limit

        # Use TCP proxy if DOCKER_HOST is set, otherwise use Unix socket
        self.docker_host = settings.docker_host
        if self.docker_host and self.docker_host.startswith("tcp://"):
            self.use_tcp = True
            parsed = urlparse(self.docker_host)
            self.docker_url = f"http://{parsed.netloc}"
        else:
            self.use_tcp = False
            self.socket_path = DOCKER_SOCKET

    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for Docker API communication."""
        if self.use_tcp:
            return httpx.AsyncClient(base_url=self.docker_url, timeout=30.0)
        else:
            transport = httpx.AsyncHTTPTransport(uds=self.socket_path)
            return httpx.AsyncClient(transport=transport, timeout=30.0)

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a request to Docker API."""
        api_path = f"/{DOCKER_API_VERSION}{path}"

        if self.use_tcp:
            url = api_path
        else:
            url = f"http://docker{api_path}"

        async with self._get_client() as client:
            response = await client.request(
                method,
                url,
                json=json_data,
                params=params,
            )
            return response

    def _container_name(self, bot_id: uuid.UUID) -> str:
        """Generate deterministic container name for a bot."""
        return f"bot-{str(bot_id)[:8]}"

    async def start_bot(
        self,
        bot_id: uuid.UUID,
        telegram_token: str,
        api_url: str,
    ) -> tuple[bool, str | None, str]:
        """
        Start a bot container.

        Returns:
            tuple: (success, container_id, message)
        """
        container_name = self._container_name(bot_id)

        # Check if container already exists
        existing = await self._get_container(container_name)
        if existing:
            # If exists but not running, start it
            if existing.get("State", {}).get("Running", False):
                return True, existing["Id"], "Container already running"

            # Remove old container first
            await self._remove_container(existing["Id"])

        # Create container config
        config = {
            "Image": self.runner_image,
            "Env": [
                f"BOT_ID={str(bot_id)}",
                f"TELEGRAM_TOKEN={telegram_token}",
                f"API_URL={api_url}",
                f"RUNNER_SECRET={settings.runner_shared_secret}",
                f"OPENROUTER_API_KEY={settings.openrouter_api_key}",
                f"OPENROUTER_MODEL={settings.openrouter_model}",
            ],
            "Labels": {
                "botcreator.bot_id": str(bot_id),
                "botcreator.managed": "true",
            },
            "HostConfig": {
                "Memory": self._parse_memory_limit(self.memory_limit),
                "NanoCpus": self._parse_cpu_limit(self.cpu_limit),
                "RestartPolicy": {"Name": "unless-stopped"},
                "NetworkMode": self.network,
            },
            "Healthcheck": {
                "Test": ["CMD", "python", "-c", "import sys; sys.exit(0)"],
                "Interval": 30_000_000_000,  # 30s in nanoseconds
                "Timeout": 10_000_000_000,   # 10s
                "Retries": 3,
            },
        }

        try:
            # Create container
            response = await self._request(
                "POST",
                "/containers/create",
                json_data=config,
                params={"name": container_name},
            )

            if response.status_code not in (200, 201):
                error = response.json().get("message", response.text)
                logger.error(
                    "Failed to create container",
                    bot_id=str(bot_id),
                    error=error,
                )
                return False, None, f"Failed to create container: {error}"

            container_id = response.json()["Id"]

            # Start container
            start_response = await self._request(
                "POST",
                f"/containers/{container_id}/start",
            )

            if start_response.status_code not in (200, 204):
                error = start_response.text
                logger.error(
                    "Failed to start container",
                    bot_id=str(bot_id),
                    container_id=container_id,
                    error=error,
                )
                return False, container_id, f"Failed to start container: {error}"

            logger.info(
                "Bot container started",
                bot_id=str(bot_id),
                container_id=container_id[:12],
            )
            return True, container_id, "Container started successfully"

        except Exception as e:
            logger.error(
                "Docker operation failed",
                bot_id=str(bot_id),
                error=str(e),
            )
            return False, None, f"Docker error: {str(e)}"

    async def stop_bot(self, bot_id: uuid.UUID) -> tuple[bool, str]:
        """Stop a bot container."""
        container_name = self._container_name(bot_id)

        try:
            container = await self._get_container(container_name)
            if not container:
                return True, "Container not found (already stopped)"

            container_id = container["Id"]

            # Stop container with 10 second timeout
            response = await self._request(
                "POST",
                f"/containers/{container_id}/stop",
                params={"t": 10},
            )

            if response.status_code in (200, 204, 304):
                logger.info(
                    "Bot container stopped",
                    bot_id=str(bot_id),
                    container_id=container_id[:12],
                )
                return True, "Container stopped"

            error = response.text
            return False, f"Failed to stop container: {error}"

        except Exception as e:
            logger.error(
                "Failed to stop container",
                bot_id=str(bot_id),
                error=str(e),
            )
            return False, f"Docker error: {str(e)}"

    async def restart_bot(
        self,
        bot_id: uuid.UUID,
        telegram_token: str,
        api_url: str,
    ) -> tuple[bool, str | None, str]:
        """Restart a bot container."""
        # Stop first
        await self.stop_bot(bot_id)

        # Wait a moment
        await asyncio.sleep(1)

        # Start fresh
        return await self.start_bot(bot_id, telegram_token, api_url)

    async def get_bot_status(self, bot_id: uuid.UUID) -> dict[str, Any]:
        """Get status of a bot container."""
        container_name = self._container_name(bot_id)

        try:
            container = await self._get_container(container_name)
            if not container:
                return {
                    "running": False,
                    "status": "not_found",
                    "container_id": None,
                }

            state = container.get("State", {})
            return {
                "running": state.get("Running", False),
                "status": state.get("Status", "unknown"),
                "container_id": container["Id"][:12],
                "started_at": state.get("StartedAt"),
                "health": state.get("Health", {}).get("Status"),
            }

        except Exception as e:
            logger.error(
                "Failed to get container status",
                bot_id=str(bot_id),
                error=str(e),
            )
            return {
                "running": False,
                "status": "error",
                "error": str(e),
            }

    async def get_bot_logs(
        self,
        bot_id: uuid.UUID,
        tail: int = 100,
        since: int | None = None,
    ) -> list[str]:
        """Get logs from a bot container."""
        container_name = self._container_name(bot_id)

        try:
            container = await self._get_container(container_name)
            if not container:
                return ["Container not found"]

            params = {
                "stdout": True,
                "stderr": True,
                "tail": tail,
                "timestamps": True,
            }
            if since:
                params["since"] = since

            response = await self._request(
                "GET",
                f"/containers/{container['Id']}/logs",
                params=params,
            )

            if response.status_code != 200:
                return [f"Failed to get logs: {response.text}"]

            # Parse Docker log format (remove stream header bytes)
            logs = []
            for line in response.content.split(b"\n"):
                if len(line) > 8:
                    # Skip 8-byte header
                    logs.append(line[8:].decode("utf-8", errors="replace"))

            return logs

        except Exception as e:
            logger.error(
                "Failed to get container logs",
                bot_id=str(bot_id),
                error=str(e),
            )
            return [f"Error getting logs: {str(e)}"]

    async def _get_container(self, name: str) -> dict[str, Any] | None:
        """Get container by name."""
        try:
            response = await self._request(
                "GET",
                f"/containers/{name}/json",
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None

    async def _remove_container(self, container_id: str) -> bool:
        """Remove a container."""
        try:
            response = await self._request(
                "DELETE",
                f"/containers/{container_id}",
                params={"force": True},
            )
            return response.status_code in (200, 204)
        except Exception:
            return False

    def _parse_memory_limit(self, limit: str) -> int:
        """Parse memory limit string to bytes."""
        limit = limit.lower()
        if limit.endswith("g"):
            return int(float(limit[:-1]) * 1024 * 1024 * 1024)
        elif limit.endswith("m"):
            return int(float(limit[:-1]) * 1024 * 1024)
        elif limit.endswith("k"):
            return int(float(limit[:-1]) * 1024)
        return int(limit)

    def _parse_cpu_limit(self, limit: str) -> int:
        """Parse CPU limit to nanoseconds."""
        # Docker uses NanoCpus (1 CPU = 1e9)
        return int(float(limit) * 1_000_000_000)

    async def cleanup_orphaned_containers(self) -> int:
        """Remove containers for bots that no longer exist."""
        # This should be called periodically by a background worker
        # Implementation would query all containers with our label
        # and remove those without matching bots in DB
        # For MVP, this is a placeholder
        return 0
