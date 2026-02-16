# -*- coding: utf-8 -*-
"""
썸네일 생성 모듈 — 타로운세 썸네일 1장만 생성 (배경 랜덤, 후킹 문구 순차)
"""
import random
from PIL import Image, ImageDraw
from typing import List, Optional
from pathlib import Path
from datetime import datetime

import config


# 썸네일 배경 확장자
THUMB_BG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _list_thumbnail_backgrounds() -> List[Path]:
    """thumbnail_backgrounds 폴더에서 이미지 파일 목록."""
    d = getattr(config, "THUMBNAIL_BACKGROUNDS_DIR", None) or (config.ASSETS_DIR / "thumbnail_backgrounds")
    if not d or not Path(d).exists():
        return []
    return [p for p in Path(d).iterdir() if p.is_file() and p.suffix.lower() in THUMB_BG_EXT]


def get_thumbnail_backgrounds_ratio_info() -> List[tuple]:
    """
    썸네일 배경 이미지별 크기·비율 정보 (UI 확인용).
    Returns: [(파일명, 가로, 세로, 비율(w/h), 9:16 여부), ...]
    """
    files = _list_thumbnail_backgrounds()
    result = []
    target_ratio = 9 / 16  # Shorts 권장 세로
    for p in sorted(files):
        try:
            img = Image.open(p)
            w, h = img.size
            ratio = round(w / h, 3) if h else 0
            ok_916 = abs(ratio - target_ratio) < 0.05
            result.append((p.name, w, h, ratio, ok_916))
        except Exception:
            result.append((p.name, 0, 0, 0.0, False))
    return result


def _wrap_text(draw, font, text: str, max_width: int) -> List[str]:
    """후킹 문구를 화면 너비에 맞게 줄바꿈. 단어(공백 단위)가 잘리지 않게 끊고, 한 단어가 너무 길면 글자 단위로만 끊는다."""
    if not text:
        return [""]
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = ""
    for word in words:
        sep = " " if current else ""
        candidate = current + sep + word
        b = draw.textbbox((0, 0), candidate, font=font)
        if (b[2] - b[0]) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            b_word = draw.textbbox((0, 0), word, font=font)
            if (b_word[2] - b_word[0]) <= max_width:
                current = word
            else:
                current = ""
                for ch in word:
                    cnd = (current + ch) if current else ch
                    b = draw.textbbox((0, 0), cnd, font=font)
                    if (b[2] - b[0]) <= max_width:
                        current = cnd
                    else:
                        if current:
                            lines.append(current)
                        current = ch
    if current:
        lines.append(current)
    return lines


def _wrap_text_max_chars(text: str, max_chars: int = 8) -> List[str]:
    """한 줄 최대 max_chars글자. 단어를 자르지 않고 넘치면 그 단어는 다음 줄로. (썸네일용)"""
    if not text or max_chars < 1:
        return [text] if text else [""]
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = ""
    for word in words:
        sep = " " if current else ""
        candidate = (current + sep + word) if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            if len(word) <= max_chars:
                current = word
            else:
                # 단어가 max_chars 초과면 한 줄에 한 단어만 (단어는 자르지 않음)
                lines.append(word)
                current = ""
    if current:
        lines.append(current)
    return lines


def _get_thumbnail_font_path() -> Optional[str]:
    """assets/fonts에 넣어 둔 폰트 우선 사용 (.ttf → .otf, 정렬해서 첫 번째). 절대경로 반환."""
    fonts_dir = Path(config.FONTS_DIR).resolve()
    if not fonts_dir.exists():
        return None
    candidates = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))
    candidates = [str(p.resolve()) for p in sorted(candidates) if p.is_file()]
    return candidates[0] if candidates else None


def _hook_to_lines(hook_phrase: str, max_chars_per_line: int = 8) -> List[str]:
    """후킹 문구를 한 줄 최대 8글자로 줄바꿈. 수정칸에서 넣은 줄바꿈(\\n)은 그대로 반영. 단어는 자르지 않음."""
    if not hook_phrase or not hook_phrase.strip():
        return [""]
    out = []
    for part in hook_phrase.strip().split("\n"):
        part = part.strip()
        if not part:
            continue
        out.extend(_wrap_text_max_chars(part, max_chars_per_line))
    return out if out else [""]


def _hook_to_lines_exact(hook_phrase: str) -> List[str]:
    """수정칸에서 입력한 그대로 반영: 줄바꿈(\\n)만 구분, 자동 줄바꿈 없음. 빈 줄은 빈 문자열로 유지."""
    if not hook_phrase:
        return [""]
    return [line for line in hook_phrase.split("\n")]


def _text_line_width(draw, text: str, font) -> int:
    """한 줄 텍스트의 총 픽셀 너비."""
    if not text:
        return 0
    return sum(draw.textbbox((0, 0), ch, font=font)[2] - draw.textbbox((0, 0), ch, font=font)[0] for ch in text)


def _draw_line_per_char(draw, x_start: int, y: int, text: str, font, fill_per_char: Optional[List[str]], default_fill: str, stroke_width: int, stroke_fill: str) -> int:
    """한 줄 텍스트를 글자마다 fill_per_char 색으로 그리기. fill_per_char가 부족하면 default_fill 사용. 줄 높이 반환."""
    if not text:
        b = draw.textbbox((0, 0), "한", font=font)
        return b[3] - b[1]
    x = x_start
    line_h = 0
    for i, ch in enumerate(text):
        fill = (fill_per_char[i] if fill_per_char and i < len(fill_per_char) else default_fill)
        b = draw.textbbox((0, 0), ch, font=font)
        cw, ch_h = b[2] - b[0], b[3] - b[1]
        line_h = max(line_h, ch_h)
        draw.text((x, y), ch, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        x += cw
    return line_h


def hook_phrase_to_lines(phrase: str, max_per_line: int = 8) -> List[str]:
    """후킹 문구를 한 줄 최대 글자 수로 줄바꿈. 앱 미리보기·썸네일 동일 줄바꿈용."""
    return _hook_to_lines(phrase or "", max_chars_per_line=max_per_line)


def list_thumbnail_fonts() -> List[tuple]:
    """
    썸네일용 폰트 목록. 반환: [(표시이름, 절대경로), ...]
    1) assets/fonts의 .ttf/.otf
    2) config.FONT_FALLBACKS에서 실제 존재하는 폰트 (시스템 폰트 포함)
    """
    result = []
    seen_paths = set()

    # 1. assets/fonts
    fonts_dir = Path(config.FONTS_DIR).resolve()
    if fonts_dir.exists():
        candidates = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))
        for p in sorted(candidates):
            if p.is_file():
                path_str = str(p.resolve())
                if path_str not in seen_paths:
                    seen_paths.add(path_str)
                    result.append((p.name, path_str))

    # 2. FONT_FALLBACKS (시스템 폰트 포함) - 실제 존재하는 것만
    fallback_names = {
        "malgun.ttf": "맑은 고딕 (시스템)",
        "gulim.ttc": "굴림 (시스템)",
        "GmarketSansBold.otf": "Gmarket Sans Bold",
        "GmarketSansTTFBold.ttf": "Gmarket Sans TTF Bold",
        "Pretendard-ExtraBold.otf": "Pretendard ExtraBold",
        "NanumSquareRoundBold.ttf": "나눔스퀘어 라운드 Bold",
        "NanumSquareRoundR.ttf": "나눔스퀘어 라운드 R",
        "NanumGothicBold.ttf": "나눔고딕 Bold",
        "NanumGothic.ttf": "나눔고딕",
    }
    for path in getattr(config, "FONT_FALLBACKS", []):
        if path and Path(path).exists():
            path_abs = str(Path(path).resolve())
            if path_abs not in seen_paths:
                seen_paths.add(path_abs)
                name = Path(path).name
                display = fallback_names.get(name, name)
                result.append((display, path_abs))

    return result


def generate_one_tarot_fortune_thumbnail(
    time_slot: str = "아침",
    output_dir: Optional[Path] = None,
    hook_phrase_override: Optional[str] = None,
    theme_label: Optional[str] = None,
    line1_override: Optional[str] = None,
    line2_override: Optional[str] = None,
    background_path_override: Optional[str] = None,
    font_path_override: Optional[str] = None,
    font_size_scale: float = 1.0,
    line1_fill: str = "#FFFFFF",
    line2_fill: str = "#00FFCC",
    hook_fill: str = "#FFFFFF",
    hook_fill_per_line: Optional[List[str]] = None,
    line1_fill_per_char: Optional[List[str]] = None,
    line2_fill_per_char: Optional[List[str]] = None,
    hook_fill_per_char: Optional[List[List[str]]] = None,
) -> Optional[tuple]:
    """
    타로운세 썸네일 1장 생성.
    line1_fill_per_char, line2_fill_per_char, hook_fill_per_char: 글자별 색상 리스트(있으면 글자마다 적용).
    hook_fill_per_char: 후킹 줄별로 [색,색,...] 리스트의 리스트.
    그 외 인자: 기존과 동일.

    Returns:
        (저장 경로, 2번째 줄 문구, 후킹 문구 원문, 후킹 문구_썸네일과 동일 줄바꿈, 사용한 배경 경로) 또는 None
    """
    from modules.tarot_thumbnail_phrases import get_hook_phrase_with_gpt
    from modules import theme_phrases_db

    THEME_LINE_COLOR = "#00FFCC"   # 밝은 민트
    THEME_STROKE_COLOR = "#000080"  # 진한 남색

    backgrounds = _list_thumbnail_backgrounds()
    if not backgrounds:
        return None
    if background_path_override and Path(background_path_override).exists():
        bg_path = Path(background_path_override)
    else:
        bg_path = random.choice(backgrounds)
    out_dir = Path(output_dir or config.THUMBNAILS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    default_date = f"{now.month}월 {now.day}일"
    default_line2 = theme_label.strip() if (theme_label and theme_label.strip()) else (f"오늘 {time_slot} 타로운세" if time_slot else "오늘 타로운세")

    # 빈 문자열이면 해당 줄 생략. None이면 기본값 사용.
    line1 = (line1_override if line1_override is not None else default_date).strip()
    line2 = (line2_override if line2_override is not None else default_line2).strip()

    if hook_phrase_override and hook_phrase_override.strip():
        hook_phrase = hook_phrase_override.strip()
        # 한 줄 최대 8글자로 자동 줄바꿈 (수정칸과 동일)
        line3_lines = _hook_to_lines(hook_phrase, max_chars_per_line=8)
    elif theme_label and theme_label in theme_phrases_db.THEME_DB_NAMES:
        hook_phrase = theme_phrases_db.get_random_phrase(theme_label) or get_hook_phrase_with_gpt()
        line3_lines = _hook_to_lines(hook_phrase, max_chars_per_line=8)
    else:
        hook_phrase = get_hook_phrase_with_gpt()
        line3_lines = _hook_to_lines(hook_phrase, max_chars_per_line=8)

    out_path = out_dir / "thumbnail_tarot_fortune.png"
    raw_font = font_path_override or _get_thumbnail_font_path()
    font_path = str(Path(raw_font).resolve()) if raw_font else None
    size_scale = max(0.5, min(2.0, float(font_size_scale)))
    try:
        img = Image.open(bg_path).convert("RGBA")
        w, h = img.size
        draw = ImageDraw.Draw(img)
        scale = 1.0 if h >= 800 else 0.75
        size1 = int(72 * scale * size_scale)
        size2 = int(68 * scale * size_scale)
        size3 = int(64 * scale * size_scale)
        font1 = config.get_korean_font(size1, font_path=font_path) if font_path else config.get_korean_font(size1)
        font2 = config.get_korean_font(size2, font_path=font_path) if font_path else config.get_korean_font(size2)
        font3 = config.get_korean_font(size3, font_path=font_path) if font_path else config.get_korean_font(size3)
        gap = int(h * 0.04)
        total_h = 0
        if line1:
            b = draw.textbbox((0, 0), line1, font=font1)
            total_h += (b[3] - b[1]) + gap
        if line2:
            b = draw.textbbox((0, 0), line2, font=font2)
            total_h += (b[3] - b[1]) + gap
        # 빈 줄은 한 줄 높이만큼 공간 확보 (위치 맞추기)
        ref_b = draw.textbbox((0, 0), "한", font=font3)
        empty_line_h = ref_b[3] - ref_b[1]
        for ln in line3_lines:
            if ln.strip():
                b = draw.textbbox((0, 0), ln, font=font3)
                total_h += (b[3] - b[1]) + gap
            else:
                total_h += empty_line_h + gap
        total_h -= gap
        y = (h - total_h) // 2

        if line1:
            if line1_fill_per_char and len(line1_fill_per_char) >= len(line1):
                tw = _text_line_width(draw, line1, font1)
                x = (w - tw) // 2
                th_line = _draw_line_per_char(draw, x, y, line1, font1, line1_fill_per_char, line1_fill, 5, "black")
            else:
                b = draw.textbbox((0, 0), line1, font=font1)
                tw, th_line = b[2] - b[0], b[3] - b[1]
                x = (w - tw) // 2
                draw.text((x, y), line1, font=font1, fill=line1_fill, stroke_width=5, stroke_fill="black")
            y += th_line + gap
        if line2:
            if line2_fill_per_char and len(line2_fill_per_char) >= len(line2):
                tw = _text_line_width(draw, line2, font2)
                x = (w - tw) // 2
                th_line = _draw_line_per_char(draw, x, y, line2, font2, line2_fill_per_char, line2_fill, 5, THEME_STROKE_COLOR)
            else:
                b = draw.textbbox((0, 0), line2, font=font2)
                tw, th_line = b[2] - b[0], b[3] - b[1]
                x = (w - tw) // 2
                draw.text((x, y), line2, font=font2, fill=line2_fill, stroke_width=5, stroke_fill=THEME_STROKE_COLOR)
            y += th_line + gap
        for i, ln in enumerate(line3_lines):
            if ln.strip():
                fills = None
                if hook_fill_per_char and i < len(hook_fill_per_char) and len(hook_fill_per_char[i]) >= len(ln):
                    fills = hook_fill_per_char[i]
                line_fill = (hook_fill_per_line[i] if hook_fill_per_line and i < len(hook_fill_per_line) else hook_fill)
                if fills is not None:
                    tw = _text_line_width(draw, ln, font3)
                    x = (w - tw) // 2
                    th_line = _draw_line_per_char(draw, x, y, ln, font3, fills, line_fill, 5, "black")
                else:
                    b = draw.textbbox((0, 0), ln, font=font3)
                    tw, th_line = b[2] - b[0], b[3] - b[1]
                    x = (w - tw) // 2
                    draw.text((x, y), ln, font=font3, fill=line_fill, stroke_width=5, stroke_fill="black")
                y += th_line + gap
            else:
                y += empty_line_h + gap
        img.convert("RGB").save(out_path, "PNG")
        hook_display = "\n".join(line3_lines)  # 썸네일에 그려진 그대로 줄바꿈한 문자열
        return (str(out_path), line2, hook_phrase, hook_display, str(bg_path))
    except Exception:
        return None
