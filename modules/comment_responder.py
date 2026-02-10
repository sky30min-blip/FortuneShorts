import os
import re
import random
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, List, Dict

from googleapiclient.discovery import build

import config
from modules.youtube_uploader import authenticate_youtube
from modules.metadata_generator import _get_client

DB_PATH = config.DATABASE_DIR / "comment_replies.db"


def _init_reply_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS replied_comments (
            comment_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def _has_replied(comment_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM replied_comments WHERE comment_id = ?", (comment_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def _mark_replied(comment_id: str, video_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO replied_comments (comment_id, video_id, replied_at) VALUES (?, ?, ?)",
        (comment_id, video_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


# "95년/2월/운세" 형식 인식
COMMENT_REGEX = re.compile(
    r"(?P<year>\d{2,4})\s*년\s*/\s*(?P<month>\d{1,2})\s*월\s*/\s*운세",
    re.UNICODE,
)


def _parse_comment(text: str) -> Optional[Tuple[int, int]]:
    """댓글에서 '95년/2월/운세' 같은 패턴을 찾아서 (year, month) 반환."""
    if not text:
        return None
    m = COMMENT_REGEX.search(text)
    if not m:
        return None
    try:
        year = int(m.group("year"))
        if year < 100:
            # 두 자리 연도 보정 (예: 95 -> 1995, 02 -> 2002 정도)
            year += 1900 if year > 30 else 2000
        month = int(m.group("month"))
        if not (1 <= month <= 12):
            return None
        return year, month
    except Exception:
        return None


def generate_personal_fortune(year: int, month: int, fortune_type: str) -> str:
    """개별 댓글용 맞춤 운세 생성 (50~60자, 1~2문장)."""
    client = _get_client()
    prompt = f"""
당신은 유튜브 댓글에 짧게 답글을 다는 운세 상담가입니다.

다음 정보를 참고해서, 50~60자 정도의 짧고 힘이 되는 운세를 한국어로 작성해 주세요.

- 출생년도: {year}년
- 출생월: {month}월
- 운세 종류: {fortune_type} (금전운/애정운/건강운 중 하나)

조건:
- 결과는 1~2문장, 존댓말
- 너무 뻔하지 않고 구체적인 상황이나 조언 1개 포함
- "금전운 : ~~~입니다." 같은 형식으로,
  맨 앞에 운세 종류를 한 번만 명시하고 뒤에는 자연스럽게 이어서 작성
- 길이: 전체 50~60자 정도

JSON 형식만 출력:
{{"reply": "금전운 : 오늘은 ~~ 입니다."}}
"""
    if not client or not config.OPENAI_API_KEY:
        return f"{fortune_type} : 오늘은 작은 선택이 큰 변화를 부를 수 있는 날이에요. 긍정적인 마음으로 움직여 보세요."

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.9,
        )
        import json

        data = json.loads(resp.choices[0].message.content)
        text = (data.get("reply") or "").strip()
        if not text:
            text = f"{fortune_type} : 오늘은 사소한 일에서도 좋은 징조를 발견할 수 있는 날이에요. 열린 마음으로 지켜보세요."
        return text
    except Exception as e:
        print(f"❌ 개인 운세 생성 실패: {e}")
        return f"{fortune_type} : 오늘은 작은 기회라도 놓치지 않는다면 예상 밖의 도움이 들어올 수 있는 날이에요."


def _list_recent_top_level_comments(
    youtube, video_id: str, max_results: int = 100
) -> List[Dict]:
    results: List[Dict] = []
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_results,
        order="time",
        textFormat="plainText",
    )
    response = request.execute()
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        top = snippet.get("topLevelComment", {}).get("snippet", {})
        results.append(
            {
                "thread_id": item.get("id"),
                "comment_id": item.get("snippet", {})
                .get("topLevelComment", {})
                .get("id"),
                "video_id": snippet.get("videoId"),
                "author": top.get("authorDisplayName"),
                "text": top.get("textDisplay") or top.get("textOriginal") or "",
            }
        )
    return results


def reply_to_comments_for_video(video_id: str, max_replies: int = 15) -> None:
    """지정한 영상에 달린 댓글 중 아직 응답하지 않은 것들을 대상으로 최대 max_replies명에게 자동 답글."""
    _init_reply_db()
    creds = authenticate_youtube()
    youtube = build("youtube", "v3", credentials=creds)

    comments = _list_recent_top_level_comments(youtube, video_id, max_results=100)
    candidates = []
    for c in comments:
        if not c["comment_id"] or _has_replied(c["comment_id"]):
            continue
        parsed = _parse_comment(c["text"])
        if not parsed:
            continue  # 형식이 "년/월/운세" 가 아니면 스킵
        year, month = parsed
        fortune_type = random.choice(["금전운", "애정운", "건강운"])
        candidates.append((c, year, month, fortune_type))

    if not candidates:
        print("ℹ️ 응답 대상 댓글이 없습니다.")
        return

    if len(candidates) > max_replies:
        candidates = random.sample(candidates, max_replies)

    for c, year, month, ftype in candidates:
        reply_text = generate_personal_fortune(year, month, ftype)
        try:
            body = {
                "snippet": {
                    "parentId": c["comment_id"],
                    "textOriginal": reply_text,
                }
            }
            youtube.comments().insert(part="snippet", body=body).execute()
            _mark_replied(c["comment_id"], video_id)
            print(f"✅ 댓글 응답 완료: {c['author']} / {c['comment_id']}")
        except Exception as e:
            print(f"❌ 댓글 응답 실패 ({c['comment_id']}): {e}")


if __name__ == "__main__":
    target_video_id = os.getenv("YOUTUBE_REPLY_VIDEO_ID", "").strip()
    if not target_video_id:
        print("⚠️ 환경변수 YOUTUBE_REPLY_VIDEO_ID 가 설정되어 있지 않습니다.")
    else:
        reply_to_comments_for_video(target_video_id, max_replies=15)
