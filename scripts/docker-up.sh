#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================"
echo "  StudyBot - Docker 起動"
echo "============================================"
echo

if [ ! -f .env ]; then
    echo "[ERROR] .env が見つかりません。先に setup.sh を実行してください。"
    exit 1
fi

echo "全サービスをビルド・起動します..."
docker-compose up -d --build

echo
echo "============================================"
echo "  起動完了!"
echo "============================================"
echo
echo "  Web:     http://localhost:3000"
echo "  API:     http://localhost:8000"
echo "  Swagger: http://localhost:8000/docs"
echo
echo "  ログ確認: docker-compose logs -f"
echo "  停止:     scripts/docker-down.sh"
