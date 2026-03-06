"""Single place for Elasticsearch connectivity.

This module owns:
- building the AsyncElasticsearch client from environment config
- exposing a shared client getter
- lightweight health check helpers
- clean shutdown of the shared client
"""

from __future__ import annotations

from elasticsearch import AsyncElasticsearch

from .config import ElasticConfig


class ElasticConnectionManager:
    """Creates and reuses one AsyncElasticsearch client instance."""

    def __init__(self, config: ElasticConfig) -> None:
        self._config = config
        self._client: AsyncElasticsearch | None = None

    def get_client(self) -> AsyncElasticsearch:
        """Return a shared AsyncElasticsearch client.

        The client is created lazily on first access.
        """
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> AsyncElasticsearch:
        """Create the async Elasticsearch client using configured auth.

        Authentication priority:
        1) API key if present
        2) username/password
        """
        common_kwargs: dict[str, object] = {
            "hosts": [self._config.url],
            "verify_certs": self._config.verify_certs,
        }
        if self._config.ca_certs:
            common_kwargs["ca_certs"] = self._config.ca_certs

        if self._config.api_key:
            return AsyncElasticsearch(api_key=self._config.api_key, **common_kwargs)

        return AsyncElasticsearch(
            basic_auth=(self._config.username or "", self._config.password or ""),
            **common_kwargs,
        )

    async def ping(self) -> bool:
        """Check connectivity to Elasticsearch via client ping."""
        client = self.get_client()
        return await client.ping()

    async def close(self) -> None:
        """Close shared client if it was created."""
        if self._client is not None:
            await self._client.close()
            self._client = None


_manager: ElasticConnectionManager | None = None


def get_connection_manager() -> ElasticConnectionManager:
    """Return a singleton connection manager initialized from environment."""
    global _manager
    if _manager is None:
        _manager = ElasticConnectionManager(ElasticConfig.from_env())
    return _manager


def get_elasticsearch_client() -> AsyncElasticsearch:
    """Shortcut for obtaining the shared AsyncElasticsearch client."""
    return get_connection_manager().get_client()


async def ping_elasticsearch() -> bool:
    """Shortcut for pinging Elasticsearch connectivity."""
    return await get_connection_manager().ping()


async def close_elasticsearch_client() -> None:
    """Close shared Elasticsearch client instance."""
    await get_connection_manager().close()
