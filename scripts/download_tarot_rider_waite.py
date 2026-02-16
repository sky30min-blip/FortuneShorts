# -*- coding: utf-8 -*-
"""
라이더 웨이트 타로 덱 다운로드 (저작권 없음 - Public Domain)
Internet Archive에서 78장 PNG 다운로드 후 assets/tarot/deck_01/ 에 저장
+ 카드 뒷장(back.png) 자동 생성 (저작권 없음)
"""
import urllib.request
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None

# 프로젝트 루트
BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "assets" / "tarot" / "deck_01"
ARCHIVE_URL = "https://archive.org/download/rider-waite-tarot"

# 78장 카드: Internet Archive 파일명 -> 00~77 순서
# Major Arcana (0-21)
MAJOR = [
    "major_arcana_fool", "major_arcana_magician", "major_arcana_priestess",
    "major_arcana_empress", "major_arcana_emperor", "major_arcana_hierophant",
    "major_arcana_lovers", "major_arcana_chariot", "major_arcana_strength",
    "major_arcana_hermit", "major_arcana_fortune", "major_arcana_justice",
    "major_arcana_hanged", "major_arcana_death", "major_arcana_temperance",
    "major_arcana_devil", "major_arcana_tower", "major_arcana_star",
    "major_arcana_moon", "major_arcana_sun", "major_arcana_judgement",
    "major_arcana_world"
]
# Minor: Wands(22-35), Cups(36-49), Swords(50-63), Pentacles(64-77)
SUITS = ["wands", "cups", "swords", "pentacles"]
RANKS = ["ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "page", "knight", "queen", "king"]

# 카드 뒷장 크기 (앞면과 비율 맞춤, 나중에 리사이즈 가능)
CARD_W, CARD_H = 400, 700


def create_card_back(out_path: Path):
    """
    카드 뒷장 이미지 생성 (저작권 없음 - 자체 제작)
    클래식 타로 스타일 기하학적 패턴
    """
    if Image is None:
        print("  PIL 없음. 뒷장 생략. pip install pillow 후 재실행하거나, 직접 back.png 추가하세요.")
        return False
    img = Image.new("RGB", (CARD_W, CARD_H), color=(30, 40, 80))  # 진한 남색
    draw = ImageDraw.Draw(img)
    # 테두리 (금색)
    margin = 20
    draw.rectangle([margin, margin, CARD_W - margin, CARD_H - margin], outline=(180, 150, 80), width=4)
    # 내부 이중선
    m2 = margin + 15
    draw.rectangle([m2, m2, CARD_W - m2, CARD_H - m2], outline=(100, 90, 60), width=2)
    # 중앙 다이아몬드 패턴 (가역적 디자인)
    cx, cy = CARD_W // 2, CARD_H // 2
    r = min(CARD_W, CARD_H) // 3
    for i in range(4):
        angle = math.pi * i / 2
        x1 = cx + int(r * math.cos(angle))
        y1 = cy + int(r * math.sin(angle))
        angle2 = math.pi * (i + 1) / 2
        x2 = cx + int(r * math.cos(angle2))
        y2 = cy + int(r * math.sin(angle2))
        draw.line([(cx, cy), (x1, y1)], fill=(120, 110, 80), width=2)
    # 꼭짓점에서 중앙으로
    for dx, dy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]:
        px = cx + dx * r
        py = cy + dy * r
        draw.line([(cx, cy), (px, py)], fill=(100, 95, 70), width=1)
    img.save(out_path, "PNG")
    print(f"  [뒷장] back.png 생성됨 (저작권 없음)")
    return True


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for i, name in enumerate(MAJOR):
        url = f"{ARCHIVE_URL}/{name}.png"
        out = OUT_DIR / f"{i:02d}_{name.replace('major_arcana_', '')}.png"
        try:
            urllib.request.urlretrieve(url, out)
            print(f"  [{i+1}/78] {out.name}")
            total += 1
        except Exception as e:
            print(f"  실패: {name} - {e}")

    idx = 22
    for suit in SUITS:
        for rank in RANKS:
            name = f"minor_arcana_{suit}_{rank}"
            url = f"{ARCHIVE_URL}/{name}.png"
            out = OUT_DIR / f"{idx:02d}_{suit}_{rank}.png"
            try:
                urllib.request.urlretrieve(url, out)
                print(f"  [{idx+1}/78] {out.name}")
                total += 1
            except Exception as e:
                print(f"  실패: {name} - {e}")
            idx += 1

    # 카드 뒷장 생성 (Internet Archive에 없음 → 자체 생성)
    back_path = OUT_DIR / "back.png"
    if not back_path.exists():
        create_card_back(back_path)
    else:
        print("  [뒷장] back.png 이미 존재 (덮어쓰지 않음)")

    print(f"\n완료: {total}/78 장 + 뒷장 저장됨 -> {OUT_DIR}")


if __name__ == "__main__":
    main()
