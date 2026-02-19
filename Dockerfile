FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy memory-mcp source so it's importable as memory_mcp
COPY memory-mcp/src/memory_mcp/ ./memory_mcp/

COPY server.py .

ENV PORT=8080
ENV CHROMA_PERSIST_PATH=/tmp/chroma_data
EXPOSE 8080

CMD ["python", "server.py"]
