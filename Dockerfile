FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 仅拷贝真实存在的源码
COPY app.py scheduler.py ./
COPY web ./web

EXPOSE 19841

CMD ["python", "app.py"]
