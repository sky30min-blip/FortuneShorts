@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 숏츠 생성기 현재 버전을 _backup_9cards_54sec 에 백업합니다.
.venv\Scripts\python.exe do_backup_9cards.py
pause
