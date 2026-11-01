from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from config import Settings
from pipeline import ResearchPipeline
from presenters import script_to_markdown
from benchmark_reference import BENCHMARK_URL, make_benchmark_reference
from closing_quality import ending_warnings
from storage import RunStore
from strategy_hub import StrategyStore, consult_strategy
from decision_intelligence import market_observation, evidence_for_comparison
from trend_provider import capture_topic_trends, lookup_term
from topic_ranking import priority_label, rank_reason, relative_reason, order_recommendations
from comment_intelligence import absolute_comment_leaderboard, fetch_top_level_comments, classify_comment_sample
from research_resilience import safe_error, SearchQuotaExhausted

PROJECT_ROOT = Path(__file__).resolve().parent
BUILD_VERSION = "v2.2-resilient-evidence-review-2026-10-31"
load_dotenv(PROJECT_ROOT / ".env")

def default_data_root() -> str:
    env_root = os.getenv("YRA_DATA_DIR")
    if env_root:
        return env_root
    desktop = Path.home() / "Desktop"
    return str((desktop / "youtube_consultant_data") if desktop.exists() else (PROJECT_ROOT / "data"))


def load_business_profile(data_root: str) -> str:
    path = Path(data_root).expanduser() / "business_profile.txt"
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""

st.set_page_config(
    page_title="YouTube Content Consultant",
    page_icon="●",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
/* Creator Decision Intelligence — Quiet graphite design system.
   One visual hierarchy across the live app and the synthetic public demo. */
:root { color-scheme: dark; --cdi-bg:#101112; --cdi-panel:#1d1f20;
 --cdi-panel-hover:#252729; --cdi-line:#303234; --cdi-text:#f0f0ee;
 --cdi-muted:#a3a5a6; --cdi-dim:#777a7c; }
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{
 background:var(--cdi-bg)!important;color:var(--cdi-text)!important;
 font-family:Inter,"Pretendard","Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif!important;
}
[data-testid="stHeader"] {background:rgba(16,17,18,.94)!important;}
[data-testid="stToolbar"],#MainMenu,footer {visibility:hidden!important;}
.block-container {max-width:786px!important;padding:4.5rem 1.7rem 7rem!important;}
*,*::before,*::after {box-sizing:border-box;}
h1,h2,h3,h4,p {letter-spacing:-.025em;}
h1,h2,h3 {color:var(--cdi-text)!important;}
p,li {line-height:1.72;}
a {color:#dededd!important;text-underline-offset:3px;}
hr {border:0!important;border-top:1px solid var(--cdi-line)!important;margin:2rem 0!important;}
/* Homepage: intentional negative space, one task. */
.hero {text-align:center;margin:clamp(3.8rem,12vh,8rem) 0 1.8rem;}
.hero h1 {font-size:clamp(1.65rem,3.5vw,2.3rem);letter-spacing:-.05em;
 line-height:1.32;font-weight:680;margin:0;color:#f4f3f1;}
.hero p,.hero .brand {display:none!important;}
[data-testid="stForm"] {background:#202223!important;border:1px solid #353738!important;
 border-radius:23px!important;padding:14px 16px!important;box-shadow:none!important;}
[data-testid="stTextArea"] textarea {background:transparent!important;color:#f0f0ee!important;
 border:0!important;box-shadow:none!important;resize:vertical!important;
 line-height:1.65!important;font-size:.96rem!important;}
[data-testid="stTextArea"] textarea:focus {box-shadow:none!important;outline:none!important;}
[data-testid="stTextArea"] textarea::placeholder {color:#777b7d!important;}
[data-testid="stTextInput"] input {background:#202223!important;border-color:#3a3d3e!important;color:#f0f0ee!important;}
[data-testid="stFormSubmitButton"] button {background:#f0f0ee!important;border:1px solid #f0f0ee!important;
 color:#151617!important;border-radius:999px!important;min-height:40px!important;font-weight:680!important;}
[data-testid="stFormSubmitButton"] button:hover {background:#dcdedc!important;border-color:#dcdedc!important;}
.stButton>button,.stDownloadButton>button {border:1px solid #3b3d3e!important;border-radius:999px!important;
 background:#1c1e1f!important;color:#ececeb!important;min-height:40px!important;font-weight:600!important;
 transition:background .15s ease,border-color .15s ease!important;}
.stButton>button:hover,.stDownloadButton>button:hover {background:#2a2c2d!important;border-color:#67696a!important;}
.stButton>button[kind="primary"] {background:#eeeef0!important;color:#141414!important;border-color:#eeeef0!important;}
.stButton>button[kind="primary"]:hover {background:#dcdcdc!important;border-color:#dcdcdc!important;}
.stButton>button:disabled {opacity:.35!important;}
/* Quiet choices: readable single-scan cards, no blue, no distracting decoration. */
[data-testid="stRadio"] {margin:.5rem 0 1.25rem!important;}
[data-testid="stRadio"] div[role="radiogroup"]:not([aria-orientation="horizontal"]) > label {
 padding:13px 15px!important;margin:0 0 9px!important;min-height:56px!important;
 background:#1a1c1d!important;border:1px solid #303234!important;border-radius:13px!important;
 align-items:center!important;transition:background .12s ease,border-color .12s ease!important;
}
[data-testid="stRadio"] div[role="radiogroup"]:not([aria-orientation="horizontal"]) > label:hover {background:#232526!important;border-color:#505254!important;}
[data-testid="stRadio"] div[role="radiogroup"]:not([aria-orientation="horizontal"]) > label:has(input:checked) {
 border-color:#9fa2a3!important;background:#222425!important;
}
[data-testid="stRadio"] label p {font-size:.94rem!important;line-height:1.43!important;color:#e4e4e2!important;}
.st-key-find_mode div[role="radiogroup"] {justify-content:center!important;gap:9px!important;}
.st-key-find_mode div[role="radiogroup"]>label {
 margin:0!important;padding:6px 15px!important;border:1px solid #343637!important;
 border-radius:999px!important;background:#1c1e1f!important;}
.st-key-find_mode div[role="radiogroup"]>label:has(input:checked) {background:#eeefef!important;border-color:#eeefef!important;}
.st-key-find_mode div[role="radiogroup"]>label:has(input:checked) p {color:#171717!important;font-weight:700!important;}
.st-key-find_mode div[role="radiogroup"]>label [data-testid="stMarkdownContainer"] p {font-size:.87rem!important;}
/* The demo uses the same audience-goal selector as the live app. */
.st-key-goal div[role="radiogroup"] {justify-content:center!important;gap:9px!important;}
.st-key-goal div[role="radiogroup"]>label {margin:0!important;padding:6px 15px!important;border:1px solid #343637!important;border-radius:999px!important;background:#1c1e1f!important;}
.st-key-goal div[role="radiogroup"]>label:has(input:checked) {background:#eeefef!important;border-color:#eeefef!important;}
.st-key-goal div[role="radiogroup"]>label:has(input:checked) p {color:#171717!important;font-weight:700!important;}
/* Editorial step headings and selected-topic summary. */
.flow-head {margin:.7rem 0 1.8rem;padding:0;}
.flow-head h2 {font-size:clamp(1.4rem,2.7vw,1.85rem)!important;line-height:1.34!important;
 font-weight:680!important;letter-spacing:-.045em;margin:0!important;}
.flow-head p {display:none!important;}
.flow-picked {background:#1a1c1d!important;border:1px solid #333536!important;
 border-radius:15px!important;padding:16px 18px!important;margin:1rem 0 1.4rem!important;}
.flow-picked strong {font-size:1.025rem;line-height:1.6;font-weight:640;color:#ececea;}
.flow-picked p {font-size:.92rem;line-height:1.65;margin:0;color:#b8babb;}
.selection-hint {color:#a1a3a4;font-size:.87rem;line-height:1.6;margin:0 0 1.5rem;}
/* Explanations stay accessible, collapsed and at the bottom. */
[data-testid="stExpander"] {background:transparent!important;border:0!important;
 border-top:1px solid #343637!important;border-radius:0!important;margin:2.2rem 0 .6rem!important;}
[data-testid="stExpander"] summary {padding:.9rem .05rem!important;color:#a8aaab!important;
 font-size:.88rem!important;font-weight:550!important;}
[data-testid="stExpander"] summary:hover {color:#eeeeec!important;}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {padding:.4rem .15rem 1.2rem!important;}
[data-testid="stCaptionContainer"],.stCaption {color:#8d9192!important;font-size:.79rem!important;}
[data-testid="stAlert"] {background:#1b1d1e!important;border:1px solid #37393a!important;border-radius:13px!important;}
[data-testid="stStatusWidget"] {background:#1b1d1e!important;border:1px solid #353738!important;
 border-radius:14px!important;}
[data-testid="stMetric"] {background:transparent!important;border:0!important;}
[data-testid="stSidebar"] {background:#161718!important;border-right:1px solid #2d2f30!important;}
[data-testid="stSidebar"] .stButton>button {border-radius:10px!important;text-align:left!important;}
[data-testid="stDataFrame"] {border-radius:12px;overflow:hidden;}
/* Draft: make the manuscript feel like a document, not an API log. */
.draft-head {padding:0 0 1.45rem;margin:.1rem 0 1.5rem;border-bottom:1px solid #343637;}
.draft-head .title {font-size:clamp(1.32rem,2.8vw,1.72rem);font-weight:685;
 color:#f4f3f1;line-height:1.45;letter-spacing:-.035em;}
.draft-head .edge {display:none;}
.draft-body p {line-height:1.85;}
[data-testid="stMarkdownContainer"] h3 {font-weight:665;font-size:1.05rem!important;
 margin-top:2.1rem!important;margin-bottom:.8rem!important;}
[data-testid="stMarkdownContainer"] h2 {font-weight:665;font-size:1.2rem!important;margin-top:2rem!important;}
[data-testid="stMarkdownContainer"] p {line-height:1.76;}
[data-testid="stTextArea"]:has(textarea[disabled]) textarea {background:#181a1b!important;
 border:1px solid #313334!important;border-radius:12px!important;padding:15px!important;}
/* Narrow devices: keep readability and touch-target size. */
@media(max-width:640px){
 .block-container {padding:2.7rem 1.05rem 5rem!important;}
 .hero {margin:6vh 0 1.35rem;}
 .hero h1 {font-size:1.67rem;}
 .flow-picked {padding:13px 14px!important;}
 [data-testid="stForm"] {padding:10px 12px!important;}
}
</style>
""",
    unsafe_allow_html=True,
)

DEFAULTS = {
    "channel_handle": "@틀린영어",
    "llm_model": "gpt-5.6-luna",
    "embedding_model": "text-embedding-3-small",
    "content_mode": "pulling",
    "data_root": default_data_root(),
    "business_profile": load_business_profile(default_data_root()),
    "pipeline": None,
    "pipeline_signature": None,
    "home_recommendations": None,
    "topic_comparison": None,
    "topic_selection": None,
    "flow_stage": "find",
    "hermes_topic_error": "",
    "selected_topic_option": None,
    "consultant_brief": None,
    "research": None,
    "candidate_package": None,
    "draft_a_bundle": None,
    "draft_revisions": [],
    "draft_b_bundle": None,
    "show_draft_b_controls": False,
    "topic_first_reviews": {},
    "final_bundle": None,
    "run_path": None,
    "user_input": "",
    "view_mode": "main",
    "show_note_panel": False,
    "show_memory_panel": False,
    "show_settings_panel": False,
    "strategy_latest_consultation_id": "",
    "strategy_question": "",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def esc(v):
    return html.escape(str(v or ""))


def short(value, limit=210):
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def reset_work(keep_recommendations=True):
    st.session_state.consultant_brief = None
    st.session_state.topic_comparison = None
    st.session_state.topic_selection = None
    st.session_state.hermes_topic_error = ""
    st.session_state.selected_topic_option = None
    st.session_state.flow_stage = "find"
    st.session_state.research = None
    st.session_state.candidate_package = None
    st.session_state.draft_a_bundle = None
    st.session_state.draft_revisions = []
    st.session_state.draft_b_bundle = None
    st.session_state.show_draft_b_controls = False
    st.session_state.topic_first_reviews = {}
    st.session_state.final_bundle = None
    st.session_state.run_path = None
    st.session_state.view_mode = "main"
    if not keep_recommendations:
        st.session_state.home_recommendations = None


def build_settings():
    return Settings(
        my_channel_handle=st.session_state.channel_handle,
        llm_model=st.session_state.llm_model,
        embedding_model=st.session_state.embedding_model,
        content_goal=st.session_state.content_mode,
        business_profile=st.session_state.business_profile,
    )


def ensure_pipeline():
    signature = (
        st.session_state.channel_handle,
        st.session_state.llm_model,
        st.session_state.embedding_model,
        st.session_state.content_mode,
        st.session_state.data_root,
        st.session_state.business_profile,
    )
    if st.session_state.pipeline is None or st.session_state.pipeline_signature != signature:
        st.session_state.pipeline = ResearchPipeline(
            build_settings(),
            project_root=PROJECT_ROOT,
            data_root=st.session_state.data_root,
        )
        st.session_state.pipeline_signature = signature
        reset_work(keep_recommendations=False)
    return st.session_state.pipeline


def run_with_status(label, fn):
    with st.status(label, expanded=False) as status:
        latest = st.empty()
        def progress(stage, detail):
            latest.caption(f"{stage} · {short(detail, 100)}")
        result = fn(progress)
        latest.empty()
        status.update(label=f"{label} 완료", state="complete", expanded=False)
        return result


def show_exception(context, exc):
    # HTTP exception text can embed &key=... and a Windows file traceback.
    # Never render raw exceptions in production UI.
    st.error(f'{context} · {safe_error(exc)}')


def show_list(items):
    for item in items or []:
        st.markdown(f"- {item}")


def fmt_views(v):
    try:
        return f"{int(v):,}회"
    except Exception:
        return "조회수 확인 불가"


def rec_to_brief(rec):
    return {
        "입력유형": "아이디어발전",
        "콘텐츠목적": rec.get("콘텐츠목적", "Pulling" if st.session_state.content_mode == "pulling" else "Key"),
        "주제": rec.get("추천주제", ""),
        "콘텐츠유형": rec.get("콘텐츠유형", "판단보류"),
        "콘텐츠유형근거": "시장 기회와 채널 공백을 비교한 추천",
        "타깃시청자": json.dumps(rec.get("예상시청자") or {}, ensure_ascii=False),
        "핵심문제": rec.get("시장발견") or rec.get("추천근거요약", ""),
        "사용자가가진가설": [x for x in [rec.get("뾰족한포인트가설"), rec.get("내식번역")] if x],
        "시청자최종변화": "Deep Research에서 구체화",
        "비즈니스역할": rec.get("현재사업연결", ""),
        "살려야할제약": [x for x in [rec.get("내식번역"), rec.get("신뢰형성가치")] if x],
        "검증해야할가설": [x for x in [rec.get("불확실성"), rec.get("신규성및중복위험")] if x],
        "리서치질문": [
            "이 시장 기회가 Transcript/댓글 정밀 조사에서도 유지되는가?",
            "이 콘텐츠를 볼 사람의 실제 영어 지식 수준과 수행 수준은 어느 정도인가?",
            "내 기존 콘텐츠에서 실제로 비어 있는 부분은 무엇인가?",
            "경쟁 영상을 복제하지 않고 내 방식으로 가져올 전이 가능한 원리는 무엇인가?",
        ],
        "주검색어": rec.get("추천검색어") or rec.get("추천주제", ""),
        "보조검색어": [],
        "해외검색어": rec.get("해외검색어") or [],
        "시장근거video_ids": rec.get("시장근거video_ids") or [],
        "기회유형": rec.get("기회유형", ""),
        "발견경로": rec.get("발견경로") or [],
        "초기판단": rec.get("추천근거요약", ""),
    }


def render_audience(audience):
    if not audience:
        return
    st.markdown("**예상 시청자 — 추정**")
    if audience.get("연령맥락"):
        st.write("연령/생활 맥락 · " + audience.get("연령맥락", ""))
    if audience.get("영어지식수준"):
        st.write("영어 지식 · " + audience.get("영어지식수준", ""))
    if audience.get("수행수준"):
        st.write("실제 수행 · " + audience.get("수행수준", ""))
    if audience.get("추정근거"):
        show_list(audience.get("추정근거"))
    st.caption("연령/수준은 공개 시장 자료와 현재 채널 데이터에 기반한 추정이며 사실로 단정하지 않습니다.")


def render_market_evidence(rec):
    details = rec.get("시장근거상세") or []
    st.markdown(f"**시장 신호 · {rec.get('시장신호판정','근거 부족')}**")
    if not details:
        st.caption("표시할 수 있는 원본 영상 근거가 없습니다. 확정 근거로 사용하지 않습니다.")
        return
    for e in details:
        ratio = e.get("채널배수")
        ratio_text = f" · 채널 대비 {ratio:.1f}×" if isinstance(ratio, (int, float)) else ""
        sub_ratio = e.get("조회수_구독자배수")
        sub_text = f" · 구독자 대비 {sub_ratio:.1f}×" if isinstance(sub_ratio, (int, float)) else ""
        velocity = e.get("조회속도_일평균")
        velocity_text = f" · 일평균 약 {velocity:,.0f}회" if isinstance(velocity, (int, float)) else ""
        n = e.get("baseline_N")
        sample = f" · N={n}" if isinstance(n, int) else ""
        warning = f" · {e.get('baseline_경고')}" if e.get("baseline_경고") else ""
        breakout = " · RECENT BREAKOUT" if e.get("최근브레이크아웃") else ""
        title = esc(e.get("제목"))
        url = str(e.get("영상링크") or "")
        title_html = f'<a href="{html.escape(url)}" target="_blank" style="color:#e5e5e5;text-decoration:none">{title}</a>' if url else title
        queries = e.get("발견검색어") or []
        qtext = " · 검색축: " + ", ".join(map(str, queries)) if queries else ""
        origin = ""
        origin_values = e.get("발견출처_목록") or ([e.get("발견출처")] if e.get("발견출처") else [])
        if not origin_values and e.get("시장범위"):
            origin_values = [e.get("시장범위")]
        if origin_values:
            origin = " · 출처: " + ", ".join(map(str, origin_values))
        st.markdown(
            f'<div class="evidence-item"><div class="evidence-title">{title_html}</div>'
            f'<div class="evidence-meta">{esc(e.get("채널"))} · {fmt_views(e.get("조회수"))} · {esc(e.get("업로드날짜"))}'
            f'{velocity_text}{ratio_text}{sub_text}{sample}{warning}{breakout}{esc(origin)}<br>{esc(e.get("선정이유"))}{esc(qtext)}</div></div>',
            unsafe_allow_html=True,
        )


def render_strategy(strategy):
    for label, key in [("핵심 형식", "핵심형식"), ("첫 30초", "첫30초"), ("본문", "본문운영"), ("마지막 보상", "최종보상"), ("확장", "후속확장")]:
        if strategy and strategy.get(key):
            st.markdown(f"**{label}** · {strategy.get(key)}")


def open_research_for_topic(rec: dict, source: str, slot: int):
    """Exploration, not production approval. Preserve data when any step fails."""
    brief = rec_to_brief(rec)
    # Hermes links verified as having appeared in its actual web-tool results
    # may contain video IDs. Fetch those IDs via videos.list instead of burning
    # a new search.list request. Do not treat webpage links as demand proof.
    if source == 'B':
        from urllib.parse import urlsplit, parse_qs
        comp = st.session_state.topic_comparison or {}
        audits = (comp.get('evidence_audit') or {}).get('b') or []
        verified = audits[slot-1].get('tool_observed_urls') or [] if len(audits)>=slot else []
        extra_ids = []
        for url in verified[:18]:
            try:
                part = urlsplit(url)
                host = (part.hostname or '').lower()
                if host in ('youtube.com', 'www.youtube.com', 'm.youtube.com') and part.path == '/watch':
                    vid = (parse_qs(part.query).get('v') or [''])[0]
                elif host in ('youtu.be', 'www.youtu.be'):
                    vid = part.path.strip('/').split('/')[0]
                else:
                    continue
                if re.fullmatch(r'[a-zA-Z0-9_-]{11}', vid) and vid not in extra_ids:
                    extra_ids.append(vid)
            except (TypeError, ValueError):
                continue
        brief['시장근거video_ids'] = list(dict.fromkeys(
            (brief.get('시장근거video_ids') or []) + extra_ids))[:14]
    frozen_market = evidence_for_comparison(st.session_state.topic_comparison).get('market_videos') or {}
    st.session_state.topic_selection = {'source': source, 'rank': slot,
                                        'topic': rec.get('추천주제', ''), 'rec': rec}
    st.session_state.consultant_brief = brief
    st.session_state.user_input = rec.get('추천주제', '')
    st.session_state.pop('research_direction', None)
    result = run_with_status(
        '선택한 주제의 관련 영상·자막·설명 아이디어 조사',
        lambda cb, q=rec.get('추천검색어') or rec.get('추천주제'), b=brief:
            pipeline.research_topic(q, progress=cb, idea_brief=b, prefetched_market=frozen_market),
    )
    # Only after successfully obtaining a usable research object: record an
    # exploration event; this does NOT count as a decision to produce a video.
    st.session_state.research = result
    st.session_state.production_committed_topic = None
    strategy_store.record_topic_exploration(rec, source, slot, bool(result.get('research_ready')))
    st.session_state.candidate_package = None
    st.session_state.draft_a_bundle = None
    st.session_state.draft_revisions = []
    st.session_state.draft_b_bundle = None
    st.session_state.final_bundle = None
    st.session_state.flow_stage = 'research'
    st.rerun()


def make_draft_from_candidate(index):
    def work(cb):
        package = pipeline.build_candidate_package(st.session_state.research, index, progress=cb)
        draft_bundle = pipeline.write_draft_a(package, progress=cb)
        return package, draft_bundle

    package, draft_bundle = run_with_status("리서치 → 설계 → 초안 만들기", work)
    st.session_state.candidate_package = package
    st.session_state.draft_a_bundle = draft_bundle
    st.session_state.draft_revisions = []
    st.session_state.draft_b_bundle = None
    st.session_state.show_draft_b_controls = False
    st.session_state.final_bundle = None

    runs_root = Path(os.getenv("YRA_RUNS_DIR", str(pipeline.data_root / "runs")))
    if not runs_root.is_absolute():
        runs_root = pipeline.data_root / runs_root
    store = RunStore(runs_root)
    st.session_state.run_path = store.save_a_product_run(
        st.session_state.research,
        package,
        draft_bundle["script"],
    )
    try:
        candidate = package.get("selected_candidate") or {}
        pipeline.manual_data.append_decision(
            candidate.get("주제", ""),
            "drafted",
            reason=candidate.get("왜만들가치가있는가", ""),
            content_role=candidate.get("콘텐츠목적", ""),
        )
    except Exception:
        pass
    st.session_state.view_mode = "draft"
    st.session_state.flow_stage = "draft"


def render_research_coverage(research):
    cov = research.get("transcript_coverage") or {}
    total = int(cov.get("total", 0) or 0)
    success = int(cov.get("success", 0) or 0)
    cached = int(cov.get("cached_success", 0) or 0)
    ratio = float(cov.get("ratio", 0.0) or 0.0)
    ready = bool(cov.get("ready", False))
    state = "충분" if ready else "부족"
    st.markdown(f"**Research Coverage · {state}**  ")
    st.write(f"시장 후보 {total}개 · Transcript {success}개 ({ratio*100:.0f}%) · 캐시에서 {cached}개")
    if cov.get("blocked"):
        st.warning("이번 실행에서 YouTube Transcript IP 차단이 감지되어 추가 요청을 중단했습니다. 캐시가 있는 영상은 계속 사용합니다.")
    if not ready:
        st.error("시장 Transcript가 핵심 기준에 미달해 Knowledge Gap / Explanation Atom / Draft 생성을 중단했습니다. 메타데이터만으로 그럴듯한 대본을 만들지 않습니다.")
        for e in cov.get("errors") or []:
            st.caption(e)


def render_content_patterns(research):
    patterns = research.get("content_patterns") or []
    if not patterns:
        return
    with st.expander("이번 Research에서 발견한 콘텐츠 패턴"):
        st.caption("고정 분류표가 아니라 확보한 시장 Transcript의 Content DNA에서 만든 임시 클러스터입니다. 데이터가 쌓이면 Pattern Memory에 누적됩니다.")
        for ptn in patterns:
            st.markdown(f"**{ptn.get('클러스터명','패턴')}** · {ptn.get('설명','')}")
            st.caption(f"구조: {ptn.get('핵심구조','')} · 보상: {ptn.get('핵심보상','')} · 참여: {ptn.get('참여방식','')} · 확신: {ptn.get('확신','')}")


def current_script():
    if st.session_state.draft_revisions:
        return st.session_state.draft_revisions[-1]["script"]
    if st.session_state.draft_a_bundle:
        return st.session_state.draft_a_bundle["script"]
    return None


def render_script(script):
    if not script:
        return
    st.markdown("### 오프닝")
    st.write(script.get("오프닝", ""))
    for i, part in enumerate(script.get("파트별대본", []), start=1):
        part_title = re.sub(r"^\d+[.．)）]\s*", "", str(part.get("파트", "") or "").strip())
        st.markdown(f"### {i}. {part_title}")
        st.write(part.get("대본", ""))
    if script.get("최종지도"):
        st.markdown("### 최종 지도")
        st.write(script.get("최종지도"))
    if script.get("마무리"):
        st.markdown("### 마무리")
        st.write(script.get("마무리"))

def render_ab_comparison(comp):
    if not comp:
        return
    st.markdown("### A/B 비교")
    st.write(comp.get("한줄판단", ""))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**B가 개선한 점**")
        show_list(comp.get("B가개선한점"))
    with c2:
        st.markdown("**A가 더 나은 점**")
        show_list(comp.get("A가더나은점"))
    if comp.get("실제로비교해서볼구간"):
        st.markdown("**직접 비교해서 볼 구간**")
        show_list(comp.get("실제로비교해서볼구간"))
    st.markdown(f"**추천 · {comp.get('추천','')}**  \n{comp.get('추천이유','')}")


def _script_part_text(script: dict, slot: int) -> str:
    if slot == -1:
        return str(script.get("오프닝") or "")
    if slot == -2:
        return str(script.get("마무리") or "")
    parts = script.get("파트별대본") or []
    if slot < len(parts):
        part = parts[slot]
        title = str(part.get("파트") or "")
        return title + "\n\n" + str(part.get("대본") or "")
    return "(해당 위치에 파트 없음 — 구성이 달라졌을 수 있습니다.)"


def _short_change_text(value: str, limit: int = 235) -> str:
    val = str(value or "").strip()
    return val if len(val) <= limit else val[:limit - 1].rstrip() + "…"


def render_critic_agent_section():
    st.markdown("## Draft B")
    if st.session_state.draft_b_bundle is None:
        critic_choice = st.radio("검토 엔진", ["기존 OpenAI Critic", "Hermes Agent (Docker)"],
            index=1 if os.getenv("YRA_CRITIC_BACKEND", "openai").lower() == "hermes" else 0,
            horizontal=True, key="draft_b_engine")
        mode_choice = st.radio("대본 개선 방식", ["새롭게 재설계", "기존 대본 다듬기"], horizontal=True)
        critic_backend = "hermes" if critic_choice.startswith("Hermes") else "openai"
        revision_mode = "rebuild" if mode_choice.startswith("새롭게") else "polish"
        use_180_benchmark = st.checkbox("180도 스피킹 설명 방식 참고", value=True,
            key="draft_b_use_180_benchmark")
        benchmark_notes = st.text_input("직접 본 영상의 참고 메모 (선택)",
            key="draft_b_benchmark_notes", max_chars=1200) if use_180_benchmark else ""
        benchmark_reference = make_benchmark_reference(benchmark_notes) if use_180_benchmark else None
        if st.button("Draft B 생성", type="primary", use_container_width=True):
            try:
                base = current_script()
                bundle = run_with_status("Draft B 생성", lambda cb: pipeline.build_draft_b(
                    base, st.session_state.candidate_package, progress=cb,
                    critic_backend=critic_backend, revision_mode=revision_mode,
                    benchmark_reference=benchmark_reference))
                st.session_state.draft_b_bundle = bundle
                st.session_state.final_bundle = None
                if st.session_state.run_path:
                    runs_root = Path(os.getenv("YRA_RUNS_DIR", str(pipeline.data_root / "runs")))
                    if not runs_root.is_absolute(): runs_root = pipeline.data_root / runs_root
                    RunStore(runs_root).save_agent_outputs(st.session_state.run_path, bundle)
                st.rerun()
            except Exception as exc:
                show_exception("Draft B 생성 실패", exc)
        return

    bundle = st.session_state.draft_b_bundle
    script_a = current_script() or {}
    script_b = bundle.get("draft_b") or {}
    comparison = bundle.get("comparison") or {}
    verdict = bundle.get("topic_decision") or {}
    if bundle.get("critic_warning"):
        st.warning(str(bundle.get("critic_warning")))
    if verdict.get("valid") and verdict.get("action") == "RESEARCH_NEW":
        proposed = str(verdict.get("topic") or "").strip()
        st.warning("새 주제 조사가 필요하다는 판정입니다. 현재 Draft B를 그대로 검증된 것으로 취급하지 마세요.")
        if proposed and st.button("제안 주제로 다시 조사", key="market_pivot_research"):
            try:
                rerun_research = run_with_status("대안 주제 조사", lambda cb: pipeline.research_topic(proposed, progress=cb))
                reset_work(keep_recommendations=True)
                st.session_state.user_input = proposed
                st.session_state.research = rerun_research
                st.rerun()
            except Exception as exc: show_exception("새 주제 조사 실패", exc)
    if comparison.get("한줄판단"):
        st.write(str(comparison["한줄판단"]))
    if comparison.get("추천"):
        st.caption("AI 비교 판단 · " + str(comparison["추천"]))

    st.markdown("### A/B 비교")
    parts_a, parts_b = script_a.get("파트별대본") or [], script_b.get("파트별대본") or []
    comparison_part_names = []
    for i in range(max(len(parts_a),len(parts_b))):
        reference_part = parts_b[i] if i < len(parts_b) else parts_a[i]
        name = re.sub(r"^\d+[.．)）]\s*", "", str(reference_part.get("파트") or ""))
        comparison_part_names.append(f"{i+1}. {_short_change_text(name, 27)}")
    labels = ["오프닝"] + comparison_part_names + ["마무리"]
    selected = st.selectbox("비교할 구간", labels, key="ab_section_picker")
    idx = labels.index(selected)
    slot = -1 if idx == 0 else -2 if idx == len(labels)-1 else idx-1
    left, right = st.columns(2)
    with left: st.text_area("Draft A", _script_part_text(script_a, slot), height=240, disabled=True)
    with right: st.text_area("Draft B", _script_part_text(script_b, slot), height=240, disabled=True)

    st.markdown("### 최종 원고 선택")
    final_choice = st.radio("촬영할 원고", ["Draft B", "Draft A"], horizontal=True,
        key="final_script_base_choice")
    final_script = script_b if final_choice == "Draft B" else script_a
    ending = final_script.get("마무리") or ""
    if ending:
        st.markdown("**마무리**")
        st.write(ending)
    for warn in ending_warnings(final_script): st.warning(warn)
    if st.button("이 원고로 최종 확정", type="primary", use_container_width=True,
        key="final_script_direct_confirm"):
        copied = json.loads(json.dumps(final_script, ensure_ascii=False, default=str))
        st.session_state.final_bundle = {"feedback": f"{final_choice} 원본 그대로 확정", "result": copied,
            "cached": True, "source": final_choice}
        if st.session_state.run_path:
            runs_root = Path(os.getenv("YRA_RUNS_DIR", str(pipeline.data_root / "runs")))
            if not runs_root.is_absolute(): runs_root = pipeline.data_root / runs_root
            RunStore(runs_root).save_final_script(st.session_state.run_path,
                st.session_state.final_bundle["feedback"], copied)
        st.rerun()

    with st.form("final_feedback_form", clear_on_submit=False):
        final_feedback = st.text_area("고칠 내용 (선택)", height=82,
            placeholder="예: A의 도입을 유지하고 B의 예시를 넣어줘.")
        submit = st.form_submit_button("수정 반영해 최종 원고 만들기", use_container_width=True)
    if submit:
        if not final_feedback.strip():
            st.warning("수정 내용을 적어 주세요. 그대로 쓰려면 위 확정 버튼을 누르세요.")
        else:
            try:
                result = run_with_status("최종 원고 수정", lambda cb:
                    pipeline.finalize_from_draft_b(final_script, final_feedback.strip(), progress=cb))
                st.session_state.final_bundle = {"feedback":final_feedback.strip(),"source":final_choice, **result}
                if st.session_state.run_path:
                    runs_root = Path(os.getenv("YRA_RUNS_DIR", str(pipeline.data_root / "runs")))
                    if not runs_root.is_absolute(): runs_root = pipeline.data_root / runs_root
                    RunStore(runs_root).save_final_script(st.session_state.run_path,
                        final_feedback.strip(), result["result"])
                st.rerun()
            except Exception as exc: show_exception("최종 원고 수정 실패", exc)

    if st.session_state.final_bundle:
        st.success("최종 원고 확정")
        final = st.session_state.final_bundle.get("result") or {}
        st.download_button("최종 대본 다운로드 (.md)", script_to_markdown(final, "Final Script"),
            file_name="final_script.md", mime="text/markdown", use_container_width=True)

    with st.expander("판단 근거 · 데이터 보기"):
        st.markdown("**이번 Draft B에서 바뀐 점**")
        for item in (script_b.get("변경요약") or comparison.get("B가개선한점") or [])[:8]:
            st.write("- " + _short_change_text(item))
        if verdict.get("valid"):
            st.markdown("**주제 판정**")
            st.write(str(verdict.get("action")) + " · " + str(verdict.get("reason") or ""))
        audit = bundle.get("market_audit") or {}
        st.caption(f"시장 후보 {audit.get('시장후보수',0)}개 · 자막 {audit.get('실제자막확보수',0)}개")
        if audit.get("해석한계"): st.caption(str(audit['해석한계']))
        entries = audit.get("경쟁영상") or []
        if entries:
            st.dataframe([{"제목":e.get("제목"),"채널":e.get("채널"),
                "조회수":e.get("조회수"),"자막":"O" if e.get("원문확보") else "X",
                "출처":e.get("영상링크")} for e in entries], use_container_width=True, hide_index=True)
        st.markdown("**원문 비교**")
        st.markdown("**Draft A**")
        render_script(script_a)
        st.markdown("**Draft B**")
        render_script(script_b)
        if st.session_state.final_bundle:
            st.markdown("**확정된 최종 대본**")
            render_script(st.session_state.final_bundle.get("result") or {})
        st.markdown("**비평 보고서**")
        st.write(bundle.get("critic_report") or "")
        if comparison: render_ab_comparison(comparison)
        st.markdown("**도구 사용 기록 · 검증 출처**")
        st.caption(f"엔진: {bundle.get('critic_model','')} · 웹 호출 {bundle.get('critic_web_attempted',0)}회 / 응답 {bundle.get('critic_web_completed',0)}회")
        for ev in bundle.get("critic_tool_trace") or []:
            st.write(f"{ev.get('tool')} · {ev.get('status')} · {ev.get('request') or ''}")
        for src in bundle.get("critic_sources") or []:
            u = str(src.get("url") or "")
            if u.startswith(("https://", "http://")): st.write(u)
    if st.button("Draft B 다시 만들기", key="redo_draft_b"):
        st.session_state.draft_b_bundle = None
        st.session_state.final_bundle = None
        st.rerun()

def render_draft_workspace():
    package = st.session_state.candidate_package or {}
    candidate = package.get("selected_candidate") or {}
    design = package.get("design_pack") or {}
    core = design.get("핵심엣지추천") or {}
    st.markdown(f'<div class="draft-head"><div class="title">{esc(candidate.get("주제") or "대본")}</div></div>',
        unsafe_allow_html=True)
    if st.session_state.draft_b_bundle is not None:
        render_critic_agent_section()
        back, new = st.columns(2)
        if back.button("← 심층 조사", key="draft_back_b", use_container_width=True):
            navigate_to("research")
        if new.button("새 콘텐츠", key="draft_new_b", use_container_width=True):
            st.session_state.user_input = ""
            reset_work(keep_recommendations=False)
            st.rerun()
        return

    script = current_script() or {}
    st.markdown("## Draft A")
    if st.button("Draft B 만들기" if not st.session_state.show_draft_b_controls else "Draft B 옵션 닫기",
        key="draft_b_setup_toggle", type="primary" if not st.session_state.show_draft_b_controls else "secondary",
        use_container_width=True):
        st.session_state.show_draft_b_controls = not st.session_state.show_draft_b_controls
        st.rerun()
    if st.session_state.show_draft_b_controls:
        render_critic_agent_section()
    render_script(script)
    for note in ending_warnings(script): st.warning("마무리 점검 · " + note)
    st.download_button("Draft A 다운로드 (.md)", script_to_markdown(script, "Draft A"),
        file_name="draft_a.md", mime="text/markdown", use_container_width=True)

    with st.form("draft_feedback_form", clear_on_submit=True):
        feedback = st.text_area("Draft A 수정 (선택)", placeholder="바꾸고 싶은 부분만 적어주세요.", height=88)
        apply_feedback = st.form_submit_button("Draft A 수정하기", use_container_width=True)
    if apply_feedback:
        if not feedback.strip():
            st.warning("수정할 내용을 적어주세요.")
        else:
            try:
                base = current_script()
                revised = run_with_status("Draft A 수정", lambda cb: pipeline.revise_draft_a(
                    base, feedback.strip(), progress=cb))
                result = revised["result"]
                st.session_state.draft_revisions.append({"feedback":feedback.strip(),"script":result})
                st.session_state.draft_b_bundle = None
                st.session_state.final_bundle = None
                if st.session_state.run_path:
                    runs_root = Path(os.getenv("YRA_RUNS_DIR", str(pipeline.data_root / "runs")))
                    if not runs_root.is_absolute(): runs_root = pipeline.data_root / runs_root
                    RunStore(runs_root).append_revision(st.session_state.run_path, feedback.strip(), result)
                st.rerun()
            except Exception as exc: show_exception("수정 실패", exc)
    with st.expander("판단 근거 · 데이터 보기"):
        if st.session_state.show_draft_b_controls:
            st.caption("180도 스피킹은 채널 소개·제목 수준의 참고 자료이며 실제 영상 자막 분석은 아닙니다.")
            st.caption("Draft B는 AI API 호출 비용이 발생할 수 있습니다.")
            if os.getenv("YRA_CRITIC_BACKEND", "openai").lower() == "hermes" or st.session_state.get("draft_b_engine", "").startswith("Hermes"):
                st.markdown("**Hermes 연결 점검**")
                if st.button("연결 검사", key="hermes_audit_ready"):
                    try:
                        from hermes_integration.adapter import check_ready
                        st.success("연결 확인: " + str(check_ready()))
                    except Exception as exc: st.error(safe_error(exc))
                if st.button("웹 검색 도구 검사 (API 사용)", key="hermes_web_test"):
                    try:
                        from hermes_integration.adapter import run_verified_web_research
                        check = run_with_status("Hermes 웹 도구 검사", lambda cb: run_verified_web_research(
                            "Cambridge Dictionary present perfect usage 영어 교육"))
                        st.write(f"웹 호출 {check.get('web_attempted',0)}회, 응답 {check.get('web_completed',0)}회")
                    except Exception as exc: st.error(safe_error(exc))
        if script.get("핵심세일즈포인트"):
            st.markdown("**대본의 핵심 약속**")
            st.write(script["핵심세일즈포인트"])
        st.markdown("**제목 후보**")
        show_list(script.get("제목후보") or [])
        st.markdown("**썸네일 후보**")
        show_list(script.get("썸네일문구후보") or [])
        if core:
            st.markdown("**Core Edge**")
            st.write(core.get("엣지") or "")
            if core.get("선택이유"): st.write(core["선택이유"])
        structure = package.get("structure_result") or {}
        for i, part in enumerate(structure.get("구조블루프린트",[]),1):
            st.write(f"{i}. {part.get('파트','')} · {part.get('목적','')}")
        if st.session_state.draft_revisions:
            st.markdown("**수정 기록**")
            for i, rev in enumerate(st.session_state.draft_revisions,1):
                st.write(f"{i}. {rev.get('feedback')}")
        if script.get("수정요약"):
            st.markdown("**최근 변경**")
            show_list(script["수정요약"])
        st.download_button("Draft A JSON 저장", json.dumps(script,ensure_ascii=False,indent=2),
            file_name="draft_a.json", mime="application/json")
    back, new = st.columns(2)
    if back.button("← 심층 조사", key="draft_back", use_container_width=True):
        navigate_to("research")
    if new.button("새 콘텐츠", key="draft_new", use_container_width=True):
        st.session_state.user_input = ""
        reset_work(keep_recommendations=False)
        st.rerun()

def _data_editor_table(name: str, title: str, help_text: str):
    store = pipeline.manual_data
    st.markdown(f"### {title}")
    st.caption(help_text)
    df = store.read(name)
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"manual_editor_{name}",
    )
    c1, c2 = st.columns([1, 1])
    if c1.button("저장", key=f"save_manual_{name}", type="primary", use_container_width=True):
        path = store.write(name, edited)
        st.success(f"저장했습니다 · {path}")
        # 새 Studio/Reference 데이터는 다음 추천부터 즉시 반영되어야 한다.
        st.session_state.pipeline = None
        st.session_state.pipeline_signature = None
        st.session_state.home_recommendations = None
        st.session_state.research = None
        st.session_state.consultant_brief = None
    csv_bytes = edited.to_csv(index=False).encode("utf-8-sig")
    c2.download_button("CSV 백업", csv_bytes, file_name=f"{name}.csv", mime="text/csv", key=f"download_manual_{name}", use_container_width=True)
    st.caption(f"직접 편집 경로 · {store.path(name)}")


def render_data_workspace():
    c1, c2 = st.columns([1, 1])
    if c1.button("← 메인으로", use_container_width=True):
        st.session_state.view_mode = "main"
        st.rerun()
    if c2.button("데이터 폴더 위치 보기", use_container_width=True):
        st.info(str(pipeline.manual_data.root))

    st.markdown(
        '<div class="draft-head"><div class="eyebrow">STUDIO / REFERENCE DATA</div>'
        '<div class="title">내가 직접 업데이트하는 시장 지도</div>'
        '<div class="edge">Studio의 Audience Neighborhood와 실제 영상 성과를 여기에 쌓습니다. 비어 있는 값은 추정하지 않습니다.</div></div>',
        unsafe_allow_html=True,
    )
    st.info("가장 먼저 `참고 채널`에 Studio → 분석 → 시청자층의 **내 시청자가 보는 다른 채널 5~10개**를 넣으세요. 다음 추천부터 그 채널들을 직접 스캔합니다.")

    tabs = st.tabs(["참고 채널", "내 영상 성과", "추천 옆자리", "Audience", "전략 가설", "선택 기록"])
    with tabs[0]:
        st.markdown("**role 값** · `audience_neighbor` / `korean_reference` / `global_reference`")
        st.caption("channel_ref에는 @handle, YouTube 채널 URL, UC로 시작하는 channel ID 중 하나를 넣으면 됩니다. 해외 영어교육 채널은 global_reference로 추가하세요.")
        _data_editor_table(
            "reference_channels",
            "Reference Channels",
            "Audience Neighborhood는 내가 어느 줄에 설지 정하는 seed입니다. Global Reference는 해외에서 검증된 지식/설명법/포맷을 한국식으로 재해석할 후보를 찾습니다.",
        )

    with tabs[1]:
        _data_editor_table(
            "my_video_performance",
            "내 영상 성과 · 7일 / 28일 / 현재",
            "Studio에서 보이는 값을 틈날 때 추가하세요. 같은 video_id를 7일, 28일, current로 여러 행 기록해도 됩니다. impressions/CTR/순시청자/최근10개 순위/리드 등을 추천 근거와 사후 진단에 사용합니다.",
        )
        diags = pipeline.manual_data.performance_diagnostics()
        if diags:
            with st.expander("현재 입력값 기준 진단 · 가설"):                 
                st.caption("CTR/지속률/최근10개 순위만으로 원인을 확정하지 않습니다. 아래는 다음에 무엇을 확인할지 정하는 보조 가설입니다.")
                for d in diags[-8:]:
                    st.markdown(f"**{d.get('title','영상')}**")
                    for sig in d.get("signals") or []:
                        st.write("- " + sig)
                    for u in d.get("unknown") or []:
                        st.caption("모름 · " + u)

    with tabs[2]:
        _data_editor_table(
            "suggested_neighbors",
            "내 영상이 실제로 붙은 추천 옆자리",
            "추천 동영상 트래픽에서 확인한 source video/channel을 기록합니다. source_channel_ref를 넣으면 이 채널은 다음 Pulling 탐색에서 실제 Audience Neighborhood 신호로 자동 재사용됩니다.",
        )

    with tabs[3]:
        _data_editor_table(
            "audience_snapshots",
            "Audience Snapshot",
            "연령/성별/지역/기기 등 채널 전체 수치를 날짜별로 기록합니다. 연령을 영어 수준과 동일시하지 않고, 콘텐츠별 지식/수행 수준은 별도로 추정합니다.",
        )

    with tabs[4]:
        _data_editor_table(
            "hypotheses",
            "전략 가설 Memory",
            "'어순 재탕은 자기잠식할 수 있다' 같은 전략 판단을 하드코딩하지 않고 검증 중인 가설로 쌓습니다. evidence_for / evidence_against를 나중에 갱신하세요.",
        )

    with tabs[5]:
        _data_editor_table(
            "content_decisions",
            "콘텐츠 선택 기록",
            "추천에서 '더 파보기'를 누르거나 Draft를 만들면 일부 기록이 자동으로 쌓입니다. 나중에 왜 선택/보류했는지 reason과 notes를 보완할 수 있습니다.",
        )

    st.markdown("---")
    st.markdown("### 파일로 직접 관리하고 싶을 때")
    st.caption("앱에서 입력해도 되고 CSV를 직접 열어 수정해도 됩니다. 새 앱 버전을 받아도 이 manual 폴더는 유지하세요.")
    st.code(str(pipeline.manual_data.root), language="text")
    readme = pipeline.manual_data.root / "README_DATA_INPUT.md"
    if readme.exists():
        with st.expander("입력 필드 설명 보기"):
            st.markdown(readme.read_text(encoding="utf-8"))



from workflow_ui import FLOW_STAGES, available_stages, topic_choices


def navigate_to(stage: str):
    permitted = available_stages(st.session_state)
    if stage not in permitted:
        return
    st.session_state.flow_stage = stage
    st.session_state.view_mode = "draft" if stage == "draft" else "main"
    st.rerun()


def render_stage_find():
    st.markdown('<div class="hero"><h1>내 채널에 맞는 다음 주제 찾기</h1></div>', unsafe_allow_html=True)
    mode = st.radio(
        "영상 목적", ["pulling", "key"],
        format_func=lambda x: "신규 유입" if x == "pulling" else "신뢰 형성",
        horizontal=True, label_visibility="collapsed", key="find_mode",
        index=0 if st.session_state.content_mode == "pulling" else 1,
    )
    if mode != st.session_state.content_mode:
        st.session_state.content_mode = mode
        st.session_state.pipeline = None
        st.session_state.pipeline_signature = None
        reset_work(keep_recommendations=False)
        st.rerun()

    with st.form("find_chat_form", clear_on_submit=False):
        query = st.text_area("영상 주제", value=st.session_state.user_input or "",
            height=104, label_visibility="collapsed", placeholder="주제를 입력하거나 비워두면 AI가 추천합니다.")
        sent = st.form_submit_button("주제 찾기", type="primary", use_container_width=True)

    if sent:
        query = query.strip()
        if query:
            st.session_state.user_input = query
            st.session_state.pop("research_direction", None)
            try:
                brief = run_with_status("주제 조사", lambda cb: pipeline.consult(query, progress=cb))
                if brief.get("kind") == "recommendations":
                    st.session_state.home_recommendations = brief.get("recommendations") or []
                    st.session_state.topic_comparison = None
                    st.session_state.hermes_topic_error = "직접 입력한 주제에는 Hermes 비교 자료가 없습니다."
                    navigate_to("compare")
                else:
                    st.session_state.consultant_brief = brief.get("brief")
                    st.session_state.research = brief["research"]
                    st.session_state.topic_selection = {"topic": query, "source": "직접 입력"}
                    navigate_to("research")
            except Exception as exc:
                show_exception("주제 조사 실패", exc)
        else:
            try:
                recs = run_with_status("내 채널·시장 분석", lambda cb: pipeline.recommend_home(progress=cb))
                st.session_state.home_recommendations = recs
                st.session_state.topic_comparison = None
                st.session_state.hermes_topic_error = ""
                st.session_state.selected_topic_option = None
                st.session_state.topic_selection = None
                st.session_state.research = None
                st.session_state.candidate_package = None
                st.session_state.draft_a_bundle = None
                st.session_state.draft_b_bundle = None
                st.session_state.final_bundle = None
                st.session_state.draft_revisions = []
            except Exception as exc:
                show_exception("시장 조사 실패", exc)
                return
            if recs:
                try:
                    from topic_experiment import execute_topic_experiment
                    st.session_state.topic_comparison = run_with_status(
                        "Hermes 독립 웹 조사", lambda cb: execute_topic_experiment(pipeline, recs, st.session_state.content_mode))
                except Exception as exc:
                    st.session_state.hermes_topic_error = safe_error(exc)
                if os.getenv("SERPAPI_API_KEY", "").strip():
                    try:
                        comp = st.session_state.topic_comparison or {}
                        trend_result = run_with_status("YouTube 검색 관심도 조사",
                            lambda cb: capture_topic_trends(recs, comp.get("b_topics") or [], strategy_store.root))
                        if st.session_state.topic_comparison is None:
                            st.session_state.topic_comparison = {}
                        st.session_state.topic_comparison["interest_signal"] = trend_result
                        if comp.get("run_folder"):
                            from strategy_hub import _atomic_json
                            _atomic_json(Path(comp["run_folder"]) / "comparison.json", st.session_state.topic_comparison)
                        if trend_result.get("status") == "ERROR":
                            st.session_state.hermes_topic_error += " · 관심도: " + trend_result.get("error", "")
                    except Exception as exc:
                        st.warning("추가 검색 관심도 수집은 실패했으나 주제 추천은 보존됩니다.")
                navigate_to("compare")
            else:
                st.warning("추천된 주제가 없습니다.")

    if st.session_state.home_recommendations:
        if st.button("이전 조사 이어가기", key="resume_recommendations", use_container_width=True):
            navigate_to("compare")

def render_stage_compare():
    st.markdown('<div class="flow-head"><h2>다음 영상, 무엇을 만들까요?</h2></div>', unsafe_allow_html=True)
    recs = order_recommendations(st.session_state.home_recommendations or [], require_rank=False)
    if not recs:
        st.info("먼저 주제를 찾아주세요.")
        if st.button("주제 찾기로", key="cmp_empty_back"): navigate_to("find")
        return
    comp = st.session_state.topic_comparison or {}
    b_topics = comp.get("b_topics") if comp.get("status") == "TOPICS_READY" else []
    choices = topic_choices(recs, b_topics)
    if not choices:
        return

    options = [x[0] for x in choices]
    if st.session_state.selected_topic_option not in options:
        st.session_state.selected_topic_option = None
    label_map = {x[0]: f"{x[1]} · {short(x[3].get('추천주제'), 100)}" for x in choices}
    selection = st.radio("A/B 추천 · 제작할 주제 하나 선택", options, format_func=lambda v: label_map[v],
        key="selected_topic_option", index=None)
    selected = next((x for x in choices if x[0] == selection), None)
    if selected:
        _, _, source, rec, rank = selected
        reason_preview = rank_reason(rec) or rec.get("추천근거요약") or ""
        if reason_preview:
            st.markdown(f'<div class="selection-hint">{esc(short(reason_preview, 155))}</div>', unsafe_allow_html=True)
        if st.button("이 주제 심층 조사", type="primary", use_container_width=True):
            try:
                open_research_for_topic(rec, source, rank)
            except Exception as exc:
                show_exception("심층 조사 실패", exc)

    if not b_topics:
        if st.button("Hermes 조사 재시도", key="retry_hermes_compare", use_container_width=True):
            try:
                from topic_experiment import execute_topic_experiment
                st.session_state.topic_comparison = run_with_status("Hermes 웹 조사", lambda cb:
                    execute_topic_experiment(pipeline, recs, st.session_state.content_mode))
                st.session_state.hermes_topic_error = ""
                st.rerun()
            except Exception as exc:
                st.session_state.hermes_topic_error = safe_error(exc)
                st.error("Hermes 조사에 실패했습니다. A 추천은 보존됩니다.")

    with st.expander("판단 근거 · 데이터 보기"):
        if st.session_state.hermes_topic_error:
            st.markdown("**Hermes 상태**")
            st.code(st.session_state.hermes_topic_error, language=None)
        coverage = comp.get("channel_coverage") or {}
        if coverage:
            st.caption(f"공개 영상 {coverage.get('channel_video_rows','?')}개 · 과거 대본 {coverage.get('historical_script_excerpts',0)}개 · Studio 기록 {coverage.get('studio_performance_rows',0)}행")
        st.caption("A/B는 서로 다른 데이터 기반의 제안입니다. 조회수 예측이나 모델 성능 시험이 아닙니다.")
        for source, topic_list in (("A", recs[:3]), ("B", b_topics[:3])):
            st.markdown(f"**{source} 추천 근거**")
            for i, item in enumerate(topic_list, 1):
                st.markdown(f"**{i}. {item.get('추천주제','')}**")
                st.write(rank_reason(item) or item.get('추천근거요약') or "근거 미확인")
                if relative_reason(item):
                    st.caption("다른 후보와 비교: " + relative_reason(item))
        if selected:
            _, _, source, rec, rank = selected
            st.markdown("**선택한 주제의 조사 근거**")
            frozen = evidence_for_comparison(comp).get("market_videos") or {}
            observation = market_observation(rec.get("추천검색어") or rec.get("추천주제"), frozen)
            interest = lookup_term(comp.get("interest_signal"), rec.get("추천검색어") or rec.get("추천주제"))
            st.write(f"연결된 경쟁 영상 {observation['matched_videos']}개 / 전체 조사 표본 {observation['sample_pool']}개")
            if observation["matched_videos"] < 2:
                st.warning("현재 확보한 근거만으로 반복적인 시장 수요는 검증할 수 없습니다.")
            if interest and interest.get("latest_4_avg") is not None:
                st.write(f"YouTube 검색 상대 관심도: {interest['latest_4_avg']}/100 · 검색 횟수는 아님")
            else:
                st.caption("검색 관심도 실측 없음")
            prior = strategy_store.forecast_context().get("historical_day_28_views_descriptive_only") or {}
            st.caption("28일 조회수 예측: " + ("과거 비교 표본만 존재" if prior.get("status")=="DESCRIPTIVE_BASELINE" else "표본 부족으로 보류"))
            audits = (comp.get("evidence_audit") or {}).get("a" if source == "A" else "b") or []
            current_audit = audits[rank - 1] if rank - 1 < len(audits) else {}
            if current_audit:
                st.write("출처 검증: " + str(current_audit.get("status") or "미확인"))
                for limitation in current_audit.get("limitations") or []:
                    st.caption("한계: " + str(limitation))
                for url in current_audit.get("tool_observed_urls") or []:
                    if isinstance(url, str) and url.startswith(("https://", "http://")):
                        st.write(url)
            for label, field in (("채널 공백", "내채널공백"),
                ("핵심 차별점", "뾰족한포인트가설"), ("전략 근거", "전략판단근거"),
                ("중복·제작 위험", "신규성및중복위험")):
                if rec.get(field): st.write(label + ": " + str(rec[field]))
            for u in (rec.get('검증출처URL') or [])[:5]:
                if isinstance(u,str) and u.startswith(('https://','http://')):
                    st.write(u)
            if source == "A": render_market_evidence(rec)
            from evidence_charts import chart_observations, interest_bars
            evidence = evidence_for_comparison(comp)
            chart = chart_observations(rec, evidence)
            if chart['own']:
                st.markdown("**내 채널 근거 영상 · 누적 조회수**")
                st.bar_chart(chart['own'], x='영상', y='누적 조회수')
            if chart['market']:
                st.markdown("**경쟁 영상 · 누적 조회수**")
                st.bar_chart(chart['market'], x='영상', y='누적 조회수')
            interest_rows = interest_bars(interest)
            if interest_rows:
                st.bar_chart(interest_rows, x='기간', y='상대 관심도')
        st.markdown("**조사 기록**")
        st.caption(f"Hermes 웹 도구 응답 {comp.get('web_verified_calls',0)}회 · URL {comp.get('web_source_count',0)}개")
        for warning in comp.get("warnings") or []:
            st.caption(str(warning))
        if comp.get("run_folder"): st.code(str(comp['run_folder']), language=None)
        top = strategy_store.comment_context().get('top_videos') or []
        if top:
            st.markdown("**내 채널 댓글 반응**")
            st.dataframe([{"영상": v['title'], "댓글": v['comments'], "조회수": v['views']}
                for v in top], hide_index=True, use_container_width=True)
    if st.button("← 주제 찾기", key="compare_back"):
        navigate_to("find")

def render_stage_research():
    research = st.session_state.research
    st.markdown('<div class="flow-head"><h2>영상 방향 선택</h2></div>', unsafe_allow_html=True)
    if research is None:
        st.warning("조사된 주제가 없습니다.")
        if st.button("← 주제 선택", key="res_empty_back"):
            navigate_to("compare" if st.session_state.home_recommendations else "find")
        return
    selection = st.session_state.topic_selection or {}
    title = selection.get("topic") or st.session_state.user_input or research.get("query") or "선택한 주제"
    st.markdown(f'<div class="flow-picked"><strong>{esc(title)}</strong></div>', unsafe_allow_html=True)
    brief = st.session_state.consultant_brief or research.get("idea_brief") or {}
    candidates = research.get("content_candidates", []) if research.get("research_ready", False) else []
    if not research.get("research_ready", False):
        st.warning("시장 자막이 부족해 대본을 만들 수 없습니다.")
    if not research.get("research_ready", False):
        with st.container():
            st.caption("외부자막은 시장 경쟁 영상에만 사용합니다. 무료 Supadata 키를 등록하면 IP 차단 시 자동으로 기존 자막을 가져옵니다. 유료 AI 음성인식은 사용하지 않습니다.")
            st.markdown("무료 키 발급: [Supadata](https://dash.supadata.ai/) (외부 사이트, 무료 계정 필요)")
            key_path = pipeline.cache.root.parent / "supadata_key.txt"
            configured = bool((key_path.exists() and key_path.read_text(encoding="utf-8").strip()) or os.getenv("SUPADATA_API_KEY"))
            st.caption("Supadata 키 상태: " + ("등록됨" if configured else "미등록"))
            with st.form("external_transcript_provider"):
                new_provider_key = st.text_input("Supadata API 키", type="password", placeholder="여기에 무료 API 키 붙여넣기")
                connect = st.form_submit_button("키 등록 후 시장 자막 다시 조사", use_container_width=True)
            if connect:
                if not new_provider_key.strip():
                    st.error("API 키를 입력하세요.")
                else:
                    key_path.parent.mkdir(parents=True, exist_ok=True)
                    key_path.write_text(new_provider_key.strip(), encoding="utf-8")
                    try:
                        os.chmod(key_path, 0o600)
                    except OSError:
                        pass
                    pipeline.evidence.transcript_blocked = True  # 같은 IP로 재요청하지 않고 예비 API 먼저 사용
                    try:
                        q = research.get("query") or st.session_state.user_input
                        st.session_state.research = run_with_status("시장 Transcript 복구", lambda cb: pipeline.research_topic(q, progress=cb, idea_brief=brief,
                            prefetched_market=evidence_for_comparison(st.session_state.topic_comparison).get("market_videos")))
                        st.rerun()
                    except Exception as exc:
                        show_exception("외부 자막 재조사에 실패했습니다.", exc)

            failed_df = research.get("transcript_df")
            if failed_df is not None and not failed_df.empty:
                missing_df = failed_df.loc[failed_df["대본상태"].ne("성공")]
                missing_options = {str(r["video_id"]): str(r["영상제목"]) for _, r in missing_df.iterrows()}
                if missing_options:
                    st.caption("외부 서비스 없이도 YouTube에서 직접 표시한 자막을 붙여넣으면 해당 영상의 실제 대본으로 저장됩니다.")
                    with st.form("paste_video_transcript"):
                        selected_id = st.selectbox("자막을 넣을 시장 영상", list(missing_options), format_func=lambda x: missing_options[x] + " (" + x + ")")
                        pasted_text = st.text_area("YouTube의 '스크립트 표시'에서 복사한 실제 자막", height=170)
                        submitted = st.form_submit_button("이 영상의 자막 저장 후 다시 조사", use_container_width=True)
                    if submitted:
                        from transcript_fallback import import_pasted_transcript
                        try:
                            import_pasted_transcript(pipeline.cache, selected_id, pasted_text)
                            q = research.get("query") or st.session_state.user_input
                            st.session_state.research = run_with_status("시장 Transcript 복구", lambda cb: pipeline.research_topic(q, progress=cb, idea_brief=brief,
                            prefetched_market=evidence_for_comparison(st.session_state.topic_comparison).get("market_videos")))
                            st.rerun()
                        except Exception as exc:
                            st.error(safe_error(exc))
        if st.button("Transcript 다시 시도", use_container_width=True):
            try:
                pipeline.evidence.transcript_blocked = False
                pipeline.evidence.transcript_block_reason = ""
                q = research.get("query") or st.session_state.user_input
                st.session_state.research = run_with_status("Deep Research 재시도", lambda cb: pipeline.research_topic(q, progress=cb, idea_brief=brief,
                            prefetched_market=evidence_for_comparison(st.session_state.topic_comparison).get("market_videos")))
                st.rerun()
            except Exception as exc:
                show_exception("Deep Research 재시도 중 오류가 발생했습니다.", exc)


    if candidates:
        cov = research.get("transcript_coverage") or {}
        if cov.get("ready") and cov.get("total"):
            st.caption(f"시장 자막 {int(cov.get('success') or 0)}/{int(cov.get('total') or 0)}개 확보")
        opts = list(range(len(candidates)))
        chosen = st.radio("만들 영상의 방향", opts,
            format_func=lambda i: f"{i+1}. {short(candidates[i].get('주제'), 115)}", key="research_direction")
        item = candidates[chosen]
        if item.get("핵심엣지가설"):
            st.markdown(f'<div class="flow-picked"><p>{esc(short(item["핵심엣지가설"], 220))}</p></div>', unsafe_allow_html=True)
        if st.button("이 방향으로 대본 만들기", type="primary", use_container_width=True):
            try:
                make_draft_from_candidate(chosen)
                st.rerun()
            except Exception as exc:
                show_exception("대본 생성 실패", exc)
    with st.expander("판단 근거 · 데이터 보기"):
        render_research_coverage(research)
        patterns = research.get("content_patterns") or []
        if patterns:
            st.markdown("**발견된 설명 패턴**")
            for ptn in patterns:
                st.markdown(f"**{ptn.get('클러스터명','패턴')}** · {ptn.get('설명','')}")
                st.caption(f"구조: {ptn.get('핵심구조','')} · 보상: {ptn.get('핵심보상','')}")
        if candidates:
            st.markdown("**선택한 방향의 근거**")
            for name, value in (("가르칠 지식",item.get("가르칠영어지식")),
                ("시장 발견",item.get("시장발견")),("내 채널 공백",item.get("내채널공백")),
                ("중복 위험",item.get("신규성및중복위험"))):
                if value: st.write(f"**{name}** · {value}")
            render_market_evidence(item)
        df = research.get("candidate_df")
        if df is not None and not df.empty:
            cols = [x for x in ("제목","채널","조회수","영상링크") if x in df.columns]
            if cols: st.dataframe(df[cols], use_container_width=True, hide_index=True)
        tdf = research.get("transcript_df")
        if tdf is not None and not tdf.empty:
            st.markdown("**자막 확보 현황**")
            cols = [x for x in ("영상제목","대본상태","대본출처","대본캐시") if x in tdf.columns]
            if cols: st.dataframe(tdf[cols], use_container_width=True, hide_index=True)
        selection_rec = selection.get('rec') or {}
        if selection_rec and research.get('research_ready'):
            if st.session_state.get('production_committed_topic') == title:
                st.caption("제작 확정 기록 저장됨")
            elif st.button("제작 결정 기록에 저장", key="save_decision_research"):
                from topic_experiment import save_selection
                frozen = evidence_for_comparison(st.session_state.topic_comparison).get('market_videos') or {}
                market_signal = market_observation(selection_rec.get('추천검색어') or title, frozen)
                interest_signal = lookup_term((st.session_state.topic_comparison or {}).get('interest_signal'),
                    selection_rec.get('추천검색어') or title)
                if interest_signal: market_signal['google_trends_relative_interest'] = interest_signal
                strategy_store.record_topic_choice(selection_rec, selection.get('source','A'),
                    market_signal=market_signal,
                    experiment_ref=str((st.session_state.topic_comparison or {}).get('run_folder') or ''))
                save_selection(st.session_state.topic_comparison, selection_rec, selection.get('source','A'))
                st.session_state.production_committed_topic = title
                st.success("제작 결정 기록 저장")
    if st.button("← 주제 비교" if st.session_state.home_recommendations else "← 주제 찾기", key="research_back"):
        navigate_to("compare" if st.session_state.home_recommendations else "find")

def render_strategy_workspace():
    """One screen for strategic decisions; no research workflow changes."""
    c1, c2 = st.columns([1, 1])
    if c1.button("← 다음 주제 찾기로", use_container_width=True):
        st.session_state.view_mode = "main"
        st.rerun()
    if c2.button("공개 성과 새로 확인", use_container_width=True):
        with st.spinner("내 공개 영상 조회수를 갱신하는 중"):
            st.session_state.strategy_sync_result = strategy_store.sync_public(
                pipeline.youtube, st.session_state.channel_handle, force=True)
        st.rerun()

    st.markdown('<div class="flow-head"><h2>채널 전략 검증</h2><p>현재 선택을 지지하는 데이터와 반론을 비교합니다. 판단과 실제 성과는 누적 검증합니다.</p></div>', unsafe_allow_html=True)
    st.caption("과거 채택 전략·실제 공개 성과·사전 선택 기록을 바탕으로 반론까지 검토합니다. 실시간 검색 수요 자료가 없으면 없다고 말합니다. 최신 경쟁 조사에는 ① 주제 찾기의 Hermes를 사용합니다.")

    sync = st.session_state.get("strategy_sync_result") or {}
    summary = strategy_store.metrics_summary()
    if summary.get("measured_at"):
        st.caption(f"공개 영상 {summary.get('count', 0)}개 · 마지막 기록 {summary['measured_at'][:16].replace('T', ' ')} (UTC) · 최대 하루 한 번 자동 갱신")
    else:
        st.caption("아직 공개 성과 기록이 없습니다. YouTube API 확인 후 자동 누적됩니다.")
    if sync.get("error"):
        with st.expander("최근 공개 성과 갱신 오류 · 기존 기록은 보존됨"):
            st.code(sync["error"], language=None)

    calibration = strategy_store.forecast_context()
    outcomes = calibration.get("past_decision_outcomes") or {}
    st.caption(f"누적 판단 {outcomes.get('total_decisions', 0)}건 · 실제 발행 후 28일 결과 확인 {outcomes.get('observed_28d', 0)}건 · 수치 예측은 실측 표본이 부족하면 보류")
    check = outcomes.get("baseline_check") or {}
    if check.get("status") == "OBSERVED_BASELINE_CHECK":
        st.caption(f"과거 채널 기준 범위의 실제 포함률 {check['inside_percent']}% · N={check['n']} (주제 선택의 성공률 아님)")
    with st.expander("과거 판단과 7일·28일 실제 성과 비교"):
        rows = outcomes.get("rows") or []
        if rows:
            st.dataframe([{"선택 주제":str(x.get('topic'))[:55], "진행":x.get("status"),
                           "7일 실측":", ".join(map(str, x['day_7'].values())) if x.get("day_7") else "미관측",
                           "28일 실측":", ".join(map(str, x['day_28'].values())) if x.get("day_28") else "미관측"}
                          for x in rows[-12:]], hide_index=True, use_container_width=True)
        else:
            st.write("주제를 선택한 뒤 실제 영상과 연결하면 결과가 여기에 자동으로 누적됩니다.")
        st.caption("영상 업로드 뒤 7±1일·28±1일에 앱을 열어 조회수를 수집해야 해당 시점 값이 기록됩니다. 소급 추정하지 않습니다.")
    with st.form("strategy_consultation_form", clear_on_submit=True):
        question = st.text_area("검증할 전략·가설", placeholder="예: 주 1편도 버거운데 2주에 한 번으로 낮춰야 할까? 어순 콘텐츠를 더 깊게 파야 할까?", height=110)
        submitted = st.form_submit_button("내 판단에 도전하기 →", type="primary", use_container_width=True)
    if submitted:
        if not question.strip():
            st.warning("고민을 한 문장이라도 입력하세요.")
        else:
            try:
                with st.spinner("기존 성과와 선택했던 전략을 기준으로 검토하는 중"):
                    advice_sources = {
                        "market_pattern_memory_unverified_hypotheses": pipeline.pattern_memory.prompt_context(limit=5),
                        "user_input_studio_data": pipeline.manual_data.studio_context(max_rows=12),
                    }
                    answer = consult_strategy(pipeline.clients.openai, pipeline.settings.llm_model,
                                              question, strategy_store, st.session_state.content_mode,
                                              evidence_context=advice_sources)
                    record = strategy_store.add_consultation(question, answer, pipeline.settings.llm_model,
                                                             {"public_snapshot_at": summary.get("measured_at")})
                st.session_state.strategy_latest_consultation_id = record["id"]
                st.rerun()
            except Exception as exc:
                show_exception("전략 검증 실패 · 이번 질문은 저장하지 않았습니다.", exc)

    conversation = strategy_store.conversations()
    if conversation:
        latest_id = st.session_state.strategy_latest_consultation_id
        latest = next((x for x in conversation if x.get("id") == latest_id), conversation[-1])
        st.markdown("### 최근 판단")
        st.markdown(f"**{esc(short(latest.get('question'), 140))}**")
        st.write(latest.get("answer") or "")
        if latest.get("status", "").startswith("운영자 채택"):
            st.caption("내가 채택한 운영 판단 · 실제 효과는 아직 검증되지 않았습니다.")
        elif st.button("이 판단을 내 운영 원칙으로 채택", use_container_width=True):
            if strategy_store.accept_decision(latest["id"]):
                st.success("바탕화면 전략 폴더에 채택 기록을 저장했습니다. 다음 주제 추천에도 반영됩니다.")
                st.rerun()
        with st.expander(f"지난 전략 검토 {max(0, len(conversation) - 1)}건"):
            for item in reversed([r for r in conversation if r.get("id") != latest["id"]][-8:]):
                st.markdown(f"**{item.get('created_at', '')[:10]} · {short(item.get('question'), 140)}**")
                st.caption(item.get('status', 'AI 제안'))
                st.write(short(item.get('answer'), 420))
                if not item.get("status", "").startswith("운영자 채택"):
                    if st.button("이전 판단 채택", key=f"accept_{item['id']}"):
                        strategy_store.accept_decision(item['id'])
                        st.rerun()
    else:
        st.info("첫 전략 가설을 검토하면 판단과 반론이 날짜별로 누적돼요.")

    with st.expander("내 운영 원칙 · 다음 주제 추천에 반영"):
        st.caption("AI 답변 전체를 자동으로 채택하지는 않습니다. 여기의 원칙과 직접 채택한 전략 판단만 주제 추천에 활용합니다.")
        with st.form("strategy_principles_form"):
            principles = st.text_area("운영 원칙", value=strategy_store.principles(), height=160)
            if st.form_submit_button("운영 원칙 저장", use_container_width=True):
                try:
                    strategy_store.set_principles(principles)
                    st.success("기존 주제 데이터와 별도로 저장했습니다.")
                except Exception as exc:
                    st.error(safe_error(exc))
        st.caption(f"저장 폴더: {strategy_store.root}")

    with st.expander("댓글 기반 실제 반응 · 절대 댓글 수 및 내용 검토"):
        st.caption("조회수 대비 비율을 계산하지 않습니다. 공개 총댓글 수는 답글 포함 가능 · 댓글 텍스트 분석은 관련도 순 원댓글 최대 60개 표본입니다.")
        all_videos = strategy_store.latest_public().get("videos") or []
        ranked = absolute_comment_leaderboard(all_videos)
        if ranked:
            st.dataframe([{"영상": x["title"], "공개 댓글 총수": x["comments"],
                           "누적 조회수(참고)": x["views"], "업로드일": x["published_date"]}
                          for x in ranked], hide_index=True, use_container_width=True)
            selected_id = st.selectbox("내용을 검토할 영상", [x['video_id'] for x in ranked if len(x['video_id']) == 11],
                          format_func=lambda vid: next((x['title'] for x in ranked if x['video_id'] == vid), vid),
                          key="review_comment_video_id")
            existing = next((x for x in strategy_store.comment_reviews() if x.get('video_id') == selected_id), None)
            if st.button("선택 영상의 원댓글 최대 60개 읽고 분류하기", use_container_width=True):
                try:
                    with st.spinner("공개 원댓글 표본을 읽고 구체적 행동 유형을 분류하는 중"):
                        sample = fetch_top_level_comments(pipeline.clients.youtube, selected_id, 60)
                        report = classify_comment_sample(pipeline.clients.openai, pipeline.settings.llm_model, sample, selected_id)
                        report['public_total_comments_at_review'] = next(x['comments'] for x in ranked if x['video_id'] == selected_id)
                        strategy_store.save_comment_review(report)
                        st.session_state['comment_review_transient'] = report
                    st.success("AI 분류 집계만 바탕화면 전략 폴더에 저장했습니다. 댓글 원문과 작성자 정보는 저장하지 않습니다.")
                    existing = report
                except Exception as exc:
                    st.error("댓글 검토 실패 · 이전 기록 유지: " + safe_error(exc))
            visible = st.session_state.get('comment_review_transient')
            if not visible or visible.get('video_id') != selected_id:
                visible = existing
            if visible:
                st.caption(f"분류 표본 {visible.get('sample_count',0)}개 · 분석일 {str(visible.get('measured_at',''))[:10]} · AI 잠정 분류")
                counts = visible.get('category_counts') or {}
                st.dataframe([{'반응 유형': label, '관측 원댓글 수': count} for label, count in counts.items()],
                             hide_index=True, use_container_width=True)
                st.caption("댓글의 학습·구매 효과를 입증하지 않음. 관련도 순 표본 편향, 댓글 미작성 시청자, 작성자 반복, 영상 경과일을 고려해야 합니다.")
                for label, examples in (visible.get('_transient_examples') or {}).items():
                    if examples and label in ('구체적 이해·칭찬', '실제 적용·행동', '주제 토론·의견', '강의·상품 관심'):
                        st.caption(f"{label} · 검토 예문: {' / '.join(examples[:1])}")
            else:
                st.caption("이 영상의 댓글 내용 분석 기록이 없습니다. 버튼을 누르면 API 비용이 발생할 수 있습니다.")
        else:
            st.info("공개 영상 데이터가 아직 없습니다. 우선 공개 성과를 가져오세요.")

    with st.expander("자동 누적되는 공개 영상 성과 · 주제 연결"):
        st.caption("YouTube API에서 조회수/좋아요/댓글/업로드일을 갱신합니다. 노출·CTR·지속률은 별도 Studio 데이터입니다. 수집 시점이 달라 7일/28일 수치를 소급할 수는 없습니다.")
        recent = summary.get("videos") or []
        if recent:
            st.dataframe([{"영상": row.get("title"), "조회수": row.get("views"),
                          "직전 기록 이후 증가": row.get("views_change_since_previous_snapshot"),
                          "업로드": row.get("published_date"), "주제 연결": "확인" if row.get("linked_to_topic") else "미연결"}
                         for row in recent[:10]], use_container_width=True, hide_index=True)
        st.caption("추천한 주제와 실제로 올린 영상을 자동 추정해 연결하지 않습니다. 최초 한 번만 연결하면 이후 공개 성과는 자동 기록됩니다.")
        try:
            decisions_df = pipeline.manual_data.read("content_decisions")
            ideas = [] if decisions_df is None or decisions_df.empty else [str(v).strip() for v in decisions_df["topic"].fillna("").tolist() if str(v).strip()]
            ideas = list(dict.fromkeys(reversed(ideas)))[:25]
        except (KeyError, OSError, ValueError):
            ideas = []
        if ideas and recent:
            with st.form("strategy_link_video_form"):
                topic = st.selectbox("실제로 영상화한 추천 주제", ideas)
                video_id = st.selectbox("게시한 내 영상", [v["video_id"] for v in recent],
                                        format_func=lambda v: next((x["title"] for x in recent if x["video_id"] == v), v))
                if st.form_submit_button("주제와 영상 한 번만 연결", use_container_width=True):
                    try:
                        strategy_store.link_video(topic, video_id)
                        st.success("연결 완료. 다음 공개 성과 수집부터 같은 ID로 추적합니다.")
                    except Exception as exc:
                        st.error(safe_error(exc))
        elif not recent:
            st.caption("영상 목록을 먼저 가져와야 연결할 수 있습니다.")
        else:
            st.caption("주제 추천을 하나 선택한 뒤 업로드하면 연결할 수 있습니다.")
        st.caption(f"기록 경로 · {strategy_store.root / 'public_snapshots'}")


missing = [name for name in ["YOUTUBE_API_KEY", "OPENAI_API_KEY"] if not os.getenv(name)]
if missing:
    st.error(".env 설정이 필요합니다: " + ", ".join(missing))
    st.code("YOUTUBE_API_KEY=...\nOPENAI_API_KEY=...", language="text")
    st.stop()

try:
    pipeline = ensure_pipeline()
except Exception as exc:
    show_exception("파이프라인 초기화 실패", exc)
    st.stop()

# The strategy journal is independent of app versions and topic-research caches.
strategy_store = StrategyStore()
# Runs on app opening (and no more than once per day while user interacts).
# Failure never prevents use of the app; previous snapshots are preserved.
st.session_state.strategy_sync_result = strategy_store.sync_public(
    pipeline.youtube, st.session_state.channel_handle)

if st.session_state.view_mode == "data":
    render_data_workspace()
    st.stop()
if st.session_state.view_mode == "strategy":
    render_strategy_workspace()
    st.stop()

if st.session_state.flow_stage == "draft" and st.session_state.draft_a_bundle is not None:
    render_draft_workspace()
    st.stop()
elif st.session_state.flow_stage == "compare":
    render_stage_compare()
elif st.session_state.flow_stage == "research":
    render_stage_research()
else:
    render_stage_find()


with st.sidebar:
    st.markdown("### 메뉴")

    if st.button("새 주제 찾기", use_container_width=True):
        st.session_state.user_input = ""
        reset_work(keep_recommendations=False)
        st.rerun()

    if st.button("채널 전략 검증 · 누적 학습", use_container_width=True):
        st.session_state.view_mode = "strategy"
        st.rerun()

    if st.button("데이터 입력 · Studio", use_container_width=True):
        st.session_state.view_mode = "data"
        st.rerun()

    from topic_experiment import load_latest_topic_comparison
    if st.button("이전 주제 비교 불러오기", use_container_width=True):
        previous = load_latest_topic_comparison(pipeline.data_root)
        if previous and previous.get("a_topics"):
            st.session_state.home_recommendations = previous["a_topics"]
            st.session_state.topic_comparison = previous
            st.session_state.hermes_topic_error = ""
            st.session_state.view_mode = "main"
            st.session_state.flow_stage = "compare"
            st.rerun()
        else:
            st.warning("저장된 주제 비교를 찾지 못했습니다.")


    with st.expander("아이디어 보관함", expanded=False):
        st.caption("다른 영상을 보며 발견한 좋은 설명·특이점·겹침·빈틈을 저장합니다. 다음 리서치에서 다시 참고합니다.")
        current_topic = (st.session_state.consultant_brief or {}).get("주제", "")
        memory_topic = st.text_input("주제", value=current_topic, key="memory_topic_hint", placeholder="예: be동사")
        memory_note = st.text_area("메모", key="memory_note_text", placeholder="발견한 아이디어를 적으세요", height=90)
        if st.button("아이디어 저장", key="save_memory_note", use_container_width=True):
            if not memory_note.strip():
                st.warning("저장할 메모를 적어주세요.")
            else:
                try:
                    saved = run_with_status("아이디어 저장", lambda cb: pipeline.save_manual_note(memory_note, topic_hint=memory_topic, current_brief=st.session_state.consultant_brief, progress=cb))
                    st.success(f"{len(saved.get('items', []))}개 아이디어 단위로 저장했습니다.")
                except Exception as exc:
                    show_exception("메모 저장 중 오류가 발생했습니다.", exc)
        memory_items = pipeline.memory.recent(10)
        if memory_items:
            st.markdown("**최근 저장**")
            for item in memory_items[:6]:
                st.caption(f"{item.get('topic','')} · {item.get('title','')}")

    with st.expander("시장 패턴 지도", expanded=False):
        st.caption("Deep Research가 쌓일수록 시장 영상의 구조 클러스터를 누적합니다. 고정된 강의형/훈련형 분류가 아니라 실제 Content DNA에서 발견한 패턴입니다.")
        stats = pipeline.pattern_memory.stats()
        st.caption(f"누적 Research {stats.get('runs',0)}회 · 발견 패턴 {stats.get('patterns',0)}개")
        for ptn in pipeline.pattern_memory.recent_patterns(6):
            st.markdown(f"**{ptn.get('name','패턴')}**")
            st.caption(f"{ptn.get('description','')} · 반복 {ptn.get('times_seen',1)}회")

    with st.expander("설정 · 캐시", expanded=False):
        st.text_input("내 채널 handle", key="channel_handle")
        st.text_input("LLM model", key="llm_model")
        st.text_input("Embedding model", key="embedding_model")
        st.text_input(
            "공용 데이터 폴더",
            key="data_root",
            help="cache, Content Edge Memory, 실행 기록이 이 폴더에 저장됩니다. 새 앱 버전을 지워도 이 폴더는 남겨두면 됩니다.",
        )
        cache_dir = Path(st.session_state.data_root).expanduser() / "cache"
        transcript_count = len(list((cache_dir / "transcripts").glob("*.json"))) if (cache_dir / "transcripts").exists() else 0
        comment_count = len(list((cache_dir / "comments").glob("*.json"))) if (cache_dir / "comments").exists() else 0
        llm_count = len(list((cache_dir / "llm").glob("*.json"))) if (cache_dir / "llm").exists() else 0
        st.caption(f"현재 캐시 · Transcript {transcript_count} · Comments {comment_count} · LLM {llm_count}")
        pstats = pipeline.pattern_memory.stats()
        st.caption(f"Memory · Content Edge {len(pipeline.memory.all_items())} · 시장 패턴 {pstats.get('patterns',0)}")
        st.caption(r"기본값은 바탕화면\youtube_consultant_data 입니다.")
        st.text_area("Key용 실제 상품/서비스 정보", key="business_profile", height=100, placeholder="예: 현재 판매 중인 서비스, 가격대, 누구의 어떤 문제를 해결하는지. 비워두면 Key 추천에서 상품 정보 부족으로 처리합니다.")
        if st.button("설정 적용", use_container_width=True):
            try:
                root = Path(st.session_state.data_root).expanduser()
                root.mkdir(parents=True, exist_ok=True)
                (root / "business_profile.txt").write_text(st.session_state.business_profile or "", encoding="utf-8")
            except Exception:
                pass
            st.session_state.pipeline = None
            st.session_state.pipeline_signature = None
            reset_work(keep_recommendations=False)
            st.rerun()
        st.caption(BUILD_VERSION)

