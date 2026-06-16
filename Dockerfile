# ReceiptGuard backend — deploys to Alibaba Function Compute (custom container) or SAE.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY static ./static

ENV PYTHONPATH=/app/src
# Function Compute custom containers must listen on $FC_SERVER_PORT (default 9000).
ENV PORT=9000
EXPOSE 9000

CMD ["sh", "-c", "uvicorn receiptguard.api.app:app --host 0.0.0.0 --port ${PORT}"]
