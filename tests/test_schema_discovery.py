import pytest

from mcp_elastic_logs.models import FieldMappingConfig
from mcp_elastic_logs.schema_discovery import (
    DEFAULT_CORRELATION_CANDIDATES,
    DEFAULT_LEVEL_CANDIDATES,
    DEFAULT_MESSAGE_CANDIDATES,
    DEFAULT_SERVICE_CANDIDATES,
    DEFAULT_TIMESTAMP_CANDIDATES,
    discover_schema,
    select_preferred_field,
)


def test_select_preferred_field_uses_priority_order() -> None:
    available = {"timestamp", "@timestamp", "message"}
    selected = select_preferred_field(available, ["@timestamp", "timestamp"])
    assert selected == "@timestamp"


def test_select_preferred_field_prefers_populated_sample() -> None:
    available = {"message", "event.original"}
    sample = {"event": {"original": "real payload"}}
    selected = select_preferred_field(
        available,
        ["message", "event.original"],
        sample,
    )
    assert selected == "event.original"


def test_kibana_csv_style_headers_are_supported() -> None:
    available = {
        "@timestamp",
        "fields.app",
        "severity",
        "fields.ets_correlationid",
        "evento",
    }
    sample = {
        "@timestamp": "2026-03-07T15:27:06.521Z",
        "fields.app": "lemoncaas-catalog",
        "severity": "CRITICAL",
        "fields.ets_correlationid": "f7d0fd09",
        "evento": "request started",
    }

    assert select_preferred_field(available, DEFAULT_TIMESTAMP_CANDIDATES, sample) == "@timestamp"
    assert select_preferred_field(available, DEFAULT_MESSAGE_CANDIDATES, sample) is None
    assert select_preferred_field(available, DEFAULT_LEVEL_CANDIDATES, sample) == "severity"
    assert select_preferred_field(available, DEFAULT_SERVICE_CANDIDATES, sample) is None
    assert select_preferred_field(available, DEFAULT_CORRELATION_CANDIDATES, sample) is None


def test_extra_candidates_are_prepended_to_defaults() -> None:
    available = {"message", "evento", "fields.app", "service.name", "fields.ets_correlationid"}
    sample = {
        "message": "default message",
        "evento": "custom message",
        "fields.app": "catalog",
        "service": {"name": "payments"},
        "fields.ets_correlationid": "abc123",
    }
    field_mapping = FieldMappingConfig(
        extra_message_candidates=["evento"],
        extra_service_candidates=["fields.app"],
        extra_correlation_candidates=["fields.ets_correlationid"],
    )

    message_candidates = field_mapping.extra_message_candidates + DEFAULT_MESSAGE_CANDIDATES
    service_candidates = field_mapping.extra_service_candidates + DEFAULT_SERVICE_CANDIDATES
    correlation_candidates = (
        field_mapping.extra_correlation_candidates + DEFAULT_CORRELATION_CANDIDATES
    )

    assert select_preferred_field(available, message_candidates, sample) == "evento"
    assert select_preferred_field(available, service_candidates, sample) == "fields.app"
    assert (
        select_preferred_field(available, correlation_candidates, sample)
        == "fields.ets_correlationid"
    )


class _FakeIndicesClient:
    async def get_mapping(self, **_: object) -> dict[str, object]:
        return {
            "logs-2026.03.10": {
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "message": {"type": "text"},
                        "evento": {"type": "text"},
                        "fields": {
                            "properties": {
                                "app": {"type": "keyword"},
                                "ets_correlationid": {"type": "keyword"},
                            }
                        },
                    }
                }
            }
        }


class _FakeClient:
    def __init__(self) -> None:
        self.indices = _FakeIndicesClient()

    async def search(self, **_: object) -> dict[str, object]:
        return {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2026-03-10T12:00:00Z",
                            "message": "default message",
                            "evento": "custom message",
                            "fields.app": "catalog",
                            "fields.ets_correlationid": "corr-1",
                        }
                    }
                ]
            }
        }


@pytest.mark.asyncio
async def test_discover_schema_uses_field_mapping_overrides_and_extras() -> None:
    client = _FakeClient()
    field_mapping = FieldMappingConfig(
        service_field="fields.app",
        extra_message_candidates=["evento"],
        extra_correlation_candidates=["fields.ets_correlationid"],
        extra_message_fallbacks=["message"],
    )

    schema = await discover_schema(client, "logs-*", field_mapping)

    assert schema.timestamp_field == "@timestamp"
    assert schema.message_field == "evento"
    assert schema.message_fallbacks == ["message"]
    assert schema.service_field == "fields.app"
    assert schema.correlation_field == "fields.ets_correlationid"
