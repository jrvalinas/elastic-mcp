FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8093

EXPOSE 8093

CMD ["python", "-m", "mcp_elastic_logs.server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8093"]
