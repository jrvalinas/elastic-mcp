from mcp_elastic_logs.schema_discovery import select_preferred_field


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
