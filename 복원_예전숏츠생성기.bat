@echo off
chcp 65001 >nul
echo ========================================
echo   예전 숏츠 생성기 (9장 54초) 복원
echo ========================================
echo.
set "BACKUP=_backup_9cards_54sec"
if not exist "%BACKUP%" (
    echo [오류] 백업 폴더가 없습니다: %BACKUP%
    pause
    exit /b 1
)
echo 백업 폴더에서 현재 타로숏츠 폴더로 복사합니다.
echo (.env, .venv, client_secrets.json 은 덮어쓰지 않습니다.)
echo.
robocopy "%BACKUP%" "." /E /XD "%BACKUP%" .venv __pycache__ .git /XF .env client_secrets.json /NFL /NDL
echo.
echo 복원이 완료되었습니다.
pause
