# -*- coding: utf-8 -*-
"""
타로 카드 셔플 스타일 - 영상 생성 시 랜덤 선택
실제 셔플 애니메이션은 각 스타일별 파라미터로 구분
"""
import random
from typing import TypedDict


class ShuffleStyle(TypedDict):
    id: str
    name: str
    duration: float      # 셔플 구간 길이 (초)
    ease: str            # ease_in, ease_out, ease_in_out
    card_movement: str   # spread, cascade, riffle, overhand, fan


SHUFFLE_STYLES: list[ShuffleStyle] = [
    {"id": "chaos_orbit", "name": "혼돈 궤도", "duration": 7.0, "ease": "linear", "card_movement": "chaos_orbit"},
    {"id": "scatter_swirl", "name": "흩어짐 소용돌이", "duration": 7.0, "ease": "linear", "card_movement": "scatter_swirl"},
    {"id": "bounce_mix", "name": "튀어오름 섞기", "duration": 7.0, "ease": "linear", "card_movement": "bounce_mix"},
    {"id": "spiral_chaos", "name": "나선 혼돈", "duration": 7.0, "ease": "linear", "card_movement": "spiral_chaos"},
]


def pick_random_shuffle() -> ShuffleStyle:
    """영상 생성 시 랜덤 셔플 스타일 반환"""
    return random.choice(SHUFFLE_STYLES)


def get_shuffle_by_id(shuffle_id: str) -> ShuffleStyle | None:
    """ID로 셔플 스타일 조회"""
    for s in SHUFFLE_STYLES:
        if s["id"] == shuffle_id:
            return s
    return None
