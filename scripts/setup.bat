@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   StudyBot - 初期セットアップ
echo ============================================
echo.

cd /d "%~dp0\.."

:: .env ファイルの作成
if not exist ".env" (
    copy .env.example .env >nul
    echo [OK] .env を作成しました。編集して設定してください:
    echo      - DISCORD_TOKEN (必須)
    echo      - DISCORD_CLIENT_ID (Web連携時)
    echo      - DISCORD_CLIENT_SECRET (Web連携時)
    echo      - OPENAI_API_KEY (AI機能を使う場合)
) else (
    echo [SKIP] .env は既に存在します
)
echo.

:: Python 仮想環境 (Bot)
echo --- Discord Bot セットアップ ---
if not exist "apps\discord-bot\.venv" (
    echo 仮想環境を作成中...
    python -m venv apps\discord-bot\.venv
    call apps\discord-bot\.venv\Scripts\activate.bat
    pip install -q -r apps\discord-bot\requirements.txt
    call deactivate
    echo [OK] Discord Bot の依存関係をインストールしました
) else (
    echo [SKIP] 仮想環境は既に存在します
)
echo.

:: Python 仮想環境 (API)
echo --- REST API セットアップ ---
if not exist "apps\api\.venv" (
    echo 仮想環境を作成中...
    python -m venv apps\api\.venv
    call apps\api\.venv\Scripts\activate.bat
    pip install -q -r apps\api\requirements.txt
    call deactivate
    echo [OK] REST API の依存関係をインストールしました
) else (
    echo [SKIP] 仮想環境は既に存在します
)
echo.

:: Node.js (Web)
echo --- Web App セットアップ ---
if not exist "apps\web\node_modules" (
    cd apps\web
    call npm install
    cd ..\..
    echo [OK] Web App の依存関係をインストールしました
) else (
    echo [SKIP] node_modules は既に存在します
)
echo.

echo ============================================
echo   セットアップ完了!
echo ============================================
echo.
echo 次のステップ:
echo   1. .env を編集して DISCORD_TOKEN 等を設定
echo   2. scripts\docker-up.bat で Docker 起動
echo      または scripts\dev.bat でローカル開発
echo.
pause
