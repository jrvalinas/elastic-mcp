"""Pydantic models used by tools and schema discovery."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FieldMappingConfig(BaseModel):
    """User-provided field mapping overrides and extra candidates."""

    timestamp_field: str | None = None
    message_field: str | None = None
    level_field: str | None = None
    service_field: str | None = None
    correlation_field: str | None = None
    hostname_field: str | None = None

    extra_timestamp_candidates: list[str] = Field(default_factory=list)
    extra_message_candidates: list[str] = Field(default_factory=list)
    extra_level_candidates: list[str] = Field(default_factory=list)
    extra_service_candidates: list[str] = Field(default_factory=list)
    extra_correlation_candidates: list[str] = Field(default_factory=list)
    extra_hostname_candidates: list[str] = Field(default_factory=list)

    extra_message_fallbacks: list[str] = Field(default_factory=list)


class DiscoveredSchema(BaseModel):
    """Resolved source fields for normalized log concepts."""

    index_pattern: str
    timestamp_field: str | None = None
    message_field: str | None = None
    message_fallbacks: list[str] = Field(default_factory=list)
    level_field: str | None = None
    service_field: str | None = None
    correlation_field: str | None = None
    hostname_field: str | None = None
    available_fields_count: int = 0
    candidate_summary: dict[str, list[str]] = Field(default_factory=dict)
    keyword_map: dict[str, str] = Field(default_factory=dict)

    def term_field(self, field: str | None) -> str | None:
        """Return the `.keyword` sub-field for term queries when available."""
        if field is None:
            return None
        return self.keyword_map.get(field, field)


class NormalizedLogEntry(BaseModel):
    """Log entry shape returned by MCP tools."""

    timestamp: str | None = None
    service: str | None = None
    level: str | None = None
    message: str | None = None
    correlation_id: str | None = None
    hostname: str | None = None
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class TimeRangeInput(BaseModel):
    """Mutually exclusive time-range styles accepted by tools."""

    last: str | None = None
    start: datetime | str | None = None
    end: datetime | str | None = None


class PingResponse(BaseModel):
    """Connectivity check result."""

    ok: bool
    cluster_name: str | None = None
    version: str | None = None


class LogSearchResponse(BaseModel):
    """Response returned by log-search tools."""

    schema_data: DiscoveredSchema = Field(alias="schema", serialization_alias="schema")
    total: int
    logs: list[NormalizedLogEntry]


class DiagnoseIssueResponse(BaseModel):
    """Response returned by the diagnose tool."""

    mode: str
    schema_data: DiscoveredSchema = Field(alias="schema", serialization_alias="schema")
    total: int
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    counts_by_level: dict[str, int] = Field(default_factory=dict)
    logs: list[NormalizedLogEntry]
