# MCP Tools

Este documento lista todas las tools implementadas en `src/mcp_elastic_logs/tools/logs.py`.

## 1) `ping`

- **Objetivo**: comprobar conectividad con Elasticsearch.
- **Inputs**: ninguno.
- **Salida**: `ok`, `cluster_name`, `version`.

## 2) `discover_log_schema`

- **Objetivo**: descubrir el esquema dinámico de logs para el `ELASTICSEARCH_INDEX_PATTERN` activo.
- **Inputs**: ninguno.
- **Salida**:
  - campos elegidos: `timestamp_field`, `message_field`, `level_field`, `service_field`, `correlation_field`
  - `available_fields_count`
  - `candidate_summary` por tipo de campo.

## 3) `get_latest_logs`

- **Objetivo**: obtener los logs mas recientes.
- **Inputs**:
  - `limit: int = 100`
  - `service: str | None = None`
  - `level: str | None = None`
  - `last: str = "15m"`
- **Comportamiento**:
  - orden descendente por timestamp
  - filtrado opcional por servicio y nivel.

## 4) `get_logs_for_service`

- **Objetivo**: obtener logs de un servicio en una ventana temporal.
- **Inputs**:
  - `service: str`
  - `last: str | None = None`
  - `start: datetime | str | None = None`
  - `end: datetime | str | None = None`
  - `level: str | None = None`
  - `limit: int = 200`
- **Comportamiento**:
  - si no se pasa rango temporal, usa `last="15m"`
  - orden descendente por timestamp.

## 5) `get_logs_by_correlation_id`

- **Objetivo**: traer el flujo completo por `correlation/trace/request id`.
- **Inputs**:
  - `correlation_id: str`
  - `last: str | None = None`
  - `start: datetime | str | None = None`
  - `end: datetime | str | None = None`
  - `limit: int = 500`
- **Comportamiento**:
  - exige que se haya descubierto `correlation_field`
  - si no se pasa rango temporal, usa `last="1h"`
  - orden ascendente por timestamp para lectura del flujo.

## 6) `diagnose_issue`

- **Objetivo**: tool de conveniencia para diagnostico rapido.
- **Inputs**:
  - `service: str | None = None`
  - `correlation_id: str | None = None`
  - `last: str | None = "1h"`
  - `start: datetime | str | None = None`
  - `end: datetime | str | None = None`
  - `level: str | None = None`
  - `limit: int = 200`
- **Comportamiento**:
  - si llega `correlation_id`, prioriza busqueda por correlacion
  - si no, busca por servicio + tiempo
  - devuelve:
    - logs normalizados
    - `counts_by_level`
    - `first_timestamp` y `last_timestamp`.

## Formato normalizado de logs

Todas las tools de logs devuelven entradas normalizadas y no hits crudos de Elasticsearch:

- `timestamp`
- `service`
- `level`
- `message`
- `correlation_id`
- `raw_fields` (metadatos breves como `_index` y `_id`)
