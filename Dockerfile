FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# ---------- 系统依赖 ----------
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    php-fpm \
    php-sqlite3 \
    php-zip \
    php-cli \
    && rm -rf /var/lib/apt/lists/*

# ---------- Python 依赖 ----------
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---------- 项目文件 ----------
COPY app.py /app/app.py
COPY scheduler.py /app/scheduler.py
COPY web /app/web
COPY data /app/data
COPY logs /app/logs

# ---------- 配置文件 ----------
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ---------- 权限 ----------
RUN chown -R www-data:www-data /app/web /app/logs /app/data

# ---------- 端口 ----------
EXPOSE 19841

# ---------- 启动 ----------
CMD ["/usr/bin/supervisord", "-n"]
