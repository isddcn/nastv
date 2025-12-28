FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py scheduler.py ./
COPY web ./web

EXPOSE 19841
CMD ["python", "app.py"]
