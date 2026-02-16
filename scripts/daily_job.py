# scripts/daily_job.py
import os
import random
from pathlib import Path
from datetime import datetime

import config
from modules.tarot_video_generator import generate_tarot_video
from modules.metadata_generator import (
    generate_titles,
    generate_description,
    generate_hashtags,
    set_openai_api_key,
)
from modules.youtube_uploader import upload_video

# GitHub Actions 시크릿에서 API 키 가져오기
openai_key = os.getenv("OPENAI_API_KEY", "") or (config.OPENAI_API_KEY or "")
if openai_key:
    config.OPENAI_API_KEY = openai_key
    set_openai_api_key(openai_key)


def _pick_random_background() -> str:
    """assets/images 폴더에서 랜덤 배경 1장 선택."""
    folder = Path(config.BASE_DIR) / "assets" / "images"
    if not folder.exists():
        raise RuntimeError(f"배경 폴더가 없습니다: {folder}")

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    candidates = [
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts
    ]
    if not candidates:
        raise RuntimeError(f"배경 폴더에 이미지가 없습니다: {folder}")

    chosen = random.choice(candidates)
    print("🖼️ 선택된 배경:", chosen)
    return str(chosen)


def main():
    # 1) 오늘 날짜
    today = datetime.now().strftime("%m월 %d일")

    # 2) 배경 이미지 (이미지 폴더에서 랜덤)
    background_path = _pick_random_background()

    # 3) 운세 종류 랜덤 선택
    fortune_type = random.choice(["총운", "애정운", "금전운", "건강운"])

    # 4) 영상 파일 경로
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = config.OUTPUT_DIR / f"tarot_{timestamp}.mp4"

    # 5) 배경음악(있으면) 랜덤 선택
    music_arg = config.get_random_music_path()

    # 6) 타로 영상 생성
    video_path, theme_name, metadata_extra = generate_tarot_video(
        fortune_type=fortune_type,
        background_path=background_path,
        music_path=music_arg,
        output_path=str(output_path),
    )

    # 7) 메타데이터 자동 생성 (9장 카드 상세 설명 포함)
    titles = generate_titles(fortune_type, today)
    title = titles[0] if titles else f"🔮 {today} 오늘의 {fortune_type}"
    description = generate_description(fortune_type, today, card_metadata=metadata_extra)
    tags = generate_hashtags(fortune_type)

    # 8) 유튜브 업로드 (썸네일 없이)
    result = upload_video(
        video_path=str(video_path) if isinstance(video_path, str) else str(video_path),
        title=title,
        description=description,
        tags=tags,
        thumbnail_path=None,
        privacy="public",
        scheduled_time=None,
    )
    if not result.get("success"):
        raise RuntimeError(f"업로드 실패: {result.get('error')}")

    print("✅ 업로드 완료:", result["url"])


if __name__ == "__main__":
    main()
