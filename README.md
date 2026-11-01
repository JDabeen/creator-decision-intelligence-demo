# Creator Decision Intelligence
### Evidence-first YouTube Research & Script Workflow

**Applied AI · Retrieval-Augmented Generation · Decision Support · Local-first Research Prototype**

> **좋은 주제를 감으로 선택하는 대신, 어떤 근거로 제작해야 하는지 판단한다.**  
> 실제 영어교육 유튜브 채널을 운영하며 겪은 반복적 조사·판단 비용을 줄이기 위해 개발한 개인 AI 크리에이터 컨설턴트입니다.

## ▶ 공개 데모 시연 영상

https://github.com/user-attachments/assets/d79eaee2-9893-4e34-bd19-6b4d91ca16f0

[데모 시연 영상 보기](https://github.com/user-attachments/assets/d79eaee2-9893-4e34-bd19-6b4d91ca16f0) · [브라우저에서 데모 체험하기](https://jdabeen.github.io/cdi-demo.html)

*실제 프로그램의 단계와 의사결정 흐름을 가상 데이터로 재현한 데모입니다. 실시간 YouTube·Hermes·RAG 호출은 수행하지 않습니다.*

## 01. 문제 정의

유튜브 영상을 하나 제작하려면 경쟁 영상과 시장 수요를 조사하고, 조회수·댓글·자막을 읽고, 내 채널의 기존 설명과 비교하며, 대본까지 완성해야 합니다.

일반적인 AI 브레인스토밍은 **그럴듯한 추천**을 제시하지만, **그 추천이 관측 자료에 연결되는지** 별도 검증이 필요합니다.

**프로젝트 목표:** 시장 조사 → 독립 추천 비교 → 근거 감사 → 선택 주제의 심층 조사 → 대본 A/B → 제작자 최종 확정을 하나의 화면 흐름으로 연결하는 것.

## 02. 핵심 워크플로

| 단계 | 핵심 구현 | 사용자에게 제공하는 가치 |
| --- | --- | --- |
| **Discover** | YouTube Data API, 채널 기준 Outlier / Recent 신호 | 제작 후보 발견 |
| **Compare** | 채널 분석·Hybrid RAG 기반 A vs 별도 웹 조사 Hermes B | 근거가 다른 추천 비교 |
| **Research** | 댓글·Transcript, Content DNA, Knowledge/Format Gap | 설명 소재 및 차별점 도출 |
| **Write** | 구조 설계 → Draft A → Critic → 선택적 Draft B | 촬영 가능한 원고 |
| **Decide & Learn** | 사용자 선택, 7/28일 실제 관측 기록 | 추후 가설 재검토 |

**A/B 주의:** 모델 품질을 동일 조건에서 실험하는 것이 아니라 서로 다른 자료 접근 방식을 가진 **추천 워크플로의 비교**입니다. 링크 확보만으로 시장 수요나 조회수 성공이 증명되지 않습니다.

## 03. 기술 아키텍처

```mermaid
flowchart TD
  U["Creator goal & channel data"] --> Y["YouTube discovery / comments / transcripts"]
  Y --> G["Evidence + transcript coverage gates"]
  U --> R["My-channel Hybrid RAG: BM25 / semantic / RRF"]
  R --> A["Baseline A"]
  G --> A
  G --> B["Hermes B: independent web research"]
  A --> H["Human topic selection"]
  B --> H
  H --> F["Focused research / Content DNA / Knowledge Gap"]
  F --> D["Draft A"]
  D --> C["Critic / optional Draft B"]
  C --> S["Final manuscript"]
  S --> P["Observed 7D / 28D feedback"]
```

| 영역 | 기술 |
| --- | --- |
| UI | Python, Streamlit, HTML/CSS |
| 데이터 수집 | YouTube Data API, public transcripts, comments, manual Studio CSV |
| 검색/RAG | BM25, OpenAI embeddings, Reciprocal Rank Fusion |
| LLM | OpenAI Responses API, structured outputs & validation |
| 에이전트 | Hermes, local adapter, Docker isolation |
| 기록 | Persistent local cache, evidence provenance, decision logs |
| 검증 | Unit tests, mocked integrations, coverage/error checks |

## 04. 중요한 기술적 선택

**Evidence-first:** 조회수가 높다는 이유만으로 인기 주제라고 단정하지 않습니다. 채널 기준 Outlier, 업로드 경과 시간, 표본 크기, 출처 연결 상태를 구분합니다.

**Transcript Coverage Gate:** 충분한 자막이 없으면 상세 분석을 정상 완료한 것으로 가장하지 않습니다.

**Hybrid Retrieval:** 내 채널의 과거 설명과 중복되는지 키워드 BM25 및 semantic retrieval을 결합해 확인합니다.

**Human-in-the-loop:** 추천 순위는 결론이 아닙니다. 제작자가 선택하고, 이후 관측값이 쌓이면 판단을 재검토합니다.

**[🔎 상세 기술 사례: 실제 오류·원인·수정·남은 문제 보기](docs/CASE_STUDIES.md)**

**[실제 개발 시행착오와 문제 해결 과정 자세히 읽기](docs/ENGINEERING_CASE_STUDY.md)** — 조회수 편향, 자막 IP 차단, RAG, Hermes URL 불일치, API 비용, UI 과밀 등

## 05. 시행착오와 한계

| 문제 | 대응 / 현재 상태 |
| --- | --- |
| YouTube API 검색 quota 소진 | 캐시·기존 영상 ID 재사용 방향; 신규 탐색은 여전히 한도 영향을 받음 |
| 자막 접근 차단 및 누락 | 로컬 캐시와 Coverage Gate, 실패 시 명시적 중단 |
| LLM API 429, 크레딧 부족 | 실패 원인을 구분해 안내; 실제 이용 요금은 사용자 계정 부담 |
| Hermes 추천과 근거 URL 불일치 | 링크 검증 및 재연결 로직; 관측 링크≠수요 검증 |
| UI 정보 과밀 | 결론을 먼저 보여주고 상세 증거는 펼쳐보기로 분리 |
| 버전·상태 재현성 | 앱 코드와 외부 사용자 데이터/캐시 분리, 오프라인 검사 |

**검증 범위:** 오프라인 테스트를 통과한 이력이 있으나, 모든 Windows / Docker / 외부 API 조합의 종단 간 성공이나 조회수 개선 효과가 입증된 것은 아닙니다.

**[개발 과정과 실제 문제 해결 기록 자세히 보기](docs/ENGINEERING_CASE_STUDY.md)**


## 06. 실제 프로그램 실행 방법 · API 설정

웹 데모는 별도 설치 없이 체험할 수 있습니다. **실제 분석 엔진은 로컬 Python 앱**이므로, 사용자가 자신의 API 키를 발급해 설정해야 합니다.

1. [전체 소스 코드](full_app/)를 내려받고 Windows에서 Python과 필요한 패키지를 준비합니다. Hermes B 독립 조사를 실행할 경우 **Docker Desktop**도 필요합니다.
2. [\`full_app/.env.example\`](full_app/.env.example) 파일을 복사해 같은 폴더에 **\`.env\`**라는 이름으로 저장합니다.
3. 아래 필수 키를 발급받아 \`.env\`에 입력합니다. 샘플 파일과 코드에 개인 API 키는 포함하지 않습니다.
4. [전체 실행 안내](full_app/README.md)에 따라 \`1_SETUP_ONCE.bat\`로 설치하거나 \`0_START_WITH_HERMES.bat\`로 실행합니다.

| 설정 이름 | 발급처 | 용도 |
| --- | --- | --- |
| \`YOUTUBE_API_KEY\` **필수** | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) | YouTube Data API 영상·채널 검색 및 메타데이터 |
| \`OPENAI_API_KEY\` **필수** | [OpenAI API Platform](https://platform.openai.com/api-keys) | LLM 분석, 대본 생성, embeddings |
| \`TAVILY_API_KEY\` / \`EXA_API_KEY\` **선택** | 각 서비스 | Hermes의 추가 웹 검색·추출 |
| \`SUPADATA_API_KEY\` **선택** | Supadata | 자막 수집 보조 경로 |
| \`SERPAPI_API_KEY\` **선택** | SerpApi | 검색 관심도 관련 보조 자료 |

**보안:** \`.env\`, \`.streamlit/secrets.toml\`, 개인 YouTube Studio 데이터, 로컬 캐시와 비공개 원고는 GitHub에 올리지 마세요. 이 저장소의 \`.gitignore\`는 \`.env\`를 제외하도록 설정돼 있습니다. 이미 공개한 키는 파일 삭제만으로 안전해지지 않으므로 **발급처에서 폐기하고 새로 발급**해야 합니다.

**비용 및 제한:** ChatGPT 구독과 OpenAI API 사용 요금은 별도입니다. YouTube Data API는 프로젝트별 할당량 제한이 있고, 선택한 외부 서비스에도 요금이 발생할 수 있습니다.
