# -*- coding: utf-8 -*-
"""
운세 Shorts 자동 생성기 - Streamlit 메인 앱
영상 생성 → 미리보기/승인 → 메타데이터 → 썸네일 → YouTube 업로드
"""
import streamlit as st
import pandas as pd
import config
from datetime import datetime, time
from pathlib import Path

from modules.video_generator import generate_fortune_video
from modules.metadata_generator import (
    generate_titles,
    generate_description,
    generate_hashtags,
    generate_fortune_text,
    set_openai_api_key,
)
from modules.thumbnail_creator import generate_thumbnails
from modules.image_generator import generate_background_image
from modules.youtube_uploader import (
    upload_video,
    save_upload_record,
    get_upload_history,
    init_database,
)

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

    st.markdown("---")
    st.subheader("🚀 빠른 설정")
    auto_meta = st.toggle("메타데이터 자동 생성", value=True)
    auto_hashtags = st.toggle("해시태그 자동 생성", value=True)
    auto_thumbnail = st.toggle("썸네일 자동 생성", value=True)

    st.markdown("---")
    with st.expander("📖 사용 가이드"):
        st.markdown("""
        **1단계: 영상 생성**
        - 배경 테마 선택
        - 퍼즐 모양/방향 선택
        - 운세 종류 선택
        - 영상 생성 버튼 클릭

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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📹 영상 생성",
    "📝 메타데이터",
    "🎨 썸네일",
    "📤 업로드",
    "📊 업로드 내역"
])

# ========================================
# 탭 1: 영상 생성
# ========================================
with tab1:
    st.subheader("영상 생성 설정")

    col1, col2 = st.columns(2)

    with col1:
        background_theme = st.selectbox(
            "🖼️ 배경 테마",
            ["우주", "자연", "도시", "판타지"],
            help="영상의 배경 이미지 테마"
        )
        puzzle_shape = st.selectbox(
            "🧩 퍼즐 모양",
            ["하트", "별", "달", "클로버"],
            help="퍼즐 조각의 모양"
        )

    with col2:
        direction = st.selectbox(
            "↔️ 퍼즐 방향",
            ["위→아래", "아래→위", "좌→우", "우→좌"],
            help="퍼즐 조각이 이동하는 방향"
        )
        fortune_types = st.multiselect(
            "🎯 운세 종류",
            ["금전운", "애정운", "건강운", "총운"],
            default=["총운"],
            help="생성할 운세 종류 (복수 선택 가능)"
        )

    st.markdown("---")

    if st.button("🎬 영상 생성하기", type="primary", use_container_width=True):
        if not fortune_types:
            st.error("❌ 운세 종류를 최소 1개 선택해주세요!")
        else:
            # 배경 이미지는 매번 DALL-E로 새로 생성 (매번 다른 이미지)
            with st.spinner("🖼️ 배경 이미지 생성 중... (DALL-E, 매번 다른 이미지, 약 10~20초)"):
                background_path = generate_background_image(background_theme)

            if background_path and background_path.exists():
                fortune_type = fortune_types[0]

                with st.spinner("🤖 운세 생성 중..."):
                    fortune_text = generate_fortune_text(fortune_type)

                music_path = config.MUSIC_DIR / "cheerful.mp3"
                if not music_path.exists():
                    music_path = None
                    st.warning("⚠️ 배경음악 파일이 없습니다. 음악 없이 생성됩니다.")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = config.OUTPUT_DIR / f"fortune_{timestamp}.mp4"

                with st.spinner("🎥 영상 생성 중... (약 30초 소요)"):
                    try:
                        video_path = generate_fortune_video(
                            background_path=str(background_path),
                            puzzle_shape=puzzle_shape,
                            direction=direction,
                            fortune_text=fortune_text,
                            fortune_type=fortune_type,
                            music_path=str(music_path) if music_path else None,
                            output_path=str(output_path)
                        )
                        st.session_state.video_path = video_path
                        st.session_state.fortune_type = fortune_type
                        st.session_state.fortune_text = fortune_text
                        st.success("✅ 영상 생성 완료!")
                    except Exception as e:
                        st.error(f"❌ 영상 생성 실패: {e}")
            else:
                st.error("❌ 배경 이미지 생성에 실패했습니다. OpenAI API 키·크레딧을 확인해주세요.")

    if st.session_state.video_path:
        st.markdown("---")
        st.subheader("📹 미리보기")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.video(st.session_state.video_path)
        with col2:
            st.info(f"**운세:** {st.session_state.get('fortune_text', '')}")
            st.info(f"**파일:** {Path(st.session_state.video_path).name}")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 마음에 들어요!", use_container_width=True):
                st.session_state.approved = True
                st.success("✅ 승인되었습니다! 메타데이터 탭으로 이동하세요.")
                st.balloons()
        with col2:
            if st.button("🔄 다시 생성", use_container_width=True):
                st.session_state.video_path = None
                st.session_state.approved = False
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
        if auto_meta:
            with st.spinner("제목 생성 중..."):
                try:
                    titles = generate_titles(fortune_type, today)
                except Exception:
                    titles = [
                        f"🔮 {today} 오늘의 {fortune_type} | 일시정지 필수!",
                        f"💫 {today} {fortune_type} 확인하세요",
                        f"✨ {today} {fortune_type} | 퍼즐 맞추고 운세 보기"
                    ]
            selected_title = st.selectbox("제목 선택", titles, key="title_select")
            col1, col2 = st.columns([4, 1])
            with col1:
                final_title = st.text_input(
                    "제목 수정",
                    selected_title,
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
            with st.spinner("설명 생성 중..."):
                description = generate_description(fortune_type, today)
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
    if not st.session_state.get('video_path'):
        st.info("👈 먼저 영상을 생성해주세요.")
    else:
        st.subheader("🎨 썸네일 선택")
        if auto_thumbnail:
            title_for_thumb = st.session_state.metadata.get('title', '오늘의 운세')
            with st.spinner("썸네일 생성 중..."):
                try:
                    thumbnails = generate_thumbnails(
                        st.session_state.video_path,
                        title_for_thumb
                    )
                    st.success(f"✅ 썸네일 {len(thumbnails)}개 생성 완료")
                    cols = st.columns(3)
                    for i, thumb_path in enumerate(thumbnails):
                        with cols[i]:
                            st.image(thumb_path, caption=f"버전 {i+1}")
                            if st.button(
                                "✅ 선택",
                                key=f"thumb_{i}",
                                use_container_width=True
                            ):
                                st.session_state.selected_thumbnail = thumb_path
                                st.success(f"✅ 버전 {i+1} 선택됨!")
                                st.rerun()
                    if st.session_state.selected_thumbnail:
                        st.markdown("---")
                        st.subheader("선택된 썸네일")
                        st.image(st.session_state.selected_thumbnail, width=400)
                except Exception as e:
                    st.error(f"❌ 썸네일 생성 실패: {e}")
        else:
            uploaded_thumb = st.file_uploader(
                "썸네일 업로드 (1280x720 권장)",
                type=["jpg", "png"],
                key="thumb_upload"
            )
            if uploaded_thumb:
                thumb_path = config.THUMBNAILS_DIR / f"custom_{uploaded_thumb.name}"
                with open(thumb_path, "wb") as f:
                    f.write(uploaded_thumb.getbuffer())
                st.session_state.selected_thumbnail = str(thumb_path)
                st.image(thumb_path, caption="업로드된 썸네일", width=400)
                st.success("✅ 썸네일이 업로드되었습니다!")

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
            st.info(f"📅 예약 시간: {scheduled_time.strftime('%Y-%m-%d %H:%M')}")

        st.markdown("---")
        with st.expander("📋 업로드 정보 최종 확인", expanded=True):
            st.write("**영상:**", Path(st.session_state.video_path).name)
            st.write("**제목:**", st.session_state.metadata.get('title', ''))
            desc = st.session_state.metadata.get('description', '')
            st.write("**설명:**", desc[:100] + "..." if len(desc) > 100 else desc)
            st.write("**해시태그:**", len(st.session_state.metadata.get('tags', [])), "개")
            st.write(
                "**썸네일:**",
                "✅ 선택됨" if st.session_state.get('selected_thumbnail') else "❌ 미선택"
            )
            st.write("**공개 설정:**", privacy_kr)
            if scheduled:
                st.write("**예약 시간:**", scheduled_time.strftime('%Y-%m-%d %H:%M'))

        st.markdown("---")
        upload_disabled = not st.session_state.get('selected_thumbnail')
        if upload_disabled:
            st.warning("⚠️ 썸네일을 선택해주세요!")

        if st.button(
            "📤 유튜브에 업로드",
            type="primary",
            use_container_width=True,
            disabled=upload_disabled
        ):
            with st.spinner("업로드 중... (1-2분 소요)"):
                try:
                    result = upload_video(
                        video_path=st.session_state.video_path,
                        title=st.session_state.metadata['title'],
                        description=st.session_state.metadata['description'],
                        tags=st.session_state.metadata['tags'],
                        thumbnail_path=st.session_state.selected_thumbnail,
                        privacy=privacy,
                        scheduled_time=scheduled_time
                    )
                    if result['success']:
                        st.success("✅ 업로드 완료!")
                        st.markdown(f"**링크:** [{result['url']}]({result['url']})")
                        st.balloons()
                        save_upload_record(
                            result['video_id'],
                            st.session_state.metadata['title'],
                            datetime.now()
                        )
                        st.session_state.video_path = None
                        st.session_state.approved = False
                        st.session_state.metadata = {}
                        st.session_state.selected_thumbnail = None
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
        st.dataframe(
            history[['title', 'upload_time', 'url']],
            column_config={
                "title": "제목",
                "upload_time": st.column_config.DatetimeColumn(
                    "업로드 시간",
                    format="YYYY-MM-DD HH:mm"
                ),
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
