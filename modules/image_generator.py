# -*- coding: utf-8 -*-
"""
배경 이미지 자동 생성 모듈
OpenAI DALL-E 3 API로 테마별 배경 이미지 생성 (매번 다른 이미지)
"""
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

# 테마별 기본 프롬프트 (세로 배경, 9:16)
THEME_PROMPTS = {
    "우주": "Vertical wallpaper, outer space theme, stars, nebula, deep blue and purple cosmos, "
            "no text, no people, high quality, serene, 9:16 aspect ratio",
    "자연": "Vertical wallpaper, nature theme, beautiful landscape, green forest or mountains, "
            "sky and clouds, no text, no people, peaceful, high quality, 9:16 aspect ratio",
    "도시": "Vertical wallpaper, city theme, modern urban skyline at night, city lights, "
            "no text, no people, atmospheric, high quality, 9:16 aspect ratio",
    "판타지": "Vertical wallpaper, fantasy theme, magical landscape, soft lighting, "
              "ethereal atmosphere, no text, no people, dreamy, high quality, 9:16 aspect ratio",
}

# 매번 다른 느낌을 주기 위한 추가 표현 (프롬프트에 랜덤으로 붙임)
VARIATION_PHRASES = [
    "at golden hour, warm lighting",
    "at blue hour, twilight mood",
    "with soft mist, dreamy atmosphere",
    "vibrant colors, vivid and unique",
    "minimalist and clean style",
    "with subtle aurora or light rays",
    "dramatic clouds and sky",
    "serene and calming, one of a kind",
    "with distant mountains or horizon",
    "soft gradient sky, peaceful",
]


def _get_openai_client():
    """OpenAI 클라이언트 반환 (config 또는 metadata_generator와 동일한 키 사용)"""
    try:
        from openai import OpenAI
        key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        return OpenAI(api_key=key)
    except Exception:
        return None


def generate_background_image(theme: str) -> Optional[Path]:
    """
    DALL-E 3로 테마별 배경 이미지 생성 후 저장 (매번 다른 이미지)

    - 프롬프트에 랜덤 표현을 붙여 매번 다른 결과 생성
    - 파일명에 타임스탬프를 넣어 기존 파일 덮어쓰지 않음

    Args:
        theme: "우주", "자연", "도시", "판타지" 중 하나

    Returns:
        저장된 이미지 경로 (실패 시 None)
    """
    if theme not in THEME_PROMPTS:
        print(f"⚠️ 알 수 없는 테마: {theme}")
        return None

    client = _get_openai_client()
    if not client:
        print("⚠️ OpenAI API 키가 없습니다. .env에 OPENAI_API_KEY를 설정하세요.")
        return None

    config.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    # 매번 다른 파일명 (타임스탬프 + 랜덤)
    theme_slug = {"우주": "space", "자연": "nature", "도시": "city", "판타지": "fantasy"}[theme]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    r = random.randint(100, 999)
    filename = f"{theme_slug}_{ts}_{r}.jpg"
    out_path = config.TEMPLATES_DIR / filename

    # 매번 다른 이미지를 위해 기본 프롬프트 + 랜덤 표현
    base_prompt = THEME_PROMPTS[theme]
    extra = random.choice(VARIATION_PHRASES)
    prompt = f"{base_prompt}, {extra}"

    try:
        print(f"🖼️ 배경 이미지 생성 중: {theme} (매번 다른 이미지)...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792",
            n=1,
            quality="standard",
        )
        image_url = response.data[0].url
        if not image_url:
            b64 = getattr(response.data[0], "b64_json", None)
            if b64:
                import base64
                from PIL import Image
                import io
                data = base64.b64decode(b64)
                img = Image.open(io.BytesIO(data)).convert("RGB")
                img.save(out_path, "JPEG", quality=95)
                print(f"  ✓ 저장: {out_path}")
                return out_path
            return None

        import tempfile
        import urllib.request
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            urllib.request.urlretrieve(image_url, tmp.name)
            img = Image.open(tmp.name).convert("RGB")
            img.save(out_path, "JPEG", quality=95)
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        print(f"  ✓ 저장: {out_path}")
        return out_path

    except Exception as e:
        print(f"❌ 배경 이미지 생성 실패: {e}")
        return None
