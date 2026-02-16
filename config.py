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
IMAGES_DIR = ASSETS_DIR / "images"  # 배경 이미지 (여기에 넣으면 랜덤 선택)
CARD_BACKS_DIR = ASSETS_DIR / "card_backs"  # 카드 뒷면 이미지 (여기에 넣으면 랜덤 선택)
THUMBNAIL_BACKGROUNDS_DIR = ASSETS_DIR / "thumbnail_backgrounds"  # 썸네일 배경 (타로운세 1장 생성 시 랜덤)
MUSIC_DIR = ASSETS_DIR / "music"
# 배경음악 시작 시점
# MUSIC_AUTO_HIGHLIGHT=True: 음악에서 가장 큰 소리 구간(캐치한 부분)을 자동으로 찾아서 그 지점부터 재생
# MUSIC_AUTO_HIGHLIGHT=False: MUSIC_START_OFFSET_SEC 값(초)을 사용 (0=처음부터, 30=30초부터)
MUSIC_AUTO_HIGHLIGHT = True
MUSIC_START_OFFSET_SEC = 0
TEMPLATES_DIR = ASSETS_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
THUMBNAILS_DIR = BASE_DIR / "thumbnails"
DATABASE_DIR = BASE_DIR / "database"
TAROT_DIR = ASSETS_DIR / "tarot"

# 디렉토리 자동 생성
for dir_path in [ASSETS_DIR, FONTS_DIR, IMAGES_DIR, CARD_BACKS_DIR, THUMBNAIL_BACKGROUNDS_DIR, MUSIC_DIR, TEMPLATES_DIR,
                 OUTPUT_DIR, THUMBNAILS_DIR, DATABASE_DIR, TAROT_DIR]:
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

# 기존 숏츠: 6장 카드, 시간 단축 (~36초)
NUM_CARDS = 6
VIDEO_DURATION = 36.0  # 6장 카드 버전

# 영상 인코딩 속도 (빠를수록 파일 크기 약간 증가)
# ultrafast / superfast / veryfast / faster / fast / medium / slow
VIDEO_ENCODE_PRESET = "fast"
VIDEO_ENCODE_THREADS = 0  # 0=자동(코어 수), 4~8 권장

TAROT_SECTION_TIMES = {
    "hook": 1,               # 첫 화면 1초(문구 없음, 썸네일에만 표시) → 바로 카드 구간
    "cards_face": 3.5,       # 앞장 + 뒤집기
    "gather_to_center": 1,   # 뒷면이 중앙으로 모임
    "shuffle": 1.5,          # 6장 셔플 (1초 단축)
    "arrange_move": 1.2,     # 중앙 → 1~6번 자리
    "arrange_facedown": 3,   # 카드 뒷면 + "한 장 선택하세요"
    "arrange_faceup": 1.8,   # 카드 뒤집어서 공개
    "flip_hold": 2,          # 6장 펼쳐진 상태 유지
    "cards_1_3": 3.5,        # 1~3번 카드 리딩 3.5초
    "cards_4_6": 3.5,        # 4~6번 카드 리딩 3.5초
    "segment_transition": 1.2,  # 구간 전환
    "closing": 4,            # 마지막 인사 + 구독/좋아요
}
# 7~9번 구간 제거 (6장만 사용). 총 ~36초

# ========================================
# 폰트 설정 (한글 지원)
# ========================================
KOREAN_FONT_PATH = FONTS_DIR / "NanumGothicBold.ttf"
# 숏츠용 두껍고 각진 폰트 우선 (Gmarket, Pretendard → assets/fonts에 추가 시 사용)
FONT_FALLBACKS = [
    str(FONTS_DIR / "GmarketSansBold.otf"),
    str(FONTS_DIR / "GmarketSansTTFBold.ttf"),
    str(FONTS_DIR / "Pretendard-ExtraBold.otf"),
    str(FONTS_DIR / "NanumSquareRoundBold.ttf"),
    str(FONTS_DIR / "NanumSquareRoundR.ttf"),
    str(FONTS_DIR / "NanumGothicBold.ttf"),
    str(FONTS_DIR / "NanumGothic.ttf"),
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "malgun.ttf"),
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "gulim.ttc"),
]
FONT_SIZE_TITLE = 80
FONT_SIZE_FORTUNE = 100


def get_korean_font(size: int = 48, font_path: str | None = None) -> "ImageFont.FreeTypeFont":
    """한글 지원 폰트 반환 (PIL ImageFont). font_path 지정 시 해당 폰트 사용."""
    from PIL import ImageFont
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    for path in FONT_FALLBACKS:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    raise FileNotFoundError(
        "한글 폰트를 찾을 수 없습니다. assets/fonts/에 NanumGothicBold.ttf를 넣어주세요."
    )


def get_random_font_path() -> str | None:
    """assets/fonts에서 .ttf, .otf 랜덤 선택. 없으면 None."""
    import random
    fonts = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
    fonts = [str(p) for p in fonts if p.is_file()]
    return random.choice(fonts) if fonts else None


def get_random_background_path() -> str | None:
    """assets/images에서 배경 이미지 랜덤 선택. 없으면 None."""
    import random
    imgs = list(IMAGES_DIR.glob("*.png")) + list(IMAGES_DIR.glob("*.jpg")) + list(IMAGES_DIR.glob("*.jpeg"))
    imgs = [str(p) for p in imgs if p.is_file()]
    return random.choice(imgs) if imgs else None


def get_random_music_path() -> str | None:
    """assets/music에서 배경음악 랜덤 선택. 없으면 None."""
    import random
    musics = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav")) + list(MUSIC_DIR.glob("*.m4a"))
    musics = [str(p) for p in musics if p.is_file()]
    return random.choice(musics) if musics else None

# ========================================
# 색상 설정 (운세 종류별 배경색)
# ========================================
COLORS = {
    "금전운": "#FFD700",  # 금색
    "애정운": "#FF69B4",  # 핑크
    "건강운": "#32CD32",  # 녹색
    "총운": "#9370DB"     # 보라
}
