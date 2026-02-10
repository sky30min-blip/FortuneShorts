# -*- coding: utf-8 -*-
"""
프로젝트 설정 파일 - 한글 인코딩 및 경로 관리
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).parent

# ========================================
# 한글 인코딩 설정 (Windows 필수!)
# ========================================
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# ========================================
# 디렉토리 경로
# ========================================
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
MUSIC_DIR = ASSETS_DIR / "music"
TEMPLATES_DIR = ASSETS_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
THUMBNAILS_DIR = BASE_DIR / "thumbnails"
DATABASE_DIR = BASE_DIR / "database"

# 디렉토리 자동 생성
for dir_path in [ASSETS_DIR, FONTS_DIR, MUSIC_DIR, TEMPLATES_DIR,
                 OUTPUT_DIR, THUMBNAILS_DIR, DATABASE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ========================================
# API 설정
# ========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # YouTube Data API v3 (선택, 업로드는 OAuth 사용)
YOUTUBE_CLIENT_SECRETS = BASE_DIR / "client_secrets.json"

# ========================================
# 영상 설정
# ========================================
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_DURATION = 3.0
FORTUNE_DISPLAY_TIME = 0.15  # 운세 화면 표시 시간 (초)
PUZZLE_ANIMATION_DURATION = 2.5  # 퍼즐 애니메이션 시간

# ========================================
# 폰트 설정
# ========================================
KOREAN_FONT_PATH = FONTS_DIR / "NanumGothicBold.ttf"
FONT_SIZE_TITLE = 80
FONT_SIZE_FORTUNE = 100

# ========================================
# 색상 설정 (운세 종류별 배경색)
# ========================================
COLORS = {
    "금전운": "#FFD700",  # 금색
    "애정운": "#FF69B4",  # 핑크
    "건강운": "#32CD32",  # 녹색
    "총운": "#9370DB"     # 보라
}
