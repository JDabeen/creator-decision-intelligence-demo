# Creator Decision Intelligence — Public Demo

유튜브 콘텐츠의 다음 주제를 시장 근거와 채널 데이터로 비교하고, 대본 제작까지 연결하는 AI 크리에이터 의사결정 시스템입니다.

> 이 저장소는 **공개 데모**입니다. 데모에서는 가상 데이터를 사용하며 실제 YouTube/OpenAI/Hermes API를 호출하지 않습니다.

## 사용 흐름

신규 유입·신뢰 형성 선택 → A/B 추천 비교 → 관련 근거 검토 → 영상 방향 선택 → Draft A/B → 최종 대본

## 로컬에서 데모 실행

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

현재 앱 소스와 가상 데이터는 업로드 준비 중입니다. **README만으로 데모가 실행되지는 않습니다.**

## 전체 프로그램

전체 소스는 별도 공개 저장소로 관리할 예정입니다. 전체 프로그램은 실제 데이터 수집과 유료 AI API가 필요하며 사용자 자신의 API 키로 로컬 실행해야 합니다.

## 보안

API 키, `.env`, 개인 채널 자료, 수집 캐시 및 진단 로그는 저장소에 올리지 않습니다.

## 시연 영상

녹화 파일이 준비되면 GitHub에 직접 첨부하거나 영상 파일 링크를 이곳에 추가할 예정입니다.
