# 带 Chromium/Firefox/WebKit + 依赖 的官方镜像（最省事、最稳）
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 你的实际代码（只拷贝真实存在的）
COPY app.py scheduler.py ./
COPY web ./web

EXPOSE 19841
CMD ["python", "app.py"]
