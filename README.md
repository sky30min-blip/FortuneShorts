# 🔮 오늘의 운세 Shorts - 자동 생성 & 업로드

매일 자동으로 **운세 유튜브 Shorts**를 생성하고 업로드하는 Streamlit 웹 앱입니다.

## 📁 프로젝트 구조

```
FortuneShorts/
├── app.py                    # Streamlit 메인 앱
├── config.py                 # 설정 (한글 인코딩, 경로, API)
├── requirements.txt          # 패키지 목록
├── .env.example              # 환경변수 예시
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml           # Streamlit 한글/테마 설정
├── modules/
│   ├── __init__.py
│   ├── tarot_video_generator.py  # 타로 영상 생성 (9장 카드, 셔플)
│   ├── tarot_deck.py, tarot_meanings.py, shuffle_styles.py
│   ├── metadata_generator.py     # 제목/설명/해시태그 (GPT)
│   ├── thumbnail_creator.py     # 썸네일 생성
│   └── youtube_uploader.py      # YouTube API 업로드
├── assets/
│   ├── fonts/
│   │   └── NanumGothicBold.ttf   # 한글 폰트 (필수)
│   ├── music/
│   │   └── cheerful.mp3          # 배경음악 (선택)
│   └── templates/
│       ├── space.jpg             # 우주 배경
│       ├── nature.jpg            # 자연 배경
│       ├── city.jpg              # 도시 배경
│       └── fantasy.jpg           # 판타지 배경
├── output/                    # 생성된 영상
├── thumbnails/                # 생성된 썸네일
└── database/
    └── uploads.db             # 업로드 내역 (SQLite)
```

## ⚙️ 설정

### 1. 환경

- **Python 3.8+**
- 가상환경 권장

```bash
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### 2. 환경변수

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux
```

`.env` 파일을 열어 다음을 입력하세요.

```
OPENAI_API_KEY=sk-your-openai-api-key-here
YOUTUBE_CLIENT_SECRETS_PATH=client_secrets.json
```

### 3. 한글 폰트 (필수)

영상/썸네일 한글 표시를 위해 **나눔고딕 Bold**를 사용합니다.

**수동 설치**

1. [네이버 나눔글꼴](https://hangeul.naver.com/font)에서 나눔고딕 다운로드
2. `NanumGothicBold.ttf`를 `assets/fonts/` 폴더에 복사

**PowerShell로 다운로드 (Windows)**

```powershell
Invoke-WebRequest -Uri "https://github.com/naver/nanumfont/raw/master/fonts/NanumGothicBold.ttf" -OutFile "assets/fonts/NanumGothicBold.ttf"
```

### 4. 배경 이미지

`assets/templates/` 폴더에 다음 파일을 넣어주세요.

| 파일명      | 테마   |
|------------|--------|
| space.jpg  | 우주   |
| nature.jpg | 자연   |
| city.jpg   | 도시   |
| fantasy.jpg| 판타지 |

해상도는 1080x1920(세로)에 맞추거나, 비율이 비슷한 이미지를 사용하면 됩니다.

### 5. 배경음악 (선택)

`assets/music/cheerful.mp3`를 넣으면 영상에 배경음이 들어갑니다. 없으면 무음으로 생성됩니다.

### 6. YouTube API

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 후 **YouTube Data API v3** 사용 설정
3. **사용자 인증 정보** → **OAuth 클라이언트 ID** 만들기
4. 애플리케이션 유형: **데스크톱 앱**
5. JSON 다운로드 후 파일명을 `client_secrets.json`으로 변경
6. 프로젝트 루트(`FortuneShorts` 폴더)에 저장

## 🚀 실행 방법

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 이 열립니다.

## 📖 사용 흐름

1. **타로 영상 생성**  
   `타로덱_다운로드.bat`으로 덱 다운로드 후, 배경 테마·운세 종류 선택 → **타로 영상 생성하기** 클릭.
2. **미리보기 & 승인**  
   재생해 본 뒤 **마음에 들어요!** 로 승인.
3. **메타데이터**  
   제목·설명·해시태그를 자동 생성 후 필요하면 수정하고 **메타데이터 저장**.
4. **썸네일**  
   자동 생성된 3장 중 하나 선택 (또는 직접 업로드).
5. **업로드**  
   공개 설정·예약 여부 확인 후 **유튜브에 업로드**.

사이드바에서 **OpenAI API Key**를 입력하면 제목/운세 문구 자동 생성이 동작하고, **YouTube 인증** 버튼으로 한 번 로그인하면 이후 업로드가 가능합니다.

## ✅ 테스트 체크리스트

- [ ] 한글이 콘솔/로그에 정상 표시
- [ ] 이미지/영상에 한글 폰트 정상 렌더링
- [ ] 타로 덱 다운로드 (타로덱_다운로드.bat)
- [ ] 9장 카드 + 셔플 + 의미 표시
- [ ] 메타데이터 한국어 자연스러움
- [ ] 썸네일 한글 표시
- [ ] YouTube 업로드 성공
- [ ] 예약 업로드 동작
- [ ] 업로드 내역 DB 저장/조회

## 🔜 예정

- **별자리운세 숏츠**, **띠별 운세 숏츠** 탭 추가 예정

## ⚠️ 주의사항

- **필수 파일**: `NanumGothicBold.ttf`, `client_secrets.json`, `.env`, 타로 덱(타로덱_다운로드.bat)
- **OpenAI**: 사용량에 따라 요금 발생
- **YouTube Data API**: 일일 할당량 약 10,000 units (업로드 1회 약 1,600 units)

## 📄 라이선스

이 프로젝트는 오늘의 운세 Shorts 제작용으로, 코드·자동화는 이 저장소에서 관리합니다.
