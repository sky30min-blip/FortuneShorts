# -*- coding: utf-8 -*-
"""
타로 카드 의미 (Rider-Waite 기준)
card_index 0~77 → 카드명, 짧은 의미
"""
from typing import TypedDict


class CardInfo(TypedDict):
    name: str
    meaning: str


# Rider-Waite 78장: index → (카드명, 짧은 의미)
CARDS: dict[int, CardInfo] = {
    # Major Arcana 0-21
    0: {"name": "더 풀", "meaning": "새로운 시작, 자유로운 선택"},
    1: {"name": "매지션", "meaning": "의지력, 창조적 에너지"},
    2: {"name": "여사제", "meaning": "직관, 내면의 지혜"},
    3: {"name": "여황제", "meaning": "풍요, 사랑, 풍성함"},
    4: {"name": "황제", "meaning": "안정, 권위, 구조"},
    5: {"name": "교황", "meaning": "전통, 지혜, 가르침"},
    6: {"name": "연인", "meaning": "사랑, 선택, 조화"},
    7: {"name": "전차", "meaning": "결단, 승리, 의지"},
    8: {"name": "힘", "meaning": "용기, 인내, 내적 힘"},
    9: {"name": "은둔자", "meaning": "성찰, 지혜, 고독"},
    10: {"name": "운명의 수레바퀴", "meaning": "순환, 변화, 기회"},
    11: {"name": "정의", "meaning": "공정함, 균형, 진실"},
    12: {"name": "매달린 사람", "meaning": "포기, 새로운 시각"},
    13: {"name": "죽음", "meaning": "변화, 종말과 새로운 시작"},
    14: {"name": "절제", "meaning": "조화, 인내, 균형"},
    15: {"name": "악마", "meaning": "유혹, 집착, 해방"},
    16: {"name": "탑", "meaning": "파괴, 깨달음, 급격한 변화"},
    17: {"name": "별", "meaning": "희망, 영감, 치유"},
    18: {"name": "달", "meaning": "직관, 불안, 잠재의식"},
    19: {"name": "태양", "meaning": "행복, 성공, 낙관"},
    20: {"name": "심판", "meaning": "부활, 깨달음, 새로운 단계"},
    21: {"name": "월드", "meaning": "완성, 성취, 통합"},
    # Wands 22-35
    22: {"name": "완드 에이스", "meaning": "새로운 도전, 영감"},
    23: {"name": "완드 2", "meaning": "계획, 결정 고민"},
    24: {"name": "완드 3", "meaning": "확장, 협력, 미래"},
    25: {"name": "완드 4", "meaning": "축하, 안정, 휴식"},
    26: {"name": "완드 5", "meaning": "경쟁, 갈등, 도전"},
    27: {"name": "완드 6", "meaning": "승리, 인정, 자신감"},
    28: {"name": "완드 7", "meaning": "방어, 인내, 극복"},
    29: {"name": "완드 8", "meaning": "신속함, 움직임, 변화"},
    30: {"name": "완드 9", "meaning": "근본적인 두려움"},
    31: {"name": "완드 10", "meaning": "부담, 책임, 완수"},
    32: {"name": "완드 페이지", "meaning": "탐구, 호기심, 소식"},
    33: {"name": "완드 나이트", "meaning": "에너지, 모험, 변화"},
    34: {"name": "완드 퀸", "meaning": "리더십, 독립, 자신감"},
    35: {"name": "완드 킹", "meaning": "비전, 기업가 정신"},
    # Cups 36-49
    36: {"name": "컵 에이스", "meaning": "새로운 사랑, 감정의 시작"},
    37: {"name": "컵 2", "meaning": "파트너십, 조화"},
    38: {"name": "컵 3", "meaning": "축하, 우정, 기쁨"},
    39: {"name": "컵 4", "meaning": "성찰, 불만, 선택"},
    40: {"name": "컵 5", "meaning": "상실, 슬픔, 극복"},
    41: {"name": "컵 6", "meaning": "추억, 과거, 순수함"},
    42: {"name": "컵 7", "meaning": "선택, 환상, 꿈"},
    43: {"name": "컵 8", "meaning": "이동, 변화, 새로운 길"},
    44: {"name": "컵 9", "meaning": "만족, 풍요, 행복"},
    45: {"name": "컵 10", "meaning": "가족, 조화, 완성"},
    46: {"name": "컵 페이지", "meaning": "창의성, 직관, 소식"},
    47: {"name": "컵 나이트", "meaning": "로맨스, 초대, 감정"},
    48: {"name": "컵 퀸", "meaning": "공감, 치유, 감성"},
    49: {"name": "컵 킹", "meaning": "감정적 균형, 지도력"},
    # Swords 50-63
    50: {"name": "소드 에이스", "meaning": "깨달음, 진실, 돌파"},
    51: {"name": "소드 2", "meaning": "결정 불가, 교착"},
    52: {"name": "소드 3", "meaning": "슬픔, 상처, 회복"},
    53: {"name": "소드 4", "meaning": "휴식, 회복, 침묵"},
    54: {"name": "소드 5", "meaning": "갈등, 승리와 패배"},
    55: {"name": "소드 6", "meaning": "이동, 변화, 극복"},
    56: {"name": "소드 7", "meaning": "전략, 회피, 교활함"},
    57: {"name": "소드 8", "meaning": "제한, 포위, 인내"},
    58: {"name": "소드 9", "meaning": "불안, 두려움, 고민"},
    59: {"name": "소드 10", "meaning": "종말, 새로운 시작"},
    60: {"name": "소드 페이지", "meaning": "새로운 아이디어, 호기심"},
    61: {"name": "소드 나이트", "meaning": "행동, 돌진, 변화"},
    62: {"name": "소드 퀸", "meaning": "독립, 명확함, 판단"},
    63: {"name": "소드 킹", "meaning": "권위, 진실, 결단"},
    # Pentacles 64-77
    64: {"name": "펜타클 에이스", "meaning": "재물의 시작, 기회"},
    65: {"name": "펜타클 2", "meaning": "균형, 협상, 선택"},
    66: {"name": "펜타클 3", "meaning": "협력, 숙련, 성장"},
    67: {"name": "펜타클 4", "meaning": "안정, 저장, 보안"},
    68: {"name": "펜타클 5", "meaning": "금전적 어려움, 공유"},
    69: {"name": "펜타클 6", "meaning": "나눔, 협력, 지원"},
    70: {"name": "펜타클 7", "meaning": "인내, 투자, 장기"},
    71: {"name": "펜타클 8", "meaning": "숙련, 노동, 성과"},
    72: {"name": "펜타클 9", "meaning": "풍요, 안정, 성취"},
    73: {"name": "펜타클 10", "meaning": "부, 유산, 완성"},
    74: {"name": "펜타클 페이지", "meaning": "학습, 연구, 잠재력"},
    75: {"name": "펜타클 나이트", "meaning": "근면, 신뢰, 진전"},
    76: {"name": "펜타클 퀸", "meaning": "풍요, 안정, 돌봄"},
    77: {"name": "펜타클 킹", "meaning": "부, 리더십, 안정"},
}


def get_card_pool(fortune_type: str, use_minor_arcana: bool = False) -> list[int]:
    """운세 종류별 카드 풀 (0~77 인덱스). use_minor_arcana=True면 fortune_type별 14장 사용."""
    if use_minor_arcana:
        minor_pools = {
            "건강운": list(range(22, 36)),   # Wands
            "애정운": list(range(36, 50)),   # Cups
            "금전운": list(range(64, 78)),   # Pentacles
            "의사결정": list(range(50, 64)), # Swords
        }
        return minor_pools.get(fortune_type, list(range(22, 36)))
    pools = {
        "총운": list(range(22)),  # 메이저 22장
        "애정운": list(range(36, 50)),  # Cups
        "금전운": list(range(64, 78)),  # Pentacles
        "건강운": list(range(22, 36)),  # Wands
        "morning": list(range(22)),  # 달의서재: 방향과 태도
        "lunch": list(range(22)),  # 달의서재: 활력과 점검
        "evening": list(range(22)),  # 달의서재: 새로운 시작과 몰입
        "방향과 태도": list(range(22)),
        "활력과 점검": list(range(22)),
        "새로운 시작과 몰입": list(range(22)),
        "직장운": list(range(22)),  # 메이저 22장
        "학업운": list(range(22)),
        "인간관계운": list(range(22)),
        "재회·이별운": list(range(22)),
        "재회 및 미련": list(range(22)),
        "썸 & 짝사랑": list(range(22)),
        "관계의 비밀": list(range(22)),
        "운세 및 기회": list(range(22)),
    }
    return pools.get(fortune_type, list(range(22)))


def get_card_info(card_index: int) -> CardInfo:
    """카드 인덱스 → 의미"""
    return CARDS.get(card_index, {"name": "?", "meaning": "?"})
