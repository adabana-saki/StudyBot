#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================"
echo "  StudyBot - 初期セットアップ"
echo "============================================"
echo

# .env ファイルの作成
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[OK] .env を作成しました。編集して設定してください:"
    echo "     - DISCORD_TOKEN (必須)"
    echo "     - DISCORD_CLIENT_ID (Web連携時)"
    echo "     - DISCORD_CLIENT_SECRET (Web連携時)"
    echo "     - OPENAI_API_KEY (AI機能を使う場合)"
else
    echo "[SKIP] .env は既に存在します"
fi
echo

# Python 仮想環境 (Bot)
echo "--- Discord Bot セットアップ ---"
if [ ! -d apps/discord-bot/.venv ]; then
    python3 -m venv apps/discord-bot/.venv
    source apps/discord-bot/.venv/bin/activate
    pip install -q -r apps/discord-bot/requirements.txt
    deactivate
    echo "[OK] Discord Bot の依存関係をインストールしました"
else
    echo "[SKIP] 仮想環境は既に存在します"
fi
echo

# Python 仮想環境 (API)
echo "--- REST API セットアップ ---"
if [ ! -d apps/api/.venv ]; then
    python3 -m venv apps/api/.venv
    source apps/api/.venv/bin/activate
    pip install -q -r apps/api/requirements.txt
    deactivate
    echo "[OK] REST API の依存関係をインストールしました"
else
    echo "[SKIP] 仮想環境は既に存在します"
fi
echo

# Node.js (Web)
echo "--- Web App セットアップ ---"
if [ ! -d apps/web/node_modules ]; then
    cd apps/web
    npm install
    cd ../..
    echo "[OK] Web App の依存関係をインストールしました"
else
    echo "[SKIP] node_modules は既に存在します"
fi
echo

echo "============================================"
echo "  セットアップ完了!"
echo "============================================"
echo
echo "次のステップ:"
echo "  1. .env を編集して DISCORD_TOKEN 等を設定"
echo "  2. scripts/docker-up.sh で Docker 起動"
echo "     または scripts/dev.sh でローカル開発"
