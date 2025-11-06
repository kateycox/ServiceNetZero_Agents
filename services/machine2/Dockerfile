FROM python:3.11-slim

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /workspace/shared/
COPY services/machine2/ /workspace/services/machine2/

ENV PYTHONPATH=/workspace

CMD ["python", "/workspace/services/machine2/main.py"]
