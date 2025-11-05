FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /workspace/shared/
COPY services/machine1/ /workspace/services/machine1/

ENV PYTHONPATH=/workspace

CMD ["python", "/workspace/services/machine1/main.py"]
