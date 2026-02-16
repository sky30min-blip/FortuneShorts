# -*- coding: utf-8 -*-
"""
타로 운세 Shorts 영상 생성
6장 카드, 셔플, 의미 표시 (~36초).
"""
import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
# editor 대신 필요한 모듈만 직접 import (Blink 등 fx 호환성 문제 회피)
from moviepy.video.VideoClip import ImageClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.audio.io.AudioFileClip import AudioFileClip

import config

# 기존 숏츠 카드 수 및 그리드 (6장 = 3x2)
NUM_CARDS = getattr(config, "NUM_CARDS", 6)
GRID_COLS, GRID_ROWS = (3, 2) if NUM_CARDS == 6 else (3, 3)

from modules.tarot_deck import get_random_deck_path, get_card_path
from modules.tarot_meanings import get_card_pool, get_card_info
from modules.shuffle_styles import pick_random_shuffle
from modules.metadata_generator import generate_tarot_interpretations, generate_empathy_ment
from modules.hook_ments import (
    pick_random_hook,
    pick_hook_for_slot,
    pick_minor_fortune_hook,
    pick_major_fortune_hook,
    get_slot_color,
)
from modules import theme_phrases_db
from modules.theme_phrases_db import get_random_unused_hook_title, mark_hook_title_used


def _detect_music_highlight_start(audio_clip, need_dur: float, window_sec: float = 2.0) -> float:
    """
    음악에서 가장 큰 소리(에너지) 구간을 찾아 그 시작 시점(초)을 반환.
    보통 후렴/드롭 구간이 가장 크므로 자동으로 캐치한 부분을 찾음.
    """
    try:
        arr = audio_clip.to_soundarray()
        if arr.size == 0:
            return 0.0
        if arr.ndim == 2:
            arr = arr.mean(axis=1)
        sr = int(audio_clip.fps)
        window_samples = int(window_sec * sr)
        if window_samples >= len(arr):
            return 0.0
        n_windows = (len(arr) - window_samples) // (window_samples // 2) + 1  # 50% 오버랩
        if n_windows <= 0:
            return 0.0
        energies = []
        positions = []
        hop = max(1, window_samples // 2)
        for i in range(0, len(arr) - window_samples + 1, hop):
            chunk = arr[i : i + window_samples].astype(np.float64)
            rms = float(np.sqrt(np.mean(chunk * chunk)))
            energies.append(rms)
            positions.append(i / sr)
            if len(positions) >= 500:
                break
        if not energies:
            return 0.0
        peak_idx = int(np.argmax(energies))
        start = positions[peak_idx]
        max_start = max(0, audio_clip.duration - need_dur - 1)
        return float(min(start, max_start))
    except Exception:
        return 0.0


def _ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = (hex_str or "#1a0a2e").lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# 영상 생성 시 한 번 선택된 폰트 (generate_tarot_video 시작 시 설정)
_video_font_path: str | None = None


def _get_font(size: int, font_path: str | None = None):
    """한글 폰트 로드 (assets/fonts 랜덤 또는 폴백)"""
    try:
        path = font_path or _video_font_path or config.get_random_font_path()
        return config.get_korean_font(size, path)
    except Exception:
        try:
            return config.get_korean_font(size)
        except Exception:
            return ImageFont.load_default()


def _num_to_korean(n: int) -> str:
    """숫자를 한글로 (폰트에서 ㅁ 표시되는 문제 방지)"""
    # 자주 쓰는 수 (폰트 ㅁ 방지 - 숫자를 한글로)
    common = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 14: "열넷", 22: "스물두", 78: "일흔여덟"}
    if n in common:
        return common[n]
    if n < 10:
        return ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"][n] if n > 0 else "영"
    if n < 100:
        t, u = divmod(n, 10)
        tens = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]
        units = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]
        return tens[t] + (units[u] if u > 0 else "")
    return str(n)


def _get_empathy_highlight_keywords() -> list[str]:
    """공감 멘트에서 강조할 핵심 키워드 (감성형 타로 주제 관련). 긴 것 우선."""
    return [
        "궁금하시면", "궁금하신가요", "골라보세요", "선택하세요",
        "궁금", "골라", "선택", "진짜", "진심", "응원", "시기", "편이", "구별",
        "썸", "어장", "재회", "미련", "마음", "행동", "상대방", "솔직", "카드",
    ]


def _split_line_with_highlights(line: str, keywords: list[str]) -> list[tuple[str, bool]]:
    """
    한 줄을 (텍스트, 강조여부) 세그먼트로 분할. 키워드 포함 구간은 강조.
    """
    if not line:
        return []
    # 키워드 매칭: (시작위치, 끝위치) 집합 (겹치면 긴 것 우선)
    matches = []
    for kw in keywords:
        if len(kw) < 2:
            continue
        start = 0
        while True:
            idx = line.find(kw, start)
            if idx < 0:
                break
            matches.append((idx, idx + len(kw)))
            start = idx + 1
    if not matches:
        return [(line, False)]
    # 겹치는 구간 병합 (시작순, 겹치면 합침)
    matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
    merged = []
    for s, e in matches:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    # 세그먼트 생성
    segments = []
    pos = 0
    for s, e in merged:
        if pos < s:
            seg = line[pos:s]
            if seg:
                segments.append((seg, False))
        segments.append((line[s:e], True))
        pos = e
    if pos < len(line):
        seg = line[pos:]
        if seg:
            segments.append((seg, False))
    return segments if segments else [(line, False)]


def _wrap_by_chars(text: str, chars_per_line: int = 12, max_lines: int = 10) -> list[str]:
    """한 줄에 10~14자 정도로 줄바꿈 (단어 끊기지 않게). 한두 글자만 단독 줄 되지 않게 함."""
    if not text or chars_per_line <= 0:
        return [text] if text else []
    lines = []
    remain = text.strip()
    while remain and len(lines) < max_lines:
        if len(remain) <= chars_per_line:
            lines.append(remain)
            break
        cut = min(chars_per_line, len(remain))
        for i in range(cut - 1, 0, -1):
            if remain[i] in " \t,，.。!?、":
                cut = i + 1
                break
        line = remain[:cut].strip()
        # "그", "와" 등 한두 글자만 한 줄에 오지 않게 다음 단어까지 붙임
        if len(line) <= 2 and len(remain) > cut:
            rest = remain[cut:].strip()
            next_space = rest.find(" ")
            if next_space > 0:
                line = (line + " " + rest[:next_space]).strip()
                cut = cut + next_space + 1
                while cut < len(remain) and remain[cut] == " ":
                    cut += 1
            elif rest:
                line = (line + " " + rest).strip()
                cut = len(remain)
        lines.append(line)
        remain = remain[cut:].strip()
    return lines


def _wrap_long_text(text: str, chars_per_line: int = 24) -> list[str]:
    """긴 텍스트를 여러 줄로 분할 (구두점에서 끊기)"""
    if len(text) <= chars_per_line:
        return [text]
    lines = []
    remain = text
    while remain and len(lines) < 3:
        if len(remain) <= chars_per_line:
            lines.append(remain)
            break
        cut = chars_per_line
        for i in range(min(chars_per_line, len(remain) - 1), 0, -1):
            if remain[i] in ".,!?。、":
                cut = i + 1
                break
        lines.append(remain[:cut])
        remain = remain[cut:].strip()
    return lines


def _wrap_text_to_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width_px: int,
    max_lines: int = 8,
) -> list[str]:
    """화면을 넘지 않게 폰트 기준 너비로 줄바꿈, 단어가 잘리지 않게 (공백/구두점에서 끊기)"""
    if not text or max_width_px <= 0:
        return [text] if text else []
    lines = []
    remain = text.strip()
    while remain and len(lines) < max_lines:
        b = draw.textbbox((0, 0), remain, font=font)
        if b[2] - b[0] <= max_width_px:
            lines.append(remain)
            break
        # 이진 탐색로 맞는 길이 찾기 (단어 끊기 방지)
        low, high = 1, min(len(remain), 50)
        best = 1
        while low <= high:
            mid = (low + high) // 2
            chunk = remain[:mid]
            bb = draw.textbbox((0, 0), chunk, font=font)
            if bb[2] - bb[0] <= max_width_px:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        # 끊을 위치: 공백/쉼표/마침표 쪽으로
        cut = best
        for i in range(min(best, len(remain) - 1), 0, -1):
            if remain[i] in " \t,，.。!?、":
                cut = i + 1
                break
        if cut <= 0:
            cut = best
        lines.append(remain[:cut].strip())
        remain = remain[cut:].strip()
    return lines


def _create_text_screen(
    text: str,
    subtext: str | None,
    bg_color: str = "#1a0a2e",
    font_size: int = 72,
    bg_image: Image.Image | None = None,
    max_width_px: int | None = None,
    theme_name: str | None = None,
    theme_color: str = "#39FF14",
    line_spacing_override: int | None = None,
) -> Image.Image:
    """텍스트 화면 이미지 생성. theme_name 지정 시 해당 부분만 theme_color로 표시."""
    if bg_image is not None:
        img = bg_image.copy()
    else:
        img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=_hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    subfont = _get_font(48)
    safe_width = max_width_px or (config.VIDEO_WIDTH - 120)
    paragraphs = text.split("\n") if text else []
    lines = []
    for para in paragraphs:
        if not para.strip():
            continue
        if theme_name and (f"주제는 {theme_name} 입니다" in para or (para.strip().endswith(" 입니다.") and theme_name in para)):
            lines.append(para.strip())
        elif theme_name and "지금 이 시간의 주제는" in para and "입니다" not in para:
            lines.append(para.strip())
        else:
            wrapped = _wrap_by_chars(para.strip(), chars_per_line=16, max_lines=12)
            for w in wrapped:
                bb = draw.textbbox((0, 0), w, font=font)
                if bb[2] - bb[0] > safe_width and len(w) > 6:
                    lines.extend(_wrap_text_to_fit(draw, w, font, safe_width, max_lines=2))
                else:
                    lines.append(w)
    if not lines and text:
        lines = [text]
    line_spacing = line_spacing_override if line_spacing_override is not None else 22
    total_h = 0
    for line in lines:
        b = draw.textbbox((0, 0), line, font=font)
        total_h += (b[3] - b[1]) + line_spacing
    total_h -= line_spacing
    y_max = config.VIDEO_HEIGHT - total_h - 150
    y_start = max(60, min((config.VIDEO_HEIGHT - total_h) // 2 - 30, y_max))
    theme_rgb = _hex_to_rgb(theme_color) if theme_name else None
    for i, line in enumerate(lines):
        b = draw.textbbox((0, 0), line, font=font)
        th = b[3] - b[1]
        if theme_rgb and theme_name and theme_name in line:
            before, _, after = line.partition(theme_name)
            x_cur = (config.VIDEO_WIDTH - (b[2] - b[0])) // 2
            for part, fill in [(before, (255, 255, 255)), (theme_name, theme_rgb), (after, (255, 255, 255))]:
                if part:
                    try:
                        draw.text((x_cur, y_start), part, font=font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0))
                    except TypeError:
                        draw.text((x_cur + 2, y_start + 2), part, font=font, fill=(0, 0, 0))
                        draw.text((x_cur, y_start), part, font=font, fill=fill)
                    pb = draw.textbbox((0, 0), part, font=font)
                    x_cur += pb[2] - pb[0]
        else:
            x = (config.VIDEO_WIDTH - (b[2] - b[0])) // 2
            try:
                draw.text((x, y_start), line, font=font, fill="white", stroke_width=2, stroke_fill=(0, 0, 0))
            except TypeError:
                draw.text((x + 2, y_start + 2), line, font=font, fill=(0, 0, 0))
                draw.text((x, y_start), line, font=font, fill="white")
        y_start += th + line_spacing
    if subtext:
        sub_lines = _wrap_text_to_fit(draw, subtext, subfont, safe_width, max_lines=2)
        for sl in sub_lines:
            sb = draw.textbbox((0, 0), sl, font=subfont)
            sw = sb[2] - sb[0]
            try:
                draw.text(((config.VIDEO_WIDTH - sw) // 2, y_start + 20), sl, font=subfont, fill="white", stroke_width=2, stroke_fill=(0, 0, 0))
            except TypeError:
                draw.text(((config.VIDEO_WIDTH - sw) // 2 + 2, y_start + 22), sl, font=subfont, fill=(0, 0, 0))
                draw.text(((config.VIDEO_WIDTH - sw) // 2, y_start + 20), sl, font=subfont, fill="white")
            y_start += sb[3] - sb[1] + 12
    return img


def _create_empathy_ment_screen(
    text: str,
    bg_image: Image.Image | None = None,
    font_size: int = 82,
    chars_per_line: int = 9,
    line_spacing: int = 40,
) -> Image.Image:
    """
    감성형 타로 공감 멘트 화면. 글자 크게, 7~10자/줄, 단어 끊김 방지, 핵심 단어 강조.
    어두운 배경에서 잘 보이는 금색(#FFD700)으로 핵심 단어 강조.
    """
    HIGHLIGHT_RGB = (255, 215, 0)  # 금색 #FFD700 (어두운 배경에서 선명)
    NORMAL_RGB = (255, 255, 255)

    if bg_image is not None:
        img = bg_image.copy()
    else:
        img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=(26, 10, 46))
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    keywords = _get_empathy_highlight_keywords()

    # 7~10자/줄, 단어 끊기지 않게 줄바꿈
    wrapped = _wrap_by_chars(text.strip(), chars_per_line=chars_per_line, max_lines=14)
    lines = []
    for w in wrapped:
        lines.append(w.strip())
    if not lines and text:
        lines = [text.strip()]

    # 총 높이 계산
    line_sp = line_spacing
    total_h = 0
    line_heights = []
    for line in lines:
        b = draw.textbbox((0, 0), line, font=font)
        h = b[3] - b[1]
        line_heights.append(h)
        total_h += h + line_sp
    total_h -= line_sp

    y_start = max(80, (config.VIDEO_HEIGHT - total_h) // 2 - 40)

    for i, line in enumerate(lines):
        segments = _split_line_with_highlights(line, keywords)
        if not segments:
            segments = [(line, False)]

        # 전체 줄 너비 (중앙 정렬용)
        bl = draw.textbbox((0, 0), line, font=font)
        full_w = bl[2] - bl[0]
        x_cur = (config.VIDEO_WIDTH - full_w) // 2
        th = line_heights[i] if i < len(line_heights) else draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]

        for seg_text, is_highlight in segments:
            if not seg_text:
                continue
            fill = HIGHLIGHT_RGB if is_highlight else NORMAL_RGB
            try:
                draw.text((x_cur, y_start), seg_text, font=font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0))
            except TypeError:
                draw.text((x_cur + 2, y_start + 2), seg_text, font=font, fill=(0, 0, 0))
                draw.text((x_cur, y_start), seg_text, font=font, fill=fill)
            b = draw.textbbox((0, 0), seg_text, font=font)
            x_cur += b[2] - b[0]

        y_start += th + line_sp

    return img


def _create_closing_frame(
    bg_image: Image.Image,
    comment_blink_highlight: bool,
    font_size: int = 82,
    line_spacing: int = 44,
) -> Image.Image:
    """마지막 인사 화면. comment_blink_highlight True면 '댓글' 부분을 강조색으로 (깜빡임용). 첫 시작 멘트와 글자 크기 맞춤."""
    img = bg_image.copy()
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    subfont = _get_font(72)  # 구독 문구도 비슷한 크기
    w_center = config.VIDEO_WIDTH // 2
    # 줄 순서: 당신이 고른~ / 댓글로 남겨주세요 / 오늘도~ / 다음 영상~ / 구독과~
    lines_main = [
        "당신이 고른 카드는",
        "몇번인가요?",
        "댓글로 남겨주세요",
        "오늘도 좋은 하루 되세요.",
        "다음 영상에서 만나요",
    ]
    sub_line = "구독과 좋아요 부탁드려요"
    comment_highlight_rgb = (255, 255, 0)
    normal_rgb = (255, 255, 255)
    stroke_w = 2
    stroke_fill = (0, 0, 0)

    total_h = 0
    line_heights = []
    for line in lines_main:
        b = draw.textbbox((0, 0), line, font=font)
        line_heights.append(b[3] - b[1])
        total_h += line_heights[-1] + line_spacing
    sb = draw.textbbox((0, 0), sub_line, font=subfont)
    total_h += sb[3] - sb[1] + 20
    total_h -= line_spacing
    y_start = max(80, (config.VIDEO_HEIGHT - total_h) // 2 - 20)

    def draw_centered_text(x_center: int, y: int, text: str, f, fill_color, stroke_width=stroke_w, stroke_f=stroke_fill):
        b = draw.textbbox((0, 0), text, font=f)
        x = x_center - (b[2] - b[0]) // 2
        try:
            draw.text((x, y), text, font=f, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_f)
        except TypeError:
            draw.text((x + 2, y + 2), text, font=f, fill=(0, 0, 0))
            draw.text((x, y), text, font=f, fill=fill_color)
        return b[3] - b[1]

    for i, line in enumerate(lines_main):
        if line == "댓글로 남겨주세요":
            part1, part2 = "댓글", "로 남겨주세요"
            fill_mid = comment_highlight_rgb if comment_blink_highlight else normal_rgb
            b1 = draw.textbbox((0, 0), part1, font=font)
            b2 = draw.textbbox((0, 0), part2, font=font)
            total_w = b1[2] - b1[0] + (b2[2] - b2[0])
            x_cur = w_center - total_w // 2
            for part, fill in [(part1, fill_mid), (part2, normal_rgb)]:
                if part:
                    try:
                        draw.text((x_cur, y_start), part, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)
                    except TypeError:
                        draw.text((x_cur + 2, y_start + 2), part, font=font, fill=(0, 0, 0))
                        draw.text((x_cur, y_start), part, font=font, fill=fill)
                    pb = draw.textbbox((0, 0), part, font=font)
                    x_cur += pb[2] - pb[0]
            th = line_heights[i]
        else:
            th = draw_centered_text(w_center, y_start, line, font, normal_rgb)
        y_start += th + line_spacing

    draw_centered_text(w_center, y_start + 20, sub_line, subfont, normal_rgb)
    return img


def _get_background_image(background_path: str | None) -> Image.Image:
    """배경 이미지 반환 (경로 있으면 로드, 없으면 단색)"""
    if background_path and os.path.exists(background_path):
        return Image.open(background_path).convert("RGB").resize(
            (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), Image.Resampling.LANCZOS
        )
    return Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=(26, 10, 46))


def _add_sparkle_overlay(img: Image.Image, t: float, seed: int = 42) -> Image.Image:
    """
    은은한 반짝임 효과. t 0~1. 강도 확대하여 눈에 띄게.
    """
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    n_dots = 20
    positions = [(rng.randint(50, w - 50), rng.randint(70, h - 70)) for _ in range(n_dots)]
    pulse = 0.22 + 0.18 * math.sin(2 * math.pi * t * 1.5)
    pulse = max(0.15, min(0.42, pulse))
    for px, py in positions:
        radius = rng.randint(2, 4)
        draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=(255, 255, 220))
    transparent = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_soft = Image.blend(transparent, overlay, alpha=pulse)
    base_rgba = img.convert("RGBA")
    out = Image.alpha_composite(base_rgba, overlay_soft)
    return out.convert("RGB")


def _load_card_back(deck_path: Path, size: tuple[int, int]) -> Image.Image:
    """카드 뒷면 이미지 로드 (assets/card_backs에 있으면 랜덤 선택, 없으면 덱 기본)"""
    backs = list(config.CARD_BACKS_DIR.glob("*.png")) + list(config.CARD_BACKS_DIR.glob("*.jpg")) + list(config.CARD_BACKS_DIR.glob("*.jpeg"))
    if backs:
        back_path = Path(str(random.choice(backs)))
    else:
        back_path = deck_path / "back.png" if deck_path else None
    if back_path and back_path.exists():
        return Image.open(back_path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    return Image.new("RGB", size, color=(60, 40, 80))


def _load_card_image(deck_path: Path, card_index: int, size: tuple[int, int]) -> np.ndarray | None:
    """카드 이미지 로드 및 리사이즈"""
    path = get_card_path(deck_path, card_index)
    if not path or not path.exists():
        return None
    img = Image.open(path).convert("RGB")
    img = img.resize(size, Image.Resampling.LANCZOS)
    return np.array(img)


def _create_9cards_layout(
    deck_path: Path,
    card_indices: list[int],
    card_size: tuple[int, int] | None = None,
    gap: int = 28,
    bg_image: Image.Image | None = None,
) -> Image.Image:
    """N장 카드 그리드 레이아웃 (3장=3x1, 6장=3x2, 9장=3x3). 테두리 안쪽 82%."""
    n = len(card_indices)
    cols, rows = (3, 1) if n == 3 else ((GRID_COLS, GRID_ROWS) if n == NUM_CARDS else (3, 3))
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    if card_size is None:
        cw = (grid_w - (cols - 1) * gap) // cols
        ch = (grid_h - (rows - 1) * gap) // rows
    else:
        cw, ch = card_size
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")
    card_size_tuple = (cw, ch)
    for i, idx in enumerate(card_indices):
        arr = _load_card_image(deck_path, idx, card_size_tuple)
        if arr is None:
            card_img = Image.new("RGB", card_size_tuple, color=(80, 60, 100))
        else:
            card_img = Image.fromarray(arr)
        col, row = i % cols, i // cols
        x = offset_x + col * (cw + gap)
        y = offset_y + row * (ch + gap)
        base.paste(card_img, (x, y))
    return base


def _create_9cards_with_center_text(
    deck_path: Path,
    card_indices: list[int],
    center_text: str,
    show_text: bool,
    bg_image: Image.Image | None = None,
) -> Image.Image:
    """9장 카드 레이아웃 + 가운데 텍스트 (show_text=True일 때만 표시, 검정+흰 외곽선)"""
    base = _create_9cards_layout(deck_path, card_indices, bg_image=bg_image)
    if not show_text:
        return base
    draw = ImageDraw.Draw(base)
    font = _get_font(72)
    b = draw.textbbox((0, 0), center_text, font=font)
    tw, th = b[2] - b[0], b[3] - b[1]
    cx = (config.VIDEO_WIDTH - tw) // 2
    cy = (config.VIDEO_HEIGHT - th) // 2
    try:
        draw.text((cx, cy), center_text, font=font, fill=(0, 0, 0), stroke_width=3, stroke_fill=(255, 255, 255))
    except TypeError:
        draw.text((cx + 2, cy + 2), center_text, font=font, fill=(255, 255, 255))
        draw.text((cx, cy), center_text, font=font, fill=(0, 0, 0))
    return base


def _create_9cards_with_numbers(
    deck_path: Path,
    card_indices: list[int],
    card_size: tuple[int, int] | None = None,
    gap: int = 28,
    bg_image: Image.Image | None = None,
    num_font_size: int = 48,
) -> Image.Image:
    """N장 카드 + 1~N 번호 (선택용). 3장=가로배치(높이 축소)+브랜딩, 6장=3x2, 9장=3x3."""
    n = len(card_indices)
    cols, rows = (3, 1) if n == 3 else ((GRID_COLS, GRID_ROWS) if n == NUM_CARDS else (3, 3))
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)

    # 3장일 때: 카드 높이를 비율에 맞게 축소 (위아래 15%씩)
    if n == 3 and card_size is None:
        cw = (grid_w - (cols - 1) * gap) // cols
        ch_base = (grid_h - (rows - 1) * gap) // rows
        ch = int(ch_base * 0.7)  # 위아래 15%씩 높이 축소
        card_size = (cw, ch)

    base = _create_9cards_layout(deck_path, card_indices, card_size, gap, bg_image)
    draw = ImageDraw.Draw(base)

    cw = (grid_w - (cols - 1) * gap) // cols if card_size is None else card_size[0]
    ch = (grid_h - (rows - 1) * gap) // rows if card_size is None else card_size[1]
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2
    circle_size = 80
    num_font = _get_font(num_font_size)
    badge_margin = 18

    for i in range(n):
        col, row = i % cols, i // cols
        card_x = offset_x + col * (cw + gap)
        card_y = offset_y + row * (ch + gap)
        cx = card_x + (cw - circle_size) // 2
        cy = card_y + badge_margin
        draw.ellipse([cx, cy, cx + circle_size, cy + circle_size], fill="#2c1810", outline="#DAA520", width=4)
        num_str = str(i + 1)
        b = draw.textbbox((0, 0), num_str, font=num_font)
        tw, th = b[2] - b[0], b[3] - b[1]
        tx = cx + (circle_size - tw) // 2
        ty = cy + (circle_size - th) // 2 - 2
        try:
            draw.text((tx, ty), num_str, font=num_font, fill="white", stroke_width=3, stroke_fill="black")
        except TypeError:
            draw.text((tx + 1, ty + 1), num_str, font=num_font, fill="black")
            draw.text((tx, ty), num_str, font=num_font, fill="white")
    return base


def _create_9cards_facedown_with_numbers(
    deck_path: Path,
    gap: int = 28,
    bg_image: Image.Image | None = None,
    pick_message: str = "여기에서 카드를\n한장 선택하세요!",
    card_back: Image.Image | None = None,
    n_cards: int | None = None,
    msg_font_size: int | None = None,
) -> Image.Image:
    """N장 카드 뒷면 + 1~N 번호 + 선택 안내. n_cards 없으면 config.NUM_CARDS(6)."""
    nc = n_cards or NUM_CARDS
    cols, rows = (3, 1) if nc == 3 else ((GRID_COLS, GRID_ROWS) if nc == 6 else (3, 3))
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    cw = (grid_w - (cols - 1) * gap) // cols
    ch = (grid_h - (rows - 1) * gap) // rows
    if nc == 3:
        ch = int(ch * 0.7)  # 3장: 위아래 15%씩 높이 축소
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    if card_back is None:
        card_back = _load_card_back(deck_path, (cw, ch))
    elif card_back.size != (cw, ch):
        card_back = card_back.resize((cw, ch), Image.Resampling.LANCZOS)
    circle_size = 76
    num_font = _get_font(48)
    badge_margin = 20
    n = n_cards or NUM_CARDS

    for i in range(n):
        col, row = i % cols, i // cols
        card_x = offset_x + col * (cw + gap)
        card_y = offset_y + row * (ch + gap)
        base.paste(card_back, (card_x, card_y))
        draw = ImageDraw.Draw(base)
        cx = card_x + (cw - circle_size) // 2
        cy = card_y + badge_margin
        draw.ellipse([cx, cy, cx + circle_size, cy + circle_size], fill="#8B4513", outline="#DAA520", width=3)
        b = draw.textbbox((0, 0), str(i + 1), font=num_font)
        tw, th = b[2] - b[0], b[3] - b[1]
        tx = cx + (circle_size - tw) // 2
        ty = cy + (circle_size - th) // 2 - 2
        draw.text((tx, ty), str(i + 1), font=num_font, fill="white")

    # 선택 안내 문구: 3장=화면 중앙, 6장=상단(카드 숫자와 겹치지 않도록)
    draw = ImageDraw.Draw(base)
    msg_font = _get_font(msg_font_size or 88)
    msg_lines = pick_message.split("\n")
    total_h = 0
    line_heights = []
    for line in msg_lines:
        mb = draw.textbbox((0, 0), line, font=msg_font)
        line_heights.append(mb[3] - mb[1])
        total_h += line_heights[-1] + 12
    total_h -= 12
    if nc == 3:
        cy = max(80, (config.VIDEO_HEIGHT - total_h) // 2)  # 3장: 화면 중앙으로
    else:
        cy = int(config.VIDEO_HEIGHT * 0.26)  # 6장: 상단 (카드 숫자와 겹치지 않도록)
    for i, line in enumerate(msg_lines):
        mb = draw.textbbox((0, 0), line, font=msg_font)
        mw = mb[2] - mb[0]
        cx = (config.VIDEO_WIDTH - mw) // 2
        draw.text((cx + 3, cy + 3), line, font=msg_font, fill=(0, 0, 0))
        draw.text((cx, cy), line, font=msg_font, fill="white")
        cy += line_heights[i] + 12
    return base


def _create_3cards_facedown(
    deck_path: Path,
    bg_image: Image.Image | None = None,
    pick_message: str = "1, 2, 3 중 하나를 선택하세요",
    card_back: Image.Image | None = None,
) -> Image.Image:
    """바이럴 숏츠용: 3장 카드 뒷면 가로 배치 + 번호 + 선택 안내."""
    cols = 3
    gap = 40
    card_w = int((config.VIDEO_WIDTH - 120 - (cols - 1) * gap) / cols)
    card_h = int(card_w * 1.4)
    total_w = cols * card_w + (cols - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = int(config.VIDEO_HEIGHT * 0.35)

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    if card_back is None:
        card_back = _load_card_back(deck_path, (card_w, card_h))
    elif card_back.size != (card_w, card_h):
        card_back = card_back.resize((card_w, card_h), Image.Resampling.LANCZOS)

    circle_size = 56
    num_font = _get_font(42)
    draw = ImageDraw.Draw(base)
    for i in range(3):
        card_x = offset_x + i * (card_w + gap)
        card_y = offset_y
        base.paste(card_back, (card_x, card_y))
        cx = card_x + (card_w - circle_size) // 2
        cy = card_y + 16
        draw.ellipse([cx, cy, cx + circle_size, cy + circle_size], fill="#8B4513", outline="#DAA520", width=2)
        b = draw.textbbox((0, 0), str(i + 1), font=num_font)
        tw, th = b[2] - b[0], b[3] - b[1]
        tx = cx + (circle_size - tw) // 2
        ty = cy + (circle_size - th) // 2 - 2
        draw.text((tx, ty), str(i + 1), font=num_font, fill="white")

    msg_font = _get_font(58)
    mb = draw.textbbox((0, 0), pick_message, font=msg_font)
    mw = mb[2] - mb[0]
    mx = (config.VIDEO_WIDTH - mw) // 2
    my = offset_y + card_h + 50
    _draw_text_with_stroke(draw, (mx, my), pick_message, msg_font, (255, 255, 255))
    return base


def _create_card_flip_front_to_back_frame(
    deck_path: Path,
    card_indices: list[int],
    progress: float,
    center_text: str | None = None,
    show_center_text: bool = True,
    bg_image: Image.Image | None = None,
    card_back: Image.Image | None = None,
) -> Image.Image:
    """
    N장 카드 앞→뒤 한 번에 뒤집기. progress 0=앞면, 1=뒷면. (3장=3x1, 6장=3x2)
    """
    n_c = len(card_indices)
    cols, rows = (3, 1) if n_c == 3 else (GRID_COLS, GRID_ROWS)
    gap = 28
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    cw = (grid_w - (cols - 1) * gap) // cols
    ch = (grid_h - (rows - 1) * gap) // rows
    if n_c == 3:
        ch = int(ch * 0.7)  # 3장: 위아래 15%씩 높이 축소
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    if card_back is None:
        card_back = _load_card_back(deck_path, (cw, ch))
    elif card_back.size != (cw, ch):
        card_back = card_back.resize((cw, ch), Image.Resampling.LANCZOS)

    p = _ease_in_out(progress)
    n_cards = len(card_indices)
    for i in range(n_cards):
        if p < 0.5:
            scale_x = 1.0 - 2 * p
            show_front = True
        else:
            scale_x = 2 * (p - 0.5)
            show_front = False

        col, row = i % cols, i // cols
        card_x = offset_x + col * (cw + gap)
        card_y = offset_y + row * (ch + gap)

        if scale_x < 0.05:
            continue
        nw = max(2, int(cw * scale_x))
        if show_front:
            arr = _load_card_image(deck_path, card_indices[i], (cw, ch))
            card_img = Image.fromarray(arr) if arr is not None else Image.new("RGB", (cw, ch), (80, 60, 100))
        else:
            card_img = card_back.copy()
        squished = card_img.resize((nw, ch), Image.Resampling.LANCZOS)
        px = card_x + (cw - nw) // 2
        base.paste(squished, (px, card_y))

    if show_center_text and center_text:
        draw = ImageDraw.Draw(base)
        font = _get_font(72)
        b = draw.textbbox((0, 0), center_text, font=font)
        tw, th = b[2] - b[0], b[3] - b[1]
        cx = (config.VIDEO_WIDTH - tw) // 2
        cy = (config.VIDEO_HEIGHT - th) // 2
        try:
            draw.text((cx, cy), center_text, font=font, fill=(0, 0, 0), stroke_width=3, stroke_fill=(255, 255, 255))
        except TypeError:
            draw.text((cx + 2, cy + 2), center_text, font=font, fill=(255, 255, 255))
            draw.text((cx, cy), center_text, font=font, fill=(0, 0, 0))
    return base


def _create_card_flip_frame(
    deck_path: Path,
    card_indices: list[int],
    progress: float,
    bg_image: Image.Image | None = None,
    card_back: Image.Image | None = None,
) -> Image.Image:
    """
    카드 뒤집기 애니메이션 한 프레임. N장 순차 뒤→앞. (3장=3x1, 6장=3x2)
    """
    n_c = len(card_indices)
    cols, rows = (3, 1) if n_c == 3 else (GRID_COLS, GRID_ROWS)
    gap = 28
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    cw = (grid_w - (cols - 1) * gap) // cols
    ch = (grid_h - (rows - 1) * gap) // rows
    if n_c == 3:
        ch = int(ch * 0.7)  # 3장: 위아래 15%씩 높이 축소
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    if card_back is None:
        card_back = _load_card_back(deck_path, (cw, ch))
    elif card_back.size != (cw, ch):
        card_back = card_back.resize((cw, ch), Image.Resampling.LANCZOS)

    for i in range(n_c):
        stagger, span = 0.08, 0.55
        p = (progress - i * stagger) / span
        p = max(0, min(1, p))
        if p < 0.5:
            scale_x = 1.0 - 2 * p
            show_front = False
        else:
            scale_x = 2 * (p - 0.5)
            show_front = True

        col, row = i % cols, i // cols
        card_x = offset_x + col * (cw + gap)
        card_y = offset_y + row * (ch + gap)

        if scale_x < 0.05:
            continue
        nw = max(2, int(cw * scale_x))
        if show_front:
            arr = _load_card_image(deck_path, card_indices[i], (cw, ch))
            card_img = Image.fromarray(arr) if arr is not None else Image.new("RGB", (cw, ch), (80, 60, 100))
        else:
            card_img = card_back.copy()
        squished = card_img.resize((nw, ch), Image.Resampling.LANCZOS)
        px = card_x + (cw - nw) // 2
        base.paste(squished, (px, card_y))

    return base


def _wrap_text(text: str, chars_per_line: int = 20, max_lines: int = 6) -> list[str]:
    """긴 텍스트를 여러 줄로 분할 (한글 기준)"""
    lines = []
    remain = (text or "").strip()
    while remain and len(lines) < max_lines:
        if len(remain) <= chars_per_line:
            lines.append(remain)
            break
        lines.append(remain[:chars_per_line])
        remain = remain[chars_per_line:]
    return lines


def _draw_text_with_stroke(draw, xy, text, font, fill, stroke_w=2):
    try:
        draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=(0, 0, 0))
    except TypeError:
        draw.text((xy[0] + 1, xy[1] + 1), text, font=font, fill=(0, 0, 0))
        draw.text(xy, text, font=font, fill=fill)


def _create_3cards_with_meanings(
    deck_path: Path,
    card_indices: list[int],
    meanings: list[str],
    number_offset: int = 0,
    bg_image: Image.Image | None = None,
) -> Image.Image:
    """3장 카드. 형식: 이 카드는 / [카드명]입니다. / 의미는 / [의미]입니다. []안은 금색(#FFD700), 얇은 검정 외곽선."""
    GOLD = (255, 215, 0)  # #FFD700

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    card_w = 225  # 테두리 안쪽 배치
    gap_between_cards = 6  # 카드 간격 더 축소
    margin_top, margin_bottom = 100, 100  # 여백 축소 → 카드에 더 많은 공간 (너무 작아 보이는 것 완화)
    section_h = (config.VIDEO_HEIGHT - margin_top - margin_bottom) // 3
    raw_h = section_h - gap_between_cards
    card_h = int(raw_h * card_w / 280 * 1.15)  # 비율 유지 + 15% 높이 보정 (너무 작음 완화)
    card_x = 90
    text_x = card_x + card_w + 20
    num_font = _get_font(65)   # 5pt 추가
    label_font = _get_font(49)
    value_font = _get_font(47)
    detail_font = _get_font(43)
    card_size = (card_w, card_h)

    draw = ImageDraw.Draw(base)
    for i, idx in enumerate(card_indices):
        info = get_card_info(idx)
        name, short = info["name"], info["meaning"]
        if len(short) > 18:
            short = short[:18] + "…"

        row_y = margin_top + i * section_h + (section_h - card_h) // 2
        text_y = row_y

        arr = _load_card_image(deck_path, idx, card_size)
        if arr is not None:
            card_img = Image.fromarray(arr)
            base.paste(card_img, (card_x, row_y))

        # 번호
        _draw_text_with_stroke(draw, (card_x + 10, row_y + 10), str(number_offset + i + 1), num_font, "white")

        # 이 카드는 / [카드명]입니다. / 의미는 / [의미]입니다. (줄바꿈 최소화, []안 금색)
        lines = [
            ("이 카드는", (255, 255, 255)),
            (f"{name}입니다.", GOLD),
            ("의미는", (255, 255, 255)),
            (f"{short}입니다.", GOLD),
        ]
        for txt, color in lines:
            _draw_text_with_stroke(draw, (text_x, text_y), txt, value_font if color == GOLD else label_font, color)
            b = draw.textbbox((0, 0), txt, font=value_font if color == GOLD else label_font)
            text_y += b[3] - b[1] + 8

        # 카드 의미와 한 줄 띄우고 독립적으로 표시
        text_y += 24
        detail_lines = ["이 카드에 자세한 설명은", "더보기에 적어 두었습니다"]
        for dl in detail_lines:
            _draw_text_with_stroke(draw, (text_x, text_y), dl, detail_font, (255, 255, 255), stroke_w=2)
            b = draw.textbbox((0, 0), dl, font=detail_font)
            text_y += b[3] - b[1] + 4
    return base


def _create_segment_transition_frame(
    deck_path: Path,
    cards_out: list[int],
    cards_in: list[int],
    meanings_out: list[str],
    meanings_in: list[str],
    number_offset_out: int,
    number_offset_in: int,
    progress: float,
    bg_image: Image.Image | None = None,
    card_back: Image.Image | None = None,
) -> Image.Image:
    """
    구간 전환 프레임: 카드 앞→뒤 회전, 다음 카드 뒤→앞 회전.
    텍스트: 기존은 좌측으로 연기처럼 사라지고, 새 텍스트는 우측에서 연기처럼 등장.
    progress 0~1.
    """
    GOLD = (255, 215, 0)
    card_w = 225
    gap_between_cards = 6
    margin_top, margin_bottom = 120, 120
    section_h = (config.VIDEO_HEIGHT - margin_top - margin_bottom) // 3
    raw_h = section_h - gap_between_cards
    card_h = int(raw_h * card_w / 280)
    card_x = 90
    text_x = card_x + card_w + 20
    num_font = _get_font(65)
    label_font = _get_font(49)
    value_font = _get_font(47)
    detail_font = _get_font(43)
    card_size = (card_w, card_h)

    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    if card_back is None:
        card_back = _load_card_back(deck_path, card_size)
    elif card_back.size != card_size:
        card_back = card_back.resize(card_size, Image.Resampling.LANCZOS)

    p = _ease_in_out(progress)

    # phase: 0~0.45 flip out, 0.45~0.55 card backs, 0.55~1 flip in
    flip_out_phase = p < 0.45
    flip_in_phase = p > 0.55
    mid_phase = 0.45 <= p <= 0.55

    # 카드 플립
    for i in range(3):
        row_y = margin_top + i * section_h + (section_h - card_h) // 2

        if flip_out_phase:
            scale = 1.0 - (p / 0.45)
            arr = _load_card_image(deck_path, cards_out[i], card_size)
            card_img = Image.fromarray(arr) if arr is not None else Image.new("RGB", card_size, (80, 60, 100))
        elif flip_in_phase:
            scale = (p - 0.55) / 0.45
            arr = _load_card_image(deck_path, cards_in[i], card_size)
            card_img = Image.fromarray(arr) if arr is not None else Image.new("RGB", card_size, (80, 60, 100))
        else:
            scale = 1.0
            card_img = card_back.copy()

        if scale < 0.02:
            continue
        nw = max(2, int(card_w * scale))
        squished = card_img.resize((nw, card_h), Image.Resampling.LANCZOS)
        px = card_x + (card_w - nw) // 2
        base.paste(squished, (px, row_y))

        # 번호 (flip out일 때 cards_out 번호, flip in일 때 cards_in 번호)
        if flip_out_phase or mid_phase:
            num = str(number_offset_out + i + 1)
        else:
            num = str(number_offset_in + i + 1)
        draw = ImageDraw.Draw(base)
        _draw_text_with_stroke(draw, (card_x + 10, row_y + 10), num, num_font, "white")

    # 텍스트: 기존(0~0.4) 좌측으로 연기 사라짐, 새 텍스트(0.6~1) 우측에서 연기 등장
    draw = ImageDraw.Draw(base)
    slide_dist = 450
    bg_color = (26, 10, 46)

    def draw_card_text(cards, meanings, num_off, base_text_x: int, slide_offset: int, alpha: float):
        for i, idx in enumerate(cards):
            info = get_card_info(idx)
            name, short = info["name"], info["meaning"]
            if len(short) > 18:
                short = short[:18] + "…"
            row_y = margin_top + i * section_h + (section_h - card_h) // 2
            tx = base_text_x + slide_offset
            ty = row_y
            # alpha에 따라 색상 보간 (연기 효과)
            r = int(255 * alpha + bg_color[0] * (1 - alpha))
            g = int(255 * alpha + bg_color[1] * (1 - alpha))
            b = int(255 * alpha + bg_color[2] * (1 - alpha))
            white_fade = (r, g, b)
            gold_r = int(255 * alpha + bg_color[0] * (1 - alpha))
            gold_g = int(215 * alpha + bg_color[1] * (1 - alpha))
            gold_b = int(0 * alpha + bg_color[2] * (1 - alpha))
            gold_fade = (min(255, gold_r), min(255, gold_g), min(255, gold_b))
            lines = [
                ("이 카드는", white_fade),
                (f"{name}입니다.", gold_fade),
                ("의미는", white_fade),
                (f"{short}입니다.", gold_fade),
            ]
            for txt, color in lines:
                _draw_text_with_stroke(draw, (tx, ty), txt, value_font if color == gold_fade else label_font, color)
                bb = draw.textbbox((0, 0), txt, font=value_font if color == gold_fade else label_font)
                ty += bb[3] - bb[1] + 8
            ty += 24
            for dl in ["이 카드에 자세한 설명은", "더보기에 적어 두었습니다"]:
                _draw_text_with_stroke(draw, (tx, ty), dl, detail_font, white_fade, stroke_w=2)
                bb = draw.textbbox((0, 0), dl, font=detail_font)
                ty += bb[3] - bb[1] + 4

    # 기존 텍스트: 0~0.4 구간에서 좌측으로 이동 + 페이드
    if p < 0.5:
        out_alpha = 1.0 - (p / 0.4) if p < 0.4 else 0
        out_offset = int(-slide_dist * (p / 0.4)) if p < 0.4 else -slide_dist
        if out_alpha > 0.02:
            draw_card_text(cards_out, meanings_out, number_offset_out, text_x, out_offset, out_alpha)

    # 새 텍스트: 0.6~1 구간에서 우측에서 들어오며 페이드인
    if p > 0.5:
        in_t = (p - 0.5) / 0.5
        in_alpha = min(1.0, in_t / 0.4)  # 0.5~0.7에서 페이드인
        in_offset = int(slide_dist * (1 - in_t)) if in_t < 1 else 0
        if in_alpha > 0.02:
            draw_card_text(cards_in, meanings_in, number_offset_in, text_x, in_offset, in_alpha)

    return base


def _create_cards_fly_to_center_frames(
    deck_path: Path,
    duration_sec: float,
    bg_image: Image.Image | None = None,
    card_back: Image.Image | None = None,
    n_cards: int | None = None,
) -> list:
    """그리드 1~N번 카드가 중앙으로 날아가는 프레임. (3장=3x1, 6장=3x2)"""
    nc = n_cards or NUM_CARDS
    cols, rows = (3, 1) if nc == 3 else (GRID_COLS, GRID_ROWS)
    gap = 28
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    cw = (grid_w - (cols - 1) * gap) // cols
    ch = (grid_h - (rows - 1) * gap) // rows
    if nc == 3:
        ch = int(ch * 0.7)  # 3장: 위아래 15%씩 높이 축소
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2

    if card_back is None:
        card_img = _load_card_back(deck_path, (cw, ch))
    elif card_back.size != (cw, ch):
        card_img = card_back.resize((cw, ch), Image.Resampling.LANCZOS)
    else:
        card_img = card_back

    if bg_image is not None:
        base_bg = bg_image.copy()
    else:
        base_bg = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    cx = config.VIDEO_WIDTH // 2 - cw // 2
    cy = config.VIDEO_HEIGHT // 2 - ch // 2
    starts = []
    for i in range(nc):
        col, row = i % cols, i // cols
        sx = offset_x + col * (cw + gap)
        sy = offset_y + row * (ch + gap)
        starts.append((sx, sy))

    n_frames = max(1, int(config.VIDEO_FPS * duration_sec))
    fly_dur_sec = 0.12
    start_offset_sec = 0.12

    frames = []
    for fi in range(n_frames):
        t = fi / config.VIDEO_FPS
        frame = base_bg.copy()
        for i in range(nc):
            start_i = i * start_offset_sec
            if t <= start_i:
                x, y = starts[i]
            elif t >= start_i + fly_dur_sec:
                x, y = cx, cy
            else:
                prog = (t - start_i) / fly_dur_sec
                prog = _ease_out_quad(min(1.0, prog))
                sx, sy = starts[i]
                x = int(sx + (cx - sx) * prog)
                y = int(sy + (cy - sy) * prog)
            frame.paste(card_img, (x, y))
        frames.append(np.array(frame))
    return frames


def _create_shuffle_frame(
    deck_path: Path, style: str, frame_idx: int, n_frames: int, bg_image: Image.Image | None = None,
    card_back: Image.Image | None = None,
    n_cards: int | None = None,
) -> Image.Image:
    """셔플 - N장 카드가 계속 섞임 (3장=3x1, 6장=3x2)"""
    nc = n_cards or NUM_CARDS
    cols, rows = (3, 1) if nc == 3 else (GRID_COLS, GRID_ROWS)
    gap = 28
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    card_w = (grid_w - (cols - 1) * gap) // cols
    card_h = (grid_h - (rows - 1) * gap) // rows
    if nc == 3:
        card_h = int(card_h * 0.7)  # 3장: 위아래 15%씩 높이 축소
    if card_back is None:
        card_img = _load_card_back(deck_path, (card_w, card_h))
    elif card_back.size != (card_w, card_h):
        card_img = card_back.resize((card_w, card_h), Image.Resampling.LANCZOS)
    else:
        card_img = card_back
    if bg_image is not None:
        base = bg_image.copy()
    else:
        base = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    cx, cy = config.VIDEO_WIDTH // 2, config.VIDEO_HEIGHT // 2
    t = frame_idx / 30.0

    def clamp_x(x): return max(0, min(config.VIDEO_WIDTH - card_w, int(x)))
    def clamp_y(y): return max(0, min(config.VIDEO_HEIGHT - card_h, int(y)))

    if style == "chaos_orbit":
        for i in range(nc):
            spd = 90 + (i % 3) * 40 + (i // 3) * 25
            angle = t * spd + i * 42
            r = 120 + 80 * np.sin(t * 2.1 + i * 0.7)
            dx = int(r * np.sin(np.radians(angle)))
            dy = int(-r * 0.6 * np.cos(np.radians(angle)))
            x, y = clamp_x(cx - card_w // 2 + dx), clamp_y(cy - card_h // 2 + dy)
            base.paste(card_img, (x, y))
    elif style == "scatter_swirl":
        for i in range(nc):
            a1, a2 = t * 120 + i * 50, t * 90 - i * 35
            r1 = 100 + 60 * np.sin(t * 1.5 + i)
            r2 = 80 + 50 * np.cos(t * 1.2 + i * 0.8)
            dx = int(r1 * np.sin(np.radians(a1)) + r2 * 0.5 * np.cos(np.radians(a2)))
            dy = int(-r1 * 0.7 * np.cos(np.radians(a1)) + r2 * 0.4 * np.sin(np.radians(a2)))
            x, y = clamp_x(cx - card_w // 2 + dx), clamp_y(cy - card_h // 2 + dy)
            base.paste(card_img, (x, y))
    elif style == "bounce_mix":
        for i in range(nc):
            vx, vy = 180 + (i * 37) % 140, 150 + (i * 29) % 120
            ox = 100 * np.sin(t * 0.9 + i * 0.6)
            oy = 90 * np.cos(t * 1.1 + i * 0.5)
            dx = int(180 * np.sin(np.radians(t * vx)) + ox)
            dy = int(-160 * np.cos(np.radians(t * vy)) + oy)
            x, y = clamp_x(cx - card_w // 2 + dx), clamp_y(cy - card_h // 2 + dy)
            base.paste(card_img, (x, y))
    else:
        for i in range(nc):
            angle = t * (100 + i * 15) + i * 40
            r = 80 + 100 * (0.5 + 0.5 * np.sin(t * 2.5 + i * 0.9))
            dr = 30 * np.sin(t * 3 + i * 1.2)
            dx = int((r + dr) * np.sin(np.radians(angle)))
            dy = int(-(r + dr) * 0.7 * np.cos(np.radians(angle)))
            x, y = clamp_x(cx - card_w // 2 + dx), clamp_y(cy - card_h // 2 + dy)
            base.paste(card_img, (x, y))
    return base


def _ease_out_quad(p: float) -> float:
    """0~1 입력, 끝으로 갈수록 빠르게 도착 (스냅)."""
    return 1.0 - (1.0 - p) ** 2


def _create_cards_fly_to_grid_frames(
    deck_path: Path,
    duration_sec: float,
    bg_image: Image.Image | None = None,
    card_back: Image.Image | None = None,
    n_cards: int | None = None,
) -> list:
    """셔플 후 중앙 카드들이 1~N번 자리로 날아가는 프레임. (3장=3x1, 6장=3x2)"""
    nc = n_cards or NUM_CARDS
    cols, rows = (3, 1) if nc == 3 else (GRID_COLS, GRID_ROWS)
    gap = 28
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    cw = (grid_w - (cols - 1) * gap) // cols
    ch = (grid_h - (rows - 1) * gap) // rows
    if nc == 3:
        ch = int(ch * 0.7)  # 3장: 위아래 15%씩 높이 축소
    total_w = cols * cw + (cols - 1) * gap
    total_h = rows * ch + (rows - 1) * gap
    offset_x = (config.VIDEO_WIDTH - total_w) // 2
    offset_y = (config.VIDEO_HEIGHT - total_h) // 2

    if card_back is None:
        card_img = _load_card_back(deck_path, (cw, ch))
    elif card_back.size != (cw, ch):
        card_img = card_back.resize((cw, ch), Image.Resampling.LANCZOS)
    else:
        card_img = card_back

    if bg_image is not None:
        base_bg = bg_image.copy()
    else:
        base_bg = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color="#1a0a2e")

    cx = config.VIDEO_WIDTH // 2 - cw // 2
    cy = config.VIDEO_HEIGHT // 2 - ch // 2
    targets = []
    for i in range(nc):
        col, row = i % cols, i // cols
        tx = offset_x + col * (cw + gap)
        ty = offset_y + row * (ch + gap)
        targets.append((tx, ty))

    n_frames = max(1, int(config.VIDEO_FPS * duration_sec))
    fly_dur_sec = 0.14
    start_offset_sec = 0.14

    frames = []
    for fi in range(n_frames):
        t = fi / config.VIDEO_FPS
        frame = base_bg.copy()
        for i in range(nc):
            start_i = i * start_offset_sec
            if t <= start_i:
                x, y = cx, cy
            elif t >= start_i + fly_dur_sec:
                x, y = targets[i]
            else:
                prog = (t - start_i) / fly_dur_sec
                prog = _ease_out_quad(min(1.0, prog))
                tx, ty = targets[i]
                x = int(cx + (tx - cx) * prog)
                y = int(cy + (ty - cy) * prog)
            frame.paste(card_img, (x, y))
        frames.append(np.array(frame))
    return frames


def prepend_thumbnail_to_video(
    video_path: str,
    thumbnail_path: str,
    output_path: str | None = None,
    duration_sec: float = 2.5,
) -> str:
    """
    영상 맨 앞에 썸네일 이미지를 duration_sec초 동안 붙인 새 영상을 만듭니다.
    video_path: 원본 영상 경로
    thumbnail_path: 썸네일 이미지 경로 (PNG/JPEG)
    output_path: 출력 경로. None이면 원본과 같은 폴더에 _with_thumb 접미사로 저장
    duration_sec: 썸네일 노출 시간(초)
    Returns: 저장된 새 영상 경로
    """
    from moviepy.video.io.VideoFileClip import VideoFileClip

    video_path = str(Path(video_path).resolve())
    thumbnail_path = str(Path(thumbnail_path).resolve())
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"영상 파일 없음: {video_path}")
    if not os.path.exists(thumbnail_path):
        raise FileNotFoundError(f"썸네일 파일 없음: {thumbnail_path}")

    if output_path is None:
        p = Path(video_path)
        output_path = str(p.parent / f"{p.stem}_with_thumb{p.suffix}")

    main = VideoFileClip(video_path)
    w, h = main.size
    # MoviePy 1.0.3 ImageClip에는 resize 없음 → PIL로 리사이즈 후 ImageClip 생성
    thumb_img = Image.open(thumbnail_path).convert("RGB")
    thumb_resized = thumb_img.resize((w, h), Image.Resampling.LANCZOS)
    thumb_clip = ImageClip(np.array(thumb_resized)).set_duration(duration_sec)
    final = concatenate_videoclips([thumb_clip, main])
    encode_preset = getattr(config, "VIDEO_ENCODE_PRESET", "medium")
    encode_threads = getattr(config, "VIDEO_ENCODE_THREADS", 4) or 4
    final.write_videofile(
        output_path,
        fps=main.fps,
        codec="libx264",
        audio_codec="aac",
        preset=encode_preset,
        threads=encode_threads,
        logger=None,
    )
    thumb_clip.close()
    main.close()
    final.close()
    return output_path


def generate_tarot_video(
    fortune_type: str = "",
    background_path: str | None = None,
    music_path: str | None = None,
    output_path: str = "",
    time_slot_id: str | None = None,
    use_minor_arcana: bool = False,
    minor_fortune_type: str | None = None,
    major_theme: str | None = None,
    hook_duration_sec: float | None = None,
    hook_text_override: str | None = None,
) -> tuple[str, str]:
    """
    타로 운세 Shorts 영상 생성

    Args:
        time_slot_id: 아침(morning)/점심(lunch)/저녁(evening) 지정 시 해당 훅·테마 사용. None이면 랜덤.
        major_theme: 메이저 22장 기반 추가 주제 (직장운/학업운/인간관계운/재회·이별운)
        hook_duration_sec: 훅(첫 화면) 노출 시간(초). None이면 config 기본값 사용.
        hook_text_override: 감성형 타로(4테마) 사용 시 사용자 선택 제목. 지정 시 랜덤 문구 대신 사용.
        background_path: 배경 이미지 (None이면 단색)
        music_path: 배경음악 (None 가능)
        output_path: 출력 경로

    Returns:
        (생성된 영상 경로, 테마명)
    """
    times = config.TAROT_SECTION_TIMES
    shuffle_style = pick_random_shuffle()
    deck_path = get_random_deck_path()

    if use_minor_arcana and minor_fortune_type:
        hook_text, theme_name = pick_minor_fortune_hook(minor_fortune_type)
        slot_id = minor_fortune_type
    elif major_theme:
        if major_theme in theme_phrases_db.THEME_DB_NAMES and hook_text_override:
            hook_text = hook_text_override.strip()
            theme_name = major_theme
        elif major_theme in theme_phrases_db.THEME_DB_NAMES:
            hook_text = theme_phrases_db.get_random_phrase(major_theme) or ""
            theme_name = major_theme
            if not hook_text:
                hook_text, theme_name = pick_major_fortune_hook(major_theme)
        else:
            hook_text, theme_name = pick_major_fortune_hook(major_theme)
        slot_id = major_theme
    elif time_slot_id:
        hook_text, theme_name = pick_hook_for_slot(time_slot_id)
        slot_id = time_slot_id
    else:
        slot_id, hook_text, theme_name = pick_random_hook()

    if not deck_path or not deck_path.exists():
        raise RuntimeError(
            "타로 덱이 없습니다. '타로덱_다운로드.bat'을 실행해 덱을 다운로드하세요."
        )

    num_cards_use = 3 if (hook_text_override and hook_text_override.strip()) else NUM_CARDS
    pool = get_card_pool(slot_id, use_minor_arcana=use_minor_arcana)
    if len(pool) < num_cards_use:
        pool = list(range(22))
    card_indices = random.sample(pool, num_cards_use)
    display_order_10s = random.sample(range(num_cards_use), num_cards_use)
    shuffled_order = random.sample(range(num_cards_use), num_cards_use)
    # GPT로 전문적 동적 해석 생성 (API 키 필요)
    print("  🤖 GPT 타로 해석 생성 중...")
    card_meanings = generate_tarot_interpretations(
        card_indices, theme_name, hook_text_override=hook_text_override
    )

    # 배경: 전달받은 경로 또는 assets/images에서 랜덤
    global _video_font_path
    _video_font_path = config.get_random_font_path()
    bg_path = background_path or config.get_random_background_path()
    bg_img = _get_background_image(bg_path)

    cols, rows = (3, 1) if num_cards_use == 3 else (GRID_COLS, GRID_ROWS)
    gap = 28
    grid_w = int(config.VIDEO_WIDTH * 0.82)
    grid_h = int(config.VIDEO_HEIGHT * 0.82)
    cw = (grid_w - (cols - 1) * gap) // cols
    ch = (grid_h - (rows - 1) * gap) // rows
    if num_cards_use == 3:
        ch = int(ch * 0.7)  # 3장: 위아래 15%씩 높이 축소
    card_back_img = _load_card_back(deck_path, (cw, ch))

    # 클립 리스트
    clips = []
    t = 0.0

    is_empathy = bool(hook_text_override and hook_text_override.strip())

    # 1. 첫 화면: 감성형 타로면 공감 멘트만 (3초, 줄간격 넓게) / 아침 타로운세면 1초 배경
    if is_empathy:
        hook_title_text = hook_text_override.strip()
        hook_title_id = 0
        print("  🤖 공감 멘트 생성 중...")
        empathy_ment = generate_empathy_ment(hook_title_text)
        empathy_sec = 3.5  # 멘트 노출 3.5초
        empathy_frame = _create_empathy_ment_screen(
            empathy_ment,
            bg_image=bg_img,
            font_size=82,       # 글자 크게 (공간 활용)
            chars_per_line=9,   # 7~10자/줄 가독성
            line_spacing=40,    # 줄간격 넓게
        )
        n_empathy = max(1, int(config.VIDEO_FPS * empathy_sec))
        clips.append(ImageSequenceClip([np.array(empathy_frame)] * n_empathy, fps=config.VIDEO_FPS))
        t += empathy_sec
    else:
        hook_title_text, hook_title_id = get_random_unused_hook_title()
        hook_sec = times["hook"]  # 1초 고정
        n_hook = max(1, int(config.VIDEO_FPS * hook_sec))
        hook_frame = np.array(bg_img.copy())
        clips.append(ImageSequenceClip([hook_frame] * n_hook, fps=config.VIDEO_FPS))
        t += hook_sec
        if hook_title_id > 0:
            mark_hook_title_used(hook_title_id)

    # 2. 아침 타로운세만: N장 카드 앞면 + "이 카드를 사용해볼게요" + 앞→뒤 뒤집기 / 감성형: 스킵(바로 뒷장 셔플)
    cards_at_10s = [card_indices[display_order_10s[i]] for i in range(num_cards_use)]
    if not is_empathy:
        face_dur = times["cards_face"]
        face_show_sec = 3.0
        flip_sec = max(1.0, face_dur - face_show_sec)
        cards_face_frames = []
        n_show = max(1, int(config.VIDEO_FPS * face_show_sec))
        for i in range(n_show):
            show_text = (i // int(config.VIDEO_FPS * 0.5)) % 2 == 0
            frame = _create_9cards_with_center_text(
                deck_path, cards_at_10s, "이 카드를 사용해볼게요", show_text, bg_img
            )
            cards_face_frames.append(np.array(frame))
        n_flip_ftb = max(1, int(config.VIDEO_FPS * flip_sec))
        for i in range(n_flip_ftb):
            p = i / (n_flip_ftb - 1) if n_flip_ftb > 1 else 1.0
            frame = _create_card_flip_front_to_back_frame(
                deck_path, cards_at_10s, p,
                center_text="이 카드를 사용해볼게요", show_center_text=False,
                bg_image=bg_img, card_back=card_back_img
            )
            cards_face_frames.append(np.array(frame))
        clips.append(ImageSequenceClip(cards_face_frames, fps=config.VIDEO_FPS))
        t += face_dur

    # 3b. 그리드 1~N번 카드가 중앙으로 모임 (셔플 직전)
    gather_dur = times.get("gather_to_center", 1.5)
    gather_frames = _create_cards_fly_to_center_frames(
        deck_path, gather_dur, bg_image=bg_img, card_back=card_back_img, n_cards=num_cards_use
    )
    clips.append(ImageSequenceClip(gather_frames, fps=config.VIDEO_FPS))
    t += gather_dur

    # 4. 셔플 - 카드가 멈추지 않고 이리저리 계속 섞임
    shuffle_frames = []
    n_frames = max(1, int(config.VIDEO_FPS * times["shuffle"]))
    for i in range(n_frames):
        frame = _create_shuffle_frame(deck_path, shuffle_style["card_movement"], i, n_frames, bg_image=bg_img, card_back=card_back_img, n_cards=num_cards_use)
        shuffle_frames.append(np.array(frame))
    shuffle_clip = ImageSequenceClip(shuffle_frames, fps=config.VIDEO_FPS)
    clips.append(shuffle_clip)
    t += times["shuffle"]

    # 4b. 카드가 중앙에서 1~N번 자리로 이동
    arrange_move_dur = times.get("arrange_move", 1.6)
    fly_frames = _create_cards_fly_to_grid_frames(
        deck_path, arrange_move_dur, bg_image=bg_img, card_back=card_back_img, n_cards=num_cards_use
    )
    clips.append(ImageSequenceClip(fly_frames, fps=config.VIDEO_FPS))
    t += arrange_move_dur

    # 5a. 카드 뒷면 + 번호 + 선택 안내 (감성형: 4초, 줄바꿈 / 일반: 3초)
    facedown_sec = 3.0 if num_cards_use == 3 else times["arrange_facedown"]  # 감성형: 선택 안내 3초
    pick_msg = "1, 2, 3번 카드 중\n하나를 선택하세요" if num_cards_use == 3 else "여기에서 카드를\n한장 선택하세요!"
    arrange_facedown = _create_9cards_facedown_with_numbers(
        deck_path, bg_image=bg_img, card_back=card_back_img, n_cards=num_cards_use,
        pick_message=pick_msg, msg_font_size=96 if num_cards_use == 3 else None,
    )
    clips.append(ImageClip(np.array(arrange_facedown)).set_duration(facedown_sec))
    t += facedown_sec

    # 5b. 카드 회전하면서 뒤집어서 공개 (N장 순차 뒤→앞)
    cards_after_shuffle = [card_indices[shuffled_order[i]] for i in range(num_cards_use)]
    flip_frames = []
    n_flip_frames = max(1, int(config.VIDEO_FPS * times["arrange_faceup"]))
    for i in range(n_flip_frames):
        p = i / (n_flip_frames - 1) if n_flip_frames > 1 else 1.0
        p = _ease_in_out(p)
        frame = _create_card_flip_frame(deck_path, cards_after_shuffle, p, bg_image=bg_img, card_back=card_back_img)
        flip_frames.append(np.array(frame))
    flip_clip = ImageSequenceClip(flip_frames, fps=config.VIDEO_FPS)
    clips.append(flip_clip)
    t += times["arrange_faceup"]

    # 5c. N장 다 펼쳐진 상태 보여주기
    flip_hold_dur = times.get("flip_hold", 2)
    flip_hold_frame = _create_9cards_with_numbers(deck_path, cards_after_shuffle, bg_image=bg_img)
    clips.append(ImageClip(np.array(flip_hold_frame)).set_duration(flip_hold_dur))
    t += flip_hold_dur

    # 6. 1~3번 카드 + 의미 (감성형 3장이면 여기까지, 6장이면 seg2로)
    n_seg1 = min(3, num_cards_use)
    seg1_cards = [cards_after_shuffle[i] for i in range(n_seg1)]
    seg1_meanings = [card_meanings[shuffled_order[i]] for i in range(n_seg1)]
    seg1 = _create_3cards_with_meanings(
        deck_path, seg1_cards, seg1_meanings, number_offset=0, bg_image=bg_img
    )
    seg1_dur = 4.0 if num_cards_use == 3 else times["cards_1_3"]  # 감성형: 카드 리딩 4초
    clips.append(ImageClip(np.array(seg1)).set_duration(seg1_dur))
    t += seg1_dur

    if num_cards_use > 3:
        # 6b. 전환 (1,2,3 → 4,5,6): 카드 뒤집기 + 글자 연기 효과
        trans_dur = times.get("segment_transition", 1.5)
        seg2_cards = [cards_after_shuffle[i] for i in range(3, 6)]
        seg2_meanings = [card_meanings[shuffled_order[i]] for i in range(3, 6)]
        trans1_frames = []
        n_trans = max(1, int(config.VIDEO_FPS * trans_dur))
        for i in range(n_trans):
            p = i / (n_trans - 1) if n_trans > 1 else 1.0
            frame = _create_segment_transition_frame(
                deck_path, seg1_cards, seg2_cards, seg1_meanings, seg2_meanings,
                0, 3, p, bg_image=bg_img, card_back=card_back_img
            )
            trans1_frames.append(np.array(frame))
        clips.append(ImageSequenceClip(trans1_frames, fps=config.VIDEO_FPS))
        t += trans_dur

        # 7. 4~6번 카드 + 의미
        seg2 = _create_3cards_with_meanings(
            deck_path, seg2_cards, seg2_meanings, number_offset=3, bg_image=bg_img
        )
        clips.append(ImageClip(np.array(seg2)).set_duration(times["cards_4_6"]))
        t += times["cards_4_6"]

    # 8. 마지막 인사 (6장이므로 7~9번 구간 없음): 당신이 고른 카드는~ / 댓글로 남겨주세요(댓글 깜빡임) / 인사 / 구독과 좋아요
    closing_dur = times.get("closing", 5)
    n_closing = max(1, int(config.VIDEO_FPS * closing_dur))
    blink_interval_frames = max(1, int(config.VIDEO_FPS * 0.4))
    closing_frames = []
    for fi in range(n_closing):
        comment_highlight = (fi // blink_interval_frames) % 2 == 0
        frame = _create_closing_frame(bg_img, comment_blink_highlight=comment_highlight)
        closing_frames.append(np.array(frame))
    clips.append(ImageSequenceClip(closing_frames, fps=config.VIDEO_FPS))

    # 합성
    final = concatenate_videoclips(clips)
    music_path_str = str(music_path) if music_path else None
    if music_path_str and os.path.exists(music_path_str):
        try:
            audio_src = AudioFileClip(music_path_str)
            need_dur = final.duration
            if getattr(config, "MUSIC_AUTO_HIGHLIGHT", False):
                try:
                    start_offset = _detect_music_highlight_start(audio_src, need_dur)
                    if start_offset > 0:
                        print(f"🎵 배경음악 하이라이트 자동 감지: {start_offset:.1f}초부터 재생")
                except Exception:
                    start_offset = 0
            else:
                start_offset = getattr(config, "MUSIC_START_OFFSET_SEC", 0) or 0
            # 하이라이트 구간부터 재생: start_offset초부터 need_dur만큼 사용
            if start_offset >= audio_src.duration:
                start_offset = 0
            end_time = start_offset + need_dur
            if end_time <= audio_src.duration:
                audio = audio_src.subclip(start_offset, end_time)
            elif start_offset < audio_src.duration:
                # 남은 구간 + 앞부분 루프로 채움
                from moviepy.audio.AudioClip import concatenate_audioclips
                remaining = audio_src.duration - start_offset
                n = int((need_dur - remaining) / audio_src.duration) + 1
                parts = [audio_src.subclip(start_offset, audio_src.duration)]
                parts.extend([audio_src] * n)
                audio = concatenate_audioclips(parts).subclip(0, need_dur)
            else:
                audio = audio_src.subclip(0, need_dur)
            final = final.set_audio(audio)
        except Exception as e:
            print(f"⚠️ 배경음악 로드 실패, 무음으로 진행: {e}")
    elif not music_path_str:
        print("ℹ️ 배경음악 없음. assets/music 폴더에 mp3, wav, m4a 파일을 넣으면 자동 적용됩니다.")

    encode_preset = getattr(config, "VIDEO_ENCODE_PRESET", "medium")
    encode_threads = getattr(config, "VIDEO_ENCODE_THREADS", 4) or 4
    print(f"🎬 타로 영상 생성: {theme_name} | 덱: {deck_path.name} | 셔플: {shuffle_style['name']} (인코딩: {encode_preset})")
    final.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset=encode_preset,
        threads=encode_threads,
        logger=None,
    )
    final.close()
    print(f"✅ 영상 생성 완료: {output_path}")

    metadata_extra = {
        "cards_after_shuffle": cards_after_shuffle,
        "card_meanings": card_meanings,
        "card_indices": card_indices,
        "shuffled_order": shuffled_order,
        "num_cards": num_cards_use,
        "hook_text": hook_title_text,
        "major_theme": major_theme if major_theme else None,
        "is_empathy": is_empathy,
    }
    return output_path, theme_name, metadata_extra
