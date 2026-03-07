"""MCP tools for Elasticsearch log diagnosis."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from elasticsearch import NotFoundError
from fastmcp import FastMCP

from ..config import ElasticConfig
from ..elastic_connection import get_connection_manager
from ..models import (
    DiagnoseIssueResponse,
    DiscoveredSchema,
    LogSearchResponse,
    NormalizedLogEntry,
    PingResponse,
    TimeRangeInput,
)
from ..schema_discovery import discover_schema, get_value_by_path
from ..time_range import build_time_range_query


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_hit(hit: dict[str, Any], schema: DiscoveredSchema) -> NormalizedLogEntry:
    source = hit.get("_source", {})

    timestamp = _to_text(get_value_by_path(source, schema.timestamp_field)) if schema.timestamp_field else None
    service = _to_text(get_value_by_path(source, schema.service_field)) if schema.service_field else None
    level = _to_text(get_value_by_path(source, schema.level_field)) if schema.level_field else None
    message = _to_text(get_value_by_path(source, schema.message_field)) if schema.message_field else None
    correlation = (
        _to_text(get_value_by_path(source, schema.correlation_field))
        if schema.correlation_field
        else None
    )

    raw_fields = {
        "_index": hit.get("_index"),
        "_id": hit.get("_id"),
    }

    return NormalizedLogEntry(
        timestamp=timestamp,
        service=service,
        level=level,
        message=message,
        correlation_id=correlation,
        raw_fields=raw_fields,
    )


def _build_must_filters(
    *,
    schema: DiscoveredSchema,
    service: str | None,
    level: str | None,
    correlation_id: str | None,
    time_range: dict[str, Any],
) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = [time_range]

    if service:
        if not schema.service_field:
            raise ValueError("Service filter requested, but no service field was discovered.")
        filters.append({"term": {schema.service_field: service}})

    if level:
        if not schema.level_field:
            raise ValueError("Level filter requested, but no level field was discovered.")
        filters.append({"term": {schema.level_field: level}})

    if correlation_id:
        if not schema.correlation_field:
            raise ValueError(
                "Correlation search requested, but no correlation field was discovered. "
                "Run discover_log_schema to inspect available fields."
            )
        filters.append({"term": {schema.correlation_field: correlation_id}})

    return filters


async def _search_logs(
    *,
    index_pattern: str,
    schema: DiscoveredSchema,
    service: str | None,
    level: str | None,
    correlation_id: str | None,
    last: str | None,
    start: datetime | str | None,
    end: datetime | str | None,
    limit: int,
    sort_order: str,
) -> LogSearchResponse:
    if limit <= 0:
        raise ValueError("`limit` must be greater than 0.")

    if not schema.timestamp_field:
        raise ValueError(
            "Schema discovery could not identify a timestamp field. "
            "Cannot build time-bound queries."
        )
    if not schema.message_field:
        raise ValueError(
            "Schema discovery could not identify a message field. "
            "Cannot produce normalized log output."
        )

    client = get_connection_manager().get_client()
    time_query = build_time_range_query(
        TimeRangeInput(last=last, start=start, end=end),
        schema.timestamp_field,
    )

    must_filters = _build_must_filters(
        schema=schema,
        service=service,
        level=level,
        correlation_id=correlation_id,
        time_range=time_query,
    )

    source_fields = [schema.message_field, schema.timestamp_field]
    for optional_field in [schema.level_field, schema.service_field, schema.correlation_field]:
        if optional_field:
            source_fields.append(optional_field)

    try:
        result = await client.search(
            index=index_pattern,
            query={"bool": {"must": must_filters}},
            sort=[{schema.timestamp_field: {"order": sort_order}}],
            size=limit,
            _source=source_fields,
            track_total_hits=False,
        )
    except NotFoundError as exc:
        raise ValueError(f"Index pattern not found: {index_pattern!r}") from exc

    hits = result.get("hits", {}).get("hits", [])
    normalized = [_normalize_hit(hit, schema) for hit in hits]

    return LogSearchResponse(schema=schema, total=len(normalized), logs=normalized)


def register_log_tools(mcp: FastMCP) -> None:
    """Register all log-diagnosis MCP tools on a FastMCP instance."""

    @mcp.tool()
    async def ping() -> PingResponse:
        """Check Elasticsearch connectivity and return cluster basics."""
        manager = get_connection_manager()
        ok = await manager.ping()
        client = manager.get_client()
        info = await client.info() if ok else {}
        version = None
        if info:
            version = info.get("version", {}).get("number")
        return PingResponse(ok=ok, cluster_name=info.get("cluster_name"), version=version)

    @mcp.tool()
    async def discover_log_schema() -> dict[str, Any]:
        """Discover likely timestamp/message/service/level/correlation fields."""
        config = ElasticConfig.from_env()
        client = get_connection_manager().get_client()
        schema = await discover_schema(client, config.index_pattern)
        return schema.model_dump()

    @mcp.tool()
    async def get_latest_logs(
        limit: int = 100,
        service: str | None = None,
        level: str | None = None,
        last: str = "15m",
    ) -> dict[str, Any]:
        """Fetch latest logs, optionally filtered by service and level."""
        config = ElasticConfig.from_env()
        client = get_connection_manager().get_client()
        schema = await discover_schema(client, config.index_pattern)
        response = await _search_logs(
            index_pattern=config.index_pattern,
            schema=schema,
            service=service,
            level=level,
            correlation_id=None,
            last=last,
            start=None,
            end=None,
            limit=limit,
            sort_order="desc",
        )
        return response.model_dump(by_alias=True)

    @mcp.tool()
    async def get_logs_for_service(
        service: str,
        last: str | None = None,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        level: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Fetch logs for a service in a chosen time range."""
        config = ElasticConfig.from_env()
        client = get_connection_manager().get_client()
        schema = await discover_schema(client, config.index_pattern)

        if not last and not start and not end:
            last = "15m"

        response = await _search_logs(
            index_pattern=config.index_pattern,
            schema=schema,
            service=service,
            level=level,
            correlation_id=None,
            last=last,
            start=start,
            end=end,
            limit=limit,
            sort_order="desc",
        )
        return response.model_dump(by_alias=True)

    @mcp.tool()
    async def get_logs_by_correlation_id(
        correlation_id: str,
        last: str | None = None,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Fetch all logs for a correlation/trace/request id."""
        config = ElasticConfig.from_env()
        client = get_connection_manager().get_client()
        schema = await discover_schema(client, config.index_pattern)

        if not schema.correlation_field:
            raise ValueError(
                "No correlation field discovered. Run discover_log_schema to inspect field candidates."
            )
        if not last and not start and not end:
            last = "1h"

        response = await _search_logs(
            index_pattern=config.index_pattern,
            schema=schema,
            service=None,
            level=None,
            correlation_id=correlation_id,
            last=last,
            start=start,
            end=end,
            limit=limit,
            sort_order="asc",
        )
        return response.model_dump(by_alias=True)

    @mcp.tool()
    async def diagnose_issue(
        service: str | None = None,
        correlation_id: str | None = None,
        last: str | None = "1h",
        start: datetime | str | None = None,
        end: datetime | str | None = None,
        level: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Convenience diagnosis tool combining search + small summary."""
        if not correlation_id and not service:
            raise ValueError("Provide either `correlation_id` or `service` for diagnose_issue.")

        config = ElasticConfig.from_env()
        client = get_connection_manager().get_client()
        schema = await discover_schema(client, config.index_pattern)

        mode = "correlation" if correlation_id else "service"
        response = await _search_logs(
            index_pattern=config.index_pattern,
            schema=schema,
            service=service if not correlation_id else None,
            level=level,
            correlation_id=correlation_id,
            last=last,
            start=start,
            end=end,
            limit=limit,
            sort_order="asc" if correlation_id else "desc",
        )

        levels = [entry.level for entry in response.logs if entry.level]
        counts_by_level = dict(Counter(levels))

        timestamps = [entry.timestamp for entry in response.logs if entry.timestamp]
        first_timestamp = min(timestamps) if timestamps else None
        last_timestamp = max(timestamps) if timestamps else None

        diagnosis = DiagnoseIssueResponse(
            mode=mode,
            schema=response.schema_data,
            total=response.total,
            first_timestamp=first_timestamp,
            last_timestamp=last_timestamp,
            counts_by_level=counts_by_level,
            logs=response.logs,
        )
        return diagnosis.model_dump(by_alias=True)
