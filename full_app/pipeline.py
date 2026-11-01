from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from cache import CacheManager
from clients import build_clients
from config import Settings
from content_memory import ContentMemoryStore
from content_pattern_memory import ContentPatternMemoryStore
from critic_agent import ScriptCriticAgent
from market_audit import build_market_audit, parse_topic_decision
from manual_data import ManualDataStore
from strategy_hub import StrategyStore
from yra_tools.evidence_tools import EvidenceTools
from yra_tools.llm_tools import LLMTools
from yra_tools.retrieval_tools import RetrievalTools
from yra_tools.youtube_tools import YouTubeResearchTools
from research_resilience import SearchQuotaExhausted, source_video_ids

ProgressFn = Optional[Callable[[str, str], None]]


class ResearchPipeline:
    """개인 YouTube 콘텐츠 컨설턴트용 deterministic research pipeline.

    핵심 Research/RAG는 안정적인 순서로 실행하고, 사용자 자유 입력은 Content Brief로
    해석한 뒤 같은 엔진으로 합류한다. Draft A 이후는 bounded Critic Agent가 필요할 때만 외부 검증을 사용해 Draft B를 만든다.
    """

    def __init__(self, settings: Settings | None = None, project_root: str | Path | None = None, data_root: str | Path | None = None):
        self.settings = settings or Settings()
        self.project_root = Path(project_root or Path(__file__).resolve().parent)
        self.clients = build_clients()
        data_root_env = os.getenv("YRA_DATA_DIR")
        if data_root:
            self.data_root = Path(data_root).expanduser()
        elif data_root_env:
            self.data_root = Path(data_root_env).expanduser()
        else:
            desktop = Path.home() / "Desktop"
            self.data_root = (desktop / "youtube_consultant_data") if desktop.exists() else (self.project_root / "data")
        self.data_root.mkdir(parents=True, exist_ok=True)

        cache_root = Path(os.getenv("YRA_CACHE_DIR", str(self.data_root / "cache")))
        if not cache_root.is_absolute():
            cache_root = self.project_root / cache_root
        self.cache = CacheManager(self.clients.openai, self.settings, root=cache_root)
        self.youtube = YouTubeResearchTools(self.clients.youtube, self.settings, search_cache_root=self.data_root / "cache" / "youtube_search_ids")
        self.evidence = EvidenceTools(self.clients.youtube, self.clients.transcript, self.cache)
        self.retrieval = RetrievalTools(self.cache, self.settings)
        self.llm = LLMTools(self.cache, self.settings, self.retrieval)

        memory_file = Path(os.getenv("YRA_MEMORY_FILE", str(self.data_root / "content_memory.json")))
        if not memory_file.is_absolute():
            memory_file = self.project_root / memory_file
        self.memory = ContentMemoryStore(memory_file)

        pattern_file = Path(os.getenv("YRA_PATTERN_MEMORY_FILE", str(self.data_root / "content_pattern_memory.json")))
        if not pattern_file.is_absolute():
            pattern_file = self.project_root / pattern_file
        self.pattern_memory = ContentPatternMemoryStore(pattern_file)
        self.critic_agent = ScriptCriticAgent(self.clients.openai, self.settings)
        self.manual_data = ManualDataStore(self.data_root)
        self.strategy_store = StrategyStore()

        self.channel_snapshot = None
        self.my_catalog_df = None
        self.my_content_df = None
        self.my_chunks_df = None

    @staticmethod
    def _emit(progress: ProgressFn, stage: str, detail: str):
        if progress:
            progress(stage, detail)

    def memory_context(self, query: str = "", limit: int = 18):
        return self.memory.prompt_context(query=query, limit=limit)

    def pattern_context(self, limit: int = 12):
        return self.pattern_memory.prompt_context(limit=limit)

    def save_manual_note(self, note: str, topic_hint: str = "", current_brief: dict | None = None, progress: ProgressFn = None):
        note = str(note or "").strip()
        if not note:
            raise ValueError("저장할 메모를 적어주세요.")
        self._emit(progress, "Content Memory", "메모를 재사용 가능한 아이디어 단위로 정리하는 중")
        memory_context = self.memory.prompt_context(topic_hint or note, limit=12)
        result, usage, cached = self.llm.classify_memory_note(
            note,
            topic_hint=topic_hint,
            current_brief=current_brief,
            memory_context=memory_context,
        )
        items = result.get("메모항목", [])
        ids = self.memory.add_manual_items(items, source_context=note[:160])
        return {"items": items, "ids": ids, "usage": usage, "cached": cached}

    def confirm_core_edge_used(self, candidate_package: dict):
        info = candidate_package.get("memory_ingest") or {}
        core_id = info.get("core_edge_id")
        title = (candidate_package.get("selected_candidate") or {}).get("주제", "")
        self.memory.mark_used(core_id, title)
        return core_id

    def prepare_channel_catalog(self, progress: ProgressFn = None):
        if self.my_catalog_df is not None:
            return {"channel_title": self.channel_snapshot["channel_title"], "video_count": len(self.my_catalog_df)}

        self._emit(progress, "내 채널", "채널 영상 목록과 성과 데이터를 불러오는 중")
        self.channel_snapshot = self.youtube.load_channel_catalog(self.settings.my_channel_handle)
        self.my_catalog_df = self.channel_snapshot["videos"].copy()
        # YouTube API가 제공하지 않는 Studio 성과는 사용자가 manual CSV에 추가한 최신값을 병합한다.
        self.my_catalog_df = self.manual_data.merge_performance_into_catalog(self.my_catalog_df)
        if self.my_catalog_df.empty:
            raise RuntimeError("내 채널에서 5~60분 롱폼 영상을 찾지 못했습니다.")
        return {"channel_title": self.channel_snapshot["channel_title"], "video_count": len(self.my_catalog_df)}

    def prepare_my_index(self, progress: ProgressFn = None):
        self.prepare_channel_catalog(progress=progress)
        if self.my_chunks_df is not None:
            success_count = int((self.my_content_df["대본상태"] == "성공").sum())
            return {"transcript_success": success_count, "chunk_count": len(self.my_chunks_df)}

        self._emit(progress, "내 콘텐츠", "내 영상 Transcript를 수집하고 캐시를 확인하는 중")
        self.my_content_df, _, _ = self.evidence.collect_my_content(self.my_catalog_df)
        success_count = int((self.my_content_df["대본상태"] == "성공").sum())
        if success_count == 0:
            self._emit(progress, "내 콘텐츠", "Transcript가 막혀 제목·설명·성과 메타데이터로 임시 인덱스를 만드는 중")
            fallback = self.my_catalog_df.copy()
            fallback["전체대본"] = fallback.apply(
                lambda r: (f"제목: {r.get('제목','')}\n설명: {r.get('설명','')}\n"
                           f"업로드: {r.get('업로드날짜','')} 조회수: {r.get('조회수',0)} 좋아요: {r.get('좋아요',0)} 댓글: {r.get('댓글',0)}") * 2,
                axis=1,
            )
            self.my_chunks_df = self.retrieval.build_index(fallback[["video_id", "제목", "전체대본"]], prefix="my_meta")
            self._emit(progress, "내 콘텐츠", "Transcript 0개 · 이번 실행은 제목/설명 기반으로 진행")
            return {"transcript_success": 0, "chunk_count": len(self.my_chunks_df), "fallback": "metadata"}

        self._emit(progress, "내 콘텐츠", "Chunk + Embedding 인덱스를 만드는 중")
        self.my_chunks_df = self.retrieval.build_index(self.my_content_df, prefix="my")
        return {"transcript_success": success_count, "chunk_count": len(self.my_chunks_df)}

    def interpret_input(self, user_input: str, progress: ProgressFn = None):
        self.prepare_channel_catalog(progress=progress)
        self._emit(progress, "컨설턴트", "입력의 주제·가설·콘텐츠 유형·비즈니스 역할을 해석하는 중")
        memory_context = self.memory.prompt_context(user_input, limit=14)
        brief, usage, cached = self.llm.interpret_user_input(user_input, self.my_catalog_df, memory_context=memory_context)
        return {"brief": brief, "usage": usage, "cached": cached}

    def _collect_market_map(self, queries, max_per_duration):
        """여러 시장 탐색어를 합치고, 각 영상이 어떤 검색어에서 발견됐는지 보존한다."""
        frames = []
        for query in [str(q).strip() for q in queries if str(q).strip()]:
            try:
                df = self.youtube.build_market_map(query, max_per_duration=max_per_duration)
            except SearchQuotaExhausted:
                break  # keep verified rows from the preceding queries
            if df.empty:
                continue
            df["발견검색어"] = query
            frames.append(df)
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        query_map = combined.groupby("video_id")["발견검색어"].apply(lambda x: sorted(set(x))).to_dict()
        combined = combined.drop_duplicates("video_id").reset_index(drop=True)
        combined["발견검색어_목록"] = combined["video_id"].map(query_map)
        return combined

    def _collect_recent_market_map(self, queries, max_per_duration=8):
        """최근 45일을 date-order로 별도 탐색해 작은 채널의 emerging breakout을 놓치지 않는다."""
        frames = []
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=self.settings.recent_breakout_window_days)
        published_after = cutoff.isoformat().replace("+00:00", "Z")
        for query in [str(q).strip() for q in queries if str(q).strip()]:
            try:
                df = self.youtube.build_market_map(
                    query,
                    max_per_duration=max_per_duration,
                    order="date",
                    published_after=published_after,
                )
            except SearchQuotaExhausted:
                break
            if df.empty:
                continue
            df["발견검색어"] = query
            frames.append(df)
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        query_map = combined.groupby("video_id")["발견검색어"].apply(lambda x: sorted(set(x))).to_dict()
        combined = combined.drop_duplicates("video_id").reset_index(drop=True)
        combined["발견검색어_목록"] = combined["video_id"].map(query_map)
        return combined

    @staticmethod
    def _merge_market_maps(*dfs):
        valid = [df for df in dfs if df is not None and not df.empty]
        if not valid:
            return pd.DataFrame()
        combined = pd.concat(valid, ignore_index=True)
        query_map, source_map, scope_map = {}, {}, {}
        for vid, group in combined.groupby("video_id"):
            qs = []
            for value in group.get("발견검색어_목록", pd.Series(dtype=object)).tolist():
                if isinstance(value, list):
                    qs.extend(value)
            if "발견검색어" in group.columns:
                qs.extend([str(x) for x in group["발견검색어"].dropna().tolist()])
            query_map[vid] = sorted(set(qs))
            if "발견출처" in group.columns:
                source_map[vid] = sorted({str(x) for x in group["발견출처"].dropna().tolist() if str(x).strip()})
            if "시장범위" in group.columns:
                scope_map[vid] = sorted({str(x) for x in group["시장범위"].dropna().tolist() if str(x).strip()})
        combined = combined.drop_duplicates("video_id").reset_index(drop=True)
        combined["발견검색어_목록"] = combined["video_id"].map(query_map)
        combined["발견출처_목록"] = combined["video_id"].map(source_map).apply(lambda x: x if isinstance(x, list) else [])
        combined["시장범위_목록"] = combined["video_id"].map(scope_map).apply(lambda x: x if isinstance(x, list) else [])
        return combined

    @staticmethod
    def _market_signal_label(evidence):
        if not evidence:
            return "근거 부족"
        recent_outliers = 0
        channels = set()
        has_old_absolute = False
        for e in evidence:
            channels.add(str(e.get("채널", "")))
            age = e.get("영상나이_일")
            ratio = e.get("채널배수")
            reasons = str(e.get("선정이유", ""))
            try:
                if bool(e.get("최근브레이크아웃", False)):
                    recent_outliers += 1
            except Exception:
                pass
            try:
                if age is not None and float(age) >= 365 and "Absolute Winner" in reasons:
                    has_old_absolute = True
            except Exception:
                pass
        if recent_outliers >= 2 and len(channels) >= 2:
            return "최근 상승 신호"
        if recent_outliers >= 1:
            return "강한 최근 Breakout"
        if len(evidence) >= 2 and len(channels) >= 2:
            return "반복 수요 신호"
        if has_old_absolute:
            return "장기 누적 수요"
        return "탐색 신호"

    @staticmethod
    def _strong_market_row(row: dict) -> bool:
        views = int(row.get("조회수", 0) or 0)
        n = int(row.get("baseline_N", 0) or 0)
        ratio = row.get("채널배수")
        sub_ratio = row.get("조회수_구독자배수")
        recent = bool(row.get("최근브레이크아웃", False))
        ratio_ok = pd.notna(ratio) and float(ratio) >= 2.0 and n >= 5 and views >= 5000
        sub_ok = pd.notna(sub_ratio) and float(sub_ratio) >= 3.0 and views >= 10000
        absolute_ok = views >= 100000
        return bool(recent or ratio_ok or sub_ok or absolute_ok)

    def _annotate_landscape_gate(self, landscape: list[dict], evidence_df: pd.DataFrame, scope: str = "domestic") -> list[dict]:
        if evidence_df is None or evidence_df.empty:
            for item in landscape:
                item["게이트통과"] = False
                item["근거등급"] = "근거 부족"
                item["강한근거수"] = 0
                item["독립채널수"] = 0
            return landscape
        lookup = {str(r["video_id"]): r.to_dict() for _, r in evidence_df.iterrows()}
        for item in landscape:
            rows = [lookup[str(v)] for v in (item.get("근거video_ids") or []) if str(v) in lookup]
            strong = [r for r in rows if self._strong_market_row(r)]
            channels = {str(r.get("채널", "")) for r in strong if str(r.get("채널", ""))}
            recent = [r for r in strong if bool(r.get("최근브레이크아웃", False))]
            # Domestic 기본 Gap은 독립 채널 반복을 우선하고, Recent는 강한 단일 breakout도 탐색 가치가 있다.
            # Global은 한국 수요 증거가 아니라 "전이할 가치가 있는 해외 검증"이므로 별도 등급으로 본다.
            is_recent_opportunity = str(item.get("신호유형", "")) == "최근상대성과"
            if scope == "global":
                passed = bool(strong)
                if len(strong) >= 2 and len(channels) >= 2:
                    grade = "해외 독립 채널 반복 근거"
                elif strong:
                    grade = "해외 단일 강한 근거"
                else:
                    grade = "해외 탐색 근거 부족"
            else:
                passed = bool(recent) if is_recent_opportunity else (len(strong) >= 2 and len(channels) >= 2)
                if passed and recent:
                    grade = "강한 최근 Breakout"
                elif passed:
                    grade = "독립 채널 반복 근거"
                elif strong:
                    grade = "보조 근거"
                else:
                    grade = "근거 부족"
            item["게이트통과"] = passed
            item["근거등급"] = grade
            item["강한근거수"] = len(strong)
            item["독립채널수"] = len(channels)
        return landscape

    def _transcript_coverage(self, transcript_df: pd.DataFrame, total_candidates: int) -> dict:
        total = int(total_candidates or 0)
        if transcript_df is None or transcript_df.empty:
            return {"total": total, "success": 0, "cached_success": 0, "ratio": 0.0, "blocked": bool(self.evidence.transcript_blocked), "ready": False, "errors": []}
        success_mask = transcript_df["대본상태"].eq("성공")
        success = int(success_mask.sum())
        cached_success = int((success_mask & transcript_df.get("대본캐시", False).fillna(False).astype(bool)).sum()) if "대본캐시" in transcript_df.columns else 0
        ratio = (success / total) if total else 0.0
        ready = success >= self.settings.market_transcript_min_count and ratio >= self.settings.market_transcript_min_ratio
        errors = [str(x)[:350] for x in transcript_df.loc[~success_mask, "대본오류"].dropna().tolist()[:4]] if "대본오류" in transcript_df.columns else []
        return {"total": total, "success": success, "cached_success": cached_success, "ratio": ratio, "blocked": bool(self.evidence.transcript_blocked), "ready": bool(ready), "errors": errors}

    def _attach_grounded_evidence(self, items, evidence_df, id_key="시장근거video_ids"):
        if evidence_df is None or evidence_df.empty:
            for item in items:
                item["시장근거상세"] = []
                item["시장신호판정"] = "근거 부족"
            return items
        lookup = {str(r["video_id"]): r for _, r in evidence_df.iterrows()}
        for item in items:
            details = []
            for vid in item.get(id_key, []) or []:
                row = lookup.get(str(vid))
                if row is None:
                    continue
                details.append({
                    "video_id": str(row.get("video_id", "")),
                    "제목": str(row.get("제목", "")),
                    "채널": str(row.get("채널", "")),
                    "조회수": int(row.get("조회수", 0) or 0),
                    "업로드날짜": str(row.get("업로드날짜", "")),
                    "영상나이_일": None if pd.isna(row.get("영상나이_일")) else int(row.get("영상나이_일")),
                    "조회속도_일평균": None if pd.isna(row.get("조회속도_일평균")) else float(row.get("조회속도_일평균")),
                    "채널배수": None if pd.isna(row.get("채널배수")) else float(row.get("채널배수")),
                    "조회수_구독자배수": None if pd.isna(row.get("조회수_구독자배수")) else float(row.get("조회수_구독자배수")),
                    "최근브레이크아웃": bool(row.get("최근브레이크아웃", False)),
                    "baseline_N": None if pd.isna(row.get("baseline_N")) else int(row.get("baseline_N")),
                    "baseline_경고": str(row.get("baseline_경고", "") or ""),
                    "선정이유": str(row.get("선정이유", "")),
                    "발견검색어": row.get("발견검색어_목록", []) if isinstance(row.get("발견검색어_목록", []), list) else [],
                    "영상링크": str(row.get("영상링크", "")),
                    "시장범위": str(row.get("시장범위", "") or ""),
                    "시장범위_목록": row.get("시장범위_목록", []) if isinstance(row.get("시장범위_목록", []), list) else [],
                    "발견출처": str(row.get("발견출처", "") or row.get("seed_role", "") or ""),
                    "발견출처_목록": row.get("발견출처_목록", []) if isinstance(row.get("발견출처_목록", []), list) else [],
                    "seed_channel_ref": str(row.get("seed_channel_ref", "") or ""),
                    "reference_language": str(row.get("reference_language", "") or ""),
                    "reference_country": str(row.get("reference_country", "") or ""),
                })
            item["시장근거상세"] = details
            item["시장신호판정"] = self._market_signal_label(details)
        return items

    def _scan_manual_reference_markets(self, progress: ProgressFn = None):
        """Scan Studio-selected neighboring channels and global reference channels.

        User controls the channel list in data_root/manual/reference_channels.csv.
        Channels observed in suggested traffic are also folded into the domestic neighborhood.
        """
        domestic_refs = self.manual_data.effective_domestic_reference_channels()
        global_refs = self.manual_data.global_reference_channels()
        domestic_market, domestic_diag = pd.DataFrame(), []
        global_market, global_diag = pd.DataFrame(), []

        if not domestic_refs.empty:
            self._emit(progress, "Audience Neighborhood", f"Studio/관찰 기반 참고 채널 {len(domestic_refs)}개를 최근 12개월 기준으로 스캔하는 중")
            domestic_market, domestic_diag = self.youtube.scan_reference_channels(domestic_refs, months=12, max_per_channel=80)
            if not domestic_market.empty:
                domestic_market["시장범위"] = "domestic_reference"
                domestic_market["발견출처"] = domestic_market.get("seed_role", "audience_neighbor")

        if not global_refs.empty:
            self._emit(progress, "Global Reference", f"해외 영어교육 참고 채널 {len(global_refs)}개에서 주제·Knowledge·Format 신호를 스캔하는 중")
            global_market, global_diag = self.youtube.scan_reference_channels(global_refs, months=18, max_per_channel=100)
            if not global_market.empty:
                global_market["시장범위"] = "global_reference"
                global_market["발견출처"] = "global_reference"

        return domestic_market, global_market, {"domestic": domestic_diag, "global": global_diag}

    @staticmethod
    def _reference_filter_by_queries(df: pd.DataFrame, queries, max_rows: int = 18):
        """Lightweight title/description filter for manual reference catalogs.

        It is deliberately deterministic and only narrows an already user-selected reference pool.
        If no lexical match exists, it falls back to the strongest outliers instead of pretending semantic certainty.
        """
        if df is None or df.empty:
            return pd.DataFrame()
        import re
        work = df.copy()
        tokens = []
        for q in queries or []:
            tokens.extend([t.lower() for t in re.findall(r"[A-Za-z0-9가-힣']+", str(q)) if len(t) >= 2])
        tokens = list(dict.fromkeys(tokens))
        if tokens:
            def score(row):
                text = (str(row.get("제목", "")) + " " + str(row.get("설명", ""))).lower()
                return sum(1 for t in tokens if t in text)
            work["_query_score"] = work.apply(score, axis=1)
            matched = work[work["_query_score"] > 0].copy()
        else:
            matched = pd.DataFrame()
        if matched.empty:
            matched = work.copy()
        sort_cols = [c for c in ["_query_score", "최근브레이크아웃", "채널배수", "조회수_구독자배수", "조회수"] if c in matched.columns]
        if sort_cols:
            matched = matched.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position="last")
        return matched.head(max_rows).drop(columns=["_query_score"], errors="ignore").reset_index(drop=True)

    def recommend_home(self, progress: ProgressFn = None):
        """Pulling/Key recommendation using Audience Neighborhood + broad search + Global Transfer."""
        self.prepare_my_index(progress=progress)
        studio_context = self.manual_data.studio_context(max_rows=30)

        # 1) User-selected / observed neighboring channels. This is the concrete implementation
        # of "choose the crowded line first": scan where the current audience already overlaps.
        domestic_ref_market, global_ref_market, reference_diagnostics = self._scan_manual_reference_markets(progress=progress)

        # 2) Broad Korean-market search remains as a discovery expansion, not the only source.
        self._emit(progress, "시장 탐색", "Audience Neighborhood 밖의 시장 기회까지 보기 위해 탐색 축을 만드는 중")
        probes, _, _ = self.llm.home_probe_queries(self.my_catalog_df, studio_context=studio_context)
        probe_queries = [x["검색어"] for x in probes]
        self.last_pre_recommend_interest = {'status':'NO_KEY', 'batches':[]}
        if os.getenv('SERPAPI_API_KEY', '').strip() and probe_queries:
            from trend_provider import capture_topic_trends
            # Relative-interest measurements precede rankings, but merely sample
            # exploratory search terms; these are not the final six topic labels.
            self.last_pre_recommend_interest = capture_topic_trends(
                [{'추천검색어':str(q)} for q in probe_queries[:5]], [], self.strategy_store.root)
        combined_search = self._collect_market_map(probe_queries, max_per_duration=self.settings.home_search_per_duration)

        self._emit(progress, "Recent Scout", "최근 45일의 emerging breakout을 별도로 찾는 중")
        recent_raw = self._collect_recent_market_map(probe_queries, max_per_duration=6)
        combined_search = self._merge_market_maps(combined_search, recent_raw)
        if not combined_search.empty:
            self._emit(progress, "시장 Scout", "검색 시장의 채널 대비 성과와 Recent Breakout을 계산하는 중")
            search_market = self.youtube.attach_channel_metrics(combined_search)
            search_market["시장범위"] = "domestic_search"
            search_market["발견출처"] = "search"
        else:
            search_market = pd.DataFrame()

        # Reference channel rows already carry their own channel-relative baseline.
        domestic_market = self._merge_market_maps(domestic_ref_market, search_market)
        if domestic_market.empty and global_ref_market.empty:
            return []

        domestic_candidates = self.youtube.select_research_candidates(domestic_market, top_n=8) if not domestic_market.empty else pd.DataFrame()
        if not domestic_candidates.empty:
            # preserve provenance columns dropped nowhere by select_research_candidates (row dict carries them)
            pass
        recent_candidates = pd.DataFrame()
        if not domestic_market.empty and "최근브레이크아웃" in domestic_market.columns:
            recent_candidates = domestic_market[domestic_market["최근브레이크아웃"] == True].copy()
            if not recent_candidates.empty:
                sort_cols = [c for c in ["조회속도_일평균", "채널배수", "조회수_구독자배수", "조회수"] if c in recent_candidates.columns]
                recent_candidates = recent_candidates.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position="last").head(15)

        global_candidates = self.youtube.select_research_candidates(global_ref_market, top_n=10) if not global_ref_market.empty else pd.DataFrame()

        # 3) Cluster topics before looking at my own content. Domestic and global have different meanings.
        domestic_landscape = []
        if not domestic_candidates.empty:
            self._emit(progress, "시장 지도", "Audience Neighborhood와 국내 시장에서 반복되는 주제/문제/Knowledge Gap을 묶는 중")
            d_result, _, _ = self.llm.synthesize_home_market_landscape(domestic_candidates, scope="domestic")
            domestic_landscape = self._annotate_landscape_gate(d_result.get("시장기회", []), domestic_market, scope="domestic")

        global_landscape = []
        if not global_candidates.empty:
            self._emit(progress, "Global Transfer", "해외 참고 채널에서 한국식으로 재해석할 주제·Knowledge·Explanation·Format 기회를 묶는 중")
            g_result, _, _ = self.llm.synthesize_home_market_landscape(global_candidates, scope="global")
            global_landscape = self._annotate_landscape_gate(g_result.get("시장기회", []), global_ref_market, scope="global")

        all_landscape = []
        for x in domestic_landscape:
            y = dict(x); y["시장범위"] = "국내/Audience Neighborhood"; all_landscape.append(y)
        for x in global_landscape:
            y = dict(x); y["시장범위"] = "Global Reference"; all_landscape.append(y)

        market_result = {
            '검색관심_사전탐색':self.last_pre_recommend_interest,
            "시장기회후보": [
                {
                    "기회": " | ".join([v for v in [x.get("시장문제", ""), x.get("지식갭", ""), x.get("포맷갭", "")] if v]),
                    "근거": x.get("왜기회인가", ""),
                    "확실성": x.get("확실성", "낮음"),
                    "기회id": x.get("기회id", ""),
                    "시장문제": x.get("시장문제", ""),
                    "지식갭": x.get("지식갭", ""),
                    "포맷갭": x.get("포맷갭", ""),
                    "시장범위": x.get("시장범위", ""),
                    "게이트통과": bool(x.get("게이트통과", False)),
                    "근거등급": x.get("근거등급", "근거 부족"),
                }
                for x in all_landscape
            ]
        }

        self._emit(progress, "채널 공백", "시장 기회를 내 기존 영상 Transcript/RAG와 비교해 이미 다룬 내용과 실제 공백을 확인하는 중")
        opportunity_df, gap_df = self.llm.analyze_opportunities(market_result, self.my_chunks_df)

        self._emit(progress, "추천", "Audience Neighborhood → Market/Recent/Global → 내 채널 Gap → Core Edge 순으로 TOP 3를 고르는 중")
        memory_context = self.memory.prompt_context(limit=24)
        # Only decisions the creator explicitly adopted, never raw AI advice.
        strategy_note = (self.strategy_store.principles()[:1200] + "\n" +
                         self.strategy_store.decision_context(limit=5)[:1700])
        memory_context = list(memory_context or []) + [{
            '종류':'사전 시장 검색어 관심도 · Google Trends / SerpApi',
            '내용':self.last_pre_recommend_interest,
            '주의':'검색어 기반 보조 신호이며 최종 추천 후보의 실측 검색량이 아닙니다. 배치별 정규화 수치를 섞지 말고, 실측 실패 시 모른다고 표시',
        }, {
            "종류": "내 채널 공개 댓글 행동 신호 · 절대 개수와 표본 분류 (구매전환 아님)",
            "내용": self.strategy_store.comment_context(),
            "주의": "조회수 대비 댓글 비율 사용 금지. 많은 댓글은 흥미/반응의 단서지만 품질·실제 구매를 입증하지 않음. 영상 나이/논란/댓글 설정 고려",
        }, {
            "종류": "운영자가 채택한 채널 전략 (성과 검증 전)",
            "내용": strategy_note,
            "주의": "전략 선호이지 시장 수요 증명이 아님. 반대되는 시장 증거가 있으면 반론 제시",
        }]
        recommendations, _, _ = self.llm.home_recommendations(
            self.my_catalog_df,
            domestic_candidates,
            all_landscape,
            opportunity_df,
            memory_context=memory_context,
            recent_candidates=recent_candidates,
            pattern_context=self.pattern_memory.prompt_context(limit=12),
            global_candidates=global_candidates,
            studio_context=studio_context,
        )
        grounded_pool = self._merge_market_maps(domestic_candidates, recent_candidates, global_candidates)
        recommendations = self._attach_grounded_evidence(recommendations, grounded_pool)

        self.last_home_landscape = all_landscape
        self.last_home_opportunities = opportunity_df
        self.last_home_scout_candidates = domestic_candidates
        self.last_home_recent_candidates = recent_candidates
        self.last_home_global_candidates = global_candidates
        self.last_reference_diagnostics = reference_diagnostics
        self.last_reference_markets = {"domestic": domestic_ref_market, "global": global_ref_market}
        return recommendations

    def research_topic(self, query: str, progress: ProgressFn = None, idea_brief: dict | None = None,
                       prefetched_market: dict | None = None):
        """Deep Research with a hard Transcript gate and explicit domestic/global provenance."""
        query = str(query or "").strip()
        if not query:
            raise ValueError("조사할 주제를 입력해주세요.")

        self.prepare_my_index(progress=progress)

        related_queries = [query]
        if idea_brief:
            related_queries += [x for x in (idea_brief.get("보조검색어") or []) if str(x).strip()]
            related_queries += [x for x in (idea_brief.get("해외검색어") or []) if str(x).strip()]
        related_queries = list(dict.fromkeys([str(x).strip() for x in related_queries if str(x).strip()]))[:6]

        # First reuse already observed competitor IDs from the selected topic run.
        # `videos.list` is cheap, whereas `search.list` costs 100 quota units per query.
        # IDs are selected only when the real saved title overlaps the query; seed IDs
        # have explicitly been cited in the recommendation.
        seed_ids = [str(v) for v in ((idea_brief or {}).get('시장근거video_ids') or [])]
        reusable = source_video_ids(prefetched_market or {}, ' '.join(related_queries), seed_ids=seed_ids)
        cached_market = pd.DataFrame()
        if reusable:
            self._emit(progress, '시장 근거 재사용', f'이미 수집된 영상 ID {len(reusable)}개로 우선 확인하는 중')
            cached_market = self.youtube.market_map_from_video_ids(reusable, discovery_label='SAVED_COMPARISON_EVIDENCE')
            if not cached_market.empty:
                cached_market['시장범위'] = 'reused_market'
                cached_market['발견출처'] = 'saved_comparison'
        # 4+ relevant existing rows are enough to avoid an unnecessary search.
        # When not enough, try fresh search; quota errors must not erase reused data.
        if len(cached_market) >= 4:
            search_raw = pd.DataFrame()
            self._emit(progress, '검색 호출 절약', '기존 관련 영상 근거로 먼저 조사합니다 · YouTube 검색 추가 호출 없음')
        else:
            self._emit(progress, '시장 탐색', f'기존 근거 {len(cached_market)}개 · 부족한 검색축만 추가 확인')
            search_raw = self._collect_market_map(related_queries, max_per_duration=15)
        if getattr(self.youtube, 'search_quota_blocked', False):
            self._emit(progress, '검색 할당량 제한', '추가 검색을 중단하고 수집된 영상·선택 근거로 제한적 조사를 이어갑니다')
        if not search_raw.empty:
            self._emit(progress, "시장 탐색", "검색 결과의 Channel Outlier / Subscriber / Recent 신호를 계산하는 중")
            search_market = self.youtube.attach_channel_metrics(search_raw)
            search_market["시장범위"] = "search"
            search_market["발견출처"] = "search"
        else:
            search_market = pd.DataFrame()

        # User-selected audience/global reference channels are a second source, not a hidden hardcoded list.
        if hasattr(self, "last_reference_markets"):
            ref_domestic = self.last_reference_markets.get("domestic", pd.DataFrame())
            ref_global = self.last_reference_markets.get("global", pd.DataFrame())
            reference_diagnostics = getattr(self, "last_reference_diagnostics", {})
        else:
            ref_domestic, ref_global, reference_diagnostics = self._scan_manual_reference_markets(progress=progress)
        ref_domestic = self._reference_filter_by_queries(ref_domestic, related_queries, max_rows=18)
        ref_global = self._reference_filter_by_queries(ref_global, related_queries, max_rows=18)

        # Preserve seed evidence from the recommendation that led here.
        seed_ids = []
        if idea_brief:
            seed_ids = [str(x) for x in (idea_brief.get("시장근거video_ids") or idea_brief.get("seed_video_ids") or []) if str(x).strip()]
        known_pool = self._merge_market_maps(ref_domestic, ref_global, cached_market, search_market)
        missing_seed_ids = [v for v in seed_ids if known_pool.empty or v not in set(known_pool.get("video_id", pd.Series(dtype=str)).astype(str).tolist())]
        seed_market = pd.DataFrame()
        if missing_seed_ids:
            explicit = self.youtube.market_map_from_video_ids(missing_seed_ids, discovery_label="SELECTED_SEED")
            if not explicit.empty:
                seed_market = self.youtube.attach_channel_metrics(explicit)
                seed_market["시장범위"] = "selected_seed"
                seed_market["발견출처"] = "selected_seed"

        market_df = self._merge_market_maps(ref_domestic, ref_global, seed_market, cached_market, search_market)
        if market_df.empty:
            if getattr(self.youtube, 'search_quota_blocked', False):
                self._emit(progress, '조사 보류', '검색 한도 소진 · 확인 가능한 관련 영상이 없어 결과를 꾸며내지 않습니다')
                return {'query':query, 'search_queries':related_queries, 'idea_brief':idea_brief,
                        'research_ready':False, 'research_limitation':'SEARCH_QUOTA_NO_REUSABLE_EVIDENCE',
                        'market_df':pd.DataFrame(), 'candidate_df':pd.DataFrame(),
                        'analysis_df':pd.DataFrame(), 'comments_df':pd.DataFrame(),
                        'transcript_df':pd.DataFrame(), 'segments_df':pd.DataFrame(),
                        'transcript_coverage':{'total':0,'success':0,'ready':False,'ratio':0,'blocked':False},
                        'reference_diagnostics':reference_diagnostics,
                        'video_analysis_df':pd.DataFrame(), 'content_patterns':[], 'pattern_observations':[],
                        'market_result':{}, 'opportunity_df':pd.DataFrame(), 'gap_df':pd.DataFrame(),
                        'content_candidates':[]}
            raise RuntimeError(f"'{query}' 관련 시장 후보를 찾지 못했습니다. 참고 채널 또는 검색축을 확인해주세요.")

        for field in ('채널배수', '조회수_구독자배수'):
            if field not in market_df.columns:
                market_df[field] = float('nan')
        if '최근브레이크아웃' not in market_df.columns:
            market_df['최근브레이크아웃'] = False
        candidate_df = self.youtube.select_research_candidates(market_df, top_n=6)
        if seed_ids:
            seed_rows = market_df[market_df["video_id"].astype(str).isin(seed_ids)].copy()
            if not seed_rows.empty:
                if "선정이유" not in seed_rows.columns:
                    seed_rows["선정이유"] = "Selected Seed"
                else:
                    seed_rows["선정이유"] = seed_rows["선정이유"].fillna("").astype(str).replace("", "Selected Seed")
                if "선정이유_목록" not in seed_rows.columns:
                    seed_rows["선정이유_목록"] = [["Selected Seed"] for _ in range(len(seed_rows))]
                candidate_df = self._merge_market_maps(seed_rows, candidate_df)
        if candidate_df.empty:
            raise RuntimeError("정밀 분석 후보가 0개입니다.")
        candidate_df = candidate_df.head(14).reset_index(drop=True)

        self._emit(progress, "시장 근거", f"후보 {len(candidate_df)}개의 댓글과 Transcript를 수집하는 중")
        analysis_df, comments_df, transcript_df, segments_df = self.evidence.collect_market_evidence(candidate_df)
        coverage = self._transcript_coverage(transcript_df, len(candidate_df))
        pct = round(coverage["ratio"] * 100)
        self._emit(progress, "Research Coverage", f"시장 후보 {coverage['total']}개 · Transcript {coverage['success']}개 ({pct}%) 확보")

        base_result = {
            "query": query,
            "search_queries": related_queries,
            "idea_brief": idea_brief,
            "market_df": market_df,
            "candidate_df": candidate_df,
            "analysis_df": analysis_df,
            "comments_df": comments_df,
            "transcript_df": transcript_df,
            "segments_df": segments_df,
            "transcript_coverage": coverage,
            "reference_diagnostics": reference_diagnostics,
            "research_ready": bool(coverage["ready"]),
            "video_analysis_df": pd.DataFrame(),
            "content_patterns": [],
            "pattern_observations": [],
            "market_result": {},
            "opportunity_df": pd.DataFrame(),
            "gap_df": pd.DataFrame(),
            "content_candidates": [],
        }
        if not coverage["ready"]:
            detail = (
                f"Transcript {coverage['success']}/{coverage['total']}개. "
                f"최소 {self.settings.market_transcript_min_count}개이면서 {int(self.settings.market_transcript_min_ratio*100)}% 이상이 필요합니다."
            )
            if coverage["blocked"]:
                detail += " IP 차단이 감지되어 이번 실행의 추가 Transcript 요청을 중단했습니다."
            self._emit(progress, "Deep Research 중단", detail)
            return base_result

        # Deep analysis is strictly transcript-backed.
        transcript_ids = set(transcript_df.loc[transcript_df["대본상태"].eq("성공"), "video_id"].astype(str).tolist())
        transcript_analysis_df = analysis_df[analysis_df["video_id"].astype(str).isin(transcript_ids)].copy()
        self._emit(progress, "시장 분석", f"Transcript 확보 영상 {len(transcript_analysis_df)}개의 설명 방식·반응·Content DNA를 분석하는 중")
        video_analysis_df = self.llm.analyze_videos(transcript_analysis_df)

        # Bring provenance back onto the LLM-derived DNA rows.
        prov_cols = [c for c in ["video_id", "채널", "시장범위", "발견출처", "seed_role", "reference_language", "reference_country"] if c in candidate_df.columns]
        if prov_cols and not video_analysis_df.empty:
            video_analysis_df = video_analysis_df.merge(candidate_df[prov_cols].drop_duplicates("video_id"), on="video_id", how="left")

        self._emit(progress, "콘텐츠 패턴", "고정 분류가 아니라 Content DNA에서 시장 구조 클러스터를 발견하는 중")
        pattern_result, _, _ = self.llm.discover_content_patterns(video_analysis_df, evidence_df=candidate_df)
        content_patterns = pattern_result.get("클러스터", [])
        pattern_observations = pattern_result.get("관찰메모", [])
        dna_records = video_analysis_df[["video_id", "제목", "콘텐츠DNA"]].to_dict("records") if not video_analysis_df.empty else []
        self.pattern_memory.ingest_run(query, content_patterns, dna_records, coverage=coverage)

        self._emit(progress, "시장 분석", "국내/해외 Transcript의 반복 설명·미해결 문제·Global Transfer 가능성을 종합하는 중")
        market_result, _, _ = self.llm.synthesize_market(video_analysis_df)
        market_result["발견된콘텐츠패턴"] = content_patterns

        self._emit(progress, "채널 공백", "Transcript 기반 시장 기회와 내 기존 콘텐츠를 Hybrid Retrieval로 비교하는 중")
        opportunity_df, gap_df = self.llm.analyze_opportunities(market_result, self.my_chunks_df)

        self._emit(progress, "콘텐츠 설계", "Knowledge/Format/Global Gap → Audience → 내 방식 → Edge → 전략으로 후보 TOP 3를 만드는 중")
        memory_context = self.memory.prompt_context(query, limit=24)
        pattern_context = self.pattern_memory.prompt_context(limit=16)
        content_candidates, _, _ = self.llm.plan_content(
            opportunity_df,
            gap_df,
            self.my_catalog_df,
            idea_brief=idea_brief,
            memory_context=memory_context,
            market_evidence_df=candidate_df,
            market_result=market_result,
            pattern_context=pattern_context,
            studio_context=self.manual_data.studio_context(max_rows=30),
        )
        content_candidates = self._attach_grounded_evidence(content_candidates, candidate_df)

        base_result.update({
            "video_analysis_df": video_analysis_df,
            "content_patterns": content_patterns,
            "pattern_observations": pattern_observations,
            "market_result": market_result,
            "opportunity_df": opportunity_df,
            "gap_df": gap_df,
            "content_candidates": content_candidates,
            "research_ready": True,
        })
        return base_result

    def consult(self, user_input: str, progress: ProgressFn = None):
        """자유 입력 하나를 추천 또는 주제/아이디어 연구로 라우팅한다."""
        interpreted = self.interpret_input(user_input, progress=progress)
        brief = interpreted["brief"]
        if brief["입력유형"] == "다음콘텐츠추천":
            return {"kind": "recommendations", "brief": brief, "recommendations": self.recommend_home(progress=progress)}

        query = brief.get("주검색어") or brief.get("주제") or user_input
        research = self.research_topic(query, progress=progress, idea_brief=brief)
        return {"kind": "research", "brief": brief, "research": research}

    def build_candidate_package(self, research_result: dict, selected_content_index: int, progress: ProgressFn = None):
        """Selected direction -> transcript-grounded atoms/edge/structure. No metadata-only substitution."""
        if not research_result.get("research_ready", False):
            raise RuntimeError("시장 Transcript Coverage가 기준에 미달해 Draft를 만들 수 없습니다. Transcript를 확보한 뒤 Deep Research를 다시 실행하세요.")
        candidates = research_result["content_candidates"]
        if selected_content_index not in range(len(candidates)):
            raise ValueError(f"selected_content_index는 0~{len(candidates)-1} 범위여야 합니다.")

        selected_candidate = candidates[selected_content_index]
        analysis_df = research_result["analysis_df"]
        video_analysis_df = research_result["video_analysis_df"]
        idea_brief = research_result.get("idea_brief")

        market_content_df = analysis_df[["video_id", "제목", "전체대본", "대본상태"]].copy()
        valid_mask = market_content_df["대본상태"].eq("성공") & market_content_df["전체대본"].fillna("").astype(str).str.strip().str.len().ge(100)
        market_content_df = market_content_df[valid_mask].copy()
        if market_content_df.empty:
            raise RuntimeError("Transcript 기반 시장 Chunk가 0개입니다. 이번 Draft는 생성하지 않습니다.")

        self._emit(progress, "Focused Research", f"Transcript {market_content_df['video_id'].nunique()}개를 Chunk + Embedding으로 인덱싱하는 중")
        market_chunks_df = self.retrieval.build_index(market_content_df[["video_id", "제목", "전체대본"]], prefix="market")

        structure_query = "\n".join([
            selected_candidate["주제"],
            selected_candidate.get("타깃문제", ""),
            selected_candidate.get("핵심약속", ""),
            selected_candidate.get("가르칠영어지식", ""),
            *(idea_brief.get("리서치질문", []) if idea_brief else []),
        ])

        self._emit(progress, "Focused Research", "시장/내 콘텐츠에서 관련 원자료를 다양하게 다시 찾는 중")
        market_sources = self.retrieval.hybrid_retrieve_diverse(market_chunks_df, structure_query, top_k=24, max_per_video=2)
        if market_sources.empty:
            raise RuntimeError("Transcript는 확보했지만 선택 아이디어와 관련된 시장 Chunk를 검색하지 못했습니다.")
        my_sources = self.retrieval.hybrid_retrieve_diverse(self.my_chunks_df, structure_query, top_k=10, max_per_video=2)
        relevant_ids = market_sources["video_id"].drop_duplicates().astype(str).tolist()
        relevant_market_analysis = video_analysis_df[video_analysis_df["video_id"].astype(str).isin(relevant_ids)].copy()

        related_memory = self.memory.prompt_context(structure_query, limit=24)
        pattern_context = self.pattern_memory.prompt_context(limit=16)
        self._emit(progress, "설명/Edge 설계", "Transcript 원자를 비교해 특이점·겹침·충돌·빈틈과 Core Edge를 설계하는 중")
        design_pack, _, _ = self.llm.build_content_design_pack(
            selected_candidate,
            market_sources,
            my_sources,
            relevant_market_analysis,
            idea_brief=idea_brief,
            memory_context=related_memory,
            pattern_context=pattern_context,
        )

        memory_ingest = self.memory.ingest_design_pack(
            topic=selected_candidate.get("주제", research_result.get("query", "")),
            design_pack=design_pack,
            source_context=f"research:{research_result.get('query', '')}",
        )

        self._emit(progress, "Structure", "Core Edge·선행관계·보상 흐름을 반영한 영상 구조를 설계하는 중")
        structure_result, _, _ = self.llm.build_structure(
            selected_candidate,
            market_sources,
            my_sources,
            relevant_market_analysis,
            design_pack,
            idea_brief=idea_brief,
        )

        return {
            "selected_content_index": selected_content_index,
            "selected_candidate": selected_candidate,
            "structure_query": structure_query,
            "market_sources": market_sources,
            "my_sources": my_sources,
            "relevant_market_analysis": relevant_market_analysis,
            "design_pack": design_pack,
            "structure_result": structure_result,
            "idea_brief": idea_brief,
            "related_memory": related_memory,
            "pattern_context": pattern_context,
            "studio_context": self.manual_data.studio_context(max_rows=30),
            "memory_ingest": memory_ingest,
            "transcript_coverage": research_result.get("transcript_coverage", {}),
            "market_audit": build_market_audit(
                research_result.get("candidate_df"), research_result.get("transcript_df"),
                selected_candidate.get("주제", ""),
            ),
        }

    def review_topic_before_draft(self, research_result: dict, selected_content_index: int,
                                  progress: ProgressFn = None):
        """Optional market-grounded topic gate before spending tokens on Draft A."""
        if not research_result.get("research_ready"):
            raise RuntimeError("자막 Coverage 부족: 시장 근거 확보 전에 주제 경쟁력 진단 불가")
        candidates = research_result.get("content_candidates") or []
        if selected_content_index not in range(len(candidates)):
            raise ValueError("주제 후보 번호가 올바르지 않습니다.")
        candidate = candidates[selected_content_index]
        market_audit = build_market_audit(
            research_result.get("candidate_df"), research_result.get("transcript_df"),
            candidate.get("주제", ""),
        )
        analysis = research_result.get("analysis_df")
        snippets = []
        if isinstance(analysis, pd.DataFrame) and not analysis.empty:
            for _, row in analysis.head(14).iterrows():
                if str(row.get("대본상태")) != "성공":
                    continue
                raw_content = row.get("전체대본")
                content = raw_content[:900] if isinstance(raw_content, str) else ""
                if content.strip():
                    snippets.append({
                        "video_id": str(row.get("video_id") or ""),
                        "제목": str(row.get("제목") or ""),
                        "텍스트": content,
                    })
        # Never pass raw competitor texts lacking provenance, personal local files, or credentials.
        package = {
            "selected_candidate": candidate,
            "market_audit": market_audit,
            "market_sources": pd.DataFrame(snippets),
            "relevant_market_analysis": research_result.get("video_analysis_df"),
            "transcript_coverage": research_result.get("transcript_coverage") or {},
        }
        self._emit(progress, "주제 경쟁력", "Hermes가 실제 경쟁 영상과 Transcript를 근거로 냉정하게 평가하는 중")
        critic = self.critic_agent.run({}, package, backend="hermes",
                                       revision_mode="rebuild", purpose="topic_only")
        verdict = parse_topic_decision(
            critic.report,
            {str(v.get("video_id")) for v in market_audit.get("경쟁영상", [])},
        )
        return {
            "verdict": verdict, "report": critic.report,
            "market_audit": market_audit,
            "web_attempted": critic.web_attempted,
            "web_completed": critic.web_completed,
            "tool_trace": critic.tool_trace,
            "warning": critic.warning,
        }

    def write_draft_a(self, candidate_package: dict, progress: ProgressFn = None):
        self._emit(progress, "Draft A", "Structure와 설명 원자/보상 설계를 바탕으로 촬영 가능한 초안을 작성하는 중")
        result, usage, cached = self.llm.write_script(
            candidate_package["selected_candidate"],
            candidate_package["structure_result"],
            candidate_package["design_pack"],
            candidate_package["my_sources"],
            idea_brief=candidate_package.get("idea_brief"),
        )
        return {"script": result, "usage": usage, "cached": cached}

    def revise_draft_a(self, draft_a: dict, feedback: str, progress: ProgressFn = None):
        if not str(feedback or "").strip():
            return None
        self._emit(progress, "Draft A 수정", "내 피드백을 반영하는 중")
        result, usage, cached = self.llm.revise_script(draft_a, feedback)
        return {"result": result, "usage": usage, "cached": cached}

    def build_draft_b(self, draft_a: dict, candidate_package: dict, progress: ProgressFn = None,
                      critic_backend: str | None = None, revision_mode: str = "polish", benchmark_reference: dict | None = None):
        if revision_mode not in {"polish", "rebuild"}:
            raise ValueError("Unknown revision mode")
        self._emit(progress, "Critic Agent", "Draft A를 진단하고 필요한 검증 질문을 스스로 고르는 중")
        critic = self.critic_agent.run(draft_a, candidate_package, backend=critic_backend, revision_mode=revision_mode,
                                       benchmark_reference=benchmark_reference)
        if critic.warning:
            self._emit(progress, "Critic Agent", critic.warning)
        if critic.web_used:
            self._emit(progress, "Critic Agent", f"외부 웹 근거 {len(critic.sources)}개를 확인하고 Draft B 수정 명세를 만드는 중")
        else:
            self._emit(progress, "Critic Agent", "내부 Research/Transcript 근거를 중심으로 Draft B 수정 명세를 만드는 중")

        self._emit(progress, "Draft B", "Critic Report와 기존 Research를 함께 반영해 전체 대본을 다시 쓰는 중")
        draft_b, usage_b, cached_b = self.llm.write_draft_b(
            draft_a, critic.report, critic.sources, candidate_package, revision_mode=revision_mode,
            benchmark_reference=benchmark_reference
        )
        self._emit(progress, "A/B 비교", "Draft A와 B의 실제 차이를 편견 없이 비교하는 중")
        comparison, usage_c, cached_c = self.llm.compare_drafts(draft_a, draft_b, critic.report)
        audit = candidate_package.get("market_audit") or {}
        decision = parse_topic_decision(
            critic.report,
            {str(v.get("video_id")) for v in audit.get("경쟁영상", [])},
        ) if revision_mode == "rebuild" else {"valid": False, "error": "정교화 모드에는 주제 판단 없음"}
        return {
            "revision_mode": revision_mode,
            "benchmark_reference": benchmark_reference or None,
            "critic_report": critic.report,
            "critic_sources": critic.sources,
            "critic_model": critic.model,
            "critic_web_enabled": critic.web_enabled,
            "critic_web_used": critic.web_used,
            "critic_warning": critic.warning,
            "critic_usage": critic.usage,
            "critic_tool_trace": critic.tool_trace,
            "critic_web_attempted": critic.web_attempted,
            "critic_web_completed": critic.web_completed,
            "market_audit": audit,
            "topic_decision": decision,
            "draft_b": draft_b,
            "draft_b_usage": usage_b,
            "draft_b_cached": cached_b,
            "comparison": comparison,
            "comparison_usage": usage_c,
            "comparison_cached": cached_c,
        }

    def finalize_from_draft_b(self, draft_b: dict, feedback: str, progress: ProgressFn = None):
        if not str(feedback or "").strip():
            return None
        self._emit(progress, "Final Script", "Draft B에 사람 피드백을 반영해 최종 촬영본을 만드는 중")
        result, usage, cached = self.llm.revise_script(draft_b, feedback)
        return {"result": result, "usage": usage, "cached": cached}
