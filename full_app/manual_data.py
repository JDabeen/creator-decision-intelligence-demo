from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


REFERENCE_CHANNEL_COLUMNS = [
    "enabled",
    "role",
    "channel_name",
    "channel_ref",
    "channel_url",
    "language",
    "country",
    "source",
    "priority",
    "audience_overlap_note",
    "notes",
    "added_at",
]

MY_VIDEO_PERFORMANCE_COLUMNS = [
    "video_id",
    "title",
    "published_at",
    "measurement_day",
    "measurement_date",
    "views",
    "unique_viewers",
    "impressions",
    "ctr_pct",
    "avg_view_duration_sec",
    "avg_percentage_viewed_pct",
    "watch_time_hours",
    "subscribers_gained",
    "browse_pct",
    "suggested_pct",
    "search_pct",
    "recent_10_rank",
    "leads_count",
    "revenue_krw",
    "notes",
]

SUGGESTED_NEIGHBOR_COLUMNS = [
    "my_video_id",
    "my_video_title",
    "measurement_date",
    "source_video_id",
    "source_video_title",
    "source_channel_name",
    "source_channel_ref",
    "source_channel_subscribers",
    "source_channel_typical_views",
    "source_video_views",
    "suggested_traffic_share_pct",
    "language",
    "country",
    "notes",
]

AUDIENCE_SNAPSHOT_COLUMNS = [
    "snapshot_date",
    "watchtime_unsubscribed_pct",
    "watchtime_subscribed_pct",
    "male_pct",
    "female_pct",
    "age_18_24_pct",
    "age_25_34_pct",
    "age_35_44_pct",
    "age_45_54_pct",
    "age_55_64_pct",
    "age_65_plus_pct",
    "korea_pct",
    "us_pct",
    "mobile_pct",
    "computer_pct",
    "tv_pct",
    "tablet_pct",
    "notes",
]

HYPOTHESIS_COLUMNS = [
    "hypothesis_id",
    "statement",
    "status",
    "evidence_for",
    "evidence_against",
    "confidence_note",
    "updated_at",
    "notes",
]

CONTENT_DECISION_COLUMNS = [
    "created_at",
    "topic",
    "decision",
    "reason",
    "content_role",
    "published_video_id",
    "notes",
]

SCHEMAS = {
    "reference_channels": REFERENCE_CHANNEL_COLUMNS,
    "my_video_performance": MY_VIDEO_PERFORMANCE_COLUMNS,
    "suggested_neighbors": SUGGESTED_NEIGHBOR_COLUMNS,
    "audience_snapshots": AUDIENCE_SNAPSHOT_COLUMNS,
    "hypotheses": HYPOTHESIS_COLUMNS,
    "content_decisions": CONTENT_DECISION_COLUMNS,
}

ROLE_HELP = {
    "audience_neighbor": "YouTube Studio의 '내 시청자가 보는 다른 채널'. Pulling 주제 발견의 1차 시장 이웃.",
    "korean_reference": "운영자가 직접 추가한 한국어 영어교육/경쟁 참고 채널.",
    "global_reference": "해외 영어교육 참고 채널. 주제·지식·설명법·포맷의 Global Transfer 후보를 찾는 용도.",
    "observed_suggested_source": "내 영상이 실제로 추천된 옆자리에서 관찰된 채널. suggested_neighbors 데이터에서 자동 파생될 수 있음.",
}


class ManualDataStore:
    """사용자가 Studio에서 틈틈이 넣는 수동 데이터의 영구 저장소.

    파일은 앱 코드와 분리된 data_root/manual 아래에 둔다. 앱 버전을 갈아도 남는다.
    CSV를 직접 편집해도 되고 Streamlit data_editor를 통해 저장해도 된다.
    """

    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root).expanduser()
        self.root = self.data_root / "manual"
        self.root.mkdir(parents=True, exist_ok=True)
        self.ensure_templates()

    def path(self, name: str) -> Path:
        if name not in SCHEMAS:
            raise KeyError(name)
        return self.root / f"{name}.csv"

    def ensure_templates(self):
        for name, columns in SCHEMAS.items():
            path = self.path(name)
            if not path.exists():
                pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")
        readme = self.root / "README_DATA_INPUT.md"
        if not readme.exists():
            readme.write_text(self._readme_text(), encoding="utf-8")

    def _readme_text(self) -> str:
        roles = "\n".join(f"- `{k}`: {v}" for k, v in ROLE_HELP.items())
        return f"""# YouTube Content Consultant · 수동 데이터 입력 폴더

이 폴더는 **앱 코드와 분리된 영구 데이터**입니다. 새 버전을 받아도 지우지 마세요.
CSV는 Excel/Google Sheets/메모장으로 직접 수정하거나 앱의 `데이터 입력 · Studio` 화면에서 수정할 수 있습니다.

## 1. reference_channels.csv
`channel_ref`에 `@handle`, YouTube 채널 URL, 채널 ID(UC...) 중 하나를 넣으면 됩니다.

role:
{roles}

추천 시작점은 `audience_neighbor` 5~10개입니다. Studio → 분석 → 시청자층 → 내 시청자가 보는 다른 채널을 보고 직접 추가하세요.
해외 채널은 `global_reference`로 추가하면 한국 시장과 별도로 Global Transfer 후보를 찾습니다.

## 2. my_video_performance.csv
내 영상의 7일/28일/현재 성과를 틈날 때 넣습니다. 같은 video_id를 여러 행으로 기록해도 됩니다.
- measurement_day: 7 / 28 / current
- impressions, ctr_pct, avg_percentage_viewed_pct, unique_viewers, recent_10_rank 등
- leads_count: 단톡방/문의/리드 수처럼 실제 사업 성과가 있으면 기록

## 3. suggested_neighbors.csv
내 영상이 **어떤 영상 옆 추천 동영상으로 붙었는지** 기록합니다.
가능하면 source_channel_ref도 넣으세요. 이 채널은 다음 Pulling 탐색에서 실제 Audience Neighborhood 신호로 재사용할 수 있습니다.

## 4. audience_snapshots.csv
채널 전체 Audience 수치를 날짜별로 적습니다. 연령과 영어 수준은 동일시하지 않습니다.

## 5. hypotheses.csv
전략 가설은 하드코딩 규칙이 아니라 검증 중인 가설로 저장합니다.
예: `어순 재탕은 자기잠식할 수 있다`, `방법 무효화형 제목이 더 강할 수 있다`.

## 6. content_decisions.csv
추천을 채택/보류/거절한 이유를 남길 때 씁니다. 나중에 사용자 선택 자체를 학습 데이터로 쓸 수 있습니다.

중요: 비어 있는 값은 모르는 값입니다. 0으로 추정해서 넣지 마세요.
"""

    def read(self, name: str) -> pd.DataFrame:
        path = self.path(name)
        columns = SCHEMAS[name]
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
        except Exception:
            df = pd.DataFrame(columns=columns)
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df[columns].copy()

    def write(self, name: str, df: pd.DataFrame) -> Path:
        columns = SCHEMAS[name]
        work = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
        for col in columns:
            if col not in work.columns:
                work[col] = None
        work = work[columns]
        path = self.path(name)
        work.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    @staticmethod
    def _truthy(value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "사용", "활성"}

    def reference_channels(self, roles: Iterable[str] | None = None, enabled_only: bool = True) -> pd.DataFrame:
        df = self.read("reference_channels")
        if df.empty:
            return df
        if enabled_only:
            def enabled_value(v):
                if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
                    return True
                return self._truthy(v)
            df = df[df["enabled"].apply(enabled_value)]
        if roles:
            role_set = {str(x) for x in roles}
            df = df[df["role"].astype(str).isin(role_set)]
        return df.reset_index(drop=True)

    def derived_suggested_source_channels(self) -> pd.DataFrame:
        src = self.read("suggested_neighbors")
        if src.empty:
            return pd.DataFrame(columns=REFERENCE_CHANNEL_COLUMNS)
        src = src[src["source_channel_ref"].fillna("").astype(str).str.strip().ne("")].copy()
        if src.empty:
            return pd.DataFrame(columns=REFERENCE_CHANNEL_COLUMNS)
        rows = []
        for ref, group in src.groupby(src["source_channel_ref"].astype(str).str.strip()):
            latest = group.iloc[-1]
            rows.append({
                "enabled": True,
                "role": "observed_suggested_source",
                "channel_name": latest.get("source_channel_name", ""),
                "channel_ref": ref,
                "channel_url": "",
                "language": latest.get("language", "ko"),
                "country": latest.get("country", ""),
                "source": "suggested_neighbors",
                "priority": 1,
                "audience_overlap_note": "내 영상의 실제 추천 옆자리에서 관찰됨",
                "notes": latest.get("notes", ""),
                "added_at": latest.get("measurement_date", ""),
            })
        return pd.DataFrame(rows, columns=REFERENCE_CHANNEL_COLUMNS)

    def effective_domestic_reference_channels(self) -> pd.DataFrame:
        explicit = self.reference_channels(["audience_neighbor", "korean_reference"], enabled_only=True)
        derived = self.derived_suggested_source_channels()
        combined = pd.concat([explicit, derived], ignore_index=True) if not derived.empty else explicit.copy()
        if combined.empty:
            return combined
        combined["_key"] = combined["channel_ref"].fillna("").astype(str).str.strip().str.lower()
        combined = combined[combined["_key"].ne("")].drop_duplicates("_key").drop(columns="_key")
        return combined.reset_index(drop=True)

    def global_reference_channels(self) -> pd.DataFrame:
        return self.reference_channels(["global_reference"], enabled_only=True)

    def latest_audience_snapshot(self) -> dict:
        df = self.read("audience_snapshots")
        if df.empty:
            return {}
        work = df.copy()
        work["_dt"] = pd.to_datetime(work["snapshot_date"], errors="coerce")
        work = work.sort_values("_dt")
        row = work.iloc[-1].drop(labels=["_dt"]).to_dict()
        return {k: v for k, v in row.items() if pd.notna(v) and str(v).strip() != ""}

    def latest_my_video_performance(self) -> pd.DataFrame:
        df = self.read("my_video_performance")
        if df.empty:
            return df
        work = df.copy()
        work["_dt"] = pd.to_datetime(work["measurement_date"], errors="coerce")
        work["_row"] = range(len(work))
        # video_id가 없으면 title을 fallback key로 사용한다.
        work["_key"] = work["video_id"].fillna("").astype(str).str.strip()
        missing = work["_key"].eq("")
        work.loc[missing, "_key"] = "title:" + work.loc[missing, "title"].fillna("").astype(str).str.strip().str.lower()
        work = work[work["_key"].ne("title:")]
        if work.empty:
            return df.head(0)
        work = work.sort_values(["_dt", "_row"]).groupby("_key", as_index=False).tail(1)
        return work.drop(columns=["_dt", "_row", "_key"]).reset_index(drop=True)

    def merge_performance_into_catalog(self, catalog_df: pd.DataFrame) -> pd.DataFrame:
        if catalog_df is None or catalog_df.empty:
            return catalog_df
        perf = self.latest_my_video_performance()
        if perf.empty:
            return catalog_df.copy()
        out = catalog_df.copy()
        # ID 우선 병합
        by_id = perf[perf["video_id"].fillna("").astype(str).str.strip().ne("")].copy()
        if not by_id.empty and "video_id" in out.columns:
            rename = {c: f"studio_{c}" for c in by_id.columns if c not in {"video_id", "title"}}
            by_id = by_id.rename(columns=rename)
            out = out.merge(by_id.drop(columns=["title"], errors="ignore"), on="video_id", how="left")
        # ID가 없었던 행은 제목 기반으로 채움
        by_title = perf[perf["video_id"].fillna("").astype(str).str.strip().eq("") & perf["title"].fillna("").astype(str).str.strip().ne("")].copy()
        if not by_title.empty:
            title_map = {str(r["title"]).strip().lower(): r for _, r in by_title.iterrows()}
            for idx, row in out.iterrows():
                key = str(row.get("제목", "")).strip().lower()
                src = title_map.get(key)
                if src is None:
                    continue
                for col in MY_VIDEO_PERFORMANCE_COLUMNS:
                    if col in {"video_id", "title"}:
                        continue
                    dest = f"studio_{col}"
                    if dest not in out.columns:
                        out[dest] = None
                    if pd.isna(out.at[idx, dest]) or str(out.at[idx, dest]).strip() == "":
                        out.at[idx, dest] = src.get(col)
        return out

    def hypotheses(self) -> list[dict]:
        df = self.read("hypotheses")
        if df.empty:
            return []
        records = []
        for row in df.to_dict("records"):
            cleaned = {k: v for k, v in row.items() if pd.notna(v) and str(v).strip() != ""}
            if cleaned.get("statement"):
                records.append(cleaned)
        return records[-30:]

    def performance_diagnostics(self) -> list[dict]:
        """Conservative post-publish diagnosis from manually entered Studio metrics.

        These are hypotheses, not causal proof. The rules intentionally avoid the old
        'CTR is fine -> throw away the topic' shortcut.
        """
        df = self.latest_my_video_performance()
        if df.empty:
            return []
        out = []
        for row in df.to_dict("records"):
            title = row.get("title") or row.get("video_id") or "영상"
            def num(key):
                try:
                    v = row.get(key)
                    return None if v is None or pd.isna(v) or str(v).strip() == "" else float(v)
                except Exception:
                    return None
            rank = num("recent_10_rank")
            ctr = num("ctr_pct")
            retention = num("avg_percentage_viewed_pct")
            impressions = num("impressions")
            signals, unknown = [], []
            if rank is not None and rank <= 3:
                signals.append("최근 10개 중 1~3위: 이 주제/패키지 조합은 후속 검토 가치가 큼")
            if ctr is not None and ctr < 5:
                signals.append("CTR 5% 미만: 제목·썸네일/약속 정합성 문제 가능성")
            if ctr is not None and ctr >= 5 and retention is not None and retention < 38:
                signals.append("CTR은 버티지만 지속률이 낮음: 도입·전개·본문 payoff 점검 우선")
            if rank is not None and rank > 3 and ctr is not None and ctr >= 5 and (retention is None or retention >= 38):
                signals.append("클릭/내용 신호가 크게 나쁘지 않은데 순위가 낮음: 주제 수요·경쟁·초기 audience matching 등 원인 분리 필요")
                unknown.append("이 데이터만으로 주제를 버리면 안 됨")
            if impressions is None:
                unknown.append("노출 데이터 없음")
            out.append({
                "video_id": row.get("video_id", ""),
                "title": title,
                "measurement_day": row.get("measurement_day", ""),
                "signals": signals,
                "unknown": unknown,
            })
        return out

    def studio_context(self, max_rows: int = 20) -> dict:
        perf = self.latest_my_video_performance()
        neigh = self.read("suggested_neighbors")
        refs = self.reference_channels(enabled_only=True)
        return {
            "latest_audience_snapshot": self.latest_audience_snapshot(),
            "latest_video_performance": perf.tail(max_rows).to_dict("records") if not perf.empty else [],
            "suggested_neighbors": neigh.tail(max_rows).to_dict("records") if not neigh.empty else [],
            "reference_channels": refs.tail(max_rows).to_dict("records") if not refs.empty else [],
            "strategy_hypotheses": self.hypotheses(),
            "outcome_diagnostics": self.performance_diagnostics(),
        }

    def stats(self) -> dict:
        return {name: len(self.read(name)) for name in SCHEMAS}

    def append_decision(self, topic: str, decision: str, reason: str = "", content_role: str = "", notes: str = ""):
        df = self.read("content_decisions")
        row = {
            "created_at": datetime.now().astimezone().isoformat(),
            "topic": topic,
            "decision": decision,
            "reason": reason,
            "content_role": content_role,
            "published_video_id": "",
            "notes": notes,
        }
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        self.write("content_decisions", df)
        return row
