# -*- coding: utf-8 -*-
"""
YouTube 업로드 모듈
YouTube Data API v3를 사용한 영상 업로드
"""
import os
import pickle
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

# OAuth 2.0 스코프 (업로드 권한)
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
TOKEN_FILE = config.BASE_DIR / 'token.pickle'


def authenticate_youtube() -> Credentials:
    """
    YouTube API 인증 (저장된 토큰 또는 로컬 서버 OAuth 플로우)

    Returns:
        Google Credentials 객체
    """
    creds = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.YOUTUBE_CLIENT_SECRETS),
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
            body['status']['publishAt'] = scheduled_time.isoformat() + 'Z'
            body['status']['privacyStatus'] = 'private'
            print(f"  - 예약 시간: {scheduled_time}")

        print("  - 영상 업로드 중...")
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )

        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = request.execute()
        video_id = response['id']
        print(f"  ✓ 영상 업로드 완료: {video_id}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            print("  - 썸네일 업로드 중...")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("  ✓ 썸네일 업로드 완료")

        url = f'https://youtube.com/shorts/{video_id}'
        print(f"✅ 업로드 완료: {url}")

        return {
            'success': True,
            'video_id': video_id,
            'url': url
        }

    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def init_database() -> None:
    """업로드 내역 저장용 SQLite DB 초기화"""
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
            url TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def save_upload_record(
    video_id: str,
    title: str,
    upload_time: datetime
) -> None:
    """업로드 내역 DB 저장"""
    db_path = config.DATABASE_DIR / 'uploads.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    url = f'https://youtube.com/shorts/{video_id}'

    cursor.execute('''
        INSERT INTO uploads (video_id, title, upload_time, url)
        VALUES (?, ?, ?, ?)
    ''', (video_id, title, upload_time, url))

    conn.commit()
    conn.close()
    print(f"✅ DB 저장 완료: {title}")


def get_upload_history():
    """업로드 내역 조회 (pandas DataFrame 반환)"""
    import pandas as pd

    db_path = config.DATABASE_DIR / 'uploads.db'

    if not db_path.exists():
        return pd.DataFrame(columns=['video_id', 'title', 'upload_time', 'url'])

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        'SELECT * FROM uploads ORDER BY upload_time DESC',
        conn
    )
    conn.close()

    return df
