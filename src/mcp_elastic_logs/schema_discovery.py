"""Dynamic Elasticsearch log schema discovery."""

from __future__ import annotations

from collections.abc import Mapping
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


def _collect_mapping_fields(properties: Mapping[str, Any], prefix: str = "") -> set[str]:
    """Flatten Elasticsearch mapping properties into dotted field paths."""
    field_names: set[str] = set()

    for field_name, field_config in properties.items():
        if not field_name:
            continue

        full_name = f"{prefix}.{field_name}" if prefix else field_name
        field_names.add(full_name)

        if not isinstance(field_config, Mapping):
            continue

        nested_properties = field_config.get("properties")
        if isinstance(nested_properties, Mapping):
            field_names.update(_collect_mapping_fields(nested_properties, full_name))

        multi_fields = field_config.get("fields")
        if isinstance(multi_fields, Mapping):
            field_names.update(_collect_mapping_fields(multi_fields, full_name))

    return field_names


def _extract_available_fields(mappings_response: Mapping[str, Any]) -> set[str]:
    """Collect all mapped field names across matched indices."""
    available_fields: set[str] = set()

    for index_mapping in mappings_response.values():
        if not isinstance(index_mapping, Mapping):
            continue

        mappings = index_mapping.get("mappings")
        if not isinstance(mappings, Mapping):
            continue

        properties = mappings.get("properties")
        if isinstance(properties, Mapping):
            available_fields.update(_collect_mapping_fields(properties))

    return available_fields


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
    """Discover likely log fields from unknown schema using index mappings.

    Returns a partial schema when some concepts cannot be identified.
    """
    try:
        mappings_response = await client.indices.get_mapping(
            index=index_pattern,
            allow_no_indices=True,
            ignore_unavailable=True,
        )
    except NotFoundError as exc:
        raise ValueError(f"Index pattern not found: {index_pattern!r}") from exc

    if not mappings_response:
        raise ValueError(
            f"No indices matched index pattern {index_pattern!r}. "
            "Check ELASTICSEARCH_INDEX_PATTERN and whether logs exist."
        )

    available_fields = _extract_available_fields(mappings_response)
    if not available_fields:
        raise ValueError(
            f"No mapped fields found for index pattern {index_pattern!r}. "
            "Check index mappings and permissions."
        )

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
