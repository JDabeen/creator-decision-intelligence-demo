> **v2.2 안정화 릴리스:** `RELEASE_NOTES_V2_2.md`를 먼저 읽어주세요. API 429 대응, 근거 재사용, 비밀정보 보호, 탐색/제작 확정 분리, 관측 그래프가 핵심입니다.

# YouTube Content Consultant — Topic-first Research Agent (v1.8.1)

**Problem:** For a real Korean English-teaching YouTube channel, decide *which topic is worth producing next*, with traceable evidence instead of generic AI brainstorming.

## User experience (4 screens)

`Find topics` → `Compare A / Hermes B` → `Select one & deep research` → `Optional script`

- **A / Baseline:** YouTube Data API, channel history, RAG, existing market analysis.
- **B / Hermes:** Frozen observable market/channel evidence from the same run **plus independent web-tool research**. B cannot see A's topic shortlist or new script.
- **Human decides:** Either set of recommendations may be rejected. Optional draft comes only after topic selection and research coverage checks.

**Important:** A/B means **comparing two workflows' suggestions**, not a controlled comparison of model quality and not YouTube's randomized A/B experiment. A and B have different additional information and tools. An observed URL proves neither demand nor future views.

## Install on Windows

1. Unzip all files. Copy `.env.example` to `.env` and enter `YOUTUBE_API_KEY` and `OPENAI_API_KEY`.
2. Open Docker Desktop, confirm **Engine running**.
3. Double-click **`0_START_WITH_HERMES.bat`**. On first run, dependencies are installed with pinned top-level versions.
4. Browser opens the local Streamlit application; use **`다음 주제 찾기`**.

No new PC, other server or Windows Chrome login required. The gateway is bound to `127.0.0.1:8642`. The Docker container does not mount Windows personal directories, Chrome profiles or the Docker socket. It does have network access and a model API key; **isolation cannot guarantee zero data disclosure**. Do not give the agent passwords. Do not publish `.env` or private research files.

## Validation and public portfolio

- Run `7_OFFLINE_TEST.bat` to test Python syntax, topic provenance, failure handling, mocked Hermes connection and workflow navigation **without API charges**.
- After **one real successful A/B run**, `8_PORTFOLIO_EXPORT.bat` produces `portfolio_public/evaluation_summary.json` with only counts, evidence flags and hashes. Raw `evidence.json`, script excerpts and Studio inputs are local and **must not go into a public Git repository**.
- E2E with Windows Docker/YouTube/Hermes requires live credentials and network; passing offline tests is **not** E2E proof.
- Pinning direct dependencies is not a fully locked transitive dependency graph. A production deployment should add platform-specific lockfiles and CI.

## Evidence policy

Each recommendation has a deterministic provenance audit. A recommendation is connected to observed market video IDs (A) or URLs actually returned by web tools (B). The audit never predicts views or certifies market demand. Missing links are labeled as insufficient. Hermes retries one targeted search if fewer than two topics cite observed URLs; if none can be grounded, the B comparison **fails closed** while A is retained.

User data is stored separately (`Desktop/youtube_consultant_data` by default); deleting app files does not automatically delete that folder. The static Audience Snapshot is **not a live Studio sync**. Published script excerpts may cover only the first 950 characters of up to 60 fetched long-form transcripts; catalog up to 200 public videos.

## Engineering choices and limits

The project is an applied **decision-support prototype**, not a verified content-ranking product. It combines external observations, RAG, a tool-using research agent, a human decision checkpoint, and a recorded reproducible audit. A useful next evaluation is to track selected topics at days 7/28 and compare against a baseline while accounting for release date, packaging (title/thumbnail), impression volume and audience differences.

All historical implementation documentation is in `docs/README_OLD_VERSIONS.md` and `docs/legacy/`. See `VALIDATION.md` for known limitations.

## Signature format & search interest (v1.8.1)

Each A/B topic recommendation now distinguishes the **topic / viewer demand** from a **repeatable video format hypothesis** and a concrete format variation. This is explicitly a hypothesis, not a claim that one viral video proved the format's causal impact. No forced mix of three strategy routes. The topic comparison detail panel shows an optional **Google Trends (YouTube Search, KR, 12 months)** link. The app **does not automatically obtain absolute keyword volume or numeric Google Trends results**; never equate 0–100 relative interest with projected views or Home/Browse demand.

The next evaluation should compare 2–3 uploads using a candidate format and record 7-/28-day impression, CTR, retention, and distribution context. Do not add new API subscriptions merely to produce unsupported scores.


## v1.9: 채널 운영 상담 · 자동 로컬 누적

- 기존 **① 주제 찾기 → ② 비교·선택 → ③ 심층 조사 → ④ 대본**은 그대로 유지합니다.
- 사이드 메뉴 **채널 운영 상담 · 전략 기록**에서 자유롭게 업로드 주기·교육 전문성·시그니처 형식·경쟁 전략을 질문할 수 있습니다. OpenAI API 호출 비용이 발생할 수 있습니다.
- 사용자의 질문과 AI 답변은 즉시 `바탕화면/YT_Channel_Strategy/consultations.json`에 기록됩니다. **AI 답변은 미검증 제안입니다.** 운영자가 '이 판단을 내 운영 원칙으로 채택'할 때만 `accepted_decisions.json`에 별도 기록되며 다음 A/Hermes 주제 추천의 맥락으로 전달됩니다.
- 사용자 수정이 가능한 `operating_principles.txt`도 양쪽 추천에 전달됩니다. 사용자 전략 선호는 시장 수요의 증거가 아닙니다.
- 앱을 **열고 새 Streamlit 실행이 발생할 때** 공개 5–60분 영상의 업로드일·누적 조회수·좋아요·댓글을 **24시간에 한 번 이하**로 YouTube Data API에서 수집해 날짜별 JSON에 보존합니다. 이전 값이 존재하면 직전 스냅샷 이후 변화를 계산합니다.
- **앱을 꺼두었을 때에는 백그라운드 수집하지 않습니다.** 과거 7일/28일 수치를 소급 생성하지 않습니다. Studio의 CTR·노출·시청 지속률 등은 YouTube Data API API key만으로 수집되지 않으므로 수동 CSV 입력이 필요합니다.
- 추천 주제와 게시된 영상이 동일한지 자동으로 추정하지 않습니다. 둘을 한 번 연결하면 그 뒤의 공개 성과는 `video_id`를 이용해 자동 추적합니다.
- 기본 저장 위치는 Windows가 가리키는 바탕화면의 `YT_Channel_Strategy`. 코드 ZIP, `.env`, 기본 `youtube_consultant_data` 폴더와 분리된 개인정보가 포함된 자료입니다. GitHub에 업로드하지 마세요.
- **테스트:** `7_OFFLINE_TEST.bat`. 실제 Windows·YouTube API·Docker E2E는 별도로 검증해야 합니다.

- 상담 시 로컬 전략 기록과 저장된 공개 성과, 수동 Studio 요약, 기존 시장 패턴 일부가 **OpenAI API로 전송됩니다**. 로컬 기록 보관과 클라우드 모델 사용은 다른 문제입니다. 민감 정보를 적지 마세요.


## v2.0 — 근거 중심 의사결정 기록 (실험 기능)

- 목표: 공감형 상담이 아니라 **가설 → 사전 기록 → 공개 성과 관측 → 반론/수정**의 축적.
- 다음 주제에서 `이 주제로 더 찾기` 선택하면 바탕화면 `YT_Channel_Strategy/topic_choices.json`에 당시 주제/전략/영상 표본을 자동 저장합니다.
- 공개 영상 연결 뒤에는 7일 및 28일 부근에 실제로 수집된 스냅샷만 평가합니다. 사후 조회수로 과거를 역산하지 않습니다. 앱을 끈 동안 예약 수집은 하지 않으며, 스냅샷은 앱을 사용할 때만 갱신됩니다.
- N>=8이 될 때에만 과거 *채널 전체*의 28일 조회수 분포(20–80백분위)를 표시합니다. 이는 이번 주제의 추정 조회수, 신뢰구간, 예측 정확도 **아닙니다**.
- 기존 YouTube 시장 영상 후보의 관련 영상 수/조회수는 검색량이 아닌 **소비 대리지표**입니다. 검색 선정 편향이 있고, 검색량을 직접 제공하지 않습니다.
- Google Trends의 웹 화면 상대 관심도(0–100)는 수동 비교 링크만 제공하며 아직 수집·보존하지 않습니다. 공식 Trends API alpha 접근 권한이 없는 상태에서 실시간 검색량을 자동 수집한다고 주장하지 않습니다.
- AI 전략 검토는 네 의견에 자동 동조하는 상담이 아니며 관측값/가설/반론/중단 기준을 분리하도록 설계했습니다. 모델의 판단력 향상은 자동 보장되지 않습니다.
- v1.9과 동일한 Docker 설정 및 기존 `YT_Channel_Strategy` 폴더를 사용하므로 업데이트해도 이전 상담/원칙/공개 성과는 보존합니다.

### 선택적 실측 검색 관심도 (외부 API 비용 주의)

- `.env`에 `SERPAPI_API_KEY`를 설정하면 **주제 탐색 버튼 실행 시** 최대 두 번의 SerpApi Google Trends 조회가 자동 실행됩니다. 키가 없으면 추가 API 비용/요청 없이 YouTube 영상 소비 표본만 활용합니다.
- SerpApi는 Google의 공식 API가 **아니고 제3자 유료 API**이며 별도 가입·이용 조건·요금 확인이 필요합니다. 사용 여부는 전적으로 선택입니다.
- `geo=KR`, `gprop=youtube`, `date=today 12-m`이고 상대 관심도 0~100이므로 **절대 검색량이 아닙니다.** 5개씩 나뉜 별도 API 요청 사이의 점수는 비교하지 않습니다.
- 같은 6개 주제 구성이면 7일 동안 `YT_Channel_Strategy/trend_snapshots`의 캐시를 재사용합니다. 주제 구성이 바뀌면 추가 과금 호출이 발생할 수 있습니다.
- API 키는 기록이나 GitHub용 산출물에 저장하지 않습니다. 키가 없거나 호출에 실패하면 수요를 지어내지 않고 미측정으로 표시합니다.

### 앱을 켜지 않아도 공개 조회수를 수집하려면 (Windows 선택 기능)

- 1회 설치 이후 `9_ENABLE_DAILY_TRACKING.bat`을 실행하면 **매일 오전 9시, 컴퓨터가 켜져 있을 때** 공개 채널 메타데이터만 저장하는 Windows 작업을 등록합니다. 이 배치 파일을 실행하기 전에는 자동 예약 작업이 설치되지 않습니다.
- Google YouTube Data API만 사용하며 LLM·Hermes·SerpApi를 호출하지 않습니다. 로그는 바탕화면 `YT_Channel_Strategy/daily_sync_status.txt`에 저장됩니다.
- PC가 꺼져 있거나 잠자기 상태면 실행이 생략될 수 있습니다. 자동 재시도/항상 실행을 보장하지 않으며 7±1일·28±1일 창을 놓친 영상은 정확한 시점 조회수 산출이 불가능합니다.
- 기존 프로그램 폴더를 삭제하거나 옮기면 예약 작업이 실패합니다. **새 설치 폴더에서 `9_ENABLE_DAILY_TRACKING.bat`을 다시 실행**해 경로를 갱신하세요. 필요 없으면 `9_DISABLE_DAILY_TRACKING.bat`으로 해제합니다.
- 관리자 권한이나 추가 패키지가 필요하지 않을 수 있지만, Windows 조직 정책/보안 설정에 따라 작업 등록이 거절될 수 있습니다. 해당 설치는 Windows PC에서 아직 직접 검증되지 않았습니다.

## v2.1 · Comment Intelligence (2026-10-23)

- **Raw, absolute** public comment totals are a first-class channel observation. **No comments/views ratio is calculated** in the new feature.
- In **채널 전략 검증 · 누적 학습 → 댓글 기반 실제 반응**, inspect the absolute ranking of all channel long-form videos. Select a video and optionally sample **up to 60 public top-level comments**, ranked by YouTube's `relevance` option, for tentative LLM classification. One manual analysis call can use both YouTube and OpenAI paid/API quota.
- Category labels include specific understanding, described application, substantive discussion, requests for more teaching, explicit course/product inquiries, generic praise, questions, corrections and other.
- Persistent files are located in **Desktop/YT_Channel_Strategy/comment_reviews/**, *outside* the app installation. This feature stores **only classified category counts, sample size, video ID, provenance and limitations**; commenter identities and raw comment text are not written to these files.
- Absolute counts are also included as **bounded, clearly labeled evidence** for A recommendations and Hermes B. Neither comment volume nor LLM categories proves a better video, customer purchase, or causal impact. Video age, replies, distribution and moderation matter.
- A **separate GitHub-safe** Streamlit demo is in `public_demo/` (also packaged as a dedicated public repo). All its data is intentionally synthetic; it does not call live APIs or run Hermes.
- **Not verified**: Windows runtime, paid model categorization, Docker/Hermes live integrations, cloud deployment, and actual business conversion lift.
