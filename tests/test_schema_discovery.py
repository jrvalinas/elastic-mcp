from mcp_elastic_logs.schema_discovery import (
    CORRELATION_CANDIDATES,
    LEVEL_CANDIDATES,
    MESSAGE_CANDIDATES,
    SERVICE_CANDIDATES,
    TIMESTAMP_CANDIDATES,
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

    assert select_preferred_field(available, TIMESTAMP_CANDIDATES, sample) == "@timestamp"
    assert select_preferred_field(available, MESSAGE_CANDIDATES, sample) == "evento"
    assert select_preferred_field(available, LEVEL_CANDIDATES, sample) == "severity"
    assert select_preferred_field(available, SERVICE_CANDIDATES, sample) == "fields.app"
    assert (
        select_preferred_field(available, CORRELATION_CANDIDATES, sample)
        == "fields.ets_correlationid"
    )
