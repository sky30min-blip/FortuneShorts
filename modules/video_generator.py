# -*- coding: utf-8 -*-
"""
영상 생성 모듈
MoviePy를 사용한 퍼즐 애니메이션 및 운세 화면 합성
"""
import os
from moviepy.editor import (
    ImageClip,
    CompositeVideoClip,
    AudioFileClip,
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import Tuple

import config
from modules.puzzle_creator import (
    get_puzzle_mask,
    extract_puzzle_piece,
    create_background_with_hole,
)


def create_fortune_image(fortune_text: str, fortune_type: str) -> Image.Image:
    """
    운세 텍스트 이미지 생성

    Args:
        fortune_text: 운세 내용 (예: "금전운 대박!")
        fortune_type: 운세 종류 (금전운, 애정운, 건강운, 총운)

    Returns:
        운세 이미지 (PIL Image)
    """
    # 캔버스 생성 (RGB)
    img = Image.new(
        'RGB',
        (config.VIDEO_WIDTH, config.VIDEO_HEIGHT),
        color=config.COLORS.get(fortune_type, '#9370DB')
    )
    draw = ImageDraw.Draw(img)

    # 폰트 로드 (한글 지원)
    try:
        font = ImageFont.truetype(
            str(config.KOREAN_FONT_PATH),
            config.FONT_SIZE_FORTUNE
        )
    except Exception:
        print(f"⚠️ 폰트 로드 실패: {config.KOREAN_FONT_PATH}")
        font = ImageFont.load_default()

    # 텍스트 중앙 배치 (PIL 10+ textbbox 사용)
    bbox = draw.textbbox((0, 0), fortune_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (config.VIDEO_WIDTH - text_width) // 2
    y = (config.VIDEO_HEIGHT - text_height) // 2

    # 그림자 효과
    shadow_offset = 5
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        fortune_text,
        font=font,
        fill=(0, 0, 0)
    )

    # 메인 텍스트
    draw.text((x, y), fortune_text, font=font, fill='white')

    return img


def animate_puzzle_piece(
    piece_image: Image.Image,
    direction: str,
    duration: float
) -> ImageClip:
    """
    퍼즐 조각 애니메이션 (방향에 따라 이동)

    Args:
        piece_image: 퍼즐 조각 이미지 (RGBA)
        direction: "위→아래", "아래→위", "좌→우", "우→좌"
        duration: 애니메이션 시간 (초)

    Returns:
        MoviePy ImageClip
    """
    width, height = piece_image.size

    # 방향별 시작/끝 위치 계산
    if direction == "위→아래":
        start_pos = (0, -height)
        end_pos = (0, 0)
    elif direction == "아래→위":
        start_pos = (0, height)
        end_pos = (0, 0)
    elif direction == "좌→우":
        start_pos = (-width, 0)
        end_pos = (0, 0)
    elif direction == "우→좌":
        start_pos = (width, 0)
        end_pos = (0, 0)
    else:
        raise ValueError(f"지원하지 않는 방향: {direction}")

    # RGBA → RGB 변환 (MoviePy 호환, 흰 배경)
    arr = np.array(piece_image)
    if arr.shape[2] == 4:
        rgb = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
        alpha = arr[:, :, 3:4] / 255.0
        rgb[:, :, :] = (arr[:, :, :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
        arr = rgb

    clip = ImageClip(arr).set_duration(duration)

    # 위치 애니메이션 함수 (ease-in-out)
    def position_func(t):
        progress = t / duration
        if progress < 0.5:
            eased = 2 * progress * progress
        else:
            eased = 1 - pow(-2 * progress + 2, 2) / 2
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * eased
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * eased
        return (x, y)

    clip = clip.set_position(position_func)

    return clip


def generate_fortune_video(
    background_path: str,
    puzzle_shape: str,
    direction: str,
    fortune_text: str,
    fortune_type: str,
    music_path: str,
    output_path: str
) -> str:
    """
    운세 Shorts 영상 생성

    타임라인:
    0.0 - 0.5초: 배경만 표시 (퍼즐 구멍 있음)
    0.5 - 2.5초: 퍼즐 조각 애니메이션 (2초)
    2.5 - 2.65초: 운세 화면 표시 (0.15초)
    2.65 - 3.0초: 다시 완성된 배경

    Args:
        background_path: 배경 이미지 경로
        puzzle_shape: "하트", "별", "달", "클로버"
        direction: "위→아래", "아래→위", "좌→우", "우→좌"
        fortune_text: 운세 텍스트
        fortune_type: 운세 종류
        music_path: 배경음악 경로 (None 가능)
        output_path: 출력 파일 경로

    Returns:
        생성된 영상 경로
    """
    print("🎬 영상 생성 시작...")
    print(f"  - 배경: {background_path}")
    print(f"  - 퍼즐: {puzzle_shape} ({direction})")
    print(f"  - 운세: {fortune_text}")

    # 1. 이미지 로드
    background = Image.open(background_path).convert('RGB')
    background = background.resize((config.VIDEO_WIDTH, config.VIDEO_HEIGHT))

    # 2. 퍼즐 마스크 생성
    mask = get_puzzle_mask(puzzle_shape, background.size)

    # 3. 퍼즐 조각 & 구멍 뚫린 배경 생성
    puzzle_piece = extract_puzzle_piece(background, mask)
    background_hole = create_background_with_hole(background, mask)

    # 4. 운세 이미지 생성
    fortune_img = create_fortune_image(fortune_text, fortune_type)

    # 5. 클립 생성
    # 배경 (구멍 있음) - 0~3초 전체
    bg_hole_arr = np.array(background_hole)
    if bg_hole_arr.shape[2] == 4:
        rgb_bg = np.zeros((bg_hole_arr.shape[0], bg_hole_arr.shape[1], 3), dtype=np.uint8)
        alpha = bg_hole_arr[:, :, 3:4] / 255.0
        rgb_bg[:, :, :] = (bg_hole_arr[:, :, :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
        bg_hole_arr = rgb_bg

    clip_bg_hole = ImageClip(bg_hole_arr).set_duration(config.VIDEO_DURATION)

    # 완성된 배경 - 2.65~3초
    clip_bg_complete = (
        ImageClip(np.array(background))
        .set_start(2.65)
        .set_duration(0.35)
    )

    # 퍼즐 조각 애니메이션 - 0.5~2.5초
    clip_puzzle = animate_puzzle_piece(
        puzzle_piece,
        direction,
        config.PUZZLE_ANIMATION_DURATION
    ).set_start(0.5)

    # 운세 화면 - 2.5~2.65초
    clip_fortune = (
        ImageClip(np.array(fortune_img))
        .set_start(2.5)
        .set_duration(config.FORTUNE_DISPLAY_TIME)
    )

    # 6. 합성 (아래부터 쌓기: 배경 구멍 → 퍼즐 → 운세 → 완성 배경)
    final_clip = CompositeVideoClip(
        [clip_bg_hole, clip_puzzle, clip_fortune, clip_bg_complete],
        size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT)
    )

    # 7. 배경음악 추가 (로드 실패 시 무음으로 진행)
    audio = None
    if music_path and os.path.exists(music_path):
        try:
            audio = AudioFileClip(music_path).subclip(0, config.VIDEO_DURATION)
            final_clip = final_clip.set_audio(audio)
        except Exception as e:
            print(f"⚠️ 배경음악 로드 실패, 무음으로 진행: {e}")

    # 8. 렌더링
    print("🎥 렌더링 중...")
    final_clip.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        threads=4,
        logger=None
    )

    # 9. 메모리 정리
    clip_bg_hole.close()
    clip_bg_complete.close()
    clip_puzzle.close()
    clip_fortune.close()
    final_clip.close()
    if audio is not None:
        audio.close()

    print(f"✅ 영상 생성 완료: {output_path}")
    return output_path
