# Remote (HTTP) mode image for Cloud Run
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CLOUDHPC_MCP_MODE=remote \
    PORT=8080

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd -r -u 10001 app
USER app

EXPOSE 8080
CMD ["cloudhpc-mcp"]
