FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# システム依存パッケージ
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 fonts-noto-cjk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY . .

# 非rootユーザー
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app
USER botuser

CMD ["python", "-u", "main.py"]
