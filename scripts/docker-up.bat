@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   StudyBot - Docker 起動
echo ============================================
echo.

cd /d "%~dp0\.."

:: .env チェック
if not exist ".env" (
    echo [ERROR] .env が見つかりません。先に setup.bat を実行してください。
    pause
    exit /b 1
)

:: Docker 起動
echo 全サービスをビルド・起動します...
echo   - PostgreSQL 16
echo   - Redis 7
echo   - Discord Bot
echo   - REST API (http://localhost:8000)
echo   - Web App (http://localhost:3000)
echo.

docker-compose up -d --build

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   起動完了!
    echo ============================================
    echo.
    echo   Web:     http://localhost:3000
    echo   API:     http://localhost:8000
    echo   Swagger: http://localhost:8000/docs
    echo.
    echo   ログ確認: docker-compose logs -f
    echo   停止:     scripts\docker-down.bat
) else (
    echo.
    echo [ERROR] 起動に失敗しました。docker-compose logs で確認してください。
)
echo.
pause
