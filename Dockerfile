# Same Python version as CI (doc 07, section 1). Slim: Debian with only what Python needs.
FROM python:3.12-slim
WORKDIR /app

# Logs reach Render right away instead of sitting in a buffer
ENV PYTHONUNBUFFERED=1

# the manifest changes rarely: copy it and install first (this layer stays cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# the source changes constantly: copy it last
COPY . .

# Render sets PORT at run time; 8000 is the local default
ENV PORT=8000
EXPOSE 8000
# 0.0.0.0: reachable from outside the container. exec: uvicorn receives Render's stop signal.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
