FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
COPY app.py .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs /app/tokens

CMD ["python", "app.py"]