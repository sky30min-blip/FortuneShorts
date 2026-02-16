# -*- coding: utf-8 -*-
"""
운세 Shorts 자동 생성기 - Streamlit 메인 앱
영상 생성 → 미리보기/승인 → 메타데이터 → 썸네일 → YouTube 업로드
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path 맨 앞에 추가 (KeyError: 'config' 방지)
_proj_root = Path(__file__).resolve().parent
if str(_proj_root) not in sys.path:
    sys.path.insert(0, str(_proj_root))

import base64
import random
import streamlit as st
import pandas as pd

try:
    import config
except KeyError:
    # KeyError: 'config' (Streamlit/임포트 이슈) 시 importlib로 재시도
    import importlib.util
    _spec = importlib.util.spec_from_file_location("config", _proj_root / "config.py")
    config = importlib.util.module_from_spec(_spec)
    sys.modules["config"] = config
    _spec.loader.exec_module(config)
from datetime import datetime, time, timezone, timedelta
from pathlib import Path

# tarot_video_generator (MoviePy 포함) — 실제 사용 시에만 로드 (로딩 속도 개선)
# from modules.tarot_video_generator import generate_tarot_video, prepend_thumbnail_to_video
from modules.tarot_thumbnail_phrases import get_morning_tarot_hook_phrase
from modules.metadata_generator import (
    generate_titles,
    generate_description,
    generate_hashtags,
    generate_fortune_text,
    set_openai_api_key,
)
from modules.thumbnail_creator import (
    generate_one_tarot_fortune_thumbnail,
    get_thumbnail_backgrounds_ratio_info,
    hook_phrase_to_lines,
    list_thumbnail_fonts,
)
from modules import theme_phrases_db
from modules.youtube_uploader import (
    upload_video,
    save_upload_record,
    get_upload_history,
    get_uploaded_titles,
    init_database,
)

# 썸네일 미리보기용 캐시 (폰트·배경 base64 — 로딩 속도 개선)
@st.cache_data(ttl=3600)
def _cached_file_b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    try:
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# 썸네일 배경 비율·폰트 목록 캐시 — 버튼 클릭 시 로딩 속도 개선
@st.cache_data(ttl=3600)
def _cached_ratio_info():
    return get_thumbnail_backgrounds_ratio_info()


@st.cache_data(ttl=3600)
def _cached_list_fonts():
    return list_thumbnail_fonts()


# 페이지 설정
st.set_page_config(
    page_title="운세 Shorts 자동 생성기",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'video_path' not in st.session_state:
    st.session_state.video_path = None
if 'approved' not in st.session_state:
    st.session_state.approved = False
if 'metadata' not in st.session_state:
    st.session_state.metadata = {}
if 'selected_thumbnail' not in st.session_state:
    st.session_state.selected_thumbnail = None

# DB 초기화
init_database()

# ========================================
# 사이드바
# ========================================
with st.sidebar:
    st.header("⚙️ 설정")

    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=config.OPENAI_API_KEY or "",
        help="GPT-4o-mini 사용을 위한 API 키"
    )

    if openai_key:
        config.OPENAI_API_KEY = openai_key
        set_openai_api_key(openai_key)

    youtube_auth = st.button("🔐 YouTube 인증", use_container_width=True)
    if youtube_auth:
        try:
            from modules.youtube_uploader import authenticate_youtube
            authenticate_youtube()
            st.success("✅ YouTube 인증 완료!")
        except Exception as e:
            st.error(f"❌ 인증 실패: {e}")

    youtube_channel_change = st.button("🔄 채널 변경", use_container_width=True, help="다른 채널로 업로드하려면 클릭 후 다시 인증하세요.")
    if youtube_channel_change:
        try:
            from modules.youtube_uploader import reset_youtube_auth, authenticate_youtube
            reset_youtube_auth()
            authenticate_youtube()
            st.success("✅ 채널 변경 완료! 새 채널로 인증되었습니다.")
        except Exception as e:
            st.error(f"❌ 채널 변경 실패: {e}")

    st.markdown("---")
    st.subheader("🚀 빠른 설정")
    auto_meta = st.toggle("메타데이터 자동 생성", value=True)
    auto_hashtags = st.toggle("해시태그 자동 생성", value=True)
    auto_thumbnail = st.toggle("썸네일 자동 생성", value=True)

    st.markdown("---")
    with st.expander("📖 사용 가이드"):
        st.markdown("""
        **1단계: 타로 영상 생성**
        - 타로 영상 생성 버튼 클릭 (훅·테마·배경은 자동 랜덤 선택)

        **2단계: 미리보기 & 승인**
        - 생성된 영상 확인
        - 마음에 들면 승인

        **3단계: 메타데이터**
        - 제목/설명/해시태그 확인
        - 필요시 수정

        **4단계: 썸네일**
        - 3가지 중 선택

        **5단계: 업로드**
        - 설정 확인 후 업로드
        """)

# ========================================
# 메인 타이틀
# ========================================
st.title("🔮 운세 Shorts 자동 생성기")
st.markdown("매일 자동으로 운세 영상을 만들고 유튜브에 업로드하세요!")

# 향후: 별자리운세 숏츠, 띠별 운세 숏츠 탭 추가 예정
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🃏 타로운세",
    "📝 메타데이터",
    "🎨 썸네일",
    "📤 업로드",
    "📊 업로드 내역"
])

# ========================================
# 탭 1: 타로운세 영상 생성
# ========================================
with tab1:
    st.subheader("🃏 타로운세 영상 생성")

    use_minor_arcana = False
    minor_fortune_type = None
    time_slot_id = None
    major_theme = None
    hook_duration = 4
    selected_title = None
    VIRAL_THEMES = ("재회 및 미련", "썸 & 짝사랑", "관계의 비밀", "운세 및 기회")

    card_deck_option = st.selectbox(
        "카드 덱",
        ["메이저 아르카나 (22장)", "마이너 아르카나 (56장)"],
        help="메이저: 0~21번. 마이너: 56장 중 건강운(완드)/애정운(컵)/금전운(펜타클)/의사결정(소드) 14장씩 사용.",
    )
    use_minor_arcana = "마이너" in card_deck_option

    if use_minor_arcana:
        minor_fortune_type = st.selectbox(
            "운세 종류 (마이너 56장)",
            ["랜덤", "건강운", "애정운", "금전운", "의사결정"],
            help="랜덤: 건강운/애정운/금전운/의사결정 중 하나 랜덤 선택. 각각 완드/컵/펜타클/소드 14장",
        )
    else:
        # 감성형 타로 4테마: 별도 패널 (바로 보임)
        st.markdown("#### 💜 감성형 타로 (저녁 업로드용)")
        st.caption("재회·썸·관계·운세 4테마 — 선택하면 제목을 고를 수 있습니다.")
        empathy_choice = st.radio(
            "감성형 테마",
            options=["— 선택 안 함 —"] + list(VIRAL_THEMES),
            horizontal=True,
            key="empathy_theme_radio",
            label_visibility="collapsed",
        )
        if empathy_choice != "— 선택 안 함 —":
            major_theme = empathy_choice
            titles = theme_phrases_db.get_phrases(major_theme)
            uploaded = get_uploaded_titles()
            options = [f"{t} ✓ 발행 완료" if t in uploaded else t for t in titles]
            title_idx = st.selectbox(
                "제목 선택 (발행 완료는 업로드한 영상만 표시)",
                range(len(options)),
                format_func=lambda i: options[i],
                key="viral_title_select",
            )
            selected_title = titles[title_idx] if title_idx is not None and titles else None
            hook_duration = 4

        # 기타 테마 (아침 운세 등): 감성형 선택 안 했을 때만 표시
        if major_theme is None:
            st.markdown("---")
            st.markdown("**아침 운세 / 기타 테마**")
            time_slot_option = st.selectbox(
                "테마 (메이저 22장)",
                [
                    "랜덤",
                    "운세",
                    "직장운",
                    "학업운",
                    "인간관계운",
                    "재회·이별운",
                    "테스트",
                ],
                help="운세(오늘 그날의 운세), 직장·학업·인간관계·재회·이별 등.",
            )
            if time_slot_option == "운세":
                time_slot_id = "morning"
            else:
                major_theme = time_slot_option
            hook_duration = st.number_input(
                "훅(첫 화면) 노출 시간 (초)",
                min_value=3,
                max_value=15,
                value=4,
                step=1,
                help="영상 맨 앞 훅+테마 화면이 나오는 시간.",
                key="hook_duration_sec",
            )

    if st.button("🎬 타로 영상 생성하기", type="primary", use_container_width=True):
        from modules.tarot_video_generator import generate_tarot_video

        start_time = datetime.now()
        st.session_state.video_make_start = start_time.strftime("%H:%M:%S")
        st.session_state.video_make_end = None
        st.session_state.video_make_duration_sec = None

        # assets/images에서만 배경 랜덤 선택 (AI 생성 사용 안 함)
        imgs = list(config.IMAGES_DIR.glob("*.png")) + list(config.IMAGES_DIR.glob("*.jpg")) + list(config.IMAGES_DIR.glob("*.jpeg"))
        background_path = str(random.choice(imgs)) if imgs else None

        # assets/music에서 배경음악 랜덤 선택 (mp3, wav, m4a)
        music_path = config.get_random_music_path()

        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"tarot_{timestamp}.mp4"

        with st.spinner("🎥 타로 영상 생성 중... (약 1~2분 소요)"):
            try:
                ft = random.choice(["건강운", "애정운", "금전운", "의사결정"]) if (use_minor_arcana and minor_fortune_type == "랜덤") else minor_fortune_type
                video_path, theme_name, metadata_extra = generate_tarot_video(
                    background_path=background_path,
                    music_path=music_path,
                    output_path=str(output_path),
                    time_slot_id=time_slot_id,
                    use_minor_arcana=use_minor_arcana,
                    minor_fortune_type=ft,
                    major_theme=major_theme,
                    hook_duration_sec=hook_duration,
                    hook_text_override=selected_title,
                )
                st.session_state.video_path = video_path
                st.session_state.fortune_type = theme_name
                st.session_state.tarot_metadata = metadata_extra
                # 첫 화면 문구 재생성용 파라미터 저장
                st.session_state.video_gen_params = {
                    "use_minor_arcana": use_minor_arcana,
                    "minor_fortune_type": ft,
                    "time_slot_id": time_slot_id,
                    "major_theme": major_theme,
                    "hook_duration": hook_duration,
                    "background_path": background_path,
                    "music_path": music_path,
                }
                deck_label = "마이너 56장" if use_minor_arcana else "메이저 22장"
                n_cards = metadata_extra.get("num_cards") or getattr(config, "NUM_CARDS", 6)
                st.session_state.fortune_text = f"타로 {theme_name} {n_cards}장 ({deck_label})"
                if metadata_extra.get("major_theme") in theme_phrases_db.THEME_DB_NAMES:
                    st.session_state.thumbnail_theme_label = metadata_extra["major_theme"]
                    st.session_state.thumbnail_hook_phrase = metadata_extra.get("hook_text", "")
                # 생성한 주제에 맞게 썸네일 자동 생성
                try:
                    hook_for_thumb = metadata_extra.get("hook_text") if (metadata_extra.get("major_theme") in theme_phrases_db.THEME_DB_NAMES) else None
                    thumb_result = generate_one_tarot_fortune_thumbnail(
                        time_slot=time_slot_id or "아침",
                        theme_label=theme_name,
                        hook_phrase_override=hook_for_thumb,
                    )
                    if thumb_result:
                        one_path, line2_used, hook_used, hook_display, bg_path = thumb_result
                        if one_path and Path(one_path).exists():
                            st.session_state["last_tarot_thumb_path"] = one_path
                            st.session_state["last_thumb_line1"] = f"{datetime.now().month}월 {datetime.now().day}일"
                            st.session_state["last_thumb_line2"] = line2_used
                            st.session_state["last_thumb_hook_phrase"] = hook_used
                            st.session_state["last_thumb_hook_display"] = hook_display
                            st.session_state["last_thumb_background_path"] = bg_path
                            st.session_state["last_thumb_theme_label"] = theme_name
                            st.session_state["last_thumb_time_slot"] = time_slot_id or ""
                            st.session_state["thumb_last_preview_size"] = 1.0
                            st.session_state["selected_thumbnail"] = one_path
                except Exception:
                    pass
                end_time = datetime.now()
                duration = end_time - start_time
                st.session_state.video_make_end = end_time.strftime("%H:%M:%S")
                st.session_state.video_make_duration_sec = duration.total_seconds()
                st.success("✅ 타로 영상 생성 완료!")
            except Exception as e:
                st.session_state.video_make_end = datetime.now().strftime("%H:%M:%S")
                st.session_state.video_make_duration_sec = (datetime.now() - start_time).total_seconds()
                st.error(f"❌ 영상 생성 실패: {e}")

    if st.session_state.get("video_make_start") and st.session_state.get("video_make_end") is not None:
        start_str = st.session_state.get("video_make_start", "")
        end_str = st.session_state.get("video_make_end", "")
        sec = st.session_state.get("video_make_duration_sec") or 0
        m = int(sec // 60)
        s = int(sec % 60)
        duration_str = f"{m}분 {s}초"
        st.markdown("---")
        st.caption("⏱️ 제작 소요 시간")
        st.info(f"**제작 시작:** {start_str}  →  **제작 종료:** {end_str}  →  **이번 영상은 제작하는 데 {duration_str} 걸렸습니다.**")

    if st.session_state.get('video_path'):
        st.markdown("---")
        st.subheader("📹 미리보기")

        # 미리보기: 중앙 1/3 크기 (기존 대비 약 1/3 축소)
        col_left, col_center, col_right = st.columns([1, 1, 1])
        with col_center:
            st.video(st.session_state.get('video_path'), format="video/mp4")
        with st.container():
            st.markdown(
                f"""
                <div style="background:#f8f9fa; padding:12px 16px; border-radius:8px; margin:8px 0; color:#262730;">
                <strong>운세</strong> {st.session_state.get('fortune_text', '')}<br>
                <strong>파일</strong> {Path(st.session_state.get('video_path', '')).name}
                </div>
                """,
                unsafe_allow_html=True
            )

        # 첫 화면 문구 수정 (미리보기에서 편집 후 재생성 가능)
        card_meta = st.session_state.get("tarot_metadata") or {}
        current_hook = (card_meta.get("hook_text") or "").strip()
        st.markdown("#### ✏️ 첫 화면 문구 수정")
        st.caption("영상 맨 앞에 나오는 문구를 수정한 뒤, 아래 버튼으로 재생성하세요.")
        edited_hook = st.text_input(
            "첫 화면 문구",
            value=current_hook or "첫 화면에 표시될 문구",
            max_chars=80,
            key="preview_hook_edit",
            label_visibility="collapsed",
            placeholder="첫 화면에 표시될 문구를 입력하세요",
        )
        if st.button("🔄 이 문구로 영상 재생성", use_container_width=True, key="btn_regen_hook"):
            params = st.session_state.get("video_gen_params") or {}
            if not params:
                st.warning("재생성 정보가 없습니다. 영상을 새로 생성한 뒤 문구 수정이 가능합니다.")
            elif not (edited_hook and edited_hook.strip()):
                st.warning("수정할 문구를 입력하세요.")
            else:
                from modules.tarot_video_generator import generate_tarot_video

                imgs = list(config.IMAGES_DIR.glob("*.png")) + list(config.IMAGES_DIR.glob("*.jpg")) + list(config.IMAGES_DIR.glob("*.jpeg"))
                bg = params.get("background_path") or (str(random.choice(imgs)) if imgs else None)
                music = params.get("music_path") or config.get_random_music_path()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out = config.OUTPUT_DIR / f"tarot_{ts}.mp4"
                with st.spinner("🎥 첫 화면 문구 반영해 재생성 중... (약 1~2분)"):
                    try:
                        vp, tn, meta = generate_tarot_video(
                            background_path=bg,
                            music_path=music,
                            output_path=str(out),
                            time_slot_id=params.get("time_slot_id"),
                            use_minor_arcana=params.get("use_minor_arcana", False),
                            minor_fortune_type=params.get("minor_fortune_type"),
                            major_theme=params.get("major_theme"),
                            hook_duration_sec=params.get("hook_duration", 4),
                            hook_text_override=edited_hook.strip(),
                        )
                        st.session_state.video_path = vp
                        st.session_state.fortune_type = tn
                        st.session_state.tarot_metadata = meta
                        n_cards = meta.get("num_cards") or getattr(config, "NUM_CARDS", 6)
                        deck = "마이너 56장" if params.get("use_minor_arcana") else "메이저 22장"
                        st.session_state.fortune_text = f"타로 {tn} {n_cards}장 ({deck})"
                        if meta.get("major_theme") in theme_phrases_db.THEME_DB_NAMES:
                            st.session_state.thumbnail_theme_label = meta["major_theme"]
                            st.session_state.thumbnail_hook_phrase = meta.get("hook_text", "")
                        try:
                            hook_for_thumb = meta.get("hook_text") if (meta.get("major_theme") in theme_phrases_db.THEME_DB_NAMES) else None
                            thumb_result = generate_one_tarot_fortune_thumbnail(
                                time_slot=params.get("time_slot_id") or "아침",
                                theme_label=tn,
                                hook_phrase_override=hook_for_thumb,
                            )
                            if thumb_result:
                                one_path, line2_used, hook_used, hook_display, bg_path = thumb_result
                                if one_path and Path(one_path).exists():
                                    st.session_state["last_tarot_thumb_path"] = one_path
                                    st.session_state["last_thumb_line1"] = f"{datetime.now().month}월 {datetime.now().day}일"
                                    st.session_state["last_thumb_line2"] = line2_used
                                    st.session_state["last_thumb_hook_phrase"] = hook_used
                                    st.session_state["last_thumb_hook_display"] = hook_display
                                    st.session_state["last_thumb_background_path"] = bg_path
                                    st.session_state["last_thumb_theme_label"] = tn
                                    st.session_state["selected_thumbnail"] = one_path
                        except Exception:
                            pass
                        st.success("✅ 첫 화면 문구 반영해 영상 재생성 완료!")
                    except Exception as e:
                        st.error(f"❌ 재생성 실패: {e}")
                st.rerun()

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 마음에 들어요!", use_container_width=True):
                st.session_state.approved = True
                st.success("✅ 승인되었습니다! 메타데이터 탭으로 이동하세요.")
                st.balloons()
        with col2:
            if st.button("🔄 다시 생성", use_container_width=True):
                st.session_state['video_path'] = None
                st.session_state['approved'] = False
                st.session_state.pop('tarot_metadata', None)
                st.rerun()

        thumb_path = st.session_state.get("selected_thumbnail") or st.session_state.get("last_tarot_thumb_path")
        if thumb_path and Path(thumb_path).exists():
            st.caption("💡 썸네일을 영상 맨 앞(2.5초)에 붙인 새 영상을 만들 수 있습니다.")
            if st.button("🖼️ 영상 맨 앞에 썸네일 붙이기", use_container_width=True, key="btn_prepend_thumb"):
                from modules.tarot_video_generator import prepend_thumbnail_to_video

                with st.spinner("썸네일을 영상 앞에 붙이는 중… (약 30초~1분)"):
                    try:
                        new_path = prepend_thumbnail_to_video(
                            st.session_state["video_path"],
                            thumb_path,
                            duration_sec=2.5,
                        )
                        st.session_state["video_path"] = str(Path(new_path).resolve())
                        st.success("영상 맨 앞에 썸네일이 붙었습니다. 위 미리보기를 확인하세요.")
                    except Exception as e:
                        st.error(f"실패: {e}")
                st.rerun()

# ========================================
# 탭 2: 메타데이터
# ========================================
with tab2:
    if not st.session_state.get('approved'):
        st.info("👈 먼저 영상을 생성하고 승인해주세요.")
    else:
        st.subheader("📝 메타데이터 편집")
        fortune_type = st.session_state.get('fortune_type', '총운')
        today = datetime.now().strftime("%m월 %d일")

        st.markdown("### 📌 제목")
        card_meta_for_title = st.session_state.get("tarot_metadata") or {}
        if auto_meta:
            with st.spinner("제목 생성 중..."):
                try:
                    titles = generate_titles(fortune_type, today)
                except Exception:
                    titles = [
                        f"🔮 {today} 오늘의 {fortune_type} | 일시정지 필수!",
                        f"💫 {today} {fortune_type} 확인하세요",
                        f"✨ {today} {fortune_type} | 타로 {getattr(config, 'NUM_CARDS', 6)}장으로 운세 보기"
                    ]
            # 감성형 타로: 선택한 제목(훅)을 첫 번째 옵션으로
            hook_title = card_meta_for_title.get("hook_text", "").strip()
            if hook_title and fortune_type in ("재회 및 미련", "썸 & 짝사랑", "관계의 비밀", "운세 및 기회"):
                titles = [hook_title] + [t for t in titles if t != hook_title]
            meta_selected = st.selectbox("제목 선택", titles, key="title_select")
            col1, col2 = st.columns([4, 1])
            with col1:
                final_title = st.text_input(
                    "제목 수정",
                    meta_selected,
                    max_chars=100,
                    key="title_input"
                )
            with col2:
                if st.button("🔄 다시 생성", key="regen_title"):
                    st.rerun()
            char_count = len(final_title)
            if char_count > 50:
                st.warning(f"⚠️ 제목이 깁니다: {char_count}자 (권장: 50자 이하)")
            else:
                st.caption(f"✅ 글자 수: {char_count}/50")
        else:
            final_title = st.text_input(
                "제목",
                f"🔮 {today} 오늘의 {fortune_type}",
                max_chars=100
            )

        st.markdown("---")
        st.markdown("### 📄 설명")
        if auto_meta:
            card_meta = st.session_state.get("tarot_metadata")
            with st.spinner("설명 생성 중 (카드 상세 해석 포함)..."):
                description = generate_description(fortune_type, today, card_metadata=card_meta)
            final_description = st.text_area(
                "설명 편집",
                description,
                height=400,
                max_chars=5000,
                key="desc_input"
            )
            st.caption(f"글자 수: {len(final_description)}/5000")
        else:
            final_description = st.text_area(
                "설명",
                height=400,
                max_chars=5000
            )

        st.markdown("---")
        st.markdown("### 🏷️ 해시태그")
        if auto_hashtags:
            with st.spinner("해시태그 생성 중..."):
                tags = generate_hashtags(fortune_type)
            st.write("**생성된 해시태그:**")
            selected_tags = st.multiselect(
                "선택/삭제 (최대 15개 권장)",
                options=tags,
                default=tags,
                key="tags_select"
            )
            new_tag = st.text_input("해시태그 추가 (#없이 입력)", key="new_tag")
            if new_tag and st.button("➕ 추가", key="add_tag"):
                tag_with_hash = f"#{new_tag.strip()}"
                if tag_with_hash not in selected_tags:
                    selected_tags.append(tag_with_hash)
                    st.success(f"✅ {tag_with_hash} 추가됨")
                    st.rerun()
            if selected_tags:
                st.info(f"✅ {len(selected_tags)}개 태그 선택됨")
                st.code(" ".join(selected_tags))
            else:
                st.warning("⚠️ 태그를 최소 1개 선택해주세요!")
        else:
            tag_input = st.text_input(
                "해시태그 (쉼표로 구분)",
                "#오늘의운세, #타로, #Shorts"
            )
            selected_tags = [
                f"#{t.strip().replace('#', '')}"
                for t in tag_input.split(',')
                if t.strip()
            ]

        st.session_state.metadata = {
            "title": final_title,
            "description": final_description,
            "tags": selected_tags
        }

        if st.button("💾 메타데이터 저장", type="primary", use_container_width=True):
            st.success("✅ 메타데이터가 저장되었습니다!")

# ========================================
# 탭 3: 썸네일
# ========================================
with tab3:
    st.subheader("🖼️ 타로운세 썸네일 1장")
    st.caption("날짜 + 주제/시간대 + 후킹 문구가 썸네일에 들어갑니다. 배경은 assets/thumbnail_backgrounds에서 랜덤 선택.")
    ratio_info = _cached_ratio_info()
    if ratio_info:
        with st.expander("📐 썸네일 배경 이미지 비율 확인", expanded=False):
            st.caption("YouTube Shorts 권장: 9:16 (예: 1080×1920)")
            for name, w, h, ratio, ok in ratio_info:
                status = "✅ 9:16" if ok else f"⚠️ 비율 {ratio}"
                st.text(f"  {name}: {w} × {h}  →  {status}")
    else:
        st.caption("배경 이미지 없음. assets/thumbnail_backgrounds에 png/jpg/webp를 넣어 주세요.")

    # 영상에서 주제 타로로 만들었으면 썸네일 탭 첫 방문 시 주제 타로·해당 문구로 기본 선택
    if st.session_state.get("thumbnail_theme_label") and "thumb_type" not in st.session_state:
        st.session_state.thumb_type = "주제 타로 (재회·썸·관계·운세)"
    if st.session_state.get("thumbnail_theme_label") and "thumb_theme_select" not in st.session_state:
        theme_names = theme_phrases_db.list_theme_names()
        if st.session_state.thumbnail_theme_label in theme_names:
            st.session_state.thumb_theme_select = st.session_state.thumbnail_theme_label
    if st.session_state.get("thumbnail_theme_label") and st.session_state.get("thumbnail_hook_phrase"):
        if "thumb_phrase_input" not in st.session_state or st.session_state.get("thumb_last_theme") == st.session_state.thumbnail_theme_label:
            st.session_state.thumb_phrase_input = st.session_state.thumbnail_hook_phrase
            st.session_state.thumb_last_theme = st.session_state.thumbnail_theme_label

    thumb_type = st.radio(
        "썸네일 유형",
        ["오늘의 운세", "주제 타로 (재회·썸·관계·운세)"],
        horizontal=True,
        key="thumb_type",
    )
    use_theme_db = thumb_type == "주제 타로 (재회·썸·관계·운세)"

    if use_theme_db:
        theme_names = theme_phrases_db.list_theme_names()
        thumb_theme_name = st.selectbox("주제 선택", theme_names, key="thumb_theme_select")
        if "thumb_last_theme" not in st.session_state or st.session_state.thumb_last_theme != thumb_theme_name:
            st.session_state.thumb_last_theme = thumb_theme_name
            if thumb_theme_name == st.session_state.get("thumbnail_theme_label") and st.session_state.get("thumbnail_hook_phrase"):
                st.session_state.thumb_phrase_input = st.session_state.thumbnail_hook_phrase
            else:
                st.session_state.thumb_phrase_input = theme_phrases_db.get_random_phrase(thumb_theme_name)
        st.text_area(
            "썸네일 문구 (수동 수정 가능)",
            value=st.session_state.get("thumb_phrase_input", ""),
            height=100,
            placeholder="아래 [문구 가져오기]로 DB 문구 불러오거나 직접 입력 후 [생성하기]를 누르면 썸네일에 반영됩니다.",
            key="thumb_phrase_input",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📥 문구 가져오기 (DB에서 랜덤)", key="btn_thumb_refresh_phrase"):
                st.session_state.thumb_phrase_input = theme_phrases_db.get_random_phrase(thumb_theme_name)
                st.rerun()
        with col_b:
            btn_thumb_gen = st.button("🖼️ 생성하기", key="btn_thumb_theme_one")
        thumb_time_slot = None
    else:
        thumb_time_slot = "아침"  # 운세는 아침 한 번만 올리므로 고정
        thumb_theme_name = None
        # 오늘의 운세: 기본 문구 1회 생성, 문구 재생성 버튼
        if "thumb_morning_phrase" not in st.session_state:
            st.session_state.thumb_morning_phrase = get_morning_tarot_hook_phrase()
        st.text_area(
            "썸네일 문구 (수동 수정 가능)",
            value=st.session_state.get("thumb_morning_phrase", ""),
            height=100,
            placeholder="아침 타로 썸네일 후킹 문구. 아래 [문구 재생성]으로 새 문구를 받거나 직접 수정 후 [생성하기]를 누르세요.",
            key="thumb_morning_phrase_input",
        )
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("🔄 문구 재생성", key="btn_thumb_regenerate_phrase"):
                new_phrase = get_morning_tarot_hook_phrase()
                st.session_state.thumb_morning_phrase = new_phrase
                st.session_state.thumb_morning_phrase_input = new_phrase
                st.rerun()
        with col_m2:
            btn_thumb_gen = st.button("🖼️ 생성하기", key="btn_thumb_tarot_one")

    if btn_thumb_gen:
        with st.spinner("썸네일 1장 생성 중…"):
            if use_theme_db:
                result = generate_one_tarot_fortune_thumbnail(
                    time_slot="",
                    theme_label=thumb_theme_name,
                    hook_phrase_override=st.session_state.get("thumb_phrase_input", "").strip() or None,
                )
            else:
                # 일반: 오늘의 운세 (아침 한 번만 올리므로 통합)
                hook_override = st.session_state.get("thumb_morning_phrase_input", "").strip() or st.session_state.get("thumb_morning_phrase", "")
                if st.session_state.get("fortune_type") in theme_phrases_db.THEME_DB_NAMES and st.session_state.get("thumbnail_hook_phrase"):
                    hook_override = hook_override or st.session_state.get("thumbnail_hook_phrase")
                result = generate_one_tarot_fortune_thumbnail(
                    time_slot="",
                    theme_label="오늘의 운세",
                    hook_phrase_override=hook_override.strip() or None,
                )
        if result:
            one_path, line2_used, hook_used, hook_display, bg_path = result
            if one_path and Path(one_path).exists():
                st.session_state["last_tarot_thumb_path"] = one_path
                st.session_state["last_thumb_line1"] = f"{datetime.now().month}월 {datetime.now().day}일"
                st.session_state["last_thumb_line2"] = line2_used
                st.session_state["last_thumb_hook_phrase"] = hook_used
                st.session_state["last_thumb_hook_display"] = hook_display
                st.session_state["last_thumb_background_path"] = bg_path
                st.session_state["last_thumb_theme_label"] = thumb_theme_name if use_theme_db else None
                st.session_state["last_thumb_time_slot"] = "" if use_theme_db else (thumb_time_slot or "")
                st.session_state["thumb_last_preview_size"] = 1.0
                st.session_state["selected_thumbnail"] = one_path  # 기본으로 자동 선택
                st.success("썸네일 1장 생성 완료. 업로드용으로 자동 선택되었습니다.")
            else:
                st.warning("배경 이미지가 없습니다. assets/thumbnail_backgrounds에 png/jpg/webp를 넣어 주세요.")
        else:
            st.warning("배경 이미지가 없습니다. assets/thumbnail_backgrounds에 png/jpg/webp를 넣어 주세요.")
        st.rerun()

    if st.session_state.get("last_tarot_thumb_path") and Path(st.session_state["last_tarot_thumb_path"]).exists():
        if st.button("이 썸네일로 선택", key="use_tarot_thumb"):
            st.session_state["selected_thumbnail"] = st.session_state["last_tarot_thumb_path"]
            st.success("선택된 썸네일로 설정되었습니다. 업로드 시 사용됩니다.")
            st.rerun()

    # 썸네일 수정: 수정 시 로딩 없음. 문구·색·크기 바꾼 뒤 "최종 수정된 썸네일 등록"에서만 생성.
    if st.session_state.get("last_tarot_thumb_path"):
        st.markdown("---")
        st.subheader("✏️ 썸네일 수정")
        st.caption("문구·글자 크기·글자 색을 바꾸면 **미리보기만** 바뀝니다 (로딩 없음). 다 고친 뒤 맨 아래 **최종 수정된 썸네일 등록**을 누르면 썸네일이 생성·등록됩니다.")
        font_options = _cached_list_fonts()
        font_choices = ["기본(자동)"] + [name for name, _ in font_options]
        font_paths = {name: path for name, path in font_options}
        if "last_thumb_font_select" not in st.session_state:
            st.session_state["last_thumb_font_select"] = "기본(자동)"
        default_fill = "#FFFFFF"

        # 미리보기 크기 축소: [2, 1, 2]로 중앙 20% (반 이하)
        col_left, col_center, col_right = st.columns([2, 1, 2])
        with col_left:
            # 문구 재생성: 세션에 값 설정 후 위젯 생성 (위젯은 세션 값을 사용)
            if "thumb_edit_hook_pending" in st.session_state:
                st.session_state["thumb_edit_hook_input"] = st.session_state.pop("thumb_edit_hook_pending")
            edit_hook = st.text_area(
                "후킹 문구 (한 줄 최대 8글자, 넘으면 자동 줄바꿈)",
                value=st.session_state.get("last_thumb_hook_display") or st.session_state.get("last_thumb_hook_phrase", ""),
                height=120,
                placeholder="썸네일에 들어갈 문구 입력",
                key="thumb_edit_hook_input",
            )
            if st.button("🔄 문구 재생성", key="btn_thumb_edit_regenerate_phrase"):
                st.session_state["thumb_edit_hook_pending"] = get_morning_tarot_hook_phrase()
                st.rerun()
            hook_val = (edit_hook or "").strip() or None
            hook_lines = hook_phrase_to_lines(hook_val or "", 8)

            thumb_font = st.selectbox("폰트", font_choices, key="thumb_edit_font_select")
            size_slider = st.slider(
                "글자 크기 (배율)",
                min_value=0.5,
                max_value=1.8,
                value=float(st.session_state.get("thumb_edit_size_scale", 1.0)),
                step=0.05,
                format="%.2f",
                key="thumb_size_slider",
            )
            st.session_state["thumb_edit_size_scale"] = size_slider

            st.markdown("**글자별 색상**")
            hook_char_colors = st.session_state.get("last_thumb_hook_char_colors", [])
            for line_idx, hook_line in enumerate(hook_lines):
                while len(hook_char_colors) <= line_idx:
                    hook_char_colors.append([])
                line_colors = list(hook_char_colors[line_idx])
                while len(line_colors) < len(hook_line):
                    line_colors.append(default_fill)
                line_colors = line_colors[: len(hook_line)]
                with st.expander(f"줄 {line_idx + 1}: {hook_line or '(빈 줄)'}"):
                    for i, ch in enumerate(hook_line):
                        line_colors[i] = st.color_picker(f"'{ch}'", value=line_colors[i], key=f"thumb_hook_{line_idx}_c{i}")
                hook_char_colors[line_idx] = line_colors
            hook_char_colors = hook_char_colors[: len(hook_lines)]
            st.session_state["last_thumb_hook_char_colors"] = hook_char_colors

        with col_center:
            bg_path = st.session_state.get("last_thumb_background_path") or ""
            if Path(bg_path).exists():
                bg_b64 = _cached_file_b64(bg_path)
            else:
                tp = st.session_state.get("last_tarot_thumb_path")
                bg_b64 = _cached_file_b64(tp) if tp and Path(tp).exists() else ""
            if bg_b64:
                # 카드 크기에 맞춰 글자도 비례 스케일 (container query)
                cqw_base = 14 * size_slider  # 카드 너비의 % (slider 1.0 → 14cqw)
                font_size_css = f"clamp(10px, {cqw_base:.1f}cqw, 56px)"
                # 선택한 폰트를 미리보기에 실시간 적용: @font-face로 임베드
                font_css = ""
                preview_font_family = "sans-serif"
                if thumb_font and thumb_font != "기본(자동)":
                    fp = font_paths.get(thumb_font)
                    if fp and Path(fp).exists():
                        font_b64 = _cached_file_b64(fp)
                        if font_b64:
                            suf = Path(fp).suffix.lower()
                            if suf == ".ttf":
                                mime, fmt = "font/ttf", "truetype"
                            elif suf == ".otf":
                                mime, fmt = "font/otf", "opentype"
                            elif suf == ".ttc":
                                mime, fmt = "font/ttc", "truetype"
                            else:
                                mime, fmt = "font/ttf", "truetype"
                            font_css = f"@font-face{{font-family:'ThumbPreviewFont';src:url(data:{mime};base64,{font_b64}) format('{fmt}');}}"
                            preview_font_family = "'ThumbPreviewFont', sans-serif"
                lines_html = []
                for line_idx, line in enumerate(hook_lines):
                    colors = hook_char_colors[line_idx] if line_idx < len(hook_char_colors) else []
                    chars_html = []
                    for i, ch in enumerate(line):
                        c = colors[i] if i < len(colors) else default_fill
                        ch_esc = ch.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                        chars_html.append(f'<span style="color:{c}; text-shadow:0 0 2px #000, 0 0 2px #000;">{ch_esc}</span>')
                    lines_html.append(f'<div style="line-height:1.4; font-size:{font_size_css}; font-family:{preview_font_family};">{"".join(chars_html)}</div>')
                text_block = "".join(lines_html)
                html = f'<style>{font_css}</style><div style="container-type:size; position:relative; max-width:100%; aspect-ratio:9/16; border-radius:8px; overflow:hidden; margin:0 auto;"><img src="data:image/png;base64,{bg_b64}" style="width:100%; height:100%; object-fit:cover;" alt="배경"/><div style="position:absolute; left:0; right:0; top:50%; transform:translateY(-50%); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:4%; color:white; font-weight:bold; text-align:center; font-family:{preview_font_family};">{text_block}</div></div>'
                st.markdown(html, unsafe_allow_html=True)
                st.caption("미리보기 (폰트·글자 크기·색상 실시간 반영)")
            else:
                st.image(st.session_state["last_tarot_thumb_path"], use_container_width=True, caption="미리보기")

        if st.button("🖼️ 배경만 변경 (글자 유지)", key="btn_thumb_bg_only"):
            with st.spinner("배경만 바꿔서 생성 중…"):
                # st.rerun 직후 selectbox 반환값이 초기화되는 버그 회피: 세션 상태에서 직접 읽기
                sel_font = st.session_state.get("thumb_edit_font_select", thumb_font)
                fp = None if sel_font == "기본(자동)" else font_paths.get(sel_font)
                if fp:
                    fp = str(Path(fp).resolve())
                res = generate_one_tarot_fortune_thumbnail(
                    time_slot=st.session_state.get("last_thumb_time_slot", ""),
                    theme_label=st.session_state.get("last_thumb_theme_label"),
                    hook_phrase_override=hook_val,
                    line1_override="",
                    line2_override="",
                    background_path_override=None,
                    font_path_override=fp,
                    font_size_scale=size_slider,
                    hook_fill=default_fill,
                    hook_fill_per_char=hook_char_colors if hook_char_colors else None,
                )
            if res and res[0] and Path(res[0]).exists():
                st.session_state["last_tarot_thumb_path"] = res[0]
                st.session_state["last_thumb_background_path"] = res[4]
                st.session_state["last_thumb_hook_display"] = res[3]
                st.success("배경만 변경되었습니다.")
            st.rerun()

        st.markdown("---")
        if st.button("**최종 수정된 썸네일 등록**", type="primary", use_container_width=True, key="btn_thumb_register"):
            with st.spinner("썸네일 생성 중…"):
                # st.rerun 직후 selectbox 반환값이 초기화되는 버그 회피: 세션 상태에서 직접 읽기
                sel_font = st.session_state.get("thumb_edit_font_select", thumb_font)
                fp = None if sel_font == "기본(자동)" else font_paths.get(sel_font)
                if fp:
                    fp = str(Path(fp).resolve())
                res = generate_one_tarot_fortune_thumbnail(
                    time_slot=st.session_state.get("last_thumb_time_slot", ""),
                    theme_label=st.session_state.get("last_thumb_theme_label"),
                    hook_phrase_override=hook_val,
                    line1_override="",
                    line2_override="",
                    background_path_override=st.session_state.get("last_thumb_background_path"),
                    font_path_override=fp,
                    font_size_scale=size_slider,
                    hook_fill=default_fill,
                    hook_fill_per_char=hook_char_colors if hook_char_colors else None,
                )
            if res and res[0] and Path(res[0]).exists():
                st.session_state["last_tarot_thumb_path"] = res[0]
                st.session_state["last_thumb_background_path"] = res[4]
                st.session_state["last_thumb_hook_display"] = res[3]
                st.session_state["selected_thumbnail"] = res[0]
                st.session_state["thumb_just_registered"] = True
                st.success("최종 수정된 썸네일이 업로드용으로 등록되었습니다.")
            else:
                st.error("썸네일 생성에 실패했습니다.")
            st.rerun()

        if st.session_state.get("thumb_just_registered"):
            st.success("**등록완료!**")
            st.session_state["thumb_just_registered"] = False

        # 영상 맨 앞에 썸네일 붙이기 (썸네일 탭에서도 사용 가능)
        if st.session_state.get("video_path") and Path(st.session_state["video_path"]).exists():
            thumb_for_prepend = st.session_state.get("selected_thumbnail") or st.session_state.get("last_tarot_thumb_path")
            if thumb_for_prepend and Path(thumb_for_prepend).exists():
                st.markdown("---")
                st.subheader("🖼️ 영상 맨 앞에 썸네일 붙이기")
                st.caption("현재 썸네일을 **제작한 영상 맨 앞 2.5초**에 붙인 새 영상을 만듭니다. (영상 생성 탭에서도 같은 버튼이 있습니다.)")
                if st.button("🖼️ 영상 맨 앞에 썸네일 붙이기", type="secondary", use_container_width=True, key="btn_prepend_thumb_tab3"):
                    from modules.tarot_video_generator import prepend_thumbnail_to_video

                    with st.spinner("썸네일을 영상 앞에 붙이는 중… (약 30초~1분)"):
                        try:
                            new_path = prepend_thumbnail_to_video(
                                st.session_state["video_path"],
                                thumb_for_prepend,
                                duration_sec=2.5,
                            )
                            st.session_state["video_path"] = str(Path(new_path).resolve())
                            st.success("영상 맨 앞에 썸네일이 붙었습니다. 영상 생성 탭에서 미리보기를 확인하세요.")
                        except Exception as e:
                            st.error(f"실패: {e}")
                    st.rerun()

# ========================================
# 탭 4: 업로드
# ========================================
with tab4:
    if not st.session_state.get('video_path'):
        st.info("👈 먼저 영상을 생성해주세요.")
    elif not st.session_state.get('metadata'):
        st.info("👈 메타데이터를 설정해주세요.")
    else:
        st.subheader("📤 YouTube 업로드 설정")
        privacy_map = {
            "공개": "public",
            "비공개": "private",
            "일부 공개": "unlisted"
        }
        privacy_kr = st.radio(
            "🔒 공개 설정",
            list(privacy_map.keys()),
            horizontal=True
        )
        privacy = privacy_map[privacy_kr]

        scheduled = st.toggle("⏰ 예약 업로드")
        scheduled_time = None
        if scheduled:
            col1, col2 = st.columns(2)
            with col1:
                schedule_date = st.date_input("📅 날짜")
            with col2:
                schedule_time = st.time_input("🕐 시간", value=time(6, 0))
            scheduled_time = datetime.combine(schedule_date, schedule_time)
            st.info(f"📅 예약 시간 (한국): {scheduled_time.strftime('%Y-%m-%d %H:%M')}")
            st.caption("입력한 날짜·시간은 한국 시간(KST)으로, 유튜브 예약에 반영됩니다. 예약한 영상은 '비공개'로 올라가며, 설정한 시각에 자동 공개됩니다.")
            # 예약 시각이 과거면 유튜브가 즉시 공개할 수 있음 → 경고
            kst = timezone(timedelta(hours=9))
            scheduled_kst = scheduled_time.replace(tzinfo=kst)
            now_kst = datetime.now(kst)
            if scheduled_kst <= now_kst:
                st.warning("⚠️ 선택한 예약 시각이 이미 지났습니다. 과거 시각으로 예약하면 유튜브에서 즉시 공개될 수 있습니다. 미래 날짜·시간으로 다시 선택하세요.")

        st.markdown("---")
        # 업로드 직전에 썸네일 붙이기 (다운로드/업로드 시 반영)
        _vp = st.session_state.get("video_path", "")
        _tp = st.session_state.get("selected_thumbnail") or st.session_state.get("last_tarot_thumb_path")
        _has_thumb_in_name = "_with_thumb" in Path(_vp).name if _vp else False
        if _vp and Path(_vp).exists() and _tp and Path(_tp).exists() and not _has_thumb_in_name:
            if st.button("🖼️ 영상 맨 앞에 썸네일 붙이기 (다운로드 전 적용)", type="primary", use_container_width=True, key="btn_prepend_upload"):
                from modules.tarot_video_generator import prepend_thumbnail_to_video

                with st.spinner("썸네일 붙이는 중… (약 30초~1분)"):
                    try:
                        np = prepend_thumbnail_to_video(_vp, _tp, duration_sec=2.5)
                        st.session_state["video_path"] = str(Path(np).resolve())
                        st.success("썸네일이 영상 앞에 붙었습니다. 아래에서 다운로드하세요.")
                    except Exception as e:
                        st.error(f"실패: {e}")
                st.rerun()
        elif _has_thumb_in_name:
            st.info("✅ 현재 영상에 썸네일이 앞에 붙어 있습니다.")
        st.markdown("---")
        with st.expander("📋 업로드 정보 최종 확인", expanded=True):
            st.write("**영상:**", Path(st.session_state.get('video_path', '')).name)
            st.write("**제목:**", st.session_state.get('metadata', {}).get('title', ''))
            desc = st.session_state.get('metadata', {}).get('description', '')
            st.write("**설명:**", desc[:100] + "..." if len(desc) > 100 else desc)
            st.write("**해시태그:**", len(st.session_state.get('metadata', {}).get('tags', [])), "개")
            st.write(
                "**썸네일:**",
                "✅ 선택됨" if st.session_state.get('selected_thumbnail') else "❌ 미선택"
            )
            st.write("**공개 설정:**", privacy_kr)
            if scheduled:
                st.write("**예약 시간:**", scheduled_time.strftime('%Y-%m-%d %H:%M'))

        st.markdown("---")
        st.subheader("📥 파일 다운로드 (수동 업로드용)")
        meta = st.session_state.get('metadata', {})
        video_path = st.session_state.get('video_path')
        if video_path:
            video_path = str(Path(video_path).resolve())
        thumb_path = st.session_state.get('selected_thumbnail')
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            if video_path and Path(video_path).exists():
                with open(video_path, 'rb') as f:
                    st.download_button(
                        "🎬 영상 다운로드",
                        data=f.read(),
                        file_name=Path(video_path).name,
                        mime="video/mp4",
                        use_container_width=True,
                        key="dl_video"
                    )
            else:
                st.caption("영상 파일 없음")
        with col_d2:
            if thumb_path and Path(thumb_path).exists():
                with open(thumb_path, 'rb') as f:
                    ext = Path(thumb_path).suffix.lower()
                    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                    st.download_button(
                        "🖼️ 썸네일 다운로드",
                        data=f.read(),
                        file_name=Path(thumb_path).name,
                        mime=mime,
                        use_container_width=True,
                        key="dl_thumb"
                    )
            else:
                st.caption("썸네일 선택 필요")
        with col_d3:
            title = meta.get('title', '')
            desc = meta.get('description', '')
            tags_str = ', '.join(meta.get('tags', []))
            meta_txt = f"제목:\n{title}\n\n설명:\n{desc}\n\n해시태그:\n{tags_str}"
            st.download_button(
                "📋 메타데이터 다운로드",
                data=meta_txt.encode('utf-8'),
                file_name="metadata.txt",
                mime="text/plain",
                use_container_width=True,
                key="dl_meta"
            )
        st.caption("수동 업로드 시 위 파일들을 다운로드한 뒤 유튜브 스튜디오에서 올려주세요.")

        st.markdown("---")
        has_video = bool(st.session_state.get('video_path') and Path(st.session_state.get('video_path', '')).exists())
        has_title = bool((st.session_state.get('metadata', {}).get('title') or '').strip())
        upload_disabled = not (has_video and has_title)
        if upload_disabled:
            st.warning("⚠️ 영상과 제목이 있어야 업로드할 수 있습니다.")
        elif not st.session_state.get('selected_thumbnail'):
            st.caption("💡 썸네일 없이 업로드하면 YouTube가 영상 프레임을 자동으로 사용합니다.")
        else:
            st.caption("💡 선택한 썸네일은 업로드 시 함께 전송됩니다. 반영까지 수 분 걸릴 수 있으며, **휴대폰 인증된 계정**에서만 커스텀 썸네일이 적용됩니다.")

        if st.button(
            "📤 유튜브에 업로드",
            type="primary",
            use_container_width=True,
            disabled=upload_disabled
        ):
            with st.spinner("업로드 중... (1-2분 소요)"):
                try:
                    thumb_path = st.session_state.get('selected_thumbnail')
                    if thumb_path and Path(thumb_path).exists():
                        thumb_path = str(Path(thumb_path).resolve())
                    result = upload_video(
                        video_path=st.session_state.get('video_path'),
                        title=st.session_state.get('metadata', {}).get('title', ''),
                        description=st.session_state.get('metadata', {}).get('description', ''),
                        tags=st.session_state.get('metadata', {}).get('tags', []),
                        thumbnail_path=thumb_path,
                        privacy=privacy,
                        scheduled_time=scheduled_time
                    )
                    if result['success']:
                        st.success("✅ 업로드 완료!")
                        if result.get('thumbnail_error'):
                            st.warning("⚠️ 영상은 업로드되었으나 썸네일 설정에 실패했습니다. 유튜브 스튜디오 → 콘텐츠에서 해당 영상을 열어 썸네일을 수동으로 지정해 주세요.")
                        st.markdown(f"**링크:** [{result['url']}]({result['url']})")
                        if scheduled_time:
                            st.info("📅 예약 설정됨. 유튜브 스튜디오 → 콘텐츠에서 해당 영상을 열면 '예약됨'으로 표시됩니다. 설정한 시각(한국 시간)에 자동 공개됩니다.")
                        st.balloons()
                        save_upload_record(
                            result['video_id'],
                            st.session_state.get('metadata', {}).get('title', ''),
                            datetime.now(),
                            is_scheduled=bool(scheduled_time),
                            scheduled_publish_at=scheduled_time
                        )
                        st.session_state['video_path'] = None
                        st.session_state['approved'] = False
                        st.session_state['metadata'] = {}
                        st.session_state['selected_thumbnail'] = None
                    else:
                        st.error(f"❌ 업로드 실패: {result.get('error', '알 수 없는 오류')}")
                except Exception as e:
                    st.error(f"❌ 업로드 중 오류 발생: {e}")

# ========================================
# 탭 5: 업로드 내역
# ========================================
with tab5:
    st.subheader("📊 업로드 내역")
    if st.button("🔄 새로고침", key="refresh_history"):
        st.rerun()

    history = get_upload_history()

    if not history.empty:
        display_cols = ['title', 'upload_time', 'upload_type_kr', 'scheduled_publish_at', 'url']
        available = [c for c in display_cols if c in history.columns]
        st.dataframe(
            history[available],
            column_config={
                "title": "제목",
                "upload_time": st.column_config.DatetimeColumn(
                    "업로드한 시각",
                    format="YYYY-MM-DD HH:mm"
                ),
                "upload_type_kr": st.column_config.TextColumn("업로드 유형"),
                "scheduled_publish_at": st.column_config.TextColumn("예약 공개 시각 (KST)"),
                "url": st.column_config.LinkColumn("링크")
            },
            hide_index=True,
            use_container_width=True
        )
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 총 업로드", len(history))
        with col2:
            try:
                ut = pd.to_datetime(history['upload_time'])
                this_month = history[ut.dt.to_period('M') == pd.Timestamp.now().to_period('M')]
            except Exception:
                this_month = history.head(0)
            st.metric("📅 이번 달", len(this_month))
        with col3:
            try:
                ut = pd.to_datetime(history['upload_time'])
                today_df = history[ut.dt.date == pd.Timestamp.now().date()]
            except Exception:
                today_df = history.head(0)
            st.metric("📆 오늘", len(today_df))
    else:
        st.info("아직 업로드 내역이 없습니다.")
        st.markdown("영상을 생성하고 업로드해보세요! 👈")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        🔮 운세 Shorts 자동 생성기 | Made with ❤️ using Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
