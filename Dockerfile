FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 仅拷贝“代码本身”
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py scheduler.py ./
COPY routes ./routes
COPY static ./static
COPY templates ./templates
COPY web ./web

# 运行时目录由宿主机 volume 挂载
# /data /logs 不在镜像内创建

EXPOSE 19841

CMD ["python", "app.py"]
