# -*- coding: utf-8 -*-
"""
메타데이터 생성 모듈
OpenAI GPT를 사용한 제목/설명/해시태그 자동 생성
"""
import json
from datetime import datetime
from typing import List, Optional

import config

# OpenAI 클라이언트 (API 키는 config 또는 런타임에 설정)
_openai_client = None


def _get_client():
    """OpenAI 클라이언트 반환 (지연 초기화)"""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=config.OPENAI_API_KEY or "")
        except Exception:
            pass
    return _openai_client


def set_openai_api_key(api_key: str) -> None:
    """앱에서 API 키를 설정할 때 호출 (세션용)"""
    global _openai_client
    if api_key:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=api_key)
        except Exception:
            _openai_client = None
    else:
        _openai_client = None


def generate_titles(
    fortune_type: str,
    date: Optional[str] = None
) -> List[str]:
    """
    유튜브 쇼츠 제목 3가지 생성

    Args:
        fortune_type: "금전운", "애정운", "건강운", "총운"
        date: "2월 10일" (None이면 오늘 날짜)

    Returns:
        제목 3개 리스트
    """
    if date is None:
        date = datetime.now().strftime("%m월 %d일")

    prompt = f"""
유튜브 쇼츠 제목을 3가지 생성해줘.

조건:
- 날짜: {date}
- 운세 종류: {fortune_type}
- 길이: 45-50자
- 이모지 1-2개 포함
- 클릭 유도 문구 포함
- 호기심 자극하는 스타일

스타일 예시:
1. 🔮 {date} 오늘의 {fortune_type} | 일시정지 필수!
2. 💰 대박 예감? {date} {fortune_type} 확인하세요
3. ❤️ {date} {fortune_type} | 90% 안 믿다가 소름...

JSON 형식으로 반환:
{{"titles": ["제목1", "제목2", "제목3"]}}
"""

    client = _get_client()
    if not client or not config.OPENAI_API_KEY:
        return [
            f"🔮 {date} 오늘의 {fortune_type} | 일시정지하고 확인하세요!",
            f"💫 {date} {fortune_type} | 당신의 운세는?",
            f"✨ {date} {fortune_type} | 퍼즐 맞추고 확인!"
        ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.9
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("titles", [
            f"🔮 {date} 오늘의 {fortune_type} | 일시정지하고 확인하세요!",
            f"💫 {date} {fortune_type} | 당신의 운세는?",
            f"✨ {date} {fortune_type} | 퍼즐 맞추고 확인!"
        ])
    except Exception as e:
        print(f"❌ 제목 생성 실패: {e}")
        return [
            f"🔮 {date} 오늘의 {fortune_type} | 일시정지하고 확인하세요!",
            f"💫 {date} {fortune_type} | 당신의 운세는?",
            f"✨ {date} {fortune_type} | 퍼즐 맞추고 확인!"
        ]


def generate_description(
    fortune_type: str,
    date: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> str:
    """
    유튜브 설명란 자동 생성

    Args:
        fortune_type: 운세 종류
        date: 날짜
        keywords: 행운 키워드 리스트

    Returns:
        설명란 텍스트
    """
    if date is None:
        date = datetime.now().strftime("%m월 %d일")

    if keywords is None:
        keywords = ["행운", "성공", "기회", "만남", "돈"]

    description = f"""🔮 {date} 오늘의 {fortune_type}를 확인하세요!

👆 일시정지해서 당신의 운세를 확인하세요!
놓치셨다면? 다시 돌려보세요! 😊

💬 자세한 운세가 궁금하시다면?
댓글에 "년생 + 월 + 운세" 입력해주세요!
예) 95년생 2월 운세 
→ 맞춤 운세를 댓글로 알려드립니다!

📌 오늘의 행운 키워드
{', '.join(keywords[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━

👍 이 영상이 도움이 되셨다면? 
   → 좋아요 버튼을 눌러주세요!

🔔 매일 오전 6시 새로운 운세!
   → 구독하고 알림 설정하세요!

💬 당신의 경험을 공유해주세요!
   → 댓글로 소통해요!

📢 공유하기
   → 친구에게도 행운을 나눠주세요!

━━━━━━━━━━━━━━━━━━━━━━━━━

🏷️ 태그
#오늘의운세 #타로 #신년운세 #2026운세 #Shorts
#운세 #사주 #별자리 #{fortune_type} #행운
#점 #fortune #tarot #horoscope

📺 더 많은 운세 콘텐츠
→ 매일 새로운 운세를 만나보세요!
→ 커뮤니티에서 실시간 소통!

⚠️ 본 콘텐츠는 재미와 힐링을 위한 것으로,
   중요한 결정은 신중히 하시기 바랍니다.

───────────────────────────
🔮 운세 Shorts 자동 생성기
"""
    return description


def generate_hashtags(fortune_type: str, count: int = 15) -> List[str]:
    """
    해시태그 자동 생성

    Args:
        fortune_type: 운세 종류
        count: 생성할 태그 개수

    Returns:
        해시태그 리스트
    """
    base_tags = [
        "#오늘의운세", "#Shorts", "#운세", "#타로", "#점"
    ]

    type_tags = {
        "금전운": ["#금전운", "#재물운", "#로또", "#대박", "#돈", "#재테크"],
        "애정운": ["#애정운", "#연애운", "#사랑", "#인연", "#솔로탈출", "#커플"],
        "건강운": ["#건강운", "#건강", "#힐링", "#웰빙", "#활력", "#에너지"],
        "총운": ["#신년운세", "#2026운세", "#행운", "#fortune", "#lucky"]
    }

    today = datetime.now()
    date_tags = [
        f"#{today.month}월운세",
        f"#{today.year}운세",
        "#오늘"
    ]

    general_tags = [
        "#사주", "#별자리", "#점성술", "#신년", "#새해운세",
        "#tarot", "#horoscope", "#zodiac", "#astrology"
    ]

    all_tags = (
        base_tags
        + type_tags.get(fortune_type, [])
        + date_tags
        + general_tags
    )
    unique_tags = list(dict.fromkeys(all_tags))[:count]

    return unique_tags


def generate_fortune_text(fortune_type: str) -> str:
    """
    운세 텍스트 생성 (영상에 표시될 짧은 문구)

    Args:
        fortune_type: 운세 종류

    Returns:
        운세 문구
    """
    prompt = f"""
{fortune_type}에 대한 짧은 운세 문구를 생성해줘.

조건:
- 15자 이내
- 긍정적이고 희망적인 톤
- 구체적인 조언보다는 키워드 중심

예시:
- "금전운: 대박의 기운!"
- "애정운: 운명적 만남"
- "건강운: 활력 넘치는 하루"

JSON 형식:
{{"fortune": "운세 문구"}}
"""

    client = _get_client()
    if not client or not config.OPENAI_API_KEY:
        return f"{fortune_type}: 행운이 함께해요!"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("fortune", f"{fortune_type}: 좋은 일이 생길 거예요!")
    except Exception as e:
        print(f"❌ 운세 생성 실패: {e}")
        return f"{fortune_type}: 행운이 함께해요!"
