# v1.5 — 시장자료 공유 / 대본 독립 생성 / A·B 비교

**목적**: 기존 유튜브 리서치 API/RAG 자료와 내 채널 과거 대본은 활용하면서, Hermes가 지금 만드는 Draft A의 구성·내용에 끌려가지 않고 별도 Draft B를 만들게 한다.

기존 Streamlit Research와 Draft A는 그대로 유지한다. 웹 검색 도구가 실제 작동하지 않으면 Hermes B는 생성하지 않는다.

1. `.env`를 준비하고 `0_START_WITH_HERMES.bat`으로 기존 앱의 Draft A를 만든다.
2. `11_HERMES_독립_A_B_실험.bat`을 실행한다. 최신 Run JSON에서 시장 데이터와 과거 대본만 추출해 Evidence Pack을 동결한다.
3. Hermes의 실제 웹 검색을 검사한다. 웹 도구 응답과 URL 없이는 중단한다.
4. 동일한 기본 시장 데이터 + Hermes 새 검색 자료로 독립 B를 작성한다. Draft A 원문/설계안은 이 단계에서 절대 보내지 않는다.
5. 별도 OpenAI 평가 API는 Draft A와 B를 익명 X/Y로 비교하고, 결과를 `comparison.md`에 기록한다. 심사 모델이 Hermes와 동일 기저 모델일 수 있으므로 그 판단도 검증된 조회수/객관적 정답은 아니다.

자료가 빠져 있는 구버전 실행 기록을 가져와도 일부 단계는 실행할 수 있지만, 근거 부족 경고가 남는다. **정식 GitHub 데모에 쓰려면 v1.5로 새 Draft A를 생성**해야 경쟁 대본 조각·내 과거 대본 조각까지 동결된다.

결과 폴더는 기존 데이터 디렉터리의 `experiments/` 아래에 생성된다. 폴더에는 `manifest.json`, `evidence.json`, `hermes_research.json`, `draft_a.md`, `draft_b_hermes.md`, `comparison.md`가 포함된다. API 키는 저장하지 않는다.

이 평가는 **텍스트 기반 제작방식 비교 실험**이고, 실제 유튜브 사용자에게 무작위 분배하는 A/B 테스트가 아니다. 조회수·CTR·체류시간의 인과적 개선은 실제 게시 후 별도 검증해야 한다.

기술 개요: `hermes_experiment/PORTFOLIO_METHOD.md` 참고.
