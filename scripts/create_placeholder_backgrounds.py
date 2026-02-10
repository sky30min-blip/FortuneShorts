# -*- coding: utf-8 -*-
"""
assets/templates/용 배경 이미지 4장 생성 (1080x1920)
실제 사진으로 나중에 교체 가능
"""
import sys
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image
import config

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT  # 1080, 1920


def gradient(top_rgb, bottom_rgb):
    """위→아래 그라데이션 (numpy로 빠르게)"""
    y = np.arange(H, dtype=np.float32) / H
    r = (top_rgb[0] * (1 - y) + bottom_rgb[0] * y).astype(np.uint8)
    g = (top_rgb[1] * (1 - y) + bottom_rgb[1] * y).astype(np.uint8)
    b = (top_rgb[2] * (1 - y) + bottom_rgb[2] * y).astype(np.uint8)
    arr = np.stack([r, g, b], axis=1)  # (H, 3)
    arr = np.broadcast_to(arr[:, None, :], (H, W, 3))
    return Image.fromarray(arr)


def make_space():
    """우주: 진한 남색 → 보라"""
    return gradient((10, 5, 40), (60, 20, 80))


def make_nature():
    """자연: 하늘색 → 연두"""
    return gradient((135, 206, 235), (34, 139, 34))


def make_city():
    """도시: 회색 톤"""
    return gradient((70, 70, 80), (40, 42, 54))


def make_fantasy():
    """판타지: 보라 → 핑크"""
    return gradient((75, 0, 130), (255, 105, 180))


def main():
    config.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    themes = [
        ("space.jpg", make_space),
        ("nature.jpg", make_nature),
        ("city.jpg", make_city),
        ("fantasy.jpg", make_fantasy),
    ]
    for name, fn in themes:
        path = config.TEMPLATES_DIR / name
        fn().save(path, quality=95)
        print(f"  생성: {path}")
    print("배경 이미지 4장 생성 완료.")


if __name__ == "__main__":
    main()
