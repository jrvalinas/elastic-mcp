"""Time-range parsing helpers for Elasticsearch queries."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .models import TimeRangeInput

_RELATIVE_PATTERN = re.compile(r"^\d+[smhdw]$")


def _parse_datetime_like(value: datetime | str) -> str:
    """Convert datetime-like value into an ISO-8601 string."""
    if isinstance(value, datetime):
        return value.isoformat()

    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid datetime value: {value!r}") from exc

    return parsed.isoformat()


def build_time_range_query(time_input: TimeRangeInput, timestamp_field: str) -> dict[str, Any]:
    """Build a strict Elasticsearch range query from tool time inputs.

    Rules:
    - `last` cannot be combined with `start`/`end`
    - `last` must match `\\d+[smhdw]`
    - explicit range supports `start`, `end`, or both
    - when both explicit bounds are present, `start <= end` is required
    """
    if time_input.last and (time_input.start is not None or time_input.end is not None):
        raise ValueError("Use either `last` or `start/end`, not both.")

    if time_input.last:
        if not _RELATIVE_PATTERN.match(time_input.last):
            raise ValueError(
                "Invalid `last` value. Expected formats like: 15m, 1h, 24h, 7d."
            )
        return {
            "range": {
                timestamp_field: {
                    "gte": f"now-{time_input.last}",
                    "lte": "now",
                }
            }
        }

    range_body: dict[str, str] = {}
    start_iso: str | None = None
    end_iso: str | None = None

    if time_input.start is not None:
        start_iso = _parse_datetime_like(time_input.start)
        range_body["gte"] = start_iso

    if time_input.end is not None:
        end_iso = _parse_datetime_like(time_input.end)
        range_body["lte"] = end_iso

    if start_iso and end_iso and start_iso > end_iso:
        raise ValueError("Invalid time range: `start` must be before or equal to `end`.")

    if not range_body:
        raise ValueError("Time filter is required. Provide `last` or `start`/`end`.")

    return {"range": {timestamp_field: range_body}}
