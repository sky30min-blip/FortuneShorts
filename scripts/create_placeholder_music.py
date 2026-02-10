# -*- coding: utf-8 -*-
"""
assets/music/cheerful.mp3 생성 (FFmpeg로 3초 무음)
실제 BGM으로 나중에 교체 가능
"""
import subprocess
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config


def get_ffmpeg():
    """PATH 또는 imageio_ffmpeg 번들에서 ffmpeg 경로 반환"""
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def main():
    config.MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.MUSIC_DIR / "cheerful.mp3"
    duration = 3  # 초

    ffmpeg_exe = get_ffmpeg()
    if not ffmpeg_exe:
        print("ffmpeg를 찾을 수 없습니다. cheerful.mp3를 직접 넣어주세요.")
        sys.exit(1)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-acodec", "libmp3lame", "-q:a", "9",
        str(out_path)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  생성: {out_path}")
        print("배경음악(무음) 파일 생성 완료. 실제 BGM으로 교체하세요.")
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
