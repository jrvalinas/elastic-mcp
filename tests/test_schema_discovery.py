from mcp_elastic_logs.schema_discovery import (
    _extract_available_fields,
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


def test_extract_available_fields_flattens_nested_and_multi_fields() -> None:
    mappings_response = {
        "logs-2026.03.09": {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "message": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "service": {
                        "properties": {
                            "name": {"type": "keyword"},
                        }
                    },
                }
            }
        }
    }

    available_fields = _extract_available_fields(mappings_response)

    assert "@timestamp" in available_fields
    assert "message" in available_fields
    assert "message.keyword" in available_fields
    assert "service" in available_fields
    assert "service.name" in available_fields
