@echo off
chcp 65001 >nul

echo ============================================
echo   StudyBot - ログ表示
echo ============================================
echo.
echo   1: 全サービス
echo   2: Bot のみ
echo   3: API のみ
echo   4: Web のみ
echo   5: PostgreSQL のみ
echo   6: Redis のみ
echo.

cd /d "%~dp0\.."

set /p choice="番号を選択: "

if "%choice%"=="1" docker-compose logs -f --tail=100
if "%choice%"=="2" docker-compose logs -f --tail=100 bot
if "%choice%"=="3" docker-compose logs -f --tail=100 api
if "%choice%"=="4" docker-compose logs -f --tail=100 web
if "%choice%"=="5" docker-compose logs -f --tail=100 postgres
if "%choice%"=="6" docker-compose logs -f --tail=100 redis
