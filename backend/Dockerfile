FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY req.txt .
# Adding missing dependencies manually just in case, though I'll update req.txt too
RUN pip install --no-cache-dir -r req.txt && \
    pip install --no-cache-dir fastmcp openai websockets

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server_http:app", "--host", "0.0.0.0", "--port", "8000"]
