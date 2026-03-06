"""Dynamic Elasticsearch log schema discovery."""

from __future__ import annotations

from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch import NotFoundError

from .models import DiscoveredSchema

TIMESTAMP_CANDIDATES: list[str] = [
    "@timestamp",
    "timestamp",
    "time",
    "event.created",
    "event.ingested",
]

MESSAGE_CANDIDATES: list[str] = [
    "message",
    "log",
    "msg",
    "event.original",
]

LEVEL_CANDIDATES: list[str] = [
    "log.level",
    "level",
    "severity",
    "severity_text",
]

SERVICE_CANDIDATES: list[str] = [
    "service.name",
    "service",
    "app",
    "application",
    "kubernetes.container.name",
    "container.name",
]

CORRELATION_CANDIDATES: list[str] = [
    "trace.id",
    "transaction.id",
    "correlation.id",
    "request.id",
    "correlation_id",
    "trace_id",
    "req.id",
]


def get_value_by_path(source: dict[str, Any], field_path: str) -> Any | None:
    """Read a value from dotted path, supporting flattened dotted keys.

    Elasticsearch `_source` may include nested objects (`service.name`) or
    flattened dotted keys (`{"service.name": "api"}`). This helper supports both.
    """
    if field_path in source:
        return source[field_path]

    current: Any = source
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def select_preferred_field(
    available_fields: set[str],
    candidates: list[str],
    sample_doc: dict[str, Any] | None = None,
) -> str | None:
    """Pick the best field from ordered candidates.

    Selection rule:
    - choose the earliest candidate present in `available_fields`
    - if a sample document exists, prefer the first candidate that is populated
    """
    present_candidates = [candidate for candidate in candidates if candidate in available_fields]
    if not present_candidates:
        return None

    if sample_doc:
        for candidate in present_candidates:
            value = get_value_by_path(sample_doc, candidate)
            if value is not None and value != "":
                return candidate

    return present_candidates[0]


async def _fetch_sample_document(
    client: AsyncElasticsearch,
    index_pattern: str,
) -> dict[str, Any] | None:
    """Fetch one recent document source to validate candidate usefulness."""
    result = await client.search(
        index=index_pattern,
        query={"match_all": {}},
        sort=[{"_doc": {"order": "desc"}}],
        size=1,
        source=True,
    )
    hits = result.get("hits", {}).get("hits", [])
    if not hits:
        return None
    return hits[0].get("_source", {})


async def discover_schema(client: AsyncElasticsearch, index_pattern: str) -> DiscoveredSchema:
    """Discover likely log fields from unknown schema using `_field_caps`.

    Returns a partial schema when some concepts cannot be identified.
    """
    try:
        field_caps = await client.field_caps(index=index_pattern, fields="*")
    except NotFoundError as exc:
        raise ValueError(f"Index pattern not found: {index_pattern!r}") from exc

    fields_info = field_caps.get("fields", {})
    if not fields_info:
        raise ValueError(
            f"No fields found for index pattern {index_pattern!r}. "
            "Check index pattern and permissions."
        )

    available_fields = set(fields_info.keys())
    sample_doc = await _fetch_sample_document(client, index_pattern)

    timestamp_field = select_preferred_field(available_fields, TIMESTAMP_CANDIDATES, sample_doc)
    message_field = select_preferred_field(available_fields, MESSAGE_CANDIDATES, sample_doc)
    level_field = select_preferred_field(available_fields, LEVEL_CANDIDATES, sample_doc)
    service_field = select_preferred_field(available_fields, SERVICE_CANDIDATES, sample_doc)
    correlation_field = select_preferred_field(
        available_fields,
        CORRELATION_CANDIDATES,
        sample_doc,
    )

    return DiscoveredSchema(
        index_pattern=index_pattern,
        timestamp_field=timestamp_field,
        message_field=message_field,
        level_field=level_field,
        service_field=service_field,
        correlation_field=correlation_field,
        available_fields_count=len(available_fields),
        candidate_summary={
            "timestamp": [f for f in TIMESTAMP_CANDIDATES if f in available_fields],
            "message": [f for f in MESSAGE_CANDIDATES if f in available_fields],
            "level": [f for f in LEVEL_CANDIDATES if f in available_fields],
            "service": [f for f in SERVICE_CANDIDATES if f in available_fields],
            "correlation": [f for f in CORRELATION_CANDIDATES if f in available_fields],
        },
    )
