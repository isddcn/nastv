FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir supervisor

COPY app.py scheduler.py supervisord.conf ./
COPY web ./web

RUN mkdir -p /app/data /app/logs

EXPOSE 19841

CMD ["supervisord", "-c", "/app/supervisord.conf"]
