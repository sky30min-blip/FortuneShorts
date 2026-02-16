# -*- coding: utf-8 -*-
"""GPT 공감 멘트 생성 테스트 - 랜덤 5개 주제로 검증"""
import random
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from modules import theme_phrases_db
from modules.metadata_generator import generate_empathy_ment


def main():
    if not config.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY가 .env에 설정되어 있는지 확인하세요.")
        return

    # 4테마 80개에서 랜덤 5개 추출
    all_titles = []
    for theme in theme_phrases_db.VIRAL_THEME_NAMES:
        all_titles.extend(theme_phrases_db.get_phrases(theme) or [])
    random.shuffle(all_titles)
    picked = all_titles[:5]

    print("=" * 60)
    print("GPT 공감 멘트 생성 테스트 (랜덤 5개 주제)")
    print("=" * 60)

    for i, topic in enumerate(picked, 1):
        print(f"\n[{i}] 주제: {topic}")
        try:
            ment = generate_empathy_ment(topic)
            print(f"    공감 멘트: {ment}")
        except Exception as e:
            print(f"    ❌ 오류: {e}")

    print("\n" + "=" * 60)
    print("완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
