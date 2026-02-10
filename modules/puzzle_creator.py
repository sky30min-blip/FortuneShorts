# -*- coding: utf-8 -*-
"""
퍼즐 조각 생성 모듈
PIL을 사용하여 다양한 모양의 퍼즐 마스크 생성
"""
from PIL import Image, ImageDraw
import math
from typing import Tuple


def create_heart_mask(size: Tuple[int, int]) -> Image.Image:
    """
    하트 모양 마스크 생성

    Args:
        size: (width, height) 튜플

    Returns:
        PIL Image (L 모드) - 흰색이 퍼즐 조각 영역
    """
    width, height = size
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)

    # 하트 중심점 (중앙)
    center_x = width // 2
    center_y = height // 2

    # 하트 크기 (화면의 1/4)
    heart_width = width // 4
    heart_height = height // 4

    # 하트 그리기 (두 개의 원 + 삼각형)
    # 왼쪽 원
    draw.ellipse([
        center_x - heart_width, center_y - heart_height // 2,
        center_x, center_y + heart_height // 2
    ], fill=255)

    # 오른쪽 원
    draw.ellipse([
        center_x, center_y - heart_height // 2,
        center_x + heart_width, center_y + heart_height // 2
    ], fill=255)

    # 아래 삼각형
    draw.polygon([
        (center_x - heart_width, center_y),
        (center_x + heart_width, center_y),
        (center_x, center_y + int(heart_height * 1.5))
    ], fill=255)

    return mask


def create_star_mask(size: Tuple[int, int]) -> Image.Image:
    """
    별 모양 마스크 생성 (5각 별)

    Args:
        size: (width, height) 튜플

    Returns:
        PIL Image (L 모드)
    """
    width, height = size
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)

    center_x = width // 2
    center_y = height // 2
    radius = min(width, height) // 4

    # 5각 별 좌표 계산
    points = []
    for i in range(10):
        angle = math.pi * 2 * i / 10 - math.pi / 2
        if i % 2 == 0:
            r = radius
        else:
            r = radius // 2
        x = center_x + r * math.cos(angle)
        y = center_y + r * math.sin(angle)
        points.append((x, y))

    draw.polygon(points, fill=255)
    return mask


def create_moon_mask(size: Tuple[int, int]) -> Image.Image:
    """
    초승달 모양 마스크 생성

    Args:
        size: (width, height) 튜플

    Returns:
        PIL Image (L 모드)
    """
    width, height = size
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)

    center_x = width // 2
    center_y = height // 2
    radius = min(width, height) // 4

    # 큰 원 그리기
    draw.ellipse([
        center_x - radius, center_y - radius,
        center_x + radius, center_y + radius
    ], fill=255)

    # 작은 원으로 깎아내기 (초승달 효과)
    offset = radius // 3
    draw.ellipse([
        center_x - radius + offset, center_y - radius,
        center_x + radius + offset, center_y + radius
    ], fill=0)

    return mask


def create_clover_mask(size: Tuple[int, int]) -> Image.Image:
    """
    클로버 모양 마스크 생성 (네잎클로버)

    Args:
        size: (width, height) 튜플

    Returns:
        PIL Image (L 모드)
    """
    width, height = size
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)

    center_x = width // 2
    center_y = height // 2
    leaf_size = min(width, height) // 8

    # 4개의 잎 그리기
    positions = [
        (center_x, center_y - leaf_size),      # 위
        (center_x + leaf_size, center_y),      # 오른쪽
        (center_x, center_y + leaf_size),      # 아래
        (center_x - leaf_size, center_y)       # 왼쪽
    ]

    for px, py in positions:
        draw.ellipse([
            px - leaf_size, py - leaf_size,
            px + leaf_size, py + leaf_size
        ], fill=255)

    # 중앙 원
    draw.ellipse([
        center_x - leaf_size // 2, center_y - leaf_size // 2,
        center_x + leaf_size // 2, center_y + leaf_size // 2
    ], fill=255)

    return mask


def extract_puzzle_piece(image: Image.Image, mask: Image.Image) -> Image.Image:
    """
    마스크를 사용하여 이미지에서 퍼즐 조각 추출

    Args:
        image: 원본 이미지
        mask: 마스크 이미지 (L 모드)

    Returns:
        투명 배경의 퍼즐 조각 (RGBA)
    """
    # RGBA로 변환
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # 마스크 크기 맞추기
    if image.size != mask.size:
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)

    # 퍼즐 조각 추출
    piece = Image.new('RGBA', image.size, (0, 0, 0, 0))
    piece.paste(image, (0, 0), mask)

    return piece


def create_background_with_hole(image: Image.Image, mask: Image.Image) -> Image.Image:
    """
    퍼즐 조각이 빠진 배경 생성

    Args:
        image: 원본 이미지
        mask: 마스크 이미지

    Returns:
        퍼즐 조각이 빠진 배경 (RGBA)
    """
    # RGBA로 변환
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # 마스크 크기 맞추기
    if image.size != mask.size:
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)

    # 마스크 반전 (구멍 만들기)
    inverted_mask = Image.eval(mask, lambda x: 255 - x)

    # 배경 생성
    background = Image.new('RGBA', image.size, (0, 0, 0, 0))
    background.paste(image, (0, 0), inverted_mask)

    return background


# 모양별 마스크 생성 함수 매핑
SHAPE_FUNCTIONS = {
    "하트": create_heart_mask,
    "별": create_star_mask,
    "달": create_moon_mask,
    "클로버": create_clover_mask
}


def get_puzzle_mask(shape: str, size: Tuple[int, int]) -> Image.Image:
    """
    지정된 모양의 퍼즐 마스크 생성

    Args:
        shape: "하트", "별", "달", "클로버"
        size: (width, height)

    Returns:
        마스크 이미지
    """
    func = SHAPE_FUNCTIONS.get(shape)
    if func is None:
        raise ValueError(f"지원하지 않는 모양: {shape}")

    return func(size)
