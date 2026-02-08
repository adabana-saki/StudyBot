@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   StudyBot - テスト実行
echo ============================================
echo.

cd /d "%~dp0\.."

set TOTAL_PASS=0
set TOTAL_FAIL=0

:: Discord Bot テスト
echo --- Discord Bot テスト ---
cd apps\discord-bot
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    python -m pytest tests/ -x -q --tb=short 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [PASS] Discord Bot テスト成功
    ) else (
        echo [FAIL] Discord Bot テスト失敗
        set /a TOTAL_FAIL+=1
    )
    call deactivate
) else (
    python -m pytest tests/ -x -q --tb=short 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [PASS] Discord Bot テスト成功
    ) else (
        echo [FAIL] Discord Bot テスト失敗
        set /a TOTAL_FAIL+=1
    )
)
cd ..\..
echo.

:: API テスト
echo --- REST API テスト ---
cd apps\api
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    python -m pytest tests/ -x -q --tb=short 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [PASS] REST API テスト成功
    ) else (
        echo [FAIL] REST API テスト失敗
        set /a TOTAL_FAIL+=1
    )
    call deactivate
) else (
    python -m pytest tests/ -x -q --tb=short 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [PASS] REST API テスト成功
    ) else (
        echo [FAIL] REST API テスト失敗
        set /a TOTAL_FAIL+=1
    )
)
cd ..\..
echo.

:: 結果表示
echo ============================================
if %TOTAL_FAIL% EQU 0 (
    echo   全テスト成功!
) else (
    echo   %TOTAL_FAIL% スイートが失敗しました
)
echo ============================================
echo.
pause
