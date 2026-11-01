"""Optional reference for Draft B. No API keys or third-party transcripts stored here."""
from __future__ import annotations

BENCHMARK_NAME = "180도 스피킹"
BENCHMARK_URL = "https://www.youtube.com/@180도스피킹"
BENCHMARK_CHANNEL_ID = "UCTw50WTknLa1G6m48kkkEhw"


def make_benchmark_reference(user_notes: str = "") -> dict:
    """Return bounded metadata reference, not a claim of transcript-level research."""
    return {
        "channel_name": BENCHMARK_NAME,
        "channel_url": BENCHMARK_URL,
        "channel_id": BENCHMARK_CHANNEL_ID,
        "verified_as_of": "2026-10-31",
        "observed_public_positioning": [
            "성인 학습자를 대상으로 한국어 사고를 영어 표현으로 전환하는 훈련을 강조",
            "복잡한 생각을 단순한 영어 표현으로 바꾸는 접근을 채널 소개에서 강조",
            "실제 생활에서 사용할 수 있는 말하기 연습을 강조",
        ],
        "observed_video_titles": [
            "이것만 외우면, 절대 당황하지 않고 말할 수 있어요.ㅣ실전 영어 상황 (2026-10-22)",
            "이 규칙만 깨달으면, 영어초보도 하고싶은 말 다 할 수 있어요. (2026-10-18)",
            "맨날 쓰는 말부터 영어로 바꾸면, 영어로 말 금방해요. (2026-09-19)",
        ],
        "source_pages": [
            "https://vling.net/channel/UCTw50WTknLa1G6m48kkkEhw/channel-info",
            "https://kurve.gg/youtube/UCTw50WTknLa1G6m48kkkEhw",
        ],
        "evidence_limit": (
            "채널 소개와 공개 영상 제목 수준의 스냅샷이다. 해당 영상의 실제 Transcript/구성/"
            "학습효과/시청 유지율/흥행 인과관계는 확인하지 않았다. "
            "이 참고 자료를 시장 수요 검증이나 문법 정확성 근거로 사용할 수 없다."
        ),
        "creator_observation_notes_unverified": str(user_notes or "").strip()[:1200],
        "evaluation_dimensions": [
            "핵심 원리를 성인이 빠르게 이해할 수 있는가 (직관성)",
            "시청자가 자신의 문장을 직접 만들어 말할 기회가 있는가 (수행성)",
            "도입에서 제시한 질문을 마지막에 실제 답과 성취로 회수하는가 (완결성)",
        ],
    }


BENCHMARK_CRITIC_GUIDE = """
[선택 벤치마크 적용 규칙]
- 첨부한 벤치마크 자료는 채널 소개/영상 제목 수준의 관찰 정보다. 실제 영상 자막을 확보한 것처럼 말하지 마라.
- 상대 채널의 고유 대본·표현·예문·썸네일 문구·구성을 그대로 모방하지 마라.
- 관찰된 '성인용 직관성·한국어→영어 전환·생활 맥락'을 우리 원고의 비평 질문으로만 활용하라.
- Draft A를 (1) 이해하기 쉬운 원리, (2) 직접 말해보는 성취, (3) 닫힌 교육적 결말로 평가하라.
- 근거가 없는 성공 비법·수치·실제 설명 방식을 지어내지 마라.
- Critic Report에서 '벤치마크에서 확인한 사실'과 '우리에게 적용할 평가 제안'을 명시적으로 구분하라.
""".strip()


SCRIPT_CLOSING_GUIDE = """
[촬영 대본의 결말 품질 — 반드시 지켜라]
- '마무리'는 영상의 진짜 결말이다. 첫 15초에 던진 질문·문제를 마지막에 분명한 답으로 회수한다.
- 학습자가 영상이 끝날 때 할 수 있게 된 구체적 행동 또는 한 가지 핵심 원리를 보여준다.
- 가능하면 본문에서 사용한 예문/상황으로 짧게 성공을 확인하고, 한 줄로 배울 점을 압축한다.
- 실천 과제는 주제에 맞는 것 1개 이내로 간결하게 연결하고 자연스러운 종결 문장으로 끝낸다.
- 시청자에게 댓글을 달라고 하거나 추가 질문을 유도하는 문장을 결말 대신 사용하지 마라.
  댓글/구독 요청은 정말 필요한 경우 교육적 결말을 끝낸 다음 덧붙이는 짧은 선택 사항이다.
- 다음 영상 예고를 할 수는 있지만 이번 영상의 해답을 미완성 상태로 두거나 '다음 편에서 알려주겠다'로 미루지 마라.
- 상투적인 감동·과장·억지 반전이 아니라 채널의 차분하고 직관적인 설명 톤으로 마무리한다.
""".strip()
