@echo off
chcp 65001 >nul

echo ============================================
echo   StudyBot - Docker 停止
echo ============================================
echo.

cd /d "%~dp0\.."

docker-compose down

echo.
echo [OK] 全サービスを停止しました。
echo.
echo   データを完全に削除する場合:
echo     docker-compose down -v
echo.
pause
