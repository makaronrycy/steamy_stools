FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl ca-certificates gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

COPY req.txt .
# Adding missing dependencies manually just in case, though I'll update req.txt too
RUN pip install --no-cache-dir -r req.txt && \
    pip install --no-cache-dir fastmcp openai websockets

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server_http:app", "--host", "0.0.0.0", "--port", "8000"]
