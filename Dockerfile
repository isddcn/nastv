FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    libnss3 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgtk-3-0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY app.py .
RUN mkdir -p /app/data

EXPOSE 19841
CMD ["python", "app.py"]
