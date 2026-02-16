# -*- coding: utf-8 -*-
"""
타로 덱 폴더 관리 - 영상 생성 시 랜덤 덱 선택
"""
import random
from pathlib import Path

import config


def get_available_decks() -> list[str]:
    """사용 가능한 덱 ID 목록 (78장+back.png 있는 폴더만)"""
    available = []
    for folder in sorted(config.TAROT_DIR.iterdir()):
        if folder.is_dir() and folder.name.startswith("deck_"):
            cards = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
            cards = [c for c in cards if c.stem != "back"]
            if len(cards) >= 78 and (folder / "back.png").exists():
                available.append(folder.name)
    return available


def pick_random_deck() -> str | None:
    """랜덤 덱 ID 반환 (영상 생성용)"""
    decks = get_available_decks()
    return random.choice(decks) if decks else None


def get_random_deck_path() -> Path | None:
    """랜덤 덱 폴더 경로 반환"""
    deck_id = pick_random_deck()
    if deck_id:
        return config.TAROT_DIR / deck_id
    return None


def get_card_path(deck_path: Path, card_index: int) -> Path | None:
    """덱 폴더에서 카드 인덱스(0~77)에 해당하는 이미지 경로"""
    if not deck_path or not deck_path.exists():
        return None
    cards = [f for f in deck_path.iterdir() if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg")]
    cards = [c for c in cards if c.stem.lower() != "back"]
    # 00, 01, ... 또는 00_fool 등 → 숫자 기준 정렬
    def sort_key(p):
        s = p.stem
        num = ""
        for c in s:
            if c.isdigit():
                num += c
            elif num:
                break
        return int(num) if num else 999
    cards.sort(key=sort_key)
    if 0 <= card_index < len(cards):
        return cards[card_index]
    return None
