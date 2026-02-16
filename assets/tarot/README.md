# 타로 카드 덱 이미지

## 저작권 없는 소스 (Public Domain)

### 라이더 웨이트 (Rider-Waite) - 1909년
- **소스**: [Internet Archive - rider-waite-tarot](https://archive.org/details/rider-waite-tarot)
- **저작권**: 퍼블릭 도메인 (미국·영국)
- **다운로드**: `타로덱_다운로드.bat` 실행

## 폴더 구조 (덱마다 앞장 이미지 다름)

```
tarot/
  deck_01/   ← 라이더 웨이트 (Rider-Waite)
  deck_02/   ← Etteilla I (1789)
  deck_03/   ← Etteilla II (1850)
  deck_04/   ← Etteilla Grimaud (1890)
  deck_05/   ← Etteilla III (1865)
```

각 폴더마다:
- `back.png` - 카드 뒷장 (스크립트가 자동 생성)
- `00_fool.png` ~ `77_pentacles_king.png` - 78장 카드

## 다운로드 방식
- **배치 파일** (`타로덱_다운로드.bat`) 실행 시마다 **아직 없는 다음 덱**을 다운로드
- deck_01 → deck_02 → … → deck_05 순서
- 5개 덱 모두 있으면 "모든 덱이 이미 다운로드되어 있습니다" 메시지

## 영상 생성 시
- `modules/tarot_deck.get_random_deck_path()` 사용
- 존재하는 덱 중 **랜덤**으로 선택

## 이전에 같은 덱(라이더 웨이트)만 받았을 경우
deck_02~05가 라이더 웨이트와 동일한 앞장이라면, 해당 폴더를 **삭제**한 뒤
`타로덱_다운로드.bat`을 다시 실행하면 Etteilla 등 다른 덱으로 받을 수 있습니다.
