@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 타로 덱 다운로드 (실행할 때마다 다음 덱 다운로드)
echo deck_01, deck_02, ... deck_05 순서로 하나씩 다운로드됩니다.
echo.
py scripts/download_tarot_decks.py
echo.
pause
