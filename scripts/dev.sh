#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================"
echo "  StudyBot - ローカル開発モード"
echo "============================================"
echo

if [ ! -f .env ]; then
    echo "[ERROR] .env が見つかりません。先に setup.sh を実行してください。"
    exit 1
fi

# .env を読み込み
set -a
source .env
set +a

# インフラ起動
echo "[1/4] PostgreSQL + Redis を起動中..."
docker-compose up -d postgres redis
sleep 3
echo

# Bot 起動
echo "[2/4] Discord Bot を起動中..."
(
    cd apps/discord-bot
    source .venv/bin/activate 2>/dev/null || true
    python main.py
) &
BOT_PID=$!
echo "  Bot PID: $BOT_PID"
echo

# API 起動
echo "[3/4] REST API を起動中..."
(
    cd apps/api
    source .venv/bin/activate 2>/dev/null || true
    uvicorn main:app --reload --port 8000
) &
API_PID=$!
echo "  API PID: $API_PID"
echo

# Web 起動
echo "[4/4] Web App を起動中..."
(
    cd apps/web
    npm run dev
) &
WEB_PID=$!
echo "  Web PID: $WEB_PID"
echo

echo "============================================"
echo "  全サービス起動中!"
echo "============================================"
echo
echo "  Bot:     PID $BOT_PID"
echo "  API:     http://localhost:8000 (PID $API_PID)"
echo "  Web:     http://localhost:3000 (PID $WEB_PID)"
echo
echo "  Ctrl+C で全プロセスを停止します。"
echo

# シグナルハンドラ
cleanup() {
    echo
    echo "停止中..."
    kill $BOT_PID $API_PID $WEB_PID 2>/dev/null || true
    wait 2>/dev/null || true
    echo "[OK] 全プロセスを停止しました。"
    echo "  PostgreSQL/Redis: docker-compose down"
}
trap cleanup EXIT INT TERM

# 子プロセスを待機
wait
