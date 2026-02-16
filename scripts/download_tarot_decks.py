# -*- coding: utf-8 -*-
"""
여러 타로 덱 다운로드 (저작권 없음 - Public Domain)
배치 파일 실행 시: 아직 없는 덱 중 다음 덱을 다운로드
영상 생성 시: 존재하는 덱 중 랜덤 선택
"""
import io
import math
import random
import urllib.request
import zipfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None

BASE = Path(__file__).resolve().parent.parent
TAROT_DIR = BASE / "assets" / "tarot"

# 덱 소스 정의 (저작권 없음)
RIDER_WAITE_MAJOR = [
    "major_arcana_fool", "major_arcana_magician", "major_arcana_priestess",
    "major_arcana_empress", "major_arcana_emperor", "major_arcana_hierophant",
    "major_arcana_lovers", "major_arcana_chariot", "major_arcana_strength",
    "major_arcana_hermit", "major_arcana_fortune", "major_arcana_justice",
    "major_arcana_hanged", "major_arcana_death", "major_arcana_temperance",
    "major_arcana_devil", "major_arcana_tower", "major_arcana_star",
    "major_arcana_moon", "major_arcana_sun", "major_arcana_judgement",
    "major_arcana_world"
]
SUITS = ["wands", "cups", "swords", "pentacles"]
RANKS = ["ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "page", "knight", "queen", "king"]

DECKS = [
    {"id": "deck_01", "name": "라이더 웨이트", "source": "archive"},
    {"id": "deck_02", "name": "Etteilla I (1789)", "source": "zip", "url": "https://benebellwen.com/wp-content/uploads/2025/08/etteilla-i.zip"},
    {"id": "deck_03", "name": "Etteilla II (1850)", "source": "zip", "url": "https://benebellwen.com/wp-content/uploads/2025/08/etteilla-ii.zip"},
    {"id": "deck_04", "name": "Etteilla Grimaud (1890)", "source": "zip", "url": "https://benebellwen.com/wp-content/uploads/2025/08/etteilla-i-grimaud-1890.zip"},
    {"id": "deck_05", "name": "Etteilla III (1865)", "source": "zip", "url": "https://benebellwen.com/wp-content/uploads/2025/08/etteilla-iii-jeu-de-1870.zip"},
]
ARCHIVE_BASE = "https://archive.org/download/rider-waite-tarot"

CARD_W, CARD_H = 400, 700


def create_card_back(out_path: Path, hue_shift: int = 0):
    """카드 뒷장 생성 (덱마다 색조 조금씩 다르게)"""
    if Image is None:
        return False
    r, g, b = 30 + hue_shift, 40, 80
    img = Image.new("RGB", (CARD_W, CARD_H), color=(min(255, r), g, b))
    draw = ImageDraw.Draw(img)
    margin = 20
    draw.rectangle([margin, margin, CARD_W - margin, CARD_H - margin], outline=(180, 150, 80), width=4)
    m2 = margin + 15
    draw.rectangle([m2, m2, CARD_W - m2, CARD_H - m2], outline=(100, 90, 60), width=2)
    cx, cy = CARD_W // 2, CARD_H // 2
    r_val = min(CARD_W, CARD_H) // 3
    for i in range(4):
        angle = math.pi * i / 2
        x1 = cx + int(r_val * math.cos(angle))
        y1 = cy + int(r_val * math.sin(angle))
        draw.line([(cx, cy), (x1, y1)], fill=(120, 110, 80), width=2)
    for dx, dy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]:
        px = cx + dx * r_val
        py = cy + dy * r_val
        draw.line([(cx, cy), (px, py)], fill=(100, 95, 70), width=1)
    img.save(out_path, "PNG")
    return True


def download_rider_waite(out_dir: Path) -> int:
    """라이더 웨이트 (Internet Archive)"""
    url_base = ARCHIVE_BASE
    total = 0
    for i, name in enumerate(RIDER_WAITE_MAJOR):
        url = f"{url_base}/{name}.png"
        out = out_dir / f"{i:02d}_{name.replace('major_arcana_', '')}.png"
        try:
            urllib.request.urlretrieve(url, out)
            print(f"    [{i+1}/78] {out.name}")
            total += 1
        except Exception as e:
            print(f"    실패: {name} - {e}")
    idx = 22
    for suit in SUITS:
        for rank in RANKS:
            name = f"minor_arcana_{suit}_{rank}"
            url = f"{url_base}/{name}.png"
            out = out_dir / f"{idx:02d}_{suit}_{rank}.png"
            try:
                urllib.request.urlretrieve(url, out)
                print(f"    [{idx+1}/78] {out.name}")
                total += 1
            except Exception as e:
                print(f"    실패: {name} - {e}")
            idx += 1
    return total


def download_zip_deck(out_dir: Path, zip_url: str) -> int:
    """ZIP 다운로드 후 00~77로 정리 (Etteilla 등)"""
    print("    ZIP 다운로드 중...")
    try:
        with urllib.request.urlopen(zip_url, timeout=120) as resp:
            data = resp.read()
    except Exception as e:
        print(f"    ZIP 다운로드 실패: {e}")
        return 0
    z = zipfile.ZipFile(io.BytesIO(data), "r")
    img_files = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    img_files.sort()
    if len(img_files) < 78:
        print(f"    경고: 78장 미만 ({len(img_files)}장)")
    total = 0
    for i, name in enumerate(img_files[:78]):
        try:
            buf = z.read(name)
            ext = Path(name).suffix.lower() or ".jpg"
            out = out_dir / f"{i:02d}{ext}"
            with open(out, "wb") as f:
                f.write(buf)
            print(f"    [{i+1}/78] {out.name}")
            total += 1
        except Exception as e:
            print(f"    실패: {name} - {e}")
    z.close()
    return total


def get_next_deck_to_download() -> dict | None:
    """다운로드할 다음 덱 반환 (78장 부족 or 뒷장 없으면)"""
    for d in DECKS:
        folder = TAROT_DIR / d["id"]
        if not folder.exists():
            return d
        cards = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
        cards = [c for c in cards if c.stem != "back"]
        if len(cards) < 78:
            return d
        if not (folder / "back.png").exists():
            return d  # 78장은 있지만 뒷장 없음 → 뒷장 생성
    return None


def get_available_decks() -> list[str]:
    """영상 생성 시 사용 가능한 덱 목록"""
    available = []
    for d in DECKS:
        folder = TAROT_DIR / d["id"]
        if folder.exists():
            cards = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
            cards = [c for c in cards if c.stem not in ("back",)]
            if len(cards) >= 78:
                available.append(d["id"])
    return available


def pick_random_deck() -> str | None:
    """랜덤 덱 선택 (영상 생성용)"""
    decks = get_available_decks()
    return random.choice(decks) if decks else None


def main():
    TAROT_DIR.mkdir(parents=True, exist_ok=True)
    deck = get_next_deck_to_download()
    if deck is None:
        print("\n✅ 모든 덱이 이미 다운로드되어 있습니다.")
        print(f"   폴더: {TAROT_DIR}")
        print("   영상 생성 시 랜덤으로 덱이 선택됩니다.")
        return
    out_dir = TAROT_DIR / deck["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    back_path = out_dir / "back.png"
    cards = list(out_dir.glob("*.png")) + list(out_dir.glob("*.jpg"))
    cards = [c for c in cards if c.stem != "back"]
    if len(cards) >= 78 and not back_path.exists():
        # 78장은 있는데 뒷장만 없음 → 뒷장만 생성
        print(f"\n📥 {deck['name']} ({deck['id']}) 뒷장 생성 중...\n")
        if Image:
            hue = DECKS.index(deck) * 15
            create_card_back(back_path, hue)
            print("    [뒷장] back.png 생성됨")
        else:
            print("    ⚠️ PIL 없음. pip install pillow 후 재실행하세요.")
        total = 78
    else:
        print(f"\n📥 {deck['name']} ({deck['id']}) 다운로드 중...\n")
        if deck["source"] == "archive":
            total = download_rider_waite(out_dir)
        else:
            total = download_zip_deck(out_dir, deck["url"])
        if not back_path.exists() and Image:
            hue = DECKS.index(deck) * 15
            create_card_back(back_path, hue)
            print("    [뒷장] back.png 생성됨")
    print(f"\n완료: {total}/78 장 -> {out_dir}")
    remaining = get_next_deck_to_download()
    if remaining:
        print(f"\n다음 실행 시: {remaining['name']} ({remaining['id']}) 다운로드됩니다.")


if __name__ == "__main__":
    main()
