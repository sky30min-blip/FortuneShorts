# -*- coding: utf-8 -*-
"""
주제 타로(재회 및 미련, 썸&짝사랑, 관계의 비밀, 운세 및 기회) 전용 문구 DB.
썸네일·영상 훅 문구는 이 DB에서 읽는다.
바이럴 감성형 제목: 4테마 80문구 중 미사용 문구만 선택 후 사용 처리.

영상 첫 화면 훅 제목: 20개 중 미사용 1개 랜덤 → 사용 처리. 전부 사용 시 초기화 후 다시 순환.
나중에 제목 추가 가능: add_hook_title(text) 또는 DB에 INSERT.
"""
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import config

# DB에서 읽는 주제 이름 (영상/썸네일 로직에서 사용)
THEME_DB_NAMES = ("재회 및 미련", "썸 & 짝사랑", "관계의 비밀", "운세 및 기회", "테스트")

# 바이럴 감성형 제목으로 쓸 테마 (테스트 제외, 4테마 80문구)
VIRAL_THEME_NAMES = ("재회 및 미련", "썸 & 짝사랑", "관계의 비밀", "운세 및 기회")

_DB_PATH: Path = config.DATABASE_DIR / "theme_phrases.db"

# 영상 첫 화면 훅 제목 (20개). DB에 저장 후 사용/미사용만 관리, 나중에 추가 가능.
HOOK_TITLES: List[str] = [
    "지금 고른 이 카드가 당신의 하루를 바꿉니다",
    "오늘 중요한 일정이 있다면 이 카드부터",
    "한 장의 카드가 오늘 결정을 도와줍니다",
    "오늘 시작 전에 꼭 이 카드를 고르세요",
    "오늘 당신의 선택을 비추는 카드",
    "지금 고른 번호가 오늘의 흐름입니다",
    "오늘 실수하지 않으려면 이 카드",
    "오늘 움직이기 전, 이 카드부터",
    "당신의 하루를 미리 보여주는 카드",
    "오늘 중요한 대화가 있다면 이 선택",
    "지금 고른 카드가 경고를 줍니다",
    "오늘 놓치지 말아야 할 흐름",
    "오늘 운의 방향을 정하는 한 장",
    "오늘의 중심 에너지를 확인하세요",
    "이 카드를 고르면 오늘이 보입니다",
    "오늘 중요한 판단이 있다면 선택하세요",
    "당신의 오늘을 미리 알려주는 카드",
    "오늘 후회하지 않으려면 이 번호",
    "지금 선택이 오늘을 좌우합니다",
    "오늘 하루, 이 카드가 열쇠입니다",
]

# 시드 데이터: 주제명 → 문구 20개
_SEED: dict[str, list[str]] = {
    "재회 및 미련": [
        '"자니?" 밤 11시 이후 온 카톡, 진심일까?',
        "헤어진 지 3개월, 내 프로필 염탐하는 에너지가 있을까?",
        "차단당했는데... 풀릴 가능성은?",
        "나를 잊었을까? 전 애인의 솔직한 현재 일상",
        "우리가 다시 만날 운명인지 알려주는 카드",
        "환승 이별한 그 사람, 지금 행복할까?",
        "먼저 연락하면 답장 올 가능성이 있는 시기",
        "다른 사람이 생겼을까? 그 사람 주변 이성 운세",
        "그 사람이 후회하며 울고 있는 밤의 리딩",
        "우리 이별의 진짜 원인, 나만 몰랐던 진실",
        "술 마시고 전화할까 고민 중인 그의 속마음",
        '"미안해"라고 말하고 싶은데... 그의 자존심 상태',
        "조만간 그 사람에게 연락 올 가능성은?",
        "재결합하면 또 헤어질까? 미래 결과 리딩",
        "그 사람이 내 인스타 스토리를 안 보는 이유",
        "나랑 헤어지고 나서 그 사람이 겪는 불운",
        "조만간 마주칠 가능성이 있는 흐름",
        "전 애인이 아직 보관 중인 내 물건의 의미",
        "나를 대신할 사람을 찾고 있을까?",
        "앞으로 우리는 다시 남남일까 연인일까?",
    ],
    "썸 & 짝사랑": [
        "그 사람 눈에 비친 나의 진짜 첫인상 3가지",
        "썸일까 어장일까? 헷갈리는 행동의 마침표",
        "조만간 고백의 에너지가 있을 사람의 키워드",
        "짝사랑 끝내고 싶다면? 지금 당장 해야 할 행동",
        "조만간 선톡 올 가능성은?",
        "그 사람이 나를 보고 '귀엽다'고 생각한 순간",
        "우리 사이에 방해꾼이 있을까? 주변 인물 운세",
        "지금 톡 보내면 어떤 반응의 에너지인가?",
        "그 사람이 나에게 느끼는 권태로움의 정체",
        "고백 타이밍이 좋을 수 있는 흐름",
        "썸남이 나에게 숨기고 있는 치명적인 비밀",
        "나를 이성으로 볼까, 그냥 편한 친구로 볼까?",
        "그 사람과 연인이 됐을 때의 스킨십 궁합",
        "내 카톡 보고 그 사람이 지은 표정 리딩",
        "짝사랑 상대가 좋아하는 '스타일' 분석 카드",
        "데이트 신청 타이밍과 반응 가능성",
        "그 사람이 나를 차단할까 고민 중일까?",
        "나 말고 다른 썸녀가 있는지 확인하는 법",
        "조만간 우리 관계가 급진전될 사건",
        "그 사람이 먼저 번호 물어보게 만드는 팁",
    ],
    "관계의 비밀": [
        "나 말고 다른 사람도 있을까? (양다리 의심)",
        "절대 말 못 할 비밀... 그가 숨기는 과거",
        "우린 전생에 어떤 인연이었을까?",
        "조금 위험한 질문, 그 사람의 밤의 속마음",
        "지금 그 사람이 당신에게 가장 하고 싶은 욕구",
        "나를 이용하는 걸까, 사랑하는 걸까?",
        "그 사람이 나 몰래 내 친구에게 연락했을까?",
        "우리 관계가 여기까지인 진짜 이유 (소름 주의)",
        "그 사람의 핸드폰 사진첩에 내 사진이 있을까?",
        "나랑 있을 때 딴생각 하는 그 사람의 머릿속",
        "나에게 정떨어졌다고 느낀 결정적 순간",
        "집착일까 사랑일까? 상대의 소유욕 테스트",
        "그 사람에게 의심스러운 에너지가 있을까?",
        "그 사람이 나를 보고 느꼈던 가장 야한 생각",
        "우리 관계가 깊어지지 않는 영적인 이유",
        "나만 모르는 그 사람의 이성 관계 복잡도",
        "그 사람이 나에게 기대하는 경제적 이득",
        "이별을 결심한 그 사람의 현재 진행 상황",
        "나를 만나고 나서 그 사람의 운이 좋아졌을까?",
        "우리가 끝내야 할까, 버텨야 할까? 참고할 점",
    ],
    "운세 및 기회": [
        "조만간 일어날 수 있는 기분 좋은 변화",
        "조만간 들어올 돈복 에너지 확인",
        "나를 시기하는 사람 vs 도와줄 사람 구별법",
        "당신을 짝사랑하고 있는 의외의 인물",
        "이번 달, 당신에게 찾아올 운명적인 귀인의 특징",
        "지금 하는 일, 계속해도 될까? 직업운 리딩",
        "갈등이 풀리는 흐름이 있을까?",
        "이직·합격 에너지 흐름 리딩",
        "갑자기 연락 끊긴 친구의 진심",
        "오늘 밤 꿈에 나올 사람이 전하는 메시지",
        "당신의 매력이 가장 폭발하는 요일",
        "조만간 문서운(계약)이 들어올 가능성",
        "나를 질투하는 사람의 이니셜(자음) 힌트",
        "다음 주에 만날 새로운 인연의 키워드",
        "지금 고민 중인 그 문제, 어떤 방향으로 흐르는지",
        "돈복 에너지가 높은 시기의 참고점",
        "조상님이 전하는 이번 달 조심해야 할 것",
        "오늘 하루, 당신을 행복하게 해줄 컬러",
        "잃어버린 물건(또는 기회)을 찾을 수 있을까?",
        "2026년 상반기 대박 운세 키워드",
    ],
    "테스트": [
        "오늘의 변화 에너지",
        "오늘 연락 가능성",
        "오늘 피해야 할 사람",
    ],
}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """DB 및 테이블 생성, 시드 데이터 삽입(기존 데이터 있으면 건드리지 않음)."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS theme (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS phrase (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (theme_id) REFERENCES theme(id)
            );
            CREATE INDEX IF NOT EXISTS idx_phrase_theme ON phrase(theme_id);
            CREATE TABLE IF NOT EXISTS phrase_used_for_viral (
                phrase_id INTEGER PRIMARY KEY,
                used_at TEXT NOT NULL,
                FOREIGN KEY (phrase_id) REFERENCES phrase(id)
            );
            CREATE TABLE IF NOT EXISTS hook_titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                used_at TEXT NULL
            );
        """)
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM theme")
        if cur.fetchone()[0] == 0:
            for theme_name, phrases in _SEED.items():
                cur = conn.execute("INSERT INTO theme (name) VALUES (?)", (theme_name,))
                theme_id = cur.lastrowid
                for t in phrases:
                    conn.execute("INSERT INTO phrase (theme_id, text) VALUES (?, ?)", (theme_id, t))
            conn.commit()
        else:
            for theme_name, phrases in _SEED.items():
                row = conn.execute("SELECT id FROM theme WHERE name = ?", (theme_name,)).fetchone()
                if not row:
                    cur = conn.execute("INSERT INTO theme (name) VALUES (?)", (theme_name,))
                    theme_id = cur.lastrowid
                    for t in phrases:
                        conn.execute("INSERT INTO phrase (theme_id, text) VALUES (?, ?)", (theme_id, t))
                else:
                    # 기존 테마: 시드 문구로 phrase 텍스트 동기화 (수정된 제목 반영)
                    theme_id = row["id"]
                    db_phrases = conn.execute(
                        "SELECT id, text FROM phrase WHERE theme_id = ? ORDER BY id", (theme_id,)
                    ).fetchall()
                    for i, seed_text in enumerate(phrases):
                        if i < len(db_phrases) and db_phrases[i]["text"] != seed_text:
                            conn.execute(
                                "UPDATE phrase SET text = ? WHERE id = ?",
                                (seed_text, db_phrases[i]["id"]),
                            )
            conn.commit()
        # 훅 제목 시드: 20개 (없을 때만 삽입, 나중에 add_hook_title로 추가 가능)
        cur = conn.execute("SELECT COUNT(*) FROM hook_titles")
        if cur.fetchone()[0] == 0:
            for t in HOOK_TITLES:
                conn.execute("INSERT INTO hook_titles (text, used_at) VALUES (?, NULL)", (t,))
            conn.commit()
        else:
            for t in HOOK_TITLES:
                row = conn.execute("SELECT 1 FROM hook_titles WHERE text = ?", (t,)).fetchone()
                if not row:
                    conn.execute("INSERT INTO hook_titles (text, used_at) VALUES (?, NULL)", (t,))
            conn.commit()
    finally:
        conn.close()


def get_phrases(theme_name: str) -> List[str]:
    """해당 주제의 문구 목록 반환 (순서 유지)."""
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT id FROM theme WHERE name = ?", (theme_name,)).fetchone()
        if not row:
            return []
        theme_id = row["id"]
        rows = conn.execute("SELECT text FROM phrase WHERE theme_id = ? ORDER BY id", (theme_id,)).fetchall()
        return [r["text"] for r in rows]
    finally:
        conn.close()


def get_random_phrase(theme_name: str) -> str:
    """해당 주제 문구 중 랜덤 1개. 없으면 빈 문자열."""
    phrases = get_phrases(theme_name)
    return random.choice(phrases) if phrases else ""


def list_theme_names() -> List[str]:
    """DB에 등록된 주제 이름 목록."""
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT name FROM theme ORDER BY id").fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def get_random_unused_viral_phrase() -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    바이럴 감성형 제목용: 4테마(재회/썸/관계/운세) 80문구 중 아직 사용 안 한 문구 1개 랜덤 선택.
    Returns:
        (theme_name, phrase_text, phrase_id) 또는 (None, None, None) (전부 사용됐을 때)
    """
    init_db()
    conn = _get_conn()
    try:
        placeholders = ",".join("?" * len(VIRAL_THEME_NAMES))
        row = conn.execute(
            f"""
            SELECT p.id AS phrase_id, t.name AS theme_name, p.text AS phrase_text
            FROM phrase p
            JOIN theme t ON p.theme_id = t.id
            WHERE t.name IN ({placeholders})
            AND p.id NOT IN (SELECT phrase_id FROM phrase_used_for_viral)
            ORDER BY RANDOM()
            LIMIT 1
            """,
            VIRAL_THEME_NAMES,
        ).fetchone()
        if row:
            return (row["theme_name"], row["phrase_text"], row["phrase_id"])
        return (None, None, None)
    finally:
        conn.close()


def mark_viral_phrase_used(phrase_id: int) -> None:
    """바이럴 영상에 사용한 문구를 DB에 기록해 재사용하지 않음."""
    init_db()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO phrase_used_for_viral (phrase_id, used_at) VALUES (?, ?)",
            (phrase_id, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_random_unused_hook_title() -> Tuple[str, int]:
    """
    영상 첫 화면용 훅 제목 1개. 미사용 제목 중 랜덤 선택.
    전부 사용했으면 used_at 초기화 후 다시 랜덤 선택.
    Returns:
        (제목 문자열, hook_titles.id)
    """
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, text FROM hook_titles WHERE used_at IS NULL ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if row:
            return (row["text"], row["id"])
        # 전부 사용됨 → 초기화 후 다시 선택
        conn.execute("UPDATE hook_titles SET used_at = NULL")
        conn.commit()
        row = conn.execute(
            "SELECT id, text FROM hook_titles ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if row:
            return (row["text"], row["id"])
        # 테이블 비어 있음: 시드에서 첫 번째 반환
        fallback = HOOK_TITLES[0] if HOOK_TITLES else "오늘의 운세"
        return (fallback, 0)
    finally:
        conn.close()


def mark_hook_title_used(hook_title_id: int) -> None:
    """사용한 훅 제목을 DB에 기록 (다음에 같은 제목이 나오지 않도록)."""
    if hook_title_id <= 0:
        return
    init_db()
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE hook_titles SET used_at = ? WHERE id = ?",
            (datetime.now().isoformat(), hook_title_id),
        )
        conn.commit()
    finally:
        conn.close()


def add_hook_title(text: str) -> None:
    """훅 제목 추가 (나중에 제목 늘릴 때 사용)."""
    if not (text and text.strip()):
        return
    init_db()
    conn = _get_conn()
    try:
        conn.execute("INSERT INTO hook_titles (text, used_at) VALUES (?, NULL)", (text.strip(),))
        conn.commit()
    finally:
        conn.close()
