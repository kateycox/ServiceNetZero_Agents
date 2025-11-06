FROM python:3.11-slim

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api_gateway/ /workspace/api_gateway/

ENV PYTHONPATH=/workspace

CMD ["python", "/workspace/api_gateway/main.py"]
