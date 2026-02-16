# -*- coding: utf-8 -*-
"""
YouTube 업로드 모듈
YouTube Data API v3를 사용한 영상 업로드
예약 업로드: 사용자가 입력한 시간은 한국 시간(KST)으로 간주하고, API에는 UTC로 변환해 전달합니다.
"""
import os
import pickle
import random
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# 한국 표준시 (KST = UTC+9). 예약 시간 입력은 이 시간대로 해석함.
KST = timezone(timedelta(hours=9))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

import config

# Resumable 업로드: 청크 크기는 256KB(262144)의 배수. 2097152(2MB) 오류 회피를 위해 256KB 사용.
UPLOAD_CHUNK_SIZE = 256 * 1024
# 5MB 이하면 한 번에 업로드(오류 방지)
SIMPLE_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
# YouTube 썸네일 최대 2MB 초과 시 자동 압축
THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# OAuth 2.0 스코프 (업로드 권한)
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
TOKEN_FILE = config.BASE_DIR / 'token.pickle'


def reset_youtube_auth() -> None:
    """저장된 YouTube 인증 정보 삭제 (채널 변경 시 사용)"""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except OSError:
            pass


def authenticate_youtube() -> Credentials:
    """
    YouTube API 인증 (저장된 토큰 또는 로컬 서버 OAuth 플로우)

    Returns:
        Google Credentials 객체
    """
    secrets_path = str(config.YOUTUBE_CLIENT_SECRETS)
    if not os.path.exists(secrets_path):
        raise FileNotFoundError(
            f"client_secrets.json을 찾을 수 없습니다. 프로젝트 루트에 {secrets_path} 파일을 넣어주세요. "
            "Google Cloud Console → API 및 서비스 → 사용자 인증 정보 → OAuth 클라이언트 ID에서 JSON 다운로드 후 client_secrets.json으로 저장하세요."
        )

    creds = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                secrets_path,
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    thumbnail_path: Optional[str] = None,
    privacy: str = "public",
    scheduled_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    YouTube에 영상 업로드

    Args:
        video_path: 영상 파일 경로
        title: 제목
        description: 설명
        tags: 해시태그 리스트 (# 포함 가능, API 전송 시 제거)
        thumbnail_path: 썸네일 이미지 경로
        privacy: "public", "private", "unlisted"
        scheduled_time: 예약 업로드 시간

    Returns:
        {"success": True/False, "video_id": "...", "url": "...", "error": "..."}
    """
    print("📤 YouTube 업로드 시작...")
    print(f"  - 제목: {title}")
    print(f"  - 공개: {privacy}")

    video_path = str(video_path) if video_path else None
    thumbnail_path = os.path.abspath(str(thumbnail_path)) if thumbnail_path else None
    tags = tags or []

    if not video_path or not os.path.exists(video_path):
        return {'success': False, 'error': f'영상 파일을 찾을 수 없습니다: {video_path}'}
    if not (title or '').strip():
        return {'success': False, 'error': '제목을 입력해주세요.'}

    try:
        creds = authenticate_youtube()
        youtube = build('youtube', 'v3', credentials=creds)

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': [tag.replace('#', '').strip() for tag in tags if tag],
                'categoryId': '22',  # People & Blogs
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False,
            }
        }

        if scheduled_time:
            # 사용자 입력은 한국 시간(KST). YouTube API는 UTC만 받으므로 변환.
            if scheduled_time.tzinfo is None:
                kst_dt = scheduled_time.replace(tzinfo=KST)
                utc_dt = kst_dt.astimezone(timezone.utc)
            else:
                utc_dt = scheduled_time.astimezone(timezone.utc)
            # YouTube API: publishAt은 반드시 ISO 8601 형식, 예약 시 privacyStatus는 'private' 필수
            publish_at_str = utc_dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
            body['status']['publishAt'] = publish_at_str
            body['status']['privacyStatus'] = 'private'
            print(f"  - 예약 시간 (한국): {scheduled_time}")
            print(f"  - 예약 시간 (UTC 전송): {publish_at_str}")

        print("  - 영상 업로드 중...")
        file_size = os.path.getsize(video_path)
        use_simple = file_size <= SIMPLE_UPLOAD_MAX_BYTES
        if use_simple:
            media = MediaFileUpload(
                video_path,
                resumable=False,
                mimetype='video/mp4'
            )
            response = youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            ).execute()
        else:
            media = MediaFileUpload(
                video_path,
                chunksize=UPLOAD_CHUNK_SIZE,
                resumable=True,
                mimetype='video/mp4'
            )
            request = youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            response = None
            retry = 0
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if response is not None and 'id' in response:
                        break
                except HttpError as e:
                    if e.resp.status in RETRIABLE_STATUS_CODES and retry < MAX_RETRIES:
                        retry += 1
                        sleep_sec = random.random() * (2 ** retry)
                        print(f"  ⚠ 재시도 {retry}/{MAX_RETRIES} ({sleep_sec:.1f}초 후)...")
                        time.sleep(sleep_sec)
                    else:
                        raise
            if not response or 'id' not in response:
                return {'success': False, 'error': '영상 업로드 응답이 올바르지 않습니다.'}
        video_id = response['id']
        print(f"  ✓ 영상 업로드 완료: {video_id}")

        thumbnail_error = None
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                print("  - 썸네일 업로드 중...")
                thumb_ext = os.path.splitext(thumbnail_path)[1].lower()
                thumb_mime = "image/jpeg" if thumb_ext in (".jpg", ".jpeg") else "image/png"
                use_path = thumbnail_path
                use_mime = thumb_mime
                # YouTube 썸네일 최대 2MB. 초과 시 JPEG로 압축
                if os.path.getsize(thumbnail_path) > THUMBNAIL_MAX_BYTES:
                    try:
                        from PIL import Image
                        img = Image.open(thumbnail_path).convert("RGB")
                        tmp_path = os.path.join(os.path.dirname(thumbnail_path), "yt_thumb_temp.jpg")
                        for q in [85, 75, 65, 55]:
                            img.save(tmp_path, "JPEG", quality=q, optimize=True)
                            if os.path.getsize(tmp_path) <= THUMBNAIL_MAX_BYTES:
                                break
                        if os.path.getsize(tmp_path) <= THUMBNAIL_MAX_BYTES:
                            use_path = tmp_path
                            use_mime = "image/jpeg"
                        else:
                            # 해상도 줄여서 다시 시도
                            w, h = img.size
                            img_small = img.resize((w // 2, h // 2), Image.Resampling.LANCZOS)
                            img_small.save(tmp_path, "JPEG", quality=80, optimize=True)
                            if os.path.getsize(tmp_path) <= THUMBNAIL_MAX_BYTES:
                                use_path = tmp_path
                                use_mime = "image/jpeg"
                        if use_path == tmp_path and os.path.exists(tmp_path):
                            pass  # 업로드 후 삭제
                    except Exception as conv_err:
                        print(f"  ⚠ 썸네일 압축 실패, 원본 전송 시도: {conv_err}")
                thumb_media = MediaFileUpload(
                    use_path,
                    mimetype=use_mime,
                    resumable=False,
                )
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=thumb_media
                ).execute()
                if use_path != thumbnail_path and os.path.exists(use_path):
                    try:
                        os.remove(use_path)
                    except Exception:
                        pass
                print("  ✓ 썸네일 업로드 완료")
            except Exception as thumb_err:
                thumbnail_error = str(thumb_err)
                print(f"  ⚠ 썸네일 설정 실패 (영상은 업로드됨): {thumb_err}")

        url = f'https://youtube.com/shorts/{video_id}'
        print(f"✅ 업로드 완료: {url}")

        result = {'success': True, 'video_id': video_id, 'url': url}
        if thumbnail_error:
            result['thumbnail_error'] = thumbnail_error
        return result

    except Exception as e:
        err_msg = str(e)
        print(f"❌ 업로드 실패: {e}")
        if 'access_denied' in err_msg.lower() or '액세스 차단' in err_msg or '403' in err_msg:
            err_msg += " (Google Cloud Console → OAuth 동의 화면 → 테스트 사용자에 이메일 추가 후 다시 시도)"
        return {
            'success': False,
            'error': err_msg
        }


def init_database() -> None:
    """업로드 내역 저장용 SQLite DB 초기화 + 즉시/예약 로그 컬럼 추가"""
    config.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    db_path = config.DATABASE_DIR / 'uploads.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            title TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            url TEXT NOT NULL,
            is_scheduled INTEGER DEFAULT 0,
            scheduled_publish_at TEXT
        )
    ''')
    # 기존 DB에 컬럼 없으면 추가 (마이그레이션)
    try:
        cursor.execute(
            "SELECT is_scheduled FROM uploads LIMIT 1"
        )
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE uploads ADD COLUMN is_scheduled INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE uploads ADD COLUMN scheduled_publish_at TEXT")

    conn.commit()
    conn.close()


def save_upload_record(
    video_id: str,
    title: str,
    upload_time: datetime,
    is_scheduled: bool = False,
    scheduled_publish_at: Optional[datetime] = None
) -> None:
    """업로드 내역 DB 저장 (즉시/예약 구분 및 예약 시각 로그)"""
    db_path = config.DATABASE_DIR / 'uploads.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    url = f'https://youtube.com/shorts/{video_id}'
    scheduled_str = None
    if is_scheduled and scheduled_publish_at:
        # 한국 시간으로 저장 (ISO 형식)
        if scheduled_publish_at.tzinfo is None:
            scheduled_publish_at = scheduled_publish_at.replace(tzinfo=KST)
        scheduled_str = scheduled_publish_at.strftime('%Y-%m-%d %H:%M')

    cursor.execute('''
        INSERT INTO uploads (video_id, title, upload_time, url, is_scheduled, scheduled_publish_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (video_id, title, upload_time, url, 1 if is_scheduled else 0, scheduled_str))

    conn.commit()
    conn.close()
    log_msg = f"✅ DB 저장 완료: {title}"
    if is_scheduled and scheduled_str:
        log_msg += f" (예약 공개: {scheduled_str} KST)"
    print(log_msg)


def get_uploaded_titles() -> set:
    """업로드 완료된 제목 목록 (감성형 타로 '발행 완료' 표시용)."""
    db_path = config.DATABASE_DIR / 'uploads.db'
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT DISTINCT title FROM uploads").fetchall()
        return {row[0].strip() for row in rows if row[0]}
    finally:
        conn.close()


def get_upload_history():
    """업로드 내역 조회 (pandas DataFrame 반환). 즉시/예약 구분·예약 시각 포함."""
    import pandas as pd

    db_path = config.DATABASE_DIR / 'uploads.db'

    if not db_path.exists():
        return pd.DataFrame(columns=[
            'video_id', 'title', 'upload_time', 'url',
            'is_scheduled', 'scheduled_publish_at', 'upload_type_kr'
        ])

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        'SELECT * FROM uploads ORDER BY upload_time DESC',
        conn
    )
    conn.close()

    # 기존 DB에 컬럼이 없을 수 있음
    if 'is_scheduled' not in df.columns:
        df['is_scheduled'] = 0
    if 'scheduled_publish_at' not in df.columns:
        df['scheduled_publish_at'] = None
    df['upload_type_kr'] = df['is_scheduled'].map(lambda x: '예약 업로드' if x else '즉시 업로드')

    return df
