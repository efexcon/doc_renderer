FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/

EXPOSE 3200

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "3200"]
