#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================"
echo "  StudyBot - テスト実行"
echo "============================================"
echo

FAIL=0

# Discord Bot テスト
echo "--- Discord Bot テスト ---"
(
    cd apps/discord-bot
    source .venv/bin/activate 2>/dev/null || true
    python -m pytest tests/ -x -q --tb=short
) && echo "[PASS] Discord Bot" || { echo "[FAIL] Discord Bot"; FAIL=$((FAIL+1)); }
echo

# API テスト
echo "--- REST API テスト ---"
(
    cd apps/api
    source .venv/bin/activate 2>/dev/null || true
    python -m pytest tests/ -x -q --tb=short
) && echo "[PASS] REST API" || { echo "[FAIL] REST API"; FAIL=$((FAIL+1)); }
echo

# 結果表示
echo "============================================"
if [ $FAIL -eq 0 ]; then
    echo "  全テスト成功!"
else
    echo "  ${FAIL} スイートが失敗しました"
    exit 1
fi
echo "============================================"
