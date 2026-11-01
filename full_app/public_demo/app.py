"""Streamlit portfolio demo — fully synthetic, API-free, privacy safe."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

DATA = json.loads((Path(__file__).parent / 'demo_data.json').read_text(encoding='utf-8'))
CHANNEL = DATA['channel']

st.set_page_config(page_title='Creator Decision Intelligence · Public Demo', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {background:#101317 !important;}
.block-container{max-width:1120px!important;padding-top:2.5rem!important;}
#MainMenu,footer{visibility:hidden!important}
.h-kicker{font-size:.72rem;letter-spacing:.15em;color:#70c2d8;font-weight:700}
.h-title{font-size:2.2rem;line-height:1.2;font-weight:750;margin:.55rem 0 1rem}
.h-sub{color:#a0aab4;line-height:1.6;font-size:.94rem}
.s-kicker{color:#7c8d9f;font-size:.78rem;font-weight:700;letter-spacing:.04em}
.card{background:#192128;border:1px solid #30404a;border-radius:14px;padding:1.25rem;margin:.45rem 0 1rem}
.rank{color:#8bd4dd;font-size:.82rem;font-weight:800}.card h3{font-size:1.14rem;margin:.45rem 0}
.card p{color:#b8c6cf;font-size:.89rem;line-height:1.56;margin:.3rem 0}
.soft{background:#182129;border:1px solid #253540;border-radius:12px;padding:1.2rem}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="h-kicker">CREATOR DECISION INTELLIGENCE / INTERACTIVE DEMO</div>', unsafe_allow_html=True)
st.markdown('<div class="h-title">다음 영상을 고르는 판단까지, 기록합니다.</div>', unsafe_allow_html=True)
st.markdown('<div class="h-sub">시장 신호 × 채널 성과 × 댓글 행동 × 독립적인 AI 조사 × 발행 후 검증</div>', unsafe_allow_html=True)
st.warning('**공개 데모 · 모든 영상·조회수·댓글·AI 판단·성과는 가상 데이터입니다.** API 호출·실제 채널 연결·모델 학습·실제 예상 조회수는 실행하지 않습니다.', icon='🧪')

videos = CHANNEL['videos']
raw_comments = sum(v['comments'] for v in videos)
c1,c2,c3,c4 = st.columns(4)
c1.metric('샘플 영상', f'{len(videos)}편')
c2.metric('공개 총댓글 · 절대치', f'{raw_comments:,}개')
c3.metric('관찰된 가상 28일 결과', f"{len(DATA['mock_decisions'])}편")
c4.metric('비교 후보', 'A 3개 / B 3개')

overview, recommendations, comments, feedback = st.tabs(['01  시장·채널 진단', '02  A / Hermes 독립 판단', '03  댓글 행동 분석', '04  판단 → 실제 결과'])

with overview:
    st.subheader('내 채널의 공개 관측치 (가상)')
    st.caption('댓글 절대 수로 내림차순 정렬 · 업로드 시점 및 노출 차이를 통제한 분석이 아닙니다.')
    data = sorted(videos, key=lambda x: -x['comments'])
    st.dataframe([{'제목':v['title'],'공개 댓글(절대 수)':v['comments'],'누적 조회수(참고)':v['views'],'업로드':v['published'],'형식 가설':v['format']} for v in data], hide_index=True, use_container_width=True)
    st.bar_chart({'영상': [f"영상 {v['id'][-3:]}" for v in data], '댓글 수': [v['comments'] for v in data]}, x='영상', y='댓글 수', horizontal=True)
    st.info('가설: 절대 댓글이 많은 영상은 참여를 유발했을 가능성이 있다. 다만 구매 전환·학습 효과·알고리즘 선호는 아직 알 수 없다.')
    st.markdown('#### 시장 검색 관심 참고 · 가상 예시')
    st.dataframe([{'가상 검색어':x['keyword'], '동일 조건 내 상대 관심도 (0–100)':x['youtube_search_interest_relative']}
                  for x in DATA['illustrative_market_interest']], hide_index=True, use_container_width=True)
    st.caption('실제 검색량도, 측정된 Google Trends 값도 아닙니다. 0–100은 상대 관심도 예시이며 영상 조회수나 성공 확률을 예측하지 않습니다.')

with recommendations:
    st.subheader('A와 Hermes의 독립 우선순위')
    st.caption('각 엔진은 1~3순위와 판단 근거를 제시합니다. 동일 조건 모델 A/B 테스트나 조회수 예측이 아닙니다.')
    goal = st.segmented_control('이번 콘텐츠 목표', options=['신규 유입', '신뢰·구매'], default='신뢰·구매')
    left,right=st.columns(2)
    for col,name in ((left,'A'),(right,'Hermes')):
        with col:
            st.markdown(f'### {"A · 내부 분석" if name == "A" else "B · 독립 웹 조사 (시뮬레이션)"}')
            for r in DATA['recommendations'][name]:
                st.markdown(f'''<div class="card"><div class="rank">{r['rank']}순위 · {r['route']}</div><h3>{r['title']}</h3><p><b>선정 근거</b> · {r['reason']}</p><p><b>대안과 비교</b> · {r['tradeoff']}</p><p><b>시장 근거</b> · {r['demand']}</p></div>''',unsafe_allow_html=True)
    choices = [(name,r) for name in ('A','Hermes') for r in DATA['recommendations'][name]]
    idx = st.selectbox('제작 검토할 후보', range(len(choices)), format_func=lambda i:f"{choices[i][0]} {choices[i][1]['rank']}순위 · {choices[i][1]['title']}")
    if st.button('이번 판단을 데모에 임시 기록', type='primary'):
        st.session_state['demo_choice'] = choices[idx][1]['title']
        st.success('데모 세션에 임시 기록했습니다. 실제 앱은 판단 당시 근거를 바탕화면 별도 데이터 폴더에 기록합니다.')
    if st.session_state.get('demo_choice'):
        st.caption(f"현재 데모 선택: {st.session_state['demo_choice']}")
    st.caption(f'목표 선택: {goal}. 데모는 고정된 가상 추천을 보여주며 선택만 시뮬레이션합니다.')

with comments:
    st.subheader('Comment Intelligence · 댓글을 단순 참여가 아니라 행동으로')
    st.caption('공개 총댓글은 실제 API가 반환할 수 있는 절대 수라는 개념을 시연합니다. 원댓글 AI 분류는 일부 표본이며, 카테고리 역시 가상 예시입니다.')
    target = st.selectbox('관찰 대상 영상', [v['id'] for v in videos], format_func=lambda k:next(v['title'] for v in videos if v['id']==k))
    v=next(v for v in videos if v['id']==target)
    x,y=st.columns(2)
    x.metric('공개 총댓글 · 절대 수', f"{v['comments']:,}개")
    y.metric('누적 조회수 · 별도 참고', f"{v['views']:,}회")
    review=CHANNEL['review_samples'].get(target)
    if review:
        st.markdown(f"**분석된 원댓글 표본 {review['sample_count']}개** · 표본은 전체 댓글이 아닙니다")
        st.bar_chart({'행동':list(review['categories']),'댓글 수':list(review['categories'].values())},x='행동',y='댓글 수',horizontal=True)
        st.info(review['insight'])
    else:
        st.info('이 영상은 예시 텍스트 분석이 없습니다. 원댓글을 실제로 검토하지 않았다면 감정이나 구매 의사를 추정하지 않습니다.')
    st.caption('비율 지표를 계산하지 않습니다. 총댓글은 답글 포함 가능, 분류 표본은 원댓글 일부입니다. 댓글 숫자만으로 품질이나 구매를 입증하지 않습니다.')

with feedback:
    st.subheader('예측을 꾸미지 않고, 사전 판단과 사후 관측을 연결')
    st.caption('아래 이력은 시연용 가상 실험입니다. 실제 서비스는 발행 전 결정 기록과 관측된 7일·28일 데이터를 연결합니다.')
    st.dataframe([{'선택 당시 주제':x['topic'],'사전 판단':x['predicted'],'업로드':x['released'],'28일 조회수':x['views_28d'],'28일 총댓글':x['comments_28d'],'관측 상태':x['status']} for x in DATA['mock_decisions']], hide_index=True, use_container_width=True)
    st.markdown('''**판단 개선 원칙**: 과거 후보를 무조건 유지하지 않습니다. 새로운 근거가 생기면 기존 가설과 비교합니다. 무엇을 예상했는지 사전에 고정하고 실제 결과가 충분히 확보됐을 때만 검증합니다.''')
    st.info('이 데모는 실제 Hermes, SerpApi, YouTube API, 원댓글 수집, 로컬 누적 저장을 수행하지 않습니다. 해당 기능은 로컬 전체 앱에서 API 키·Docker 설정 후 실행합니다.')

st.divider()
st.caption('Portfolio prototype · synthetic demonstration only · privacy-safe · no API keys · no raw comments or user data shipped')
