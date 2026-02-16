@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 패키지 설치 중... (1~2분 소요)
echo.
py -m pip install -r requirements.txt

echo.
echo ========================================
echo 설치 완료!
echo 이제 타로채널.bat 을 실행하세요.
echo ========================================
pause
