# -*- coding: utf-8 -*-
"""
타로운세 썸네일 후킹 문구 — 궁금 메시지 20개 + 강한 CTA 20개, 순차 사용.
"""
from pathlib import Path
import json

# 궁금·메시지 (20개) — "당신의 운명을 바꿀 카드 골라보세요" 스타일 우선
PHRASES_CURIOUS = [
    "당신의 운명을 바꿀 카드 한 장 골라보세요. 후회 없을 거예요!",
    "오늘 카드가 당신에게 전하는 한 마디, 지금 확인하세요.",
    "한 장의 카드가 알려주는 오늘의 메시지.",
    "카드 한 장이 당신에게 말을 걸어요.",
    "오늘의 카드가 전하는 메시지, 놓치지 마세요.",
    "한 장의 카드가 알려주는 오늘의 길.",
    "카드가 고른 오늘만의 메시지.",
    "오늘 타로가 당신에게 전하는 한 마디.",
    "한 장으로 열어보는 오늘의 메시지.",
    "카드가 말하는 오늘의 운세, 확인해 보세요.",
    "오늘의 카드가 당신에게 건네는 이야기.",
    "한 장의 카드가 알려주는 오늘의 조언.",
    "타로가 고른 오늘의 메시지를 받아가세요.",
    "카드 한 장이 전하는 오늘의 인사이트.",
    "오늘 타로 메시지, 지금 확인하세요.",
    "한 장으로 오늘의 메시지를 열어보세요.",
    "카드가 당신에게 전하는 오늘의 한 마디.",
    "오늘의 카드 메시지, 놓치지 마세요.",
    "한 장의 카드가 알려주는 오늘의 이야기.",
    "타로가 전하는 오늘의 메시지를 확인하세요.",
    "카드 한 장이 말하는 오늘의 운세.",
]

# 강한 CTA (20개)
PHRASES_CTA = [
    "지금 바로, 오늘의 타로 한 장 받아가세요.",
    "30초만에 오늘 운세 확인해 보세요.",
    "지금 확인하세요. 오늘의 타로 한 장.",
    "오늘의 타로, 지금 바로 받아가세요.",
    "30초만에 오늘의 운세를 열어보세요.",
    "지금 바로 확인하세요. 오늘의 카드.",
    "한 장 받아가세요. 오늘의 타로 메시지.",
    "지금 확인! 오늘의 타로 한 장.",
    "30초 만에 오늘 운세 받아가세요.",
    "오늘의 타로 한 장, 지금 확인하세요.",
    "지금 바로 오늘의 카드를 받아가세요.",
    "30초만에 오늘의 메시지를 확인하세요.",
    "한 장으로 오늘 운세, 지금 확인!",
    "지금 받아가세요. 오늘의 타로 메시지.",
    "오늘의 타로, 30초만에 확인하세요.",
    "지금 확인하세요. 오늘의 운세 한 장.",
    "30초 만에 오늘의 타로 받아가세요.",
    "오늘의 카드, 지금 바로 확인!",
    "한 장 받아가세요. 지금 바로.",
    "오늘의 타로 한 장, 30초만에 확인.",
]

ALL_PHRASES = PHRASES_CURIOUS + PHRASES_CTA
TOTAL_PHRASES = len(ALL_PHRASES)


def _index_path() -> Path:
    import config
    return config.OUTPUT_DIR / "thumbnail_phrase_index.json"


def get_next_tarot_thumbnail_phrase() -> str:
    """다음 후킹 문구 반환 (순차). 인덱스는 파일에 저장."""
    path = _index_path()
    idx = 0
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            idx = int(data.get("index", 0)) % TOTAL_PHRASES
        except Exception:
            idx = 0
    phrase = ALL_PHRASES[idx]
    next_idx = (idx + 1) % TOTAL_PHRASES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"index": next_idx}, ensure_ascii=False), encoding="utf-8")
    return phrase


# 아침 타로 썸네일 기본 문구 (GPT 실패 시 폴백)
MORNING_DEFAULT_PHRASES = [
    "오늘 중요한 일정이 있나요?\n이 카드 먼저 보고 가세요",
    "오늘 실수하고 싶지 않다면\n지금 확인하세요",
    "오늘 결정을 앞두고 있나요?\n선택 전에 꼭 보세요",
    "오늘 큰 일이 있나요?\n먼저 확인하고 움직이세요",
    "오늘 놓치고 싶지 않다면\n지금 이 카드를 보세요",
]


def get_morning_tarot_hook_phrase() -> str:
    """
    아침 타로 썸네일용 후킹 문구 (2줄, 호기심·행동 유도 스타일).
    GPT로 생성, 실패 시 기본 문구 랜덤 반환.
    """
    import random
    import config
    key = getattr(config, "OPENAI_API_KEY", None) or ""
    if not key or "your_" in key.lower():
        return random.choice(MORNING_DEFAULT_PHRASES)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You generate Korean YouTube Shorts thumbnail hook text for a MORNING tarot short. Output ONLY the final text, no quotes or explanation. 2 lines max. Each line under 28 Korean characters."
                },
                {
                    "role": "user",
                    "content": """Create a thumbnail hook for a morning tarot short.

STYLE:
- Personally relevant
- Imply skipping may cause regret or missed opportunity
- Urgency without exaggeration
- No guaranteed outcomes
- Calm but compelling
- No emojis, no dates

STRUCTURE:
- Line 1: Situation-based question or condition
- Line 2: Action-inducing instruction or warning

EXAMPLES (match structure, do not copy):
오늘 중요한 일정이 있나요?
이 카드 먼저 보고 가세요

오늘 실수하고 싶지 않다면
지금 확인하세요

Focus on "today", make viewer feel they must check before acting. Output format:
Line 1
Line 2"""
                }
            ],
            max_tokens=80,
            temperature=0.85,
        )
        text = (resp.choices[0].message.content or "").strip()
        text = text.strip('"\'').strip()
        if text and len(text) >= 5 and "\n" in text:
            return text
        if text and len(text) >= 5:
            # 한 줄이면 줄바꿈 14자 근처에 삽입
            if len(text) > 14:
                return text[:14] + "\n" + text[14:]
            return text
    except Exception:
        pass
    return random.choice(MORNING_DEFAULT_PHRASES)


def get_hook_phrase_with_gpt() -> str:
    """
    GPT로 '클릭할 수 밖에 없는' 후킹성 문구 생성.
    아침 타로 스타일(2줄) 우선, 실패 시 순차 문구 사용.
    """
    return get_morning_tarot_hook_phrase()
