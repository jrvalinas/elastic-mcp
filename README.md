# MCP Elasticsearch Logs

Servidor MCP pequeno y orientado a produccion para diagnosticar incidencias desde logs en Elasticsearch con esquema desconocido.

## Que hace

- Conexion a Elasticsearch con cliente async oficial.
- Descubrimiento dinamico de schema con `_field_caps` + validacion opcional con documento reciente.
- Tools MCP enfocadas en diagnostico de logs.
- Respuesta normalizada (no devuelve hits crudos como salida principal).

## Tools soportadas

- `ping`
- `discover_log_schema`
- `get_latest_logs`
- `get_logs_for_service`
- `get_logs_by_correlation_id`
- `diagnose_issue`

Referencia detallada de cada tool en `tools.md`.

## Variables de entorno

- `ELASTICSEARCH_URL` (requerida)
- `ELASTICSEARCH_API_KEY` (opcional, preferida si el cluster usa auth)
- `ELASTICSEARCH_USERNAME` (opcional)
- `ELASTICSEARCH_PASSWORD` (opcional)
- `ELASTICSEARCH_INDEX_PATTERN` (default: `logs-*`)
- `ELASTICSEARCH_VERIFY_CERTS` (default: `true`)
- `ELASTICSEARCH_CA_CERTS` (opcional)

Reglas de autenticacion:

1. Si existe `ELASTICSEARCH_API_KEY`, se usa esa.
2. Si no, y existen `ELASTICSEARCH_USERNAME` + `ELASTICSEARCH_PASSWORD`, se usa basic auth.
3. Si no hay credenciales, el cliente conecta sin autenticacion.

## Como funciona el schema discovery

1. Consulta `_field_caps` sobre el index pattern configurado.
2. Detecta campos candidatos para timestamp, message, level, service y correlation.
3. Aplica listas ordenadas de prioridad.
4. Si hay sample document, prioriza campos realmente poblados.
5. Devuelve schema parcial (`null` en lo no encontrado).

## Filtro temporal

Se soporta:

- `last` relativo (`15m`, `1h`, `24h`, `7d`)
- `start`/`end` explicitos (ISO datetime)

Reglas:

- `last` no se puede combinar con `start`/`end`.
- formatos invalidos se rechazan.
- `start > end` se rechaza.

## Ejecucion local

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

Configura entorno (ejemplo):

```bash
cp .env.example .env
```

Arranque en `stdio` (default):

```bash
mcp-elastic-logs
```

Arranque en red (`streamable-http`):

```bash
python -m mcp_elastic_logs.server --transport streamable-http --host 0.0.0.0 --port 8093
```

## Ejecucion con Docker

1) Preparar variables:

```bash
cp .env.example .env
```

2) Build de imagen:

```bash
docker build -t mcp-elastic-logs:latest .
```

3) Ejecutar contenedor:

```bash
docker run --rm -p 8093:8093 --env-file .env mcp-elastic-logs:latest
```

## Ejecucion con Docker Compose

```bash
docker compose up --build
```

El servicio queda escuchando en `http://localhost:8093` con transporte `streamable-http`.

## Entorno de test (Elastic + Kibana + Logstash + MCP)

Tambien tienes un stack de test completo en `docker-compose.test.yml`, basado en tu plantilla, con un servicio extra `seed-logs` que carga documentos de ejemplo en `logs-test-000001` para poder probar tools inmediatamente.

Arranque:

```bash
docker compose -f docker-compose.test.yml up --build
```

Servicios disponibles:

- Elasticsearch: `http://localhost:9200`
- Kibana: `http://localhost:5601`
- MCP server: `http://localhost:8093`

Nota: este stack de test usa Elasticsearch con seguridad deshabilitada (`xpack.security.enabled=false`).
El MCP puede conectar sin credenciales en ese escenario, asi que el compose de test no necesita valores dummy.

## Configuracion de cliente MCP (ejemplo)

```json
{
  "mcpServers": {
    "elastic-logs": {
      "command": "mcp-elastic-logs",
      "env": {
        "ELASTICSEARCH_URL": "https://localhost:9200",
        "ELASTICSEARCH_API_KEY": "<your-api-key>",
        "ELASTICSEARCH_INDEX_PATTERN": "logs-*",
        "ELASTICSEARCH_VERIFY_CERTS": "false"
      }
    }
  }
}
```

## Documentacion auxiliar

- `tools.md`: detalle de tools, parametros y comportamiento.
- `Agents.md`: objetivo del proyecto, stack usado y guia de lectura.
