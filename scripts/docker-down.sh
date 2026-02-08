#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================"
echo "  StudyBot - Docker 停止"
echo "============================================"
echo

docker-compose down

echo
echo "[OK] 全サービスを停止しました。"
echo
echo "  データを完全に削除する場合:"
echo "    docker-compose down -v"
