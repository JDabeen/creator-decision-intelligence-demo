from dataclasses import dataclass

CHANNEL_PROFILE = """
[실제 채널 Audience Snapshot · 최근 28일 기준]
- 시청 시간 기준 구독 안 함 69.0%, 구독 중 31.0%.
- 성별: 남성 67.0%, 여성 32.9%.
- 연령: 45~54세 16.8%, 55~64세 51.9%, 65세 이상 31.3%. 즉 현재 핵심 시청자는 45세 이상, 특히 55~64세다.
- 지역: 대한민국 87.8% 중심.
- 기기: 휴대전화 73.8%, 컴퓨터 12.8%, TV 11.4%, 태블릿 2.0%.
- 최근 인기 콘텐츠는 영어 순서/어순, 회화 핵심 원리, 동사 활용, 해외여행 회화처럼 '이미 배운 지식을 다시 연결하거나 실제 말하기로 바꾸는' 주제가 강하다.

[Audience 해석 원칙]
- 45~65+ 성인이 중심이라는 사실과 '왕초보'를 동일시하지 않는다.
- 영상마다 예상 영어 수준을 다시 추정한다. 완전 초보, 기초 문법 경험자, 읽기는 되지만 말하기가 약한 사람, 문법 지식은 있으나 서로 연결되지 않는 사람 등이 함께 있을 수 있다.
- 설명은 쉽게 하되 내용까지 무조건 초급으로 낮추지 않는다. 이미 영어를 오래 공부한 성인도 새롭게 느낄 연결, 이유, 응용을 제공한다.
- 경쟁 영상의 공개 정보(제목/설명/Transcript/댓글/예문 난이도/문법 용어/학습 전제)를 바탕으로 예상 연령대와 영어 수준을 '추정 + 근거' 형태로 판단하고 사실처럼 단정하지 않는다.

[채널 방향]
문법 지식을 외우는 것보다 실제로 말이 나오게 만드는 설명, 생활밀착 예문, 반복 훈련, 흩어진 개념을 연결해 주는 설명을 중시한다.
채널의 목적은 조회수 최대화만이 아니라 Content → Audience → Trust → Product/Service → Revenue 흐름을 만드는 것이다.
따라서 추천과 대본 설계에서 시장 수요, 현재성, 내 채널 적합도, 신규성, 교육 가치, 신뢰 형성, 비즈니스 연결,
차별성, 브랜드 적합성, 확장성, 시장 포화도를 함께 고려한다.
""".strip()

HYPOTHESIS_FRAMEWORK = """
MAP:
- 어떤 주제/문제/욕구에 시청자가 반복해서 반응하는가?
- 절대 성과뿐 아니라 채널 대비 Outlier, 최근 신호, 내 채널의 과거 성과를 함께 본다.
- 조회수가 큰 포맷이 곧 내 채널에 최적이라는 뜻은 아니다. 콘텐츠 유형과 비즈니스 목적을 구분한다.

INTRO:
- 제목/썸네일을 보고 들어온 사람이 '내가 찾던 영상이 맞다'고 빠르게 확신할 수 있는가?
- 정보보다 먼저 구체적인 증상/상황으로 공감을 만든 뒤, 문제의 원인과 해결 약속을 제시하는가?
- 콜드오픈에 2~3개의 흥미로운 문제를 던지고 본문에서 회수할 수 있는가?

BODY:
- 영상이 끝났을 때 시청자가 무엇을 이해하고, 할 수 있고, 기억하거나 느끼게 되는가?
- 정보 나열보다 시청자의 상태 변화가 일어나도록 설계하는가?
- 강의형이라면 같은 깨달음을 반복하지 말고 서로 다른 종류의 인지 보상을 지속적으로 제공하는가?

STRATEGY:
- 내 채널에서 이미 잘된 패턴은 그대로 복제하지 말고 발전시킬 가치가 있는가?
- 시장의 Outlier/우수 사례에서 주제와 구조의 전이 가능한 원리를 찾을 수 있는가?
- 내 서비스/상품의 핵심 문제와 자연스럽게 이어져 신뢰를 쌓을 수 있는가?
- 경쟁 콘텐츠의 표현, 비유, 순서, 예문을 그대로 복제하지 않는다.
""".strip()

CONTENT_DESIGN_PRINCIPLES = """
[공통]
- 자료를 바로 대본으로 섞지 않는다. 먼저 설명 아이디어의 원자 단위로 분해한다.
- 각 자료에서 핵심 주장, 쉬운 설명 방식, 비유, 예문, 흔한 오해, 인지적 보상, 실전 팁,
  중복, 충돌, 독특한 관점을 분리한다.
- 같은 개념을 설명하는 자료끼리 묶어 공통점/차이/충돌을 비교하고 새 구조를 설계한다.
- 정확성이 필요한 주제에서는 형태(form), 역할(function), 뜻(meaning)을 구분한다.
- 쉬운 비유가 실제 원리와 충돌하면 비유를 버린다.
- 대본의 핵심 정의와 논리는 고정하되 진행자가 촬영에서 자신의 말투, 농담, 추가 예시를 넣을 여백을 남긴다.

[콘텐츠 패턴 해석 원칙]
- 강의형/훈련형/자료형 같은 고정 분류를 정답으로 사용하지 않는다. 실제 시장 영상의 Content DNA와 구조를 분석해 반복 패턴/클러스터를 발견한다.
- 한 영상은 여러 패턴을 동시에 가질 수 있다. 예: 개념연결 + 오해교정 + 즉시테스트.
- 다만 시장 데이터가 아직 부족할 때만 보조 휴리스틱으로 다음 보상 원리를 참고한다:
  · 개념/설명 중심: 오해 해소, 연결, 이유 발견, 즉시 활용 같은 인지 보상
  · 수행/훈련 중심: 실제 성공 경험, 피드백, 힌트 제거, 난이도 상승
  · 반복/자료 중심: 사용 편의, 반복 소비, 상황 정리
  · 관점/스토리 중심: 감정, 호기심, 갈등, 회수, 관점 변화
- 30~60초마다 억지로 보상을 만들지 않는다. 대신 30~90초 동안 새로운 보상이 없는 구간은 압축/재배치를 검토한다.
- 질문과 예문으로 먼저 발견하게 하고, 설명자는 마지막에 짧게 정리한다.
- 마지막에는 단순 공식 나열보다 따로 배운 내용을 연결하거나 실제 수행 변화가 보이게 한다.
""".strip()

CONTENT_EDGE_PRINCIPLES = """
[Content Edge]
- 모든 영상은 '왜 굳이 이 영상을 봐야 하는가?'에 답할 수 있는 Core Edge 1개를 우선 찾는다.
- 특별함은 새 정보만 뜻하지 않는다. 연결, 설명, 비유, 실험, 규모, 관점, 구조, 경험, 결과, 캐릭터도 Edge가 될 수 있다.
- 각 자료를 보며 그 자료만의 좋은 점/특이점, 다른 자료와 겹치는 설명, 비어 있는 연결, 가져올 수 있는 원리를 따로 적는다.
- 한 자료의 독창적 표현/비유/예문/순서를 복제하지 않는다. 여러 자료의 공통점과 차이를 바탕으로 새 구조를 만든다.
- '희소하다'는 판단은 현재 수집된 자료 범위에서만 말한다. 충분한 근거 없이 '아무도 안 했다', '유일하다'고 단정하지 않는다.
- Core Edge는 제목/썸네일/오프닝/본문의 핵심 약속이 서로 같은 방향을 보게 만든다.
- Supporting Edge는 본문 중간의 작은 인지/사용 보상으로 배치한다.
- 이미 사용한 Edge를 다시 쓸 때는 단순 반복이 아니라 새 맥락/난이도/응용으로 발전시키는지 확인한다.
""".strip()


@dataclass(frozen=True)
class Settings:
    my_channel_handle: str = "@틀린영어"
    llm_model: str = "gpt-5.6-luna"
    embedding_model: str = "text-embedding-3-small"

    min_duration_seconds: int = 5 * 60
    max_duration_seconds: int = 60 * 60
    recent_window_days: int = 90
    recent_breakout_window_days: int = 45
    recent_breakout_min_views: int = 5000
    recent_breakout_min_channel_ratio: float = 3.0
    recent_breakout_min_subscriber_ratio: float = 5.0
    market_signal_min_views: int = 1000
    candidates_per_signal: int = 5

    # Deep Research는 시장 Transcript가 핵심이다. 아래 기준 미달이면
    # 메타데이터만으로 그럴듯한 Draft를 만들지 않고 Research를 중단한다.
    market_transcript_min_count: int = 2
    market_transcript_min_ratio: float = 0.35
    transcript_request_delay_seconds: float = 0.65

    chunk_size: int = 1200
    chunk_overlap: int = 200

    home_probe_query_count: int = 6
    home_search_per_duration: int = 12

    channel_profile: str = CHANNEL_PROFILE
    hypothesis_framework: str = HYPOTHESIS_FRAMEWORK
    content_design_principles: str = CONTENT_DESIGN_PRINCIPLES
    content_edge_principles: str = CONTENT_EDGE_PRINCIPLES
    content_goal: str = "pulling"
    business_profile: str = ""

    @property
    def content_goal_guide(self) -> str:
        return CONTENT_GOAL_GUIDE.get(self.content_goal, CONTENT_GOAL_GUIDE["pulling"])

CONTENT_GOAL_GUIDE = {
    "pulling": """
[PULLING CONTENT]
목표는 사람을 모으는 것이다. 추천 우선순위는 시장 반응, 클릭/호기심, Knowledge Gap, 현재성, 차별화, 내 채널과의 적합성이다.
비즈니스 전환과 상품 연결은 참고 정보일 뿐 추천 순위를 좌우하는 1차 기준으로 사용하지 않는다.
특히 '어떤 영어 지식/오해/개념 연결을 알려줄 것인가'를 반드시 명시한다. 단순 포맷 추천으로 끝내지 않는다.
추천 3개 중 가능하면 1개는 최근 45일의 실제 Breakout에서 출발하고, 나머지 2개는 검증된 시장 Gap/Knowledge Gap에서 찾는다.
""".strip(),
    "key": """
[KEY CONTENT]
목표는 이미 들어온 시청자가 충분히 설득되어 상품/서비스를 사는 데 필요한 신뢰를 만드는 것이다.
추천 우선순위는 문제 진단력, 교육 가치, 실제 행동 변화, 내 방법론의 차별성, 반대/불안 해소, 서비스와의 자연스러운 연결이다.
조회수보다 '이 사람이 내 문제를 정확히 알고 있고, 이 방식이면 해볼 만하다'는 체험을 중요하게 본다.
실제 상품 정보가 부족하면 임의의 상품을 사실처럼 만들지 말고 '상품 정보 부족'을 명시한다.
현재 사업과 신규 사업 가설을 분리한다.
""".strip(),
}
