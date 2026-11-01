import json

import pandas as pd

from benchmark_reference import SCRIPT_CLOSING_GUIDE, BENCHMARK_CRITIC_GUIDE


class LLMTools:
    def __init__(self, cache_manager, settings, retrieval_tools):
        self.cache = cache_manager
        self.settings = settings
        self.retrieval = retrieval_tools

    def interpret_user_input(self, user_input, my_catalog_df, memory_context=None):
        """자유 입력을 주제/아이디어/추천 요청으로 해석해 하나의 Content Brief로 만든다."""
        schema = {
            "type": "object",
            "properties": {
                "입력유형": {"type": "string", "enum": ["다음콘텐츠추천", "주제연구", "아이디어발전"]},
                "주제": {"type": "string"},
                "콘텐츠유형": {"type": "string"},
                "콘텐츠유형근거": {"type": "string"},
                "타깃시청자": {"type": "string"},
                "핵심문제": {"type": "string"},
                "사용자가가진가설": {"type": "array", "items": {"type": "string"}},
                "시청자최종변화": {"type": "string"},
                "비즈니스역할": {"type": "string"},
                "살려야할제약": {"type": "array", "items": {"type": "string"}},
                "검증해야할가설": {"type": "array", "items": {"type": "string"}},
                "리서치질문": {"type": "array", "items": {"type": "string"}},
                "주검색어": {"type": "string"},
                "보조검색어": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
                "초기판단": {"type": "string"},
            },
            "required": ["입력유형", "주제", "콘텐츠유형", "콘텐츠유형근거", "타깃시청자", "핵심문제", "사용자가가진가설", "시청자최종변화", "비즈니스역할", "살려야할제약", "검증해야할가설", "리서치질문", "주검색어", "보조검색어", "초기판단"],
            "additionalProperties": False,
        }
        recent = my_catalog_df.head(15)[["제목", "업로드날짜", "조회수"]].to_dict("records")
        top = my_catalog_df.sort_values("조회수", ascending=False).head(12)[["제목", "업로드날짜", "조회수"]].to_dict("records")
        prompt = f"""
[채널 프로필]
{self.settings.channel_profile}

[현재 콘텐츠 목적]
{self.settings.content_goal_guide}

[사용자 자유 입력]
{user_input}

[내 최근 콘텐츠]
{json.dumps(recent, ensure_ascii=False, indent=2)}

[내 채널 상위 콘텐츠]
{json.dumps(top, ensure_ascii=False, indent=2)}

[지금까지 쌓인 Content Edge Memory]
{json.dumps(memory_context or [], ensure_ascii=False, indent=2, default=str)}

사용자의 말을 기능 메뉴로 억지로 끼워 맞추지 말고 현재 생각의 성숙도를 해석해 Content Brief를 만들어라.
- '다음에 뭐 만들까'처럼 주제가 없으면 다음콘텐츠추천.
- '현재완료', 'be동사'처럼 주제만 있으면 주제연구.
- 각도/타깃/설명가설/제작방식이 있으면 아이디어발전.
- 사용자의 아이디어에 무조건 동의하지 말고 검증해야 할 가설과 위험을 분리한다.
- 검색은 사용자의 목적이 아니라 뒤에서 근거를 찾기 위한 도구다.
- Pulling 모드에서는 비즈니스 연결을 억지로 만들지 말고 사람을 모을 지식/호기심/시장성을 우선한다. Key 모드에서는 신뢰/전문성 체험/서비스 연결을 더 중요하게 본다.
- 콘텐츠유형은 사용자의 말만으로 미리 단정하지 않는다. 데이터가 없으면 '패턴 탐색중'으로 남기고 Deep Research의 Content DNA/클러스터에서 구체화한다.
- 정보가 부족한 항목은 추측을 최소화하고 검증 질문으로 남긴다.
"""
        return self.cache.structured_response(
            "consultant_content_brief_v2_goal",
            "너는 사용자의 채널, 비즈니스, 창작 의도를 함께 해석해 조사 가능한 Content Brief로 바꾸는 개인 YouTube 콘텐츠 컨설턴트다.",
            prompt,
            schema,
        )

    def classify_memory_note(self, note, topic_hint="", current_brief=None, memory_context=None):
        schema = {
            "type": "object",
            "properties": {
                "메모항목": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "종류": {"type": "string", "enum": ["특이점", "좋은설명", "좋은비유", "좋은예문", "겹치는설명", "충돌", "오해", "아이디어", "엣지후보", "기타"]},
                            "주제": {"type": "string"},
                            "제목": {"type": "string"},
                            "내용": {"type": "string"},
                            "왜가치있는가": {"type": "string"},
                            "다음활용": {"type": "string"},
                        },
                        "required": ["종류", "주제", "제목", "내용", "왜가치있는가", "다음활용"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["메모항목"],
            "additionalProperties": False,
        }
        prompt = f"""
[주제 힌트]
{topic_hint or '없음'}

[현재 Content Brief]
{json.dumps(current_brief or {}, ensure_ascii=False, indent=2, default=str)}

[이미 쌓인 Memory]
{json.dumps(memory_context or [], ensure_ascii=False, indent=2, default=str)}

[사용자 메모]
{note}

사용자가 영상/강의/아이디어를 보며 적은 메모를 나중에 다시 활용할 수 있는 작은 단위로 분해하라.
한 메모에 여러 관찰이 있으면 여러 항목으로 나눈다.
'좋다'고만 쓰지 말고 무엇이 좋았는지, 무엇과 겹치는지, 어떤 새 영상의 Edge가 될 수 있는지 구체화한다.
사용자가 말하지 않은 출처나 사실은 만들지 않는다. 특별함/희소성은 이 메모만으로 단정하지 않는다.
"""
        return self.cache.structured_response(
            "content_memory_note_v1",
            "너는 크리에이터의 흩어진 관찰 메모를 재사용 가능한 Content Memory로 정리하는 에디터다.",
            prompt,
            schema,
        )

    def home_probe_queries(self, my_catalog_df, studio_context=None):
        """시장부터 넓게 보기 위한 탐색 질의. 내 채널 히트작을 출발점으로 삼지 않는다."""
        count = self.settings.home_probe_query_count
        schema = {
            "type": "object",
            "properties": {
                "검색어후보": {
                    "type": "array", "minItems": count, "maxItems": count,
                    "items": {
                        "type": "object",
                        "properties": {
                            "검색어": {"type": "string"},
                            "탐색축": {"type": "string", "enum": ["핵심고통", "인접니치", "사용상황", "훈련포맷", "학습실패", "지식오해", "개념연결", "구매의도"]},
                            "조사목적": {"type": "string"},
                        },
                        "required": ["검색어", "탐색축", "조사목적"], "additionalProperties": False,
                    },
                }
            },
            "required": ["검색어후보"], "additionalProperties": False,
        }
        prompt = f"""
[채널이 궁극적으로 도달하려는 고객]
{self.settings.channel_profile}

[현재 콘텐츠 목적]
{self.settings.content_goal_guide}

[사용자가 직접 추가한 Studio / Audience Neighborhood 데이터]
{json.dumps(studio_context or {}, ensure_ascii=False, indent=2, default=str)}

다음 콘텐츠 추천을 위해 먼저 '시장 자체'를 넓게 탐색할 YouTube 검색어 {count}개를 만들어라.
중요: 이 단계는 내 채널의 과거 히트작에서 비슷한 주제를 찾는 단계가 아니다.
현재 채널의 실제 핵심 연령대(45세 이상, 특히 55~64세)를 참고하되 영어 수준을 왕초보로 고정하지 말고, 성인 영어학습 시장에서 사람들이 반복해서 겪는 문제, 아직 채널에 없을 수 있는 인접 니치,
구체적 사용상황, 훈련 포맷, 학습 실패, 구매의도가 강할 수 있는 문제를 서로 다른 방향으로 탐색한다.
가능하면 핵심고통/인접니치/사용상황/훈련포맷/학습실패뿐 아니라 지식오해/개념연결 축을 반드시 포함한다.
특히 Pulling 모드에서는 단순 반복 포맷만 찾지 말고, 사람들이 이미 조금 알지만 정확히 연결하지 못하는 영어 지식, 자주 틀리는 개념, 의미 차이, 왜 그런지 궁금해하는 지점을 적극 탐색한다.
아직 데이터를 보지 않았으므로 '유행한다', '잘 된다'를 단정하지 않는다.
검색어는 실제 YouTube 검색에 쓸 수 있는 짧은 한국어 문구로 작성한다.
"""
        result, usage, cached = self.cache.structured_response(
            "home_probe_queries_v4_knowledge_gap",
            "너는 사용자의 과거 콘텐츠가 아니라 시장에서 먼저 새로운 기회 공간을 찾는 YouTube 리서처다.",
            prompt,
            schema,
        )
        return result["검색어후보"], usage, cached

    def synthesize_home_market_landscape(self, scout_candidates, scope="domestic"):
        """Metadata-only opportunity clustering. `scope` separates domestic demand from global transfer evidence."""
        schema = {
            "type": "object",
            "properties": {
                "시장기회": {
                    "type": "array", "minItems": 1, "maxItems": 8,
                    "items": {
                        "type": "object",
                        "properties": {
                            "기회id": {"type": "string"},
                            "시장문제": {"type": "string"},
                            "시장패턴": {"type": "string"},
                            "지식갭": {"type": "string"},
                            "포맷갭": {"type": "string"},
                            "신호유형": {"type": "string", "enum": ["최근상대성과", "반복수요", "장기누적", "글로벌검증", "혼합신호", "탐색단계"]},
                            "근거video_ids": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
                            "왜기회인가": {"type": "string"},
                            "포화위험": {"type": "string"},
                            "확실성": {"type": "string", "enum": ["높음", "중간", "낮음"]},
                        },
                        "required": ["기회id", "시장문제", "시장패턴", "지식갭", "포맷갭", "신호유형", "근거video_ids", "왜기회인가", "포화위험", "확실성"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["시장기회"], "additionalProperties": False,
        }
        cols = [
            "video_id", "제목", "채널", "조회수", "댓글", "좋아요", "업로드날짜", "영상나이_일", "채널배수",
            "baseline_N", "baseline_경고", "조회수_구독자배수", "선정이유", "발견검색어_목록",
            "시장범위", "발견출처", "seed_role", "reference_language", "reference_country",
        ]
        payload = scout_candidates[[c for c in cols if c in scout_candidates.columns]].to_dict("records")
        if scope == "global":
            scope_guide = """
이 자료는 사용자가 직접 고른 해외 영어교육 참고 채널에서 수집했다.
이 단계의 목적은 한국 수요를 증명하는 것이 아니라 **Global Transfer Opportunity**를 찾는 것이다.
- 해외에서 반복되거나 강하게 반응한 주제, 영어 지식, 설명 관점, 포맷을 분리한다.
- 한국 시장에서도 잘 될 것이라고 단정하지 않는다. 국내 검증 상태는 다음 단계에서 별도로 비교한다.
- 원본의 고유 예문/비유/문장 배열/연출을 베끼는 후보가 아니라, 일반적인 영어 개념과 전이 가능한 설명 원리를 찾는다.
- 여러 해외 채널에서 비슷한 주제가 강하면 `글로벌검증` 또는 `반복수요`로, 한 채널만 강하면 확실성을 낮춘다.
"""
        else:
            scope_guide = """
이 자료는 국내 검색과 사용자가 직접 선택한 Audience Neighborhood/한국 참고 채널에서 수집했다.
- 실제 내 시청자가 보는 채널에서 반복되는 주제는 중요한 Pulling 신호다.
- 서로 다른 채널에서 반복되는 주제와 최근 작은 채널 Breakout을 구분한다.
- 한 채널의 단일 성과만으로 전체 국내 수요를 단정하지 않는다.
"""
        prompt = f"""
[시장 범위]
{scope}

[시장 Scout 메타데이터]
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}

{scope_guide}

이 자료는 제목/업로드일/조회수/채널 상대성과/검색 또는 참고채널 경로 같은 메타데이터다. Transcript나 댓글은 아직 읽지 않았다.
서로 다른 기회 공간을 3~8개 찾는다.
- 제목을 재진술하지 말고 배우는 기술/영어 지식/시청자 문제를 기준으로 묶는다.
- 지식갭과 포맷갭을 분리한다. 지식갭이 없으면 없다고 쓴다.
- 최근 상대성과와 오래된 누적 수요를 구분한다.
- Channel Outlier, Subscriber Breakout, 절대 조회는 서로 다른 신호다.
- 근거video_ids는 반드시 제공된 ID만 사용한다.
- 아직 내 채널 Coverage를 보지 않았으므로 '내 채널에 없다'고 말하지 않는다.
- 메타데이터만으로 특정 설명 구조가 성공 원인이라고 단정하지 않는다.
"""
        return self.cache.structured_response(
            f"home_market_landscape_v3_{scope}",
            "너는 YouTube 메타데이터에서 반복 수요와 Global Transfer 기회를 과장 없이 묶는 리서처다.",
            prompt,
            schema,
        )

    def home_recommendations(
        self,
        my_catalog_df,
        scout_candidates,
        market_landscape,
        opportunity_df,
        memory_context=None,
        recent_candidates=None,
        pattern_context=None,
        global_candidates=None,
        studio_context=None,
    ):
        schema = {
            "type": "object",
            "properties": {
                "추천": {
                    "type": "array", "minItems": 3, "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "추천주제": {"type": "string"},
                            "추천우선순위": {"type": "integer", "minimum": 1, "maximum": 3},
                            "순위선정근거": {"type": "string"},
                            "차순위비교": {"type": "string"},
                            "전략경로": {"type": "string", "enum": ["승자 심화", "인접 확장", "신규 실험"]},
                            "전략판단근거": {"type": "string"},
                            "반복형식가설": {"type": "string"},
                            "형식변주실험": {"type": "string"},
                            "형식검증한계": {"type": "string"},
                            "추천슬롯": {"type": "string", "enum": ["최근브레이크아웃", "기본기회", "글로벌전이"]},
                            "기회유형": {"type": "string", "enum": ["국내반복수요", "최근브레이크아웃", "글로벌전이", "혼합", "탐색"]},
                            "추천검색어": {"type": "string"},
                            "해외검색어": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                            "발견경로": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
                            "콘텐츠유형": {"type": "string"},
                            "콘텐츠목적": {"type": "string", "enum": ["Pulling", "Key"]},
                            "가르칠영어지식": {"type": "string"},
                            "예상시청자": {
                                "type": "object",
                                "properties": {
                                    "연령맥락": {"type": "string"},
                                    "영어지식수준": {"type": "string"},
                                    "수행수준": {"type": "string"},
                                    "추정근거": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["연령맥락", "영어지식수준", "수행수준", "추정근거"],
                                "additionalProperties": False,
                            },
                            "시장기회id": {"type": "string"},
                            "시장발견": {"type": "string"},
                            "시장근거video_ids": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
                            "국내검증상태": {"type": "string"},
                            "글로벌전이요약": {"type": "string"},
                            "내채널공백": {"type": "string"},
                            "내식번역": {"type": "string"},
                            "뾰족한포인트가설": {"type": "string"},
                            "엣지발견방식": {"type": "string", "enum": ["시장반복", "내기존아이디어", "AI종합", "Memory회수", "혼합"]},
                            "제작전략": {
                                "type": "object",
                                "properties": {
                                    "핵심형식": {"type": "string"},
                                    "첫30초": {"type": "string"},
                                    "본문운영": {"type": "string"},
                                    "최종보상": {"type": "string"},
                                    "후속확장": {"type": "string"},
                                },
                                "required": ["핵심형식", "첫30초", "본문운영", "최종보상", "후속확장"],
                                "additionalProperties": False,
                            },
                            "추천근거요약": {"type": "string"},
                            "선택이유한줄": {"type": "string"},
                            "현재사업연결": {"type": "string"},
                            "추가사업아이디어": {"type": "string"},
                            "신뢰형성가치": {"type": "string"},
                            "신규성및중복위험": {"type": "string"},
                            "불확실성": {"type": "string"},
                        },
                        "required": [
                            "추천주제", "추천우선순위", "순위선정근거", "차순위비교", "전략경로", "전략판단근거", "반복형식가설", "형식변주실험", "형식검증한계", "추천슬롯", "기회유형", "추천검색어", "해외검색어", "발견경로", "콘텐츠유형", "콘텐츠목적",
                            "가르칠영어지식", "예상시청자", "시장기회id", "시장발견", "시장근거video_ids", "국내검증상태", "글로벌전이요약",
                            "내채널공백", "내식번역", "뾰족한포인트가설", "엣지발견방식", "제작전략", "추천근거요약", "선택이유한줄",
                            "현재사업연결", "추가사업아이디어", "신뢰형성가치", "신규성및중복위험", "불확실성"
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["추천"], "additionalProperties": False,
        }
        cols = [
            "video_id", "제목", "채널", "조회수", "댓글", "좋아요", "업로드날짜", "영상나이_일", "채널배수", "baseline_N",
            "baseline_경고", "조회수_구독자배수", "선정이유", "발견검색어_목록", "시장범위", "발견출처", "seed_role"
        ]
        scout_payload = scout_candidates[[c for c in cols if c in scout_candidates.columns]].to_dict("records") if scout_candidates is not None and not scout_candidates.empty else []
        recent_cols = cols + ["조회속도_일평균", "최근브레이크아웃"]
        recent_payload = recent_candidates[[c for c in recent_cols if c in recent_candidates.columns]].to_dict("records") if recent_candidates is not None and not recent_candidates.empty else []
        global_payload = global_candidates[[c for c in cols if c in global_candidates.columns]].to_dict("records") if global_candidates is not None and not global_candidates.empty else []
        gap_cols = ["시장기회", "시장확실성", "커버리지판정", "이미다룬내용", "부족하거나없는내용", "콘텐츠갭"]
        gap_payload = opportunity_df[[c for c in gap_cols if c in opportunity_df.columns]].to_dict("records") if opportunity_df is not None and not opportunity_df.empty else []
        own_cols = [c for c in ["video_id", "제목", "업로드날짜", "조회수", "댓글", "좋아요", "studio_unique_viewers", "studio_impressions", "studio_ctr_pct", "studio_avg_percentage_viewed_pct", "studio_recent_10_rank", "studio_leads_count"] if c in my_catalog_df.columns]
        own_recent = my_catalog_df.head(20)[own_cols].to_dict("records")
        own_top = my_catalog_df.sort_values("조회수", ascending=False).head(15)[own_cols].to_dict("records")
        prompt = f"""
[채널 프로필]
{self.settings.channel_profile}

[사용자가 직접 추가한 Studio / Audience Neighborhood / 성과 데이터]
{json.dumps(studio_context or {}, ensure_ascii=False, indent=2, default=str)}

[실제 Business Profile]
{self.settings.business_profile or '미입력 — Key 모드에서는 상품/서비스를 임의로 만들어 사실처럼 말하지 말 것'}

[1. 시장 Landscape — 내 채널 Coverage를 보기 전에 만든 기회]
{json.dumps(market_landscape, ensure_ascii=False, indent=2, default=str)}

[2. 시장 기회 vs 내 기존 콘텐츠 실제 RAG 비교]
{json.dumps(gap_payload, ensure_ascii=False, indent=2, default=str)}

[3. 국내/Audience Neighborhood 근거 영상]
{json.dumps(scout_payload, ensure_ascii=False, indent=2, default=str)}

[3-1. 최근 45일 Breakout 후보]
{json.dumps(recent_payload, ensure_ascii=False, indent=2, default=str)}

[3-2. Global Reference 후보]
{json.dumps(global_payload, ensure_ascii=False, indent=2, default=str)}

[4. 내 최근/상위 콘텐츠]
최근: {json.dumps(own_recent, ensure_ascii=False, indent=2, default=str)}
상위: {json.dumps(own_top, ensure_ascii=False, indent=2, default=str)}

[5. Content Edge Memory]
{json.dumps(memory_context or [], ensure_ascii=False, indent=2, default=str)}

[6. Content Pattern Memory]
{json.dumps(pattern_context or [], ensure_ascii=False, indent=2, default=str)}

[기본 가설 프레임]
{self.settings.hypothesis_framework}

[현재 콘텐츠 목적]
{self.settings.content_goal_guide}

핵심 철학: 좋은 다음 주제는 꼭 '아직 안 해 본 새 주제'일 필요가 없다. 이미 내 채널에서 통했던 시청자 문제를 재현·심화하는 편이 더 합리적일 수 있다. 교과목을 빠짐없이 채우는 커리큘럼 완성도를 목표로 하지 않는다.

[가장 먼저 판단할 전략: Exploit / Adjacent / Explore]
- 최우선 질문: 지금은 내 검증된 히트의 *후속 문제*를 더 깊게 해결해야 하는가, 기존 승자와 인접한 문제로 넓혀야 하는가, 신규 수요를 실험해야 하는가?
- 승자 심화: 같은 시청자 욕구를 다른 구체적 문제/훈련/결과로 한 단계 진전시킨다. 제목과 대본만 살짝 바꾼 재탕이면 제외한다.
- 인접 확장: 히트한 문제에서 다음 단계·실전 적용으로 확장한다. 기존 시청자가 왜 클릭할지 연결고리가 분명해야 한다.
- 신규 실험: 기존 강점 바깥의 새로운 수요를 테스트한다. 관찰된 외부 수요나 구체적인 반증 가능한 가설이 없으면 무리하게 추천하지 않는다.
- 3개 후보를 각 경로에서 하나씩 채우지 마라. 증거가 강하면 3개 모두 승자 심화일 수 있고, 신규 실험이 0개여도 된다.
- `전략경로`에는 위 3개 중 정확히 하나, `전략판단근거`에는 내 채널의 *실제* 영상 제목과 관측된 성과, 관련 경쟁 신호, 선택의 한계(해당 시)를 짧게 쓴다. 데이터 없는 채널 히트·원인은 만들어내지 마라.
- 댓글은 *절대 댓글 수* 중심의 관측 행동으로 참고한다. 조회수 대비 댓글 비율은 이 채널 전략에 사용하지 않는다. 댓글 수가 많다는 사실은 구매 전환이나 영상 품질을 증명하지 않는다. 토론/실제 적용/후속 학습/상품 관심을 구분하되 댓글 텍스트 분류가 없는 경우 임의로 내용을 만들어 내지 않는다.
- 조회수만 높은 오래된 영상과 최근 영상을 곧바로 비교하지 마라. 업로드 경과기간, 노출수·CTR·시청지속률이 주어지면 같이 검토하되, 미제공 지표를 추정 수치로 채우지 않는다.
- 어느 주제를 추천하든 클릭할 이유, 이전 영상과 달라진 학습자 보상, 적합한 시청자를 명확히 하라.
- 주제 전략과 별도로 '반복 가능한 시그니처 형식'을 검토하라. 주제(어순/발음)와 형식(일상 비유→직접 연습→즉시 이해 확인)은 다른 변수다.
- `반복형식가설`: 내 채널의 실제 대본/Content DNA가 근거라면 어떤 전개 방식이 재사용 가능한지 한 문장. 자료가 부족하면 "판단 근거 부족"이라고 적어라.
- `형식변주실험`: 기존 영상을 재촬영하는 대신, 같은 형식을 전혀 다른 시청자 질문·예시·즉시 보상으로 바꾸는 1편의 구체적 실험.
- `형식검증한계`: 내 영상 1편의 조회수가 높다고 그 형식이 성공 원인이라고 단정하지 마라. 최소 복수 영상과 노출·CTR·시청 지속·영상 나이를 확인하기 전에는 가설이다.
- 검색량은 실제 측정치가 제공되지 않았다. 'Google Trends 80점' 같은 숫자를 만들어내지 마라. 시장 영상 조회수와 검색 관심도는 구분하고, 추천 유입 가능성도 별도의 가설로 다루라.


Audience Neighborhood 규칙:
- Studio의 `내 시청자가 보는 다른 채널`, 실제 Suggested 옆자리에서 관찰된 채널은 높은 가치의 seed다.
- 조회수/구독자 배율 하나만으로 '주제의 힘'이라고 단정하지 않는다. Channel Outlier, Subscriber Breakout, 절대 조회, 최근성은 다른 신호다.
- 서로 다른 채널에서 반복되면 Repeated Demand 근거가 강해진다. 하지만 강한 Recent Breakout 하나나 Global Transfer를 하드컷으로 버리지 않는다.

Global Transfer 규칙:
- 해외 참고 채널에서 검증된 영어 지식/질문/설명 원리/포맷을 찾되, 해외 영상의 구체적 문장 배열·독특한 비유·예문·대사·연출을 번역 복제하지 않는다.
- 해외 근거만 있는 경우 `국내검증상태`에 '국내 수요 미검증/약함'을 명시한다. 국내 증거가 없다는 사실 자체가 정보격차 기회일 수도 있지만, 한국에서 성공한다고 단정하지 않는다.
- `글로벌전이요약`에는 무엇을 가져오고 무엇을 새로 한국식으로 설계해야 하는지 적는다.
- 글로벌 후보를 무조건 TOP3에 넣지 않는다. 실제 근거와 내 채널 공백이 강할 때만 넣는다.

추천 슬롯:
- Pulling에서는 강한 Recent Breakout이 있으면 1개를 적극 검토한다.
- 나머지는 국내 반복수요/Knowledge Gap/Global Transfer 중 근거가 가장 강한 *시청자 문제*를 고른다. 같은 승자 영역 안에서 서로 다른 실질적 후속 문제 3개가 더 낫다면 모두 같은 영역이어도 된다.
- Key에서는 Recent를 강제하지 않는다.

Audience 규칙:
- 연령과 영어 수준은 분리한다. 45세 이상이 중심이어도 왕초보로 고정하지 않는다.
- 실제 Studio snapshot, 시장 콘텐츠 난이도, 댓글/Transcript가 없으면 연령/수준을 사실처럼 단정하지 않는다.

A의 **독립 우선순위 결정**:
- A가 추천한 세 주제를 동일한 기준(내 채널 재현 가능성, 국내 시청자 수요, 영상 콘텐츠 차별화, 제작 부담, 불확실성)에서 *서로 비교*하고, 가장 먼저 제작할 1순위부터 3순위까지 정하라.
- 각 후보의 `추천우선순위`는 정수 1/2/3 중 서로 다른 값 하나다. JSON 배열도 1→2→3순위로 배치하라.
- `순위선정근거`는 **왜 지금 이 순위에 추천하는지** 채널/시장 관측치를 특정하여 1~2문장. 근거가 부족하면 부족하다고 밝혀라.
- `차순위비교`는 다른 2개 후보와 비교한 장점 또는 약점/기회비용 한 문장. 모두 똑같은 모호한 이유 금지.
- 검색량의 실측치가 지금 제공되지 않았다면 높은 검색량을 1순위 근거로 만들어 내지 마라. 서열은 편집 우선순위이지 성공 확률이나 예상 조회수가 아니다.
- '승자 심화/인접 확장/신규 실험'을 1개씩 억지로 분산시키지 않는다. A/B 간 상호 비교하지 않는다.

가장 중요한 출력 규칙:
- 모든 후보는 `가르칠영어지식` 또는 훈련할 실제 능력을 구체적으로 적는다.
- 콘텐츠유형은 강의형/훈련형 같은 고정 taxonomy가 아니라 실제 Content DNA/Pattern Memory에 가까운 자유로운 이름을 쓴다.
- Pulling에서는 상품 연결을 순위의 1차 근거로 쓰지 않는다. Key에서는 신뢰/전문성 체험/구매 설득을 핵심으로 본다.
- 내 과거 히트작은 우선 검증할 확장 가설의 출발점이다. 다만 한 편의 조회수만으로 반복 성공이 보장된다고 말하지 않는다.
- 성공 확률 숫자를 만들지 않는다.
- 시장근거video_ids는 제공된 ID에서만 고른다.
- `해외검색어`는 Global Transfer 또는 해외 검증이 유용한 후보에서 Deep Research에 쓸 짧은 영어 검색어만 넣고, 필요 없으면 빈 배열로 둔다.
- `발견경로`에는 Audience Neighborhood / Suggested Neighbor / 국내 검색 / Recent Breakout / Global Reference 중 실제 사용된 경로를 적는다.
"""
        result, usage, cached = self.cache.structured_response(
            "home_recommendations_v14_absolute_comment_actions",
            "너는 Audience Neighborhood, 국내 시장, Global Reference, 사용자 채널 RAG를 결합해 다음 콘텐츠의 자리를 찾는 개인 YouTube 전략 컨설턴트다.",
            prompt,
            schema,
        )
        from topic_ranking import order_recommendations
        return order_recommendations(result["추천"], require_rank=True), usage, cached

    def analyze_videos(self, analysis_df):
        """Transcript-backed per-video analysis + free-form Content DNA extraction."""
        schema = {
            "type": "object",
            "properties": {
                "핵심가치": {"type": "string"},
                "설명전략": {"type": "array", "items": {"type": "string"}},
                "시청자가좋아한점": {"type": "array", "items": {"type": "object", "properties": {"내용": {"type": "string"}, "근거": {"type": "string"}}, "required": ["내용", "근거"], "additionalProperties": False}},
                "미해결문제": {"type": "array", "items": {"type": "object", "properties": {"문제": {"type": "string"}, "근거": {"type": "string"}}, "required": ["문제", "근거"], "additionalProperties": False}},
                "성공가설": {"type": "array", "items": {"type": "object", "properties": {"가설": {"type": "string"}, "근거": {"type": "string"}}, "required": ["가설", "근거"], "additionalProperties": False}},
                "전이가능원리": {"type": "array", "items": {"type": "string"}},
                "알수없는것": {"type": "array", "items": {"type": "string"}},
                "콘텐츠DNA": {
                    "type": "object",
                    "properties": {
                        "시청자문제": {"type": "string"},
                        "핵심약속": {"type": "string"},
                        "지식역할": {"type": "string"},
                        "핵심구조": {"type": "string"},
                        "전달방식": {"type": "string"},
                        "핵심보상": {"type": "string"},
                        "참여방식": {"type": "string"},
                        "정보깊이": {"type": "string"},
                        "요구선행지식": {"type": "string"},
                        "감정장치": {"type": "string"},
                        "증거장치": {"type": "string"},
                        "시청자결과": {"type": "string"},
                        "제목약속": {"type": "string"},
                        "예상연령맥락": {"type": "string"},
                        "예상지식수준": {"type": "string"},
                        "예상수행수준": {"type": "string"},
                        "구조태그": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["시청자문제", "핵심약속", "지식역할", "핵심구조", "전달방식", "핵심보상", "참여방식", "정보깊이", "요구선행지식", "감정장치", "증거장치", "시청자결과", "제목약속", "예상연령맥락", "예상지식수준", "예상수행수준", "구조태그"],
                    "additionalProperties": False,
                },
            },
            "required": ["핵심가치", "설명전략", "시청자가좋아한점", "미해결문제", "성공가설", "전이가능원리", "알수없는것", "콘텐츠DNA"],
            "additionalProperties": False,
        }
        rows = []
        for _, row in analysis_df.iterrows():
            prompt = f"""
아래 데이터만 근거로 영어교육 YouTube 영상을 분석하라.

제목: {row['제목']}
선정 이유: {row['선정이유']}
조회수: {row['조회수']}
Channel Outlier: {row['채널배수']}
Baseline N: {row['baseline_N']}
댓글 수집 수: {row['수집댓글수']}
대본 상태: {row['대본상태']}

[Transcript]
{row['전체대본']}

[좋아요 상위 댓글]
{row['좋아요상위댓글']}

조회수만으로 성공 원인을 단정하지 않는다. Transcript/댓글의 확인 사실과 추론을 분리한다.
Content DNA는 기존 '강의형/훈련형' 분류표에 끼워 맞추지 말고 이 영상이 실제로 어떻게 작동하는지를 자연어로 분해한다.
예상연령맥락/지식수준/수행수준은 제목·Transcript·댓글에서 근거가 있을 때만 추정하고, 연령을 영어 실력과 동일시하지 않는다.
예: '오해를 먼저 흔든 뒤 예문으로 규칙을 재연결', '질문 후 대기시간을 주고 힌트를 줄여 수행', '한 상황을 처음부터 끝까지 역할극으로 해결'처럼 구조 자체를 적는다.
구조태그도 자유롭게 2~5개 만든다. 한 영상이 여러 패턴을 동시에 가질 수 있다.
댓글이 적으면 시청자 반응은 약한 근거라고 표시한다. Transcript가 없는 행은 이 함수에 들어오면 안 된다.
"""
            result, usage, cached = self.cache.structured_response(
                "youtube_video_analysis_v2_content_dna",
                "너는 제공된 Transcript, 댓글, 영상 성과 데이터만 근거로 영상의 설명 내용과 Content DNA를 분해하는 YouTube 리서처다.",
                prompt,
                schema,
            )
            rows.append({"video_id": row["video_id"], "제목": row["제목"], "선정이유": row["선정이유"], "조회수": row["조회수"], "채널배수": row["채널배수"], **result, "캐시사용": cached})
        return pd.DataFrame(rows)

    def discover_content_patterns(self, video_analysis_df, evidence_df=None):
        """Discover clusters from observed Content DNA instead of using a fixed taxonomy."""
        if video_analysis_df is None or video_analysis_df.empty:
            return {"클러스터": [], "관찰메모": ["분석 가능한 Transcript 기반 영상이 없습니다."]}, {}, False
        schema = {
            "type": "object",
            "properties": {
                "클러스터": {
                    "type": "array", "minItems": 1, "maxItems": 6,
                    "items": {
                        "type": "object",
                        "properties": {
                            "클러스터명": {"type": "string"},
                            "설명": {"type": "string"},
                            "시청자문제": {"type": "string"},
                            "핵심약속": {"type": "string"},
                            "지식역할": {"type": "string"},
                            "핵심구조": {"type": "string"},
                            "핵심보상": {"type": "string"},
                            "참여방식": {"type": "string"},
                            "증거장치": {"type": "string"},
                            "시청자결과": {"type": "string"},
                            "제목약속": {"type": "string"},
                            "예상연령맥락": {"type": "string"},
                            "예상지식수준": {"type": "string"},
                            "예상수행수준": {"type": "string"},
                            "video_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                            "공통점": {"type": "array", "items": {"type": "string"}},
                            "변형": {"type": "array", "items": {"type": "string"}},
                            "성과해석": {"type": "string"},
                            "최근신호": {"type": "string"},
                            "확신": {"type": "string", "enum": ["높음", "중간", "낮음"]},
                        },
                        "required": ["클러스터명", "설명", "시청자문제", "핵심약속", "지식역할", "핵심구조", "핵심보상", "참여방식", "증거장치", "시청자결과", "제목약속", "예상연령맥락", "예상지식수준", "예상수행수준", "video_ids", "공통점", "변형", "성과해석", "최근신호", "확신"],
                        "additionalProperties": False,
                    },
                },
                "관찰메모": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["클러스터", "관찰메모"],
            "additionalProperties": False,
        }
        cols = ["video_id", "제목", "조회수", "채널배수", "콘텐츠DNA", "핵심가치", "전이가능원리"]
        dna = video_analysis_df[[c for c in cols if c in video_analysis_df.columns]].to_dict("records")
        perf = []
        if evidence_df is not None and not evidence_df.empty:
            pcols = ["video_id", "채널", "조회수", "업로드날짜", "영상나이_일", "채널배수", "조회수_구독자배수", "최근브레이크아웃", "baseline_N"]
            perf = evidence_df[[c for c in pcols if c in evidence_df.columns]].to_dict("records")
        prompt = f"""
[Transcript 기반 Content DNA]
{json.dumps(dna, ensure_ascii=False, indent=2, default=str)}

[성과 메타데이터]
{json.dumps(perf, ensure_ascii=False, indent=2, default=str)}

고정된 '강의형/훈련형/자료형' 분류를 사용하지 말고, 실제 영상들의 시청자 문제·약속·글의 구조·보상·참여방식·증거장치·결과의 공통점을 보고 클러스터를 발견하라.
클러스터 이름은 시장에서 관찰된 작동방식을 압축해서 새로 만든다. 예: '오해교정→개념재연결형', '힌트제거→즉시수행형'처럼 복합 이름도 가능하다.
한 영상이 두 클러스터 성격을 가질 수 있지만, video_ids에는 대표적으로 잘 맞는 영상을 넣는다.
성과는 인과가 아니라 관찰 신호로만 해석한다. 최근 영상이 있으면 최근신호에 따로 적고, 표본이 적으면 확신을 낮춘다.
"""
        return self.cache.structured_response(
            "content_pattern_discovery_v1",
            "너는 영상 구조를 미리 정한 분류표에 넣지 않고 실제 Content DNA에서 패턴을 발견하는 시장 구조 분석가다.",
            prompt,
            schema,
        )

    def synthesize_market(self, video_analysis_df):
        schema = {
            "type": "object",
            "properties": {
                "반복되는핵심설명": {"type": "array", "items": {"type": "object", "properties": {"패턴": {"type": "string"}, "등장영상수": {"type": "integer"}, "설명": {"type": "string"}}, "required": ["패턴", "등장영상수", "설명"], "additionalProperties": False}},
                "반복되는설명전략": {"type": "array", "items": {"type": "object", "properties": {"전략": {"type": "string"}, "등장영상수": {"type": "integer"}, "설명": {"type": "string"}}, "required": ["전략", "등장영상수", "설명"], "additionalProperties": False}},
                "시청자가반복해서좋아한것": {"type": "array", "items": {"type": "object", "properties": {"반응": {"type": "string"}, "근거": {"type": "string"}}, "required": ["반응", "근거"], "additionalProperties": False}},
                "반복되는미해결문제": {"type": "array", "items": {"type": "object", "properties": {"문제": {"type": "string"}, "근거": {"type": "string"}}, "required": ["문제", "근거"], "additionalProperties": False}},
                "성과영상공통패턴": {"type": "array", "items": {"type": "object", "properties": {"패턴": {"type": "string"}, "근거": {"type": "string"}}, "required": ["패턴", "근거"], "additionalProperties": False}},
                "시장기회후보": {"type": "array", "items": {"type": "object", "properties": {"기회": {"type": "string"}, "근거": {"type": "string"}, "확실성": {"type": "string", "enum": ["높음", "중간", "낮음"]}}, "required": ["기회", "근거", "확실성"], "additionalProperties": False}},
            },
            "required": ["반복되는핵심설명", "반복되는설명전략", "시청자가반복해서좋아한것", "반복되는미해결문제", "성과영상공통패턴", "시장기회후보"],
            "additionalProperties": False,
        }
        cols = [c for c in ["제목", "채널", "시장범위", "발견출처", "선정이유", "조회수", "채널배수", "핵심가치", "설명전략", "시청자가좋아한점", "미해결문제", "성공가설", "전이가능원리", "콘텐츠DNA"] if c in video_analysis_df.columns]
        data = video_analysis_df[cols].to_dict("records")
        prompt = f"""
동일 주제를 다루는 여러 YouTube 영어교육 영상의 분석 결과다.
{json.dumps(data, ensure_ascii=False, indent=2, default=str)}

어느 영상이 최고인지 고르지 말고 반복되는 설명/설명전략/시청자 반응/미해결 문제를 찾는다.
성과와 반복 특징 사이의 인과관계를 단정하지 않는다.
시장기회는 아직 후보이며 사용자의 기존 콘텐츠를 비교하기 전에는 사용자가 안 했다고 말하지 않는다.
국내와 Global Reference가 섞여 있다면 출처를 구분한다. 해외에서 반복되는 지식/설명법이 국내에서 그대로 검증됐다고 간주하지 말고, Global Transfer 후보와 국내 반복수요를 구분한다.
"""
        return self.cache.structured_response(
            "youtube_market_synthesis",
            "너는 여러 콘텐츠 분석을 종합해 반복 패턴과 시장 기회 가설을 찾는 리서처다.",
            prompt,
            schema,
        )

    def rag_answer(self, my_chunks_df, query, top_k=5):
        sources = self.retrieval.hybrid_retrieve(my_chunks_df, query, top_k=top_k)
        if sources.empty:
            return {"answer": "관련된 내 콘텐츠를 찾지 못했습니다.", "sources": sources}
        context = "\n\n".join(f"[자료 {i+1}]\n영상: {r['제목']}\nChunk: {r['chunk번호']}\n{r['텍스트']}" for i, (_, r) in enumerate(sources.iterrows()))
        schema = {"type": "object", "properties": {"답변": {"type": "string"}, "근거": {"type": "array", "items": {"type": "string"}}, "확인불가": {"type": "array", "items": {"type": "string"}}}, "required": ["답변", "근거", "확인불가"], "additionalProperties": False}
        result, usage, cached = self.cache.structured_response(
            "my_content_rag",
            "너는 사용자의 기존 YouTube 콘텐츠를 조사하는 Research Assistant다.",
            f"질문: {query}\n\n[검색된 내 콘텐츠]\n{context}\n\n검색된 자료만 근거로 답하고 없는 내용은 추측하지 마라.",
            schema,
        )
        return {"answer": result, "sources": sources, "usage": usage, "cached": cached}

    def analyze_opportunities(self, market_result, my_chunks_df):
        schema = {
            "type": "object",
            "properties": {
                "커버리지판정": {"type": "string", "enum": ["충분히 다룸", "부분적으로 다룸", "거의 다루지 않음", "판단 불가"]},
                "이미다룬내용": {"type": "array", "items": {"type": "string"}},
                "부족하거나없는내용": {"type": "array", "items": {"type": "string"}},
                "근거": {"type": "array", "items": {"type": "object", "properties": {"영상제목": {"type": "string"}, "chunk번호": {"type": "integer"}, "설명": {"type": "string"}}, "required": ["영상제목", "chunk번호", "설명"], "additionalProperties": False}},
                "콘텐츠갭": {"type": "string"},
            },
            "required": ["커버리지판정", "이미다룬내용", "부족하거나없는내용", "근거", "콘텐츠갭"], "additionalProperties": False,
        }
        rows = []
        for item in market_result["시장기회후보"]:
            opportunity = item["기회"]
            sources = self.retrieval.hybrid_retrieve(my_chunks_df, opportunity, top_k=7)
            context = "\n\n".join(f"[내 자료 {rank}]\n영상: {r['제목']}\nChunk: {r['chunk번호']}\n{r['텍스트']}" for rank, (_, r) in enumerate(sources.iterrows(), start=1))
            prompt = f"""
[시장 기회]
{opportunity}

[시장 근거]
{item['근거']}

[검색된 내 기존 콘텐츠]
{context}

시장 기회의 핵심 문제가 기존 콘텐츠에서 실제로 해결되는지 판단하라.
검색되었다는 이유만으로 충분히 다뤘다고 하지 말고 이미 다룬 부분과 부족한 부분을 구분하라.
"""
            result, _, cached = self.cache.structured_response(
                "content_coverage_analysis",
                "너는 시장 조사와 사용자의 기존 콘텐츠 사이의 실제 Gap을 근거 기반으로 비교하는 리서처다.",
                prompt,
                schema,
            )
            rows.append({"시장기회": opportunity, "시장근거": item["근거"], "시장확실성": item["확실성"], **result, "검색Chunk수": len(sources), "캐시사용": cached})
        opportunity_df = pd.DataFrame(rows)
        gap_df = opportunity_df[opportunity_df["커버리지판정"].isin(["부분적으로 다룸", "거의 다루지 않음"])].copy()
        return opportunity_df, gap_df

    def plan_content(self, opportunity_df, gap_df, my_catalog_df, idea_brief=None, memory_context=None, market_evidence_df=None, market_result=None, pattern_context=None, studio_context=None):
        schema = {
            "type": "object",
            "properties": {"콘텐츠후보": {"type": "array", "minItems": 3, "maxItems": 3, "items": {
                "type": "object",
                "properties": {
                    "주제": {"type": "string"},
                    "추천검색어": {"type": "string"},
                    "콘텐츠유형": {"type": "string"},
                    "콘텐츠목적": {"type": "string", "enum": ["Pulling", "Key"]},
                    "가르칠영어지식": {"type": "string"},
                    "예상시청자": {
                        "type": "object",
                        "properties": {
                            "연령맥락": {"type": "string"},
                            "영어지식수준": {"type": "string"},
                            "수행수준": {"type": "string"},
                            "추정근거": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["연령맥락", "영어지식수준", "수행수준", "추정근거"],
                        "additionalProperties": False,
                    },
                    "타깃문제": {"type": "string"},
                    "핵심약속": {"type": "string"},
                    "시장발견": {"type": "string"},
                    "시장근거video_ids": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
                    "내채널공백": {"type": "string"},
                    "내식번역": {"type": "string"},
                    "핵심엣지가설": {"type": "string"},
                    "핵심엣지출처": {"type": "string", "enum": ["시장반복", "내기존아이디어", "AI종합", "Memory회수", "혼합"]},
                    "왜특별할수있는가": {"type": "string"},
                    "왜만들가치가있는가": {"type": "string"},
                    "왜지금": {"type": "string"},
                    "시장근거": {"type": "array", "items": {"type": "string"}},
                    "내채널근거": {"type": "array", "items": {"type": "string"}},
                    "현재사업연결": {"type": "string"},
                    "추가사업아이디어": {"type": "string"},
                    "신뢰형성가치": {"type": "string"},
                    "신규성및중복위험": {"type": "string"},
                    "기존콘텐츠활용방식": {"type": "string"},
                    "영상구조방향": {"type": "array", "items": {"type": "string"}},
                    "제목방향": {"type": "array", "items": {"type": "string"}},
                    "불확실성및주의": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["주제", "추천검색어", "콘텐츠유형", "콘텐츠목적", "가르칠영어지식", "예상시청자", "타깃문제", "핵심약속", "시장발견", "시장근거video_ids", "내채널공백", "내식번역", "핵심엣지가설", "핵심엣지출처", "왜특별할수있는가", "왜만들가치가있는가", "왜지금", "시장근거", "내채널근거", "현재사업연결", "추가사업아이디어", "신뢰형성가치", "신규성및중복위험", "기존콘텐츠활용방식", "영상구조방향", "제목방향", "불확실성및주의"],
                "additionalProperties": False,
            }}},
            "required": ["콘텐츠후보"], "additionalProperties": False,
        }
        source = gap_df if not gap_df.empty else opportunity_df
        data = source[["시장기회", "시장확실성", "커버리지판정", "이미다룬내용", "부족하거나없는내용", "콘텐츠갭"]].to_dict("records")
        recent = my_catalog_df.head(20)[["제목", "업로드날짜", "조회수"]].to_dict("records")
        top = my_catalog_df.sort_values("조회수", ascending=False).head(15)[["제목", "업로드날짜", "조회수"]].to_dict("records")
        brief_text = json.dumps(idea_brief, ensure_ascii=False, indent=2, default=str) if idea_brief else "없음 - 시장/채널 근거에서 후보를 설계"
        ev_cols = ["video_id", "제목", "채널", "조회수", "댓글", "좋아요", "업로드날짜", "영상나이_일", "채널배수", "선정이유", "발견검색어_목록"]
        ev = market_evidence_df[[c for c in ev_cols if c in market_evidence_df.columns]].to_dict("records") if market_evidence_df is not None and not market_evidence_df.empty else []
        prompt = f"""
[채널 프로필]
{self.settings.channel_profile}

[사용자가 직접 추가한 Studio / Audience Neighborhood 데이터]
{json.dumps(studio_context or {}, ensure_ascii=False, indent=2, default=str)}

[실제 Business Profile]
{self.settings.business_profile or '미입력 — Key 모드에서는 상품/서비스 정보 부족을 명시할 것'}

[사용자 Content Brief]
{brief_text}

[시장 종합]
{json.dumps(market_result or {}, ensure_ascii=False, indent=2, default=str)}

[시장과 내 콘텐츠 RAG 비교]
{json.dumps(data, ensure_ascii=False, indent=2, default=str)}

[정밀 분석에 사용한 실제 시장 영상]
{json.dumps(ev, ensure_ascii=False, indent=2, default=str)}

[내 최근 영상 성과]
{json.dumps(recent, ensure_ascii=False, indent=2)}

[내 상위 영상]
{json.dumps(top, ensure_ascii=False, indent=2)}

[Content Edge Memory]
{json.dumps(memory_context or [], ensure_ascii=False, indent=2, default=str)}

[시장 Content Pattern Memory]
{json.dumps(pattern_context or [], ensure_ascii=False, indent=2, default=str)}

[기본 가설 프레임]
{self.settings.hypothesis_framework}

[현재 콘텐츠 목적]
{self.settings.content_goal_guide}

실제 제작을 검토할 콘텐츠 후보 TOP 3를 설계하라.
사고 순서는 시장에서 발견한 문제/기회 → 내 채널 Coverage Gap → 내 방식으로 번역 → Core Edge → 실행 전략이다.
사용자 아이디어가 있다면 그것을 정답으로 취급하지 말고 시장/내 콘텐츠 근거와 대조해 강화하거나 반박한다.
내 히트작과 비슷한 3개를 만드는 것을 피하고, 근거가 있는 시장-채널 Gap과 인접 니치를 적극 검토한다.
최종 3개가 사실상 같은 부모 주제라면 다시 고른다.
시장근거video_ids는 제공된 video_id만 그대로 사용한다.
특정 경쟁 영상의 표현/구조를 복제하지 않고 전이 가능한 원리만 가져온다. 해외 Reference라면 일반 영어 개념/문제/설명 원리만 가져오고 한국어 설명·예문·생활 맥락은 독립적으로 다시 설계한다.
현재 실제 사업과 신규 사업 아이디어를 분리하며 성공확률 숫자는 만들지 않는다.
각 후보는 반드시 무엇을 가르치거나 어떤 사용 능력을 새로 만들지 가르칠영어지식에 구체적으로 적는다. Format Gap만으로 후보를 만들지 말고 Knowledge Gap도 적극 찾는다.
Pulling 모드에서는 비즈니스 연결을 순위 결정의 1차 근거로 쓰지 않는다. Key 모드에서는 신뢰/변화/서비스 연결을 더 중요하게 본다.
현재 채널의 핵심 연령대는 45세 이상이지만 '왕초보'로 자동 고정하지 않는다. 각 후보마다 시장 영상의 설명 난이도와 내 채널 반응을 근거로 지식 수준과 실제 수행 수준을 따로 추정한다. 설명은 쉽게 하되 내용 자체를 불필요하게 낮추지 않는다.
콘텐츠유형은 고정 taxonomy가 아니라 이번 Research에서 관찰된 Content DNA/클러스터 또는 누적 Pattern Memory에서 가장 가까운 패턴을 자유로운 이름으로 적는다. 한 영상이 복합형이면 '개념연결+즉시테스트형'처럼 조합해도 된다.
"""
        result, usage, cached = self.cache.structured_response(
            "youtube_content_planner_v8_pulling_key",
            "너는 시장 기회와 사용자 채널의 실제 Coverage Gap을 먼저 찾은 뒤 사용자의 강점으로 번역하는 콘텐츠 전략가다.",
            prompt,
            schema,
        )
        return result["콘텐츠후보"], usage, cached

    def build_content_design_pack(self, selected_candidate, market_sources, my_sources, relevant_market_analysis, idea_brief=None, memory_context=None, pattern_context=None):
        schema = {
            "type": "object",
            "properties": {
                "콘텐츠유형": {"type": "string"},
                "핵심보상": {"type": "string"},
                "설명원자": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "개념": {"type": "string"},
                        "핵심주장": {"type": "string"},
                        "쉬운설명방식": {"type": "string"},
                        "좋은비유": {"type": "string"},
                        "좋은예문": {"type": "string"},
                        "흔한오해": {"type": "string"},
                        "인지또는사용보상": {"type": "string"},
                        "실전팁": {"type": "string"},
                        "중복및차별점": {"type": "string"},
                        "충돌및정확성주의": {"type": "string"},
                        "근거": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["개념", "핵심주장", "쉬운설명방식", "좋은비유", "좋은예문", "흔한오해", "인지또는사용보상", "실전팁", "중복및차별점", "충돌및정확성주의", "근거"],
                    "additionalProperties": False,
                }},
                "개념클러스터": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "개념": {"type": "string"},
                        "공통점": {"type": "array", "items": {"type": "string"}},
                        "차이점": {"type": "array", "items": {"type": "string"}},
                        "충돌": {"type": "array", "items": {"type": "string"}},
                        "새구조기회": {"type": "string"},
                    },
                    "required": ["개념", "공통점", "차이점", "충돌", "새구조기회"],
                    "additionalProperties": False,
                }},
                "보상후보": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "보상": {"type": "string"},
                        "종류": {"type": "string"},
                        "왜먹히는가": {"type": "string"},
                        "필요선행개념": {"type": "array", "items": {"type": "string"}},
                        "추천배치": {"type": "string"},
                    },
                    "required": ["보상", "종류", "왜먹히는가", "필요선행개념", "추천배치"],
                    "additionalProperties": False,
                }},
                "선행관계": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "개념": {"type": "string"},
                        "먼저필요한것": {"type": "array", "items": {"type": "string"}},
                        "이유": {"type": "string"},
                    },
                    "required": ["개념", "먼저필요한것", "이유"],
                    "additionalProperties": False,
                }},
                "자료별특이점": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "자료": {"type": "string"},
                        "좋은점": {"type": "string"},
                        "특이점": {"type": "string"},
                        "겹치는설명": {"type": "string"},
                        "비어있는점": {"type": "string"},
                        "가져올원리": {"type": "string"},
                        "복제금지요소": {"type": "string"},
                    },
                    "required": ["자료", "좋은점", "특이점", "겹치는설명", "비어있는점", "가져올원리", "복제금지요소"],
                    "additionalProperties": False,
                }},
                "콘텐츠엣지후보": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "엣지": {"type": "string"},
                        "종류": {"type": "string", "enum": ["연결", "설명", "정보", "비유", "실험", "규모", "관점", "구조", "경험", "결과", "캐릭터", "기타"]},
                        "발견방식": {"type": "string", "enum": ["시장반복", "내기존아이디어", "AI종합", "Memory회수", "혼합"]},
                        "왜특별한가": {"type": "string"},
                        "근거": {"type": "array", "items": {"type": "string"}},
                        "시장에흔한정도": {"type": "string", "enum": ["흔함", "중간", "희소", "판단불가"]},
                        "시청자보상": {"type": "string"},
                        "영상사용위치": {"type": "string"},
                        "채널적합이유": {"type": "string"},
                        "위험": {"type": "string"},
                    },
                    "required": ["엣지", "종류", "발견방식", "왜특별한가", "근거", "시장에흔한정도", "시청자보상", "영상사용위치", "채널적합이유", "위험"],
                    "additionalProperties": False,
                }},
                "핵심엣지추천": {
                    "type": "object",
                    "properties": {
                        "엣지": {"type": "string"},
                        "발견방식": {"type": "string", "enum": ["시장반복", "내기존아이디어", "AI종합", "Memory회수", "혼합"]},
                        "한줄세일즈포인트": {"type": "string"},
                        "선택이유": {"type": "string"},
                        "근거": {"type": "array", "items": {"type": "string"}},
                        "보조엣지": {"type": "array", "items": {"type": "string"}},
                        "검증할것": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["엣지", "발견방식", "한줄세일즈포인트", "선택이유", "근거", "보조엣지", "검증할것"],
                    "additionalProperties": False,
                },
                "포화된설명": {"type": "array", "items": {"type": "string"}},
                "아직비어있는연결": {"type": "array", "items": {"type": "string"}},
                "보상공백위험": {"type": "array", "items": {"type": "string"}},
                "최종지도": {"type": "string"},
                "정확성검증포인트": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["콘텐츠유형", "핵심보상", "설명원자", "개념클러스터", "보상후보", "선행관계", "자료별특이점", "콘텐츠엣지후보", "핵심엣지추천", "포화된설명", "아직비어있는연결", "보상공백위험", "최종지도", "정확성검증포인트"],
            "additionalProperties": False,
        }
        market_context = "\n\n".join(
            f"[시장 근거 {i}]\n영상: {r['제목']}\nChunk: {r['chunk번호']}\n{r['텍스트']}"
            for i, (_, r) in enumerate(market_sources.iterrows(), start=1)
        )
        my_context = "\n\n".join(
            f"[내 근거 {i}]\n영상: {r['제목']}\nChunk: {r['chunk번호']}\n{r['텍스트']}"
            for i, (_, r) in enumerate(my_sources.iterrows(), start=1)
        )
        market_analysis_data = (
            relevant_market_analysis[["제목", "핵심가치", "설명전략", "시청자가좋아한점", "미해결문제", "전이가능원리"]].to_dict("records")
            if not relevant_market_analysis.empty else []
        )
        prompt = f"""
[채널 프로필]
{self.settings.channel_profile}

[사용자 Content Brief]
{json.dumps(idea_brief or {}, ensure_ascii=False, indent=2, default=str)}

[선택 콘텐츠]
{json.dumps(selected_candidate, ensure_ascii=False, indent=2)}

[시장 Transcript 근거]
{market_context}

[관련 시장 분석]
{json.dumps(market_analysis_data, ensure_ascii=False, indent=2, default=str)}

[내 기존 콘텐츠 근거]
{my_context}

[지금까지 쌓인 Content Edge Memory]
{json.dumps(memory_context or [], ensure_ascii=False, indent=2, default=str)}

[시장 Content Pattern Memory]
{json.dumps(pattern_context or [], ensure_ascii=False, indent=2, default=str)}

[콘텐츠 설계 원칙]
{self.settings.content_design_principles}

[Content Edge 원칙]
{self.settings.content_edge_principles}

자료를 대본으로 바로 섞지 말고 먼저 원자화/비교하라.
특정 영상의 표현, 비유, 순서, 예문을 그대로 복제하지 않는다.
같은 개념의 여러 설명을 묶어 공통점/차이/충돌을 분리하고, 근거가 없는 부분은 정확성 검증 포인트로 남긴다.
콘텐츠유형을 먼저 정해놓고 끼워 맞추지 않는다. 시장 Content DNA와 Pattern Memory를 보고 이 영상이 어떤 구조 조합인지 자유롭게 이름 붙인다.
보상의 종류도 그 구조에서 추론한다. 개념 설명 중심이면 인지 보상, 수행 중심이면 성공/피드백, 반복 사용 중심이면 편의/재사용, 관점 중심이면 감정/호기심 같은 보상이 될 수 있지만 이것은 보조 휴리스틱일 뿐 고정 카테고리가 아니다.
보상은 억지로 30~60초마다 만들지 말고, 보상 공백이 길어질 위험 구간을 찾는다.
각 시장 자료마다 '이 자료만의 좋은 점/특이점/겹치는 설명/비어 있는 점'을 따로 남긴다.
그 뒤 여러 자료를 비교해 Core Edge 1개와 Supporting Edge를 제안한다.
Core Edge는 새 정보일 필요가 없으며 연결/설명/비유/실험/규모/관점/구조/경험/결과일 수 있다.
현재 수집한 자료만으로 희소성을 판단하고, '아무도 안 했다' 같은 과도한 단정은 하지 않는다.
이미 Memory에 있는 아이디어라면 재사용 여부와 발전점을 명시한다.
"""
        return self.cache.structured_response(
            "content_design_pack_v3_chat",
            "너는 여러 자료를 설명 원자로 분해하고 콘텐츠 유형별 보상 구조로 재조합하는 Content Learning Designer다.",
            prompt,
            schema,
        )

    def build_structure(self, selected_candidate, market_sources, my_sources, relevant_market_analysis, design_pack, idea_brief=None):
        schema = {
            "type": "object",
            "properties": {
                "콘텐츠유형": {"type": "string"},
                "핵심문제": {"type": "string"},
                "시청자변화": {"type": "string"},
                "핵심보상": {"type": "string"},
                "핵심엣지": {"type": "string"},
                "보조엣지": {"type": "array", "items": {"type": "string"}},
                "엣지전달계획": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "구간": {"type": "string"},
                        "보여줄엣지": {"type": "string"},
                        "전달방식": {"type": "string"},
                    },
                    "required": ["구간", "보여줄엣지", "전달방식"],
                    "additionalProperties": False,
                }},
                "오프닝문제": {"type": "array", "items": {"type": "string"}},
                "유지할것": {"type": "array", "items": {"type": "string"}},
                "개선할것": {"type": "array", "items": {"type": "string"}},
                "시장에서참고할것": {"type": "array", "items": {"type": "string"}},
                "새로추가할것": {"type": "array", "items": {"type": "string"}},
                "이번영상핵심과제": {"type": "array", "items": {"type": "string"}},
                "오프닝약속": {"type": "string"},
                "구조블루프린트": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "파트": {"type": "string"},
                        "목적": {"type": "string"},
                        "시청자상태": {"type": "string"},
                        "핵심내용": {"type": "array", "items": {"type": "string"}},
                        "사용할보상": {"type": "array", "items": {"type": "string"}},
                        "사용할근거": {"type": "array", "items": {"type": "string"}},
                        "다음파트연결": {"type": "string"},
                    },
                    "required": ["파트", "목적", "시청자상태", "핵심내용", "사용할보상", "사용할근거", "다음파트연결"],
                    "additionalProperties": False,
                }},
                "최종지도": {"type": "string"},
                "보상감사": {"type": "array", "items": {"type": "string"}},
                "피해야할것": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["콘텐츠유형", "핵심문제", "시청자변화", "핵심보상", "핵심엣지", "보조엣지", "엣지전달계획", "오프닝문제", "유지할것", "개선할것", "시장에서참고할것", "새로추가할것", "이번영상핵심과제", "오프닝약속", "구조블루프린트", "최종지도", "보상감사", "피해야할것"],
            "additionalProperties": False,
        }
        market_context = "\n\n".join(
            f"[시장 근거 {i}]\n영상: {r['제목']}\nChunk: {r['chunk번호']}\n{r['텍스트']}"
            for i, (_, r) in enumerate(market_sources.iterrows(), start=1)
        )
        my_context = "\n\n".join(
            f"[내 근거 {i}]\n영상: {r['제목']}\nChunk: {r['chunk번호']}\n{r['텍스트']}"
            for i, (_, r) in enumerate(my_sources.iterrows(), start=1)
        )
        prompt = f"""
[채널 프로필]
{self.settings.channel_profile}

[사용자 Content Brief]
{json.dumps(idea_brief or {}, ensure_ascii=False, indent=2, default=str)}

[선택 콘텐츠]
{json.dumps(selected_candidate, ensure_ascii=False, indent=2)}

[Content Design Pack]
{json.dumps(design_pack, ensure_ascii=False, indent=2, default=str)}

[시장 근거]
{market_context}

[내 기존 콘텐츠 근거]
{my_context}

[콘텐츠 설계 원칙]
{self.settings.content_design_principles}

완성 대본이 아니라 영상 경험 구조를 설계하라.
강의형이라면 질문→예문→차이 발견→원리→짧은 정리→다음 궁금증의 리듬을 우선하고, 콜드오픈에서 던진 문제를 본문에서 회수하며 마지막에는 최종 지도를 만든다.
강한 보상을 앞에 일부 배치하되 후반 payoff를 남긴다. 선행개념을 무시해 억지로 흥미로운 순서를 만들지 않는다.
Content Design Pack의 Core Edge 1개를 영상 전체의 중심 판매 포인트로 고정하고 제목/썸네일/오프닝 약속/최종 payoff가 같은 방향을 보게 한다.
Supporting Edge는 중간의 작은 보상으로 흩어 배치한다. Core Edge를 계속 문장으로 반복하지 말고 시청자가 구조와 예시를 통해 느끼게 한다.
같은 깨달음을 표현만 바꿔 반복하지 않는다. 보상 공백이 긴 구간은 압축/재배치 대상으로 표시한다.
내 콘텐츠는 정답이 아니라 강점/표현방식 참고다. 경쟁 영상의 독창적 표현은 복제하지 않는다.
"""
        result, usage, cached = self.cache.structured_response(
            "youtube_structure_blueprint_v5_edge",
            "너는 시장 리서치와 설명 원자, 선행관계, 시청자 보상을 이용해 교육영상 경험을 설계하는 Experience Designer다.",
            prompt,
            schema,
        )
        return result, usage, cached

    def write_script(self, selected_candidate, structure_result, design_pack, my_sources, idea_brief=None):
        schema = {
            "type": "object",
            "properties": {
                "핵심세일즈포인트": {"type": "string"},
                "제목후보": {"type": "array", "items": {"type": "string"}},
                "썸네일문구후보": {"type": "array", "items": {"type": "string"}},
                "오프닝": {"type": "string"},
                "파트별대본": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "파트": {"type": "string"},
                        "목적": {"type": "string"},
                        "대본": {"type": "string"},
                        "보상포인트": {"type": "array", "items": {"type": "string"}},
                        "예시또는화면": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["파트", "목적", "대본", "보상포인트", "예시또는화면"],
                    "additionalProperties": False,
                }},
                "최종지도": {"type": "string"},
                "마무리": {"type": "string"},
                "근거상주의할점": {"type": "array", "items": {"type": "string"}},
                "촬영여백": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["핵심세일즈포인트", "제목후보", "썸네일문구후보", "오프닝", "파트별대본", "최종지도", "마무리", "근거상주의할점", "촬영여백"],
            "additionalProperties": False,
        }
        style_context = "\n\n".join(
            f"[내 표현 참고 {i}]\n영상: {r['제목']}\n{r['텍스트']}"
            for i, (_, r) in enumerate(my_sources.head(5).iterrows(), start=1)
        )
        prompt = f"""
[채널 프로필]
{self.settings.channel_profile}

[사용자 Content Brief]
{json.dumps(idea_brief or {}, ensure_ascii=False, indent=2, default=str)}

[선택 콘텐츠]
{json.dumps(selected_candidate, ensure_ascii=False, indent=2)}

[Content Design Pack]
{json.dumps(design_pack, ensure_ascii=False, indent=2, default=str)}

[Structure Blueprint]
{json.dumps(structure_result, ensure_ascii=False, indent=2)}

[내 기존 영상의 표현 참고]
{style_context}

[콘텐츠 설계 원칙]
{self.settings.content_design_principles}

촬영 가능한 YouTube 대본 Draft A를 작성하라.
- Design Pack의 Core Edge를 핵심 세일즈 포인트로 유지하되 '특별한 영상입니다'라고 선언하지 말고 제목/썸네일/오프닝/예시/회수에서 증명한다.
- Supporting Edge는 본문 중간의 작은 인지/사용 보상으로 분산한다. 같은 Edge를 표현만 바꿔 반복하지 않는다.
- 자료를 짜깁기하지 말고 Design Pack의 원자/클러스터/선행관계를 재구성한다.
- 강의형이면 질문 → 예문 → 차이 발견 → 원리 설명 → 짧은 정리 → 다음 궁금증의 리듬을 기본으로 한다.
- 인지적 보상은 '여기 중요합니다/놀랍죠'라고 선언하지 말고 시청자가 예문/질문으로 먼저 발견하게 한다.
- 같은 깨달음을 표현만 바꿔 반복하지 않는다. 각 파트는 이전과 다른 새 보상을 줘야 한다.
- 30~60초마다 억지 Aha를 만들지 않는다. 대신 보상 없는 설명이 길어지지 않게 압축한다.
- 콜드오픈의 문제를 본문에서 회수하고, 마지막에는 따로 배운 내용을 한눈에 연결하는 최종 지도를 준다.
- 정확성을 위해 형태/역할/뜻을 구분하며 쉬운 비유가 실제 원리와 충돌하면 비유를 쓰지 않는다.
- 내 과거 대본은 말투/설명 습관 참고이지 정답이 아니다. 경쟁 콘텐츠 문장/비유/독창적 예문은 복제하지 않는다.
- 진행자가 실제 촬영에서 농담, 개인 경험, 추가 예시를 자연스럽게 넣을 수 있는 여백을 남긴다.
- 문장을 지나치게 한 줄씩 끊지 말고 읽기 좋은 문단 단위로 쓴다.
{SCRIPT_CLOSING_GUIDE}
"""
        return self.cache.structured_response(
            "youtube_script_draft_v4_edge_memory",
            "너는 리서치와 콘텐츠 설계 원칙을 바탕으로 인지/사용 보상이 살아있는 촬영용 영어교육 대본을 만드는 Script Writer다.",
            prompt,
            schema,
        )

    def revise_script(self, script_result, feedback):
        schema = {
            "type": "object",
            "properties": {
                "수정요약": {"type": "array", "items": {"type": "string"}},
                "핵심세일즈포인트": {"type": "string"},
                "제목후보": {"type": "array", "items": {"type": "string"}},
                "썸네일문구후보": {"type": "array", "items": {"type": "string"}},
                "오프닝": {"type": "string"},
                "파트별대본": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "파트": {"type": "string"},
                        "목적": {"type": "string"},
                        "대본": {"type": "string"},
                        "보상포인트": {"type": "array", "items": {"type": "string"}},
                        "예시또는화면": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["파트", "목적", "대본", "보상포인트", "예시또는화면"],
                    "additionalProperties": False,
                }},
                "최종지도": {"type": "string"},
                "마무리": {"type": "string"},
                "근거상주의할점": {"type": "array", "items": {"type": "string"}},
                "촬영여백": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["수정요약", "핵심세일즈포인트", "제목후보", "썸네일문구후보", "오프닝", "파트별대본", "최종지도", "마무리", "근거상주의할점", "촬영여백"],
            "additionalProperties": False,
        }
        prompt = (
            f"[현재 Script]\n{json.dumps(script_result, ensure_ascii=False, indent=2)}\n\n"
            f"[사용자 피드백]\n{feedback}\n\n"
            "사용자 피드백을 우선해 전체 대본을 수정하라. 기존 대본에서 좋은 부분은 유지하고, 수정이 필요한 부분만 바꾼다. "
            "Structure의 핵심 논리와 Core Edge, 근거 구분은 가능한 한 유지한다. 결과는 일부 문단만이 아니라 다시 촬영 가능한 전체 구조화 대본으로 반환한다."
            + "\n\n" + SCRIPT_CLOSING_GUIDE
        )
        return self.cache.structured_response(
            "youtube_script_revision_v2_full",
            "너는 사용자의 편집 지시를 반영하면서 전체 대본의 일관성을 유지하는 Script Editor다.",
            prompt,
            schema,
        )

    def write_draft_b(self, draft_a, critic_report, critic_sources, candidate_package, revision_mode="polish", benchmark_reference=None):
        if revision_mode not in {"polish", "rebuild"}:
            raise ValueError("Unknown revision mode")
        schema = {
            "type": "object",
            "properties": {
                "변경요약": {"type": "array", "items": {"type": "string"}},
                "검증근거": {"type": "array", "items": {"type": "string"}},
                "남은불확실성": {"type": "array", "items": {"type": "string"}},
                "핵심세일즈포인트": {"type": "string"},
                "제목후보": {"type": "array", "items": {"type": "string"}},
                "썸네일문구후보": {"type": "array", "items": {"type": "string"}},
                "오프닝": {"type": "string"},
                "파트별대본": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "파트": {"type": "string"},
                        "목적": {"type": "string"},
                        "대본": {"type": "string"},
                        "보상포인트": {"type": "array", "items": {"type": "string"}},
                        "예시또는화면": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["파트", "목적", "대본", "보상포인트", "예시또는화면"],
                    "additionalProperties": False,
                }},
                "최종지도": {"type": "string"},
                "마무리": {"type": "string"},
                "근거상주의할점": {"type": "array", "items": {"type": "string"}},
                "촬영여백": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["변경요약", "검증근거", "남은불확실성", "핵심세일즈포인트", "제목후보", "썸네일문구후보", "오프닝", "파트별대본", "최종지도", "마무리", "근거상주의할점", "촬영여백"],
            "additionalProperties": False,
        }
        package_summary = {
            "selected_candidate": candidate_package.get("selected_candidate") or {},
            "design_pack": candidate_package.get("design_pack") or {},
            "structure_result": candidate_package.get("structure_result") or {},
            "transcript_coverage": candidate_package.get("transcript_coverage") or {},
        }
        prompt = f"""
[Draft A]
{json.dumps(draft_a, ensure_ascii=False, indent=2, default=str)}

[Critic Agent Report]
{critic_report}

[Critic Agent Web Sources]
{json.dumps(critic_sources or [], ensure_ascii=False, indent=2, default=str)}

[원래 Research / Design]
{json.dumps(package_summary, ensure_ascii=False, indent=2, default=str)}

[채널 프로필]
{self.settings.channel_profile}

[콘텐츠 설계 원칙]
{self.settings.content_design_principles}

Critic Report를 근거로 촬영 가능한 Draft B 전체를 작성하라.
- Draft A를 무조건 많이 바꾸지 않는다. Critic이 근거를 제시한 부분과 명백한 구조 문제만 수정한다.
- Draft A의 Core Edge가 여전히 강하면 유지한다. 더 좋은 Edge가 근거로 확인된 경우에만 변경한다.
- 영어 문법/용법/학습효과를 웹 출처가 검증했다고 해도 출처가 실제로 뒷받침한 범위를 넘어서 단정하지 않는다.
- 시장 Transcript 근거와 웹 정확성 근거를 혼동하지 않는다.
- 중복 설명, 보상 없는 구간, 과도한 문법 우회는 압축한다.
- 제목/썸네일/오프닝 약속이 본문 payoff와 일치하게 만든다.
- 경쟁 콘텐츠의 독창적 문장/비유/예문을 복제하지 않는다.
- 문장을 촬영하기 좋게 읽기 좋은 문단으로 쓴다. 불필요하게 한 줄씩 끊지 않는다.
- 변경요약에는 A와 달라진 핵심만, 검증근거에는 실제로 확인된 근거 유형을, 남은불확실성에는 아직 검증되지 않은 것을 쓴다.
{SCRIPT_CLOSING_GUIDE}
"""
        if benchmark_reference:
            prompt += "\n\n[선택한 공개 채널 벤치마크 참고 자료]\n" + json.dumps(
                benchmark_reference, ensure_ascii=False, indent=2, default=str
            ) + "\n\n" + BENCHMARK_CRITIC_GUIDE
        if revision_mode == "rebuild":
            prompt += """

[실행 모드: 새로운 대본으로 독립 재설계]
핵심 주제와 실제 근거는 지키되, Draft A의 파트 순서/예문/도입 장면을 기본값으로 복사하지 말라.
Critic Report에서 제안한 대안 콘셉트 중 근거와 시청자 보상 설계가 가장 강한 접근을 고르고,
신선한 일상 장면, 새로운 오프닝 문제, 학습자가 실제로 수행할 과제와 자연스러운 3~6단계 전개를 구성하라.
'서로 다른 구성' 자체가 목표는 아니므로 Draft A의 탁월한 부분을 가져올 때는 변경요약에서 이유를 명시하라.
내부 자막과 외부 검증 근거의 범위를 지켜라. 검증되지 않은 학습효과나 조회수 상승을 주장하지 마라.
- 반드시 Critic의 시장 근거와 주제 판정(KEEP/REFRAME/RESEARCH_NEW)을 먼저 검토하라.
- KEEP이면 기존 주제라도 설명 틀은 재설계할 수 있다. REFRAME이면 근거가 있는 범위 내에서
  약속/제목/오프닝/교육 접근을 새롭게 만든다.
- RESEARCH_NEW라면 아직 시장조사하지 않은 제안 주제에 대한 본문을 검증된 것처럼 작성하지 말라.
  이 실행의 B는 기존에 수집된 증거 범위 내에서 최선의 대본으로 쓰고, 새 주제는 재조사가 필요하다고 적는다.
- 대상 시청자의 인지 부담을 먼저 줄여라: 설명→예시→수행을 불필요하게 반복하지 않고,
  각 파트의 단일 학습 보상에 집중한다. 예시는 짧고 직관적으로, 영어 문법 설명은 필요 최소화하라.
- 초안이 길고 친절하다는 이유만으로 좋다고 판단하지 말라. 불필요한 문장은 삭제해 촬영 원고를 압축하라.
- 순서는 3~5개 핵심 파트가 기본이며, 주제에 따라 그보다 더 적어도 된다.
- 자료가 뒷받침하지 않는 경쟁 우위·조회수 전망·논문 효과를 주장하지 말라.
최종 결과는 완성된 새 대본이어야 한다. 변경요약은 'A에서 버린 것 / 새로 만든 것 / 의도한 시청자 변화'로
짧고 구체적으로 3~5개 작성하라. 대본이 길어지는 것을 개선으로 착각하지 마라.
"""
        return self.cache.structured_response(
            "youtube_script_draft_b_v3_market_cognitive" if revision_mode == "rebuild" else "youtube_script_draft_b_v1_agent_critic",
            "너는 시장 Research와 비평을 근거로 독립적으로 대본을 재설계하는 Senior Script Writer다."
            if revision_mode == "rebuild" else
            "너는 Critic Agent의 검증 결과를 반영하되 근거 없는 과수정을 피하는 Senior Script Writer다.",
            prompt,
            schema,
        )

    def compare_drafts(self, draft_a, draft_b, critic_report):
        schema = {
            "type": "object",
            "properties": {
                "한줄판단": {"type": "string"},
                "B가개선한점": {"type": "array", "items": {"type": "string"}},
                "A가더나은점": {"type": "array", "items": {"type": "string"}},
                "실제로비교해서볼구간": {"type": "array", "items": {"type": "string"}},
                "추천": {"type": "string", "enum": ["A유지", "B추천", "A와B혼합", "사람판단필요"]},
                "추천이유": {"type": "string"},
            },
            "required": ["한줄판단", "B가개선한점", "A가더나은점", "실제로비교해서볼구간", "추천", "추천이유"],
            "additionalProperties": False,
        }
        prompt = f"""
[Draft A]
{json.dumps(draft_a, ensure_ascii=False, indent=2, default=str)}

[Draft B]
{json.dumps(draft_b, ensure_ascii=False, indent=2, default=str)}

[Critic Report]
{critic_report}

두 대본을 실제 촬영/시청 관점에서 비교하라.
B가 Agent를 썼다는 이유로 B를 우대하지 마라. A가 더 직관적이거나 자연스러운 부분도 반드시 찾는다.
정확성, Core Edge 선명도, 오프닝, 정보 밀도, 반복, 보상 흐름, 촬영 자연스러움을 기준으로 판단한다.
"""
        return self.cache.structured_response(
            "youtube_script_ab_compare_v1",
            "너는 A/B 두 대본을 편견 없이 비교하는 YouTube Script Reviewer다.",
            prompt,
            schema,
        )
