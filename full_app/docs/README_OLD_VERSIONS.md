# v1.7 · 주제 찾기부터 대본까지 4단계 화면

**`다음 주제 찾기` → `A/Hermes 주제 비교·선택` → `이 주제로 더 찾기` → `대본 만들기(선택)`** 순서입니다. 화면이 누적되지 않고 현재 단계 하나만 표시됩니다. Hermes는 첫 조사 버튼 안에서 함께 실행되며, 검색 실패 시 A 추천만 남고 비교 화면에서 원인을 확인할 수 있습니다. 자세한 설명은 `README_1_7_사용자흐름.md`를 참고하세요.

---

# 최신: v1.6 · 주제 추천 비교 중심 포트폴리오

**시작: `0_START_WITH_HERMES.bat` → 첫 화면의 시장 추천 → Hermes의 독립 주제 추천 비교 → 사람이 주제 선택 → 선택적으로 Deep Research/대본 생성.**

최신 안내는 **`README_1_6_TOPIC_FIRST.md`**입니다. 아래에는 이전 시스템의 구현 및 사용 설명을 참고용으로 보존합니다. 이전 v1.5의 대본 A/B 실험은 지금의 기본 워크플로가 아닙니다.

---

> **v1.2 새 기능 안내**: `README_1_2_시장주제_검증_및_Hermes_작동확인.md`를 먼저 읽으세요. 이번 버전은 Hermes 실제 도구 사용 기록, 경쟁 영상 기반 주제 평가, 새 주제 재조사, 간결한 대본 재설계를 추가합니다. 기존 API 키·개인 캐시는 ZIP에 포함되지 않습니다.

# YouTube Content Consultant — CURRENT COMPLETE

실사용 기준 통합본입니다. 기존 정상 작동 v2.4의 `1_SETUP_ONCE.bat` / `2_RUN_APP.bat` 실행 구조는 그대로 유지했습니다.

## 지금 할 수 있는 것

### 1. 다음 콘텐츠 찾기
- **Pulling**: 사람을 모으는 주제 발견을 우선
- **Key**: 신뢰·설득·상품 구매 이유를 만드는 콘텐츠를 우선
- Audience Neighborhood: 사용자가 Studio의 **내 시청자가 보는 다른 채널 5~10개**를 직접 넣으면 그 채널들의 최근 롱폼을 스캔
- 국내 검색 확장 + Absolute Winner / Channel Outlier / Subscriber Breakout / Recent Breakout 분리
- 여러 독립 채널에서 반복되는 주제와 단일 Recent Breakout을 구분
- **Global Reference**: 사용자가 넣은 해외 영어교육 채널에서 주제·Knowledge·Explanation·Format 기회를 찾고 국내 시장/내 채널과 비교
- 해외 원본을 번역·복제하지 않고 일반 영어 개념과 전이 가능한 설명 원리만 사용

### 2. Deep Research
- 시장 댓글 + **실제 Transcript** 수집
- Transcript Coverage 표시
- 기준 미달이면 **Deep Research / Draft 중단**. 제목·조회수만으로 깊이 조사한 척하지 않음
- Transcript 기반 Content DNA 추출
- 고정된 `강의형/훈련형` 분류가 아니라 실제 데이터의 공통 구조를 클러스터링
- Content Pattern Memory에 누적
- Explanation Atom / Knowledge Gap / Format Gap / Core Edge 설계
- 내 채널 BM25 + Semantic Retrieval + RRF Hybrid RAG와 비교

### 3. 대본 완성
- Structure → Draft A
- Draft A에 사람 피드백 반영
- **Critic Agent**가 내부 Research를 먼저 읽음
- 정확성/실제 영어 사용 검증이 더 필요하면 선택적으로 웹 검색
- Draft B 생성
- Draft A/B 차이 비교
- 사람 피드백 → Final Script

### 4. Studio / Reference 데이터 직접 추가
사이드바의 **`데이터 입력 · Studio`**에서 관리합니다.

- `참고 채널`
  - `audience_neighbor`: Studio → 분석 → 시청자층 → 내 시청자가 보는 다른 채널
  - `korean_reference`: 직접 추가한 한국 영어교육/경쟁 채널
  - `global_reference`: 해외 영어교육 참고 채널
- `내 영상 성과`: 7일 / 28일 / 현재 Studio 성과
- `추천 옆자리`: 내 영상이 실제로 어떤 영상·채널 옆에 추천됐는지
- `Audience`: 연령/성별/지역/기기 snapshot
- `전략 가설`: 검증 중인 가설. 하드코딩된 진실로 취급하지 않음
- `선택 기록`: 어떤 추천을 더 파봤고 Draft까지 만들었는지

수동 데이터는 기본적으로 다음 위치에 영구 저장됩니다.

```text
바탕화면\youtube_consultant_data\manual
```

앱 버전을 바꿔도 이 폴더는 지우지 마세요.

## 첫 실행

가장 간단한 방법은 **`0_START_HERE.bat`을 실행하는 것**입니다. 첫 실행이면 기존 `1_SETUP_ONCE.bat`을 호출하고, 설치가 끝난 뒤 앱을 실행합니다.

수동으로 하려면:

1. ZIP 압축 해제
2. 기존 `.env`가 있으면 이 폴더에 복사
3. 처음 한 번 `1_SETUP_ONCE.bat`
4. 이후 `2_RUN_APP.bat`
5. 앱 사이드바 → **데이터 입력 · Studio** → `audience_neighbor` 5~10개 입력
6. 해외 참고 채널이 있으면 `global_reference`로 입력
7. 메인 화면에서 `시장과 내 채널에서 다음 콘텐츠 찾기`

`.env` 최소값:

```env
YOUTUBE_API_KEY=...
OPENAI_API_KEY=...
```

선택값:

```env
# 기본은 바탕화면\youtube_consultant_data
# YRA_DATA_DIR=C:/Users/USERNAME/Desktop/youtube_consultant_data

# Draft B Critic. 비우면 앱 기본 LLM 사용
YRA_CRITIC_MODEL=
# 1=필요하면 웹 검증 허용 / 0=내부 Research만
YRA_CRITIC_WEB_SEARCH=1
```

## 기존 캐시 가져오기

예전 프로젝트에 Transcript/댓글/LLM cache가 있으면 `4_IMPORT_OLD_CACHE.bat`을 실행해 예전 `cache` 폴더 경로를 넣습니다.

## 데이터 폴더 바로 열기

`5_OPEN_DATA_FOLDER.bat`

## Public Demo

`3_RUN_PUBLIC_DEMO.bat`은 API 없는 포트폴리오용 정적 데모입니다. 실사용은 `2_RUN_APP.bat`입니다.

## 중요한 해석 원칙

- 연령과 영어 수준을 동일시하지 않음
- 조회수/구독자 배수 하나만으로 `주제의 힘`이라고 단정하지 않음
- 절대 조회, Channel Outlier, Subscriber Breakout, Recent Breakout은 서로 다른 신호
- 여러 채널 반복 수요는 강한 신호지만, 단일 최근 폭발과 Global Transfer를 하드컷으로 버리지 않음
- 시장 Transcript의 인기 설명도 영어 문법의 최종 사실 근거는 아님
- 모르는 값은 `모름`으로 남김
- 모델의 추천 판단과 실제 CTR/노출/시청/리드 성과를 구분함

## Reference 문서

`reference/`에는 이번 설계의 근거로 사용한 사용자 제공 문서를 보존했습니다.

- `channel_evidence_strategy_20261011.txt`: 틀린영어의 실제 성과/전략 가설
- `system_spec_20261011.txt`: Research Agent 제품 요구사항

## 검증 상태

이 패키지는 Python 문법 검사와 로컬 smoke test를 수행합니다. 실제 YouTube/OpenAI 호출은 사용자의 API 키, Windows 환경, YouTube Transcript IP 상태에 따라 달라지므로 그 부분은 사용자 환경에서 처음 end-to-end 검증됩니다.

---
## v1.1 — 독립 재설계 + 간결한 A/B 결과 화면 (2026-10-18)

- `Draft B` 단계에 **독립 재설계·새 대본** / **기존 초안 정교화** 선택 추가.
- 독립 재설계 모드에서는 Hermes가 새로운 대본의 콘셉트·구성·외부 검증 필요성에 대해
  비평/기획을 수행하고, **기존 OpenAI 대본 작성기**가 그 결과로 Draft B를 생성합니다.
  Hermes가 직접 전체 Draft B를 쓰는 구조로 바뀐 것은 아닙니다.
- 결과가 나오면 먼저 변경요약과 선택 구간의 A/B 비교를 보여줍니다. 전체 원문과
  Critic Report는 별도 접기 패널로 옮겼습니다.
- 외부 웹 검색은 모델이 실제 도구 호출을 수행하고 API 응답에 흔적을 남긴 경우에만
  '호출 확인'으로 표기합니다. 검색 성공 보장은 아닙니다. 검색 제공자 인증이 필요하면
  `.env`에 `TAVILY_API_KEY=` 또는 `EXA_API_KEY=`를 선택적으로 추가할 수 있습니다.
- 비교 없이 출력만 과하게 늘리거나 근거를 지어내지 말라는 프롬프트 규칙을 유지합니다.
- 자세한 설치·제한 사항: `8_이번업데이트_읽어주세요.txt`
