# Agents Guide

## Finalidad del proyecto

Este repositorio implementa un MCP server pequeno y orientado a produccion para diagnostico de incidencias en logs de Elasticsearch cuando el esquema no es conocido de antemano.

Objetivo principal: ofrecer tools simples para buscar logs, correlacionar eventos y devolver resultados normalizados y legibles para agentes/LLMs.

## Librerias usadas

- `fastmcp`: servidor MCP y definicion de tools.
- `elasticsearch` (cliente oficial async): consultas a Elasticsearch.
- `pydantic`: modelos tipados de entrada/salida.
- `pytest` (dev): tests de helpers unit-testables.

## Como orientarse en el repo

- `src/mcp_elastic_logs/elastic_connection.py`: capa unica de conectividad a Elasticsearch.
- `src/mcp_elastic_logs/schema_discovery.py`: descubrimiento dinamico de campos.
- `src/mcp_elastic_logs/tools/logs.py`: tools MCP (solo orquestacion de casos de uso).
- `src/mcp_elastic_logs/models.py`: modelos pydantic.
- `src/mcp_elastic_logs/time_range.py`: helper de rangos temporales.

## Como usar la documentacion

- Lee primero `README.md` para:
  - requisitos
  - variables de entorno
  - ejecucion local
  - ejecucion en Docker
  - configuracion MCP de ejemplo.
- Usa `tools.md` como referencia rapida de:
  - nombre de cada tool
  - inputs esperados
  - comportamiento
  - estructura normalizada de salida.

En resumen: `README.md` explica como arrancar y operar el servicio; `tools.md` explica que puede hacer exactamente cada tool.
