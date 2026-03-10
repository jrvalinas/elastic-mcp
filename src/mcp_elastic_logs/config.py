"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .models import FieldMappingConfig


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _parse_csv(value: str | None) -> list[str]:
    """Parse comma-separated strings into a trimmed list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class ElasticConfig:
    """Strongly typed Elasticsearch configuration."""

    url: str
    api_key: str | None
    username: str | None
    password: str | None
    index_pattern: str
    verify_certs: bool
    ca_certs: str | None
    field_mapping: FieldMappingConfig

    @classmethod
    def from_env(cls) -> "ElasticConfig":
        """Build configuration from environment variables.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        url = os.getenv("ELASTICSEARCH_URL")
        if not url:
            raise ValueError("ELASTICSEARCH_URL is required")

        api_key = os.getenv("ELASTICSEARCH_API_KEY")
        username = os.getenv("ELASTICSEARCH_USERNAME")
        password = os.getenv("ELASTICSEARCH_PASSWORD")

        index_pattern = os.getenv("ELASTICSEARCH_INDEX_PATTERN", "logs-*")
        verify_certs = _parse_bool(os.getenv("ELASTICSEARCH_VERIFY_CERTS"), True)
        ca_certs = os.getenv("ELASTICSEARCH_CA_CERTS")
        field_mapping = FieldMappingConfig(
            timestamp_field=os.getenv("FIELD_TIMESTAMP"),
            message_field=os.getenv("FIELD_MESSAGE"),
            level_field=os.getenv("FIELD_LEVEL"),
            service_field=os.getenv("FIELD_SERVICE"),
            correlation_field=os.getenv("FIELD_CORRELATION"),
            hostname_field=os.getenv("FIELD_HOSTNAME"),
            extra_timestamp_candidates=_parse_csv(os.getenv("EXTRA_TIMESTAMP_CANDIDATES")),
            extra_message_candidates=_parse_csv(os.getenv("EXTRA_MESSAGE_CANDIDATES")),
            extra_level_candidates=_parse_csv(os.getenv("EXTRA_LEVEL_CANDIDATES")),
            extra_service_candidates=_parse_csv(os.getenv("EXTRA_SERVICE_CANDIDATES")),
            extra_correlation_candidates=_parse_csv(os.getenv("EXTRA_CORRELATION_CANDIDATES")),
            extra_hostname_candidates=_parse_csv(os.getenv("EXTRA_HOSTNAME_CANDIDATES")),
            extra_message_fallbacks=_parse_csv(os.getenv("EXTRA_MESSAGE_FALLBACKS")),
        )

        return cls(
            url=url,
            api_key=api_key,
            username=username,
            password=password,
            index_pattern=index_pattern,
            verify_certs=verify_certs,
            ca_certs=ca_certs,
            field_mapping=field_mapping,
        )
