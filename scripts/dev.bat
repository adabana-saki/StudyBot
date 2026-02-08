@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   StudyBot - ローカル開発モード
echo ============================================
echo.

cd /d "%~dp0\.."

:: .env チェック
if not exist ".env" (
    echo [ERROR] .env が見つかりません。先に setup.bat を実行してください。
    pause
    exit /b 1
)

:: インフラ (PostgreSQL + Redis) だけ Docker で起動
echo [1/4] PostgreSQL + Redis を起動中...
docker-compose up -d postgres redis
timeout /t 3 /nobreak >nul
echo.

:: Bot 起動
echo [2/4] Discord Bot を起動中...
start "StudyBot - Bot" cmd /k "cd /d %cd%\apps\discord-bot && call .venv\Scripts\activate.bat && python main.py"
echo.

:: API 起動
echo [3/4] REST API を起動中...
start "StudyBot - API" cmd /k "cd /d %cd%\apps\api && call .venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"
echo.

:: Web 起動
echo [4/4] Web App を起動中...
start "StudyBot - Web" cmd /k "cd /d %cd%\apps\web && npm run dev"
echo.

echo ============================================
echo   全サービス起動中!
echo ============================================
echo.
echo   Bot:     別ウィンドウで実行中
echo   API:     http://localhost:8000
echo   Swagger: http://localhost:8000/docs
echo   Web:     http://localhost:3000
echo.
echo   各ウィンドウを閉じれば停止します。
echo   PostgreSQL/Redis: docker-compose down
echo.
pause
