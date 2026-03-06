from datetime import datetime

import pytest

from mcp_elastic_logs.models import TimeRangeInput
from mcp_elastic_logs.time_range import build_time_range_query


def test_relative_time_range() -> None:
    query = build_time_range_query(TimeRangeInput(last="15m"), "@timestamp")
    assert query == {"range": {"@timestamp": {"gte": "now-15m", "lte": "now"}}}


def test_explicit_time_range() -> None:
    query = build_time_range_query(
        TimeRangeInput(
            start=datetime(2026, 1, 1, 0, 0, 0),
            end="2026-01-01T01:00:00Z",
        ),
        "@timestamp",
    )
    assert "range" in query
    assert "@timestamp" in query["range"]
    assert query["range"]["@timestamp"]["gte"].startswith("2026-01-01T00:00:00")


def test_reject_ambiguous_input() -> None:
    with pytest.raises(ValueError, match="either `last` or `start/end`"):
        build_time_range_query(
            TimeRangeInput(last="1h", start="2026-01-01T00:00:00Z"),
            "@timestamp",
        )
