# -*- coding: utf-8 -*-
"""
썸네일 생성 모듈
영상에서 프레임 추출 및 텍스트 오버레이
"""
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import List

import config


def add_text_overlay(img: Image.Image, text: str) -> Image.Image:
    """
    이미지에 텍스트 오버레이 추가 (하단 반투명 박스 + 한글 텍스트)

    Args:
        img: PIL Image (RGB)
        text: 표시할 텍스트

    Returns:
        텍스트가 추가된 이미지
    """
    draw = ImageDraw.Draw(img)

    # 폰트 로드 (한글)
    try:
        font = ImageFont.truetype(str(config.KOREAN_FONT_PATH), 60)
    except Exception:
        print("⚠️ 폰트 로드 실패, 기본 폰트 사용")
        font = ImageFont.load_default()

    # 텍스트를 2줄로 나누기 (길면)
    if len(text) > 25:
        words = text.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        lines = [line1, line2]
    else:
        lines = [text]

    # 하단부터 위로 배치
    y_start = img.height - 200
    padding = 20

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (img.width - text_width) // 2

        # 반투명 검정 배경 (RGB에서는 진한 회색으로 표현)
        draw.rectangle(
            [
                x - padding, y_start - padding,
                x + text_width + padding, y_start + text_height + padding
            ],
            fill=(40, 40, 40)
        )

        # 그림자
        shadow_offset = 3
        draw.text(
            (x + shadow_offset, y_start + shadow_offset),
            line,
            font=font,
            fill=(0, 0, 0)
        )

        # 메인 텍스트
        draw.text((x, y_start), line, font=font, fill='white')

        y_start += text_height + 10

    return img


def generate_thumbnails(
    video_path: str,
    title_text: str
) -> List[str]:
    """
    영상에서 썸네일 3개 생성 (시작 10%, 중간 50%, 끝 90% 구간 프레임)

    Args:
        video_path: 영상 파일 경로
        title_text: 썸네일에 표시할 텍스트

    Returns:
        생성된 썸네일 경로 리스트
    """
    print("🎨 썸네일 생성 중...")

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    thumbnails = []

    positions = [0.1, 0.5, 0.9]

    for i, pos in enumerate(positions):
        frame_num = int(total_frames * pos)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()

        if not ret:
            print(f"⚠️ 프레임 {i+1} 추출 실패")
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        # 썸네일 크기 (1280x720)
        img = img.resize((1280, 720), Image.Resampling.LANCZOS)

        img = add_text_overlay(img, title_text)

        thumb_path = config.THUMBNAILS_DIR / f"thumb_{i+1}.jpg"
        img.save(thumb_path, quality=95)
        thumbnails.append(str(thumb_path))
        print(f"  ✓ 썸네일 {i+1} 생성: {thumb_path}")

    cap.release()
    print(f"✅ 썸네일 {len(thumbnails)}개 생성 완료")
    return thumbnails
