import re
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
from research_resilience import SearchQuotaExhausted, is_search_quota_error

import pandas as pd


def duration_to_seconds(duration):
    hours = re.search(r"(\d+)H", duration)
    minutes = re.search(r"(\d+)M", duration)
    seconds = re.search(r"(\d+)S", duration)
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0
    return h * 3600 + m * 60 + s


def seconds_to_text(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}시간 {minutes}분 {secs}초" if hours else f"{minutes}분 {secs}초"


def safe_duration_seconds(video):
    """Return a video's duration in seconds, or None when YouTube omits it.

    Some historical/live/unavailable videos can be returned without
    contentDetails.duration. Those rows should not crash an entire research run.
    """
    content = video.get("contentDetails") or {}
    duration = content.get("duration")
    if not duration:
        return None
    try:
        return duration_to_seconds(duration)
    except (TypeError, ValueError, AttributeError):
        return None


class YouTubeResearchTools:
    def __init__(self, youtube_client, settings, search_cache_root=None):
        self.youtube = youtube_client
        self.settings = settings
        self.search_quota_blocked = False
        self.search_cache_root = Path(search_cache_root) if search_cache_root else None
        if self.search_cache_root:
            self.search_cache_root.mkdir(parents=True, exist_ok=True)

    def _cached_ids(self, kwargs):
        if not self.search_cache_root:
            return None, None
        fingerprint = hashlib.sha256(json.dumps(kwargs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = self.search_cache_root / (fingerprint + '.json')
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            observed = datetime.fromisoformat(value['observed_utc'])
            age = (datetime.now(timezone.utc) - observed).total_seconds()
            if 0 <= age < 24*3600 and isinstance(value.get('ids'), list):
                return path, [x for x in value['ids'] if isinstance(x, str)]
        except (OSError, ValueError, TypeError, KeyError):
            pass
        return path, None

    def fetch_video_details(self, video_ids):
        details = []
        ids = list(dict.fromkeys(video_ids))
        for i in range(0, len(ids), 50):
            batch = ids[i : i + 50]
            if not batch:
                continue
            response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics", id=",".join(batch)
            ).execute()
            details.extend(response.get("items", []))
        return details

    def search_video_ids(self, query, max_per_duration=50, order="relevance", published_after=None):
        ids = []
        for duration in ["medium", "long"]:
            kwargs = dict(
                part="snippet",
                q=query,
                type="video",
                videoDuration=duration,
                maxResults=max_per_duration,
                order=order,
            )
            if published_after:
                kwargs["publishedAfter"] = published_after
            cache_path, cached = self._cached_ids(kwargs)
            if cached is not None:
                fresh = cached
            else:
                if self.search_quota_blocked:
                    if ids:
                        break  # continue with cached medium-duration videos
                    raise SearchQuotaExhausted('YouTube search quota unavailable')
                try:
                    response = self.youtube.search().list(**kwargs).execute()
                except Exception as exc:
                    if is_search_quota_error(exc):
                        self.search_quota_blocked = True
                        if ids:
                            break  # keep first duration's confirmed videos
                        raise SearchQuotaExhausted('YouTube search quota exhausted') from None
                    raise
                fresh = [item.get('id', {}).get('videoId') for item in response.get('items', [])]
                if cache_path:
                    from cache import CacheManager
                    CacheManager.safe_json_dump({'observed_utc':datetime.now(timezone.utc).isoformat(),
                                                 'ids':[v for v in fresh if v]}, cache_path)
            for vid in fresh:
                if vid and vid not in ids:
                    ids.append(vid)
        return ids

    def build_market_map(self, query, max_per_duration=50, order="relevance", published_after=None):
        video_ids = self.search_video_ids(
            query,
            max_per_duration=max_per_duration,
            order=order,
            published_after=published_after,
        )
        details = self.fetch_video_details(video_ids)
        rows = []
        for video in details:
            duration_seconds = safe_duration_seconds(video)
            if duration_seconds is None:
                continue
            rows.append(
                {
                    "video_id": video["id"],
                    "제목": video["snippet"]["title"],
                    "설명": video["snippet"].get("description", ""),
                    "채널": video["snippet"]["channelTitle"],
                    "channel_id": video["snippet"]["channelId"],
                    "길이_초": duration_seconds,
                    "조회수": int(video["statistics"].get("viewCount", 0)),
                    "좋아요": int(video["statistics"].get("likeCount", 0)),
                    "댓글": int(video["statistics"].get("commentCount", 0)),
                    "업로드날짜": video["snippet"]["publishedAt"][:10],
                    "영상링크": f"https://www.youtube.com/watch?v={video['id']}",
                }
            )
        raw_df = pd.DataFrame(rows)
        if raw_df.empty:
            return raw_df

        s = self.settings
        market_df = raw_df[
            (raw_df["길이_초"] >= s.min_duration_seconds)
            & (raw_df["길이_초"] <= s.max_duration_seconds)
        ].copy()
        market_df["길이"] = market_df["길이_초"].apply(seconds_to_text)
        market_df["후보업로드일_dt"] = pd.to_datetime(market_df["업로드날짜"], utc=True)
        return market_df.reset_index(drop=True)

    def load_channel_catalog(self, handle):
        response = self.youtube.channels().list(
            part="id,snippet,contentDetails", forHandle=handle
        ).execute()
        if not response.get("items"):
            raise ValueError("채널을 찾지 못했습니다. MY_CHANNEL_HANDLE을 확인해주세요.")

        ch = response["items"][0]
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        video_ids, page_token = [], None
        while True:
            page = self.youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads,
                maxResults=50,
                pageToken=page_token,
            ).execute()
            for item in page.get("items", []):
                vid = item["contentDetails"].get("videoId")
                if vid:
                    video_ids.append(vid)
            page_token = page.get("nextPageToken")
            if not page_token:
                break

        rows = []
        for video in self.fetch_video_details(video_ids):
            dur = safe_duration_seconds(video)
            if dur is None:
                continue
            rows.append(
                {
                    "video_id": video["id"],
                    "제목": video["snippet"]["title"],
                    "설명": video["snippet"].get("description", ""),
                    "업로드날짜": video["snippet"]["publishedAt"][:10],
                    "길이_초": dur,
                    "조회수": int(video["statistics"].get("viewCount", 0)),
                    "좋아요": int(video["statistics"].get("likeCount", 0)),
                    "댓글": int(video["statistics"].get("commentCount", 0)),
                    "영상링크": f"https://www.youtube.com/watch?v={video['id']}",
                }
            )
        df = pd.DataFrame(rows)
        if not df.empty:
            s = self.settings
            df = df[
                (df["길이_초"] >= s.min_duration_seconds)
                & (df["길이_초"] <= s.max_duration_seconds)
            ].copy()
            df = df.sort_values("업로드날짜", ascending=False).reset_index(drop=True)
        return {
            "channel_id": ch["id"],
            "channel_title": ch["snippet"]["title"],
            "uploads_playlist": uploads,
            "videos": df,
        }

    def attach_channel_metrics(self, market_df):
        if market_df.empty:
            return market_df.copy()
        df = market_df.copy()
        if "후보업로드일_dt" not in df.columns:
            df["후보업로드일_dt"] = pd.to_datetime(df["업로드날짜"], utc=True)

        channel_ids = df["channel_id"].drop_duplicates().tolist()
        uploads_playlist_map, subscriber_map = {}, {}
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            response = self.youtube.channels().list(
                part="contentDetails,statistics", id=",".join(batch)
            ).execute()
            for ch in response.get("items", []):
                cid = ch["id"]
                uploads_playlist_map[cid] = ch["contentDetails"]["relatedPlaylists"]["uploads"]
                stats = ch.get("statistics", {})
                subscriber_map[cid] = None if stats.get("hiddenSubscriberCount", False) else int(stats.get("subscriberCount", 0))

        cutoff_map = {
            channel_id: group["후보업로드일_dt"].min() - pd.Timedelta(days=365)
            for channel_id, group in df.groupby("channel_id")
        }
        upload_history_rows = []
        for channel_id, playlist_id in uploads_playlist_map.items():
            cutoff = cutoff_map.get(channel_id)
            page_token = None
            while cutoff is not None:
                response = self.youtube.playlistItems().list(
                    part="contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                ).execute()
                page_dates = []
                for item in response.get("items", []):
                    vid = item["contentDetails"].get("videoId")
                    published = item["contentDetails"].get("videoPublishedAt")
                    if not vid or not published:
                        continue
                    dt = pd.to_datetime(published, utc=True)
                    page_dates.append(dt)
                    if dt >= cutoff:
                        upload_history_rows.append({"channel_id": channel_id, "video_id": vid, "published_at": dt})
                if page_dates and min(page_dates) < cutoff:
                    break
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        history_rows = []
        upload_history_df = pd.DataFrame(upload_history_rows)
        if not upload_history_df.empty:
            history_ids = upload_history_df["video_id"].drop_duplicates().tolist()
            for video in self.fetch_video_details(history_ids):
                dur = safe_duration_seconds(video)
                if dur is None:
                    continue
                if not (self.settings.min_duration_seconds <= dur <= self.settings.max_duration_seconds):
                    continue
                history_rows.append(
                    {
                        "video_id": video["id"],
                        "channel_id": video["snippet"]["channelId"],
                        "published_at": pd.to_datetime(video["snippet"]["publishedAt"], utc=True),
                        "조회수": int(video["statistics"].get("viewCount", 0)),
                    }
                )
        history_df = pd.DataFrame(history_rows)

        medians, ns, ratios, warnings = [], [], [], []
        for _, row in df.iterrows():
            candidate_date = row["후보업로드일_dt"]
            one_year_before = candidate_date - pd.Timedelta(days=365)
            if history_df.empty:
                history = pd.DataFrame()
            else:
                history = history_df[
                    (history_df["channel_id"] == row["channel_id"])
                    & (history_df["published_at"] < candidate_date)
                    & (history_df["published_at"] >= one_year_before)
                ].sort_values("published_at", ascending=False).head(30)
            n = len(history)
            if n == 0:
                med, ratio, warning = None, None, "데이터 없음"
            else:
                med = float(history["조회수"].median())
                ratio = float(row["조회수"]) / med if med > 0 else None
                warning = "표본 적음" if n < 5 else ""
            medians.append(med); ns.append(n); ratios.append(ratio); warnings.append(warning)

        df["baseline_중앙값"] = medians
        df["baseline_N"] = ns
        df["채널배수"] = ratios
        df["baseline_경고"] = warnings
        df["구독자수"] = df["channel_id"].map(subscriber_map)
        df["조회수_구독자배수"] = df.apply(
            lambda r: (r["조회수"] / r["구독자수"]) if pd.notna(r["구독자수"]) and r["구독자수"] > 0 else None,
            axis=1,
        )
        today = pd.Timestamp.now(tz="UTC")
        df["영상나이_일"] = (today - df["후보업로드일_dt"]).dt.days
        df["조회속도_일평균"] = df.apply(
            lambda r: float(r["조회수"]) / max(int(r["영상나이_일"]) + 1, 1), axis=1
        )

        s = self.settings
        def is_recent_breakout(r):
            age_value = r.get("영상나이_일", None)
            age = int(age_value) if pd.notna(age_value) else 99999
            views = int(r.get("조회수", 0) or 0)
            if age < 0 or age > s.recent_breakout_window_days or views < s.recent_breakout_min_views:
                return False
            n = int(r.get("baseline_N", 0) or 0)
            ratio = r.get("채널배수")
            sub_ratio = r.get("조회수_구독자배수")
            established = n >= 5 and pd.notna(ratio) and float(ratio) >= s.recent_breakout_min_channel_ratio
            emerging = (
                n < 5
                and pd.notna(sub_ratio)
                and float(sub_ratio) >= s.recent_breakout_min_subscriber_ratio
                and views >= max(s.recent_breakout_min_views, 10000)
            )
            strong_absolute = views >= 50000 and (
                (pd.notna(ratio) and float(ratio) >= 2.0)
                or (pd.notna(sub_ratio) and float(sub_ratio) >= 3.0)
            )
            return bool(established or emerging or strong_absolute)

        df["최근브레이크아웃"] = df.apply(is_recent_breakout, axis=1)
        return df

    def select_research_candidates(self, market_df, top_n=None):
        if market_df.empty:
            return pd.DataFrame()
        top_n = top_n or self.settings.candidates_per_signal
        reason_map, row_map = defaultdict(list), {}
        eligible = market_df[market_df["조회수"] >= self.settings.market_signal_min_views].copy()
        if eligible.empty:
            eligible = market_df.copy()
        criteria = [
            ("Absolute Winner", eligible.sort_values("조회수", ascending=False).head(top_n)),
            ("Channel Outlier", eligible[eligible["채널배수"].notna()].sort_values("채널배수", ascending=False).head(top_n)),
            ("Subscriber Breakout", eligible[eligible["조회수_구독자배수"].notna()].sort_values("조회수_구독자배수", ascending=False).head(top_n)),
        ]
        recent = market_df[market_df.get("최근브레이크아웃", False) == True].copy()
        if not recent.empty:
            sort_cols = [c for c in ["조회속도_일평균", "채널배수", "조회수_구독자배수", "조회수"] if c in recent.columns]
            recent = recent.sort_values(sort_cols, ascending=[False] * len(sort_cols)).head(top_n)
        criteria.append(("Recent Breakout", recent))

        for reason, subset in criteria:
            for _, row in subset.iterrows():
                vid = row["video_id"]
                if reason not in reason_map[vid]:
                    reason_map[vid].append(reason)
                row_map.setdefault(vid, row.to_dict())

        rows = []
        for vid, base in row_map.items():
            base = dict(base)
            reasons = reason_map[vid]
            base["선정이유_목록"] = reasons
            base["선정이유"] = " | ".join(reasons)
            base["에버그린참고"] = base.get("영상나이_일", 0) >= 365 and "Absolute Winner" in reasons
            rows.append(base)
        out = pd.DataFrame(rows)
        if not out.empty:
            out["선정기준수"] = out["선정이유_목록"].apply(len)
            out = out.sort_values(["선정기준수", "조회수"], ascending=[False, False]).reset_index(drop=True)
        return out

    def resolve_channel_reference(self, channel_ref: str):
        """Resolve @handle / UC id / YouTube channel URL / channel name to channel metadata."""
        ref = str(channel_ref or "").strip()
        if not ref:
            raise ValueError("channel_ref가 비어 있습니다.")

        channel_id = None
        handle = None
        if ref.startswith("UC") and len(ref) >= 20 and "/" not in ref:
            channel_id = ref
        else:
            m = re.search(r"youtube\.com/channel/(UC[\w-]+)", ref, flags=re.I)
            if m:
                channel_id = m.group(1)
            m = re.search(r"youtube\.com/@([\w.\-]+)", ref, flags=re.I)
            if m:
                handle = "@" + m.group(1)
            elif ref.startswith("@"):
                handle = ref

        def channel_list(**kwargs):
            return self.youtube.channels().list(
                part="id,snippet,contentDetails,statistics",
                **kwargs,
            ).execute()

        response = None
        if channel_id:
            response = channel_list(id=channel_id)
        elif handle:
            response = channel_list(forHandle=handle)

        if not response or not response.get("items"):
            # Name/custom URL fallback. This is intentionally best-effort and should be reviewed by the user.
            q = ref
            q = re.sub(r"https?://(www\.)?youtube\.com/", "", q, flags=re.I).strip("/")
            search = self.youtube.search().list(
                part="snippet",
                q=q,
                type="channel",
                maxResults=5,
                order="relevance",
            ).execute()
            items = search.get("items", [])
            if not items:
                raise ValueError(f"채널을 찾지 못했습니다: {ref}")
            candidate_id = items[0].get("id", {}).get("channelId")
            response = channel_list(id=candidate_id)

        if not response.get("items"):
            raise ValueError(f"채널을 찾지 못했습니다: {ref}")
        ch = response["items"][0]
        stats = ch.get("statistics", {})
        return {
            "channel_id": ch["id"],
            "channel_title": ch.get("snippet", {}).get("title", ""),
            "channel_description": ch.get("snippet", {}).get("description", ""),
            "uploads_playlist": ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""),
            "subscriber_count": None if stats.get("hiddenSubscriberCount", False) else int(stats.get("subscriberCount", 0) or 0),
            "channel_view_count": int(stats.get("viewCount", 0) or 0),
            "video_count": int(stats.get("videoCount", 0) or 0),
            "resolved_from": ref,
        }

    def load_reference_channel_catalog(self, channel_ref: str, months: int = 12, max_items: int = 120):
        """Load recent long-form videos for a user-selected reference channel.

        Unlike search discovery this directly scans the channel's uploads playlist, which matches
        the 'Audience Neighborhood' workflow: user chooses the neighboring channels, code scans them.
        """
        ch = self.resolve_channel_reference(channel_ref)
        uploads = ch.get("uploads_playlist")
        if not uploads:
            raise ValueError(f"업로드 playlist를 찾지 못했습니다: {channel_ref}")
        cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=max(int(months), 1))
        ids = []
        page_token = None
        stop = False
        while not stop and len(ids) < max_items:
            page = self.youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads,
                maxResults=min(50, max_items - len(ids)),
                pageToken=page_token,
            ).execute()
            dates = []
            for item in page.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                published = item.get("contentDetails", {}).get("videoPublishedAt")
                if not vid:
                    continue
                if published:
                    dt = pd.to_datetime(published, utc=True, errors="coerce")
                    if pd.notna(dt):
                        dates.append(dt)
                        if dt < cutoff:
                            stop = True
                            continue
                ids.append(vid)
                if len(ids) >= max_items:
                    break
            if dates and min(dates) < cutoff:
                stop = True
            page_token = page.get("nextPageToken")
            if not page_token:
                break

        rows = []
        for video in self.fetch_video_details(ids):
            dur = safe_duration_seconds(video)
            if dur is None or not (self.settings.min_duration_seconds <= dur <= self.settings.max_duration_seconds):
                continue
            published = pd.to_datetime(video["snippet"].get("publishedAt"), utc=True, errors="coerce")
            if pd.notna(published) and published < cutoff:
                continue
            rows.append({
                "video_id": video["id"],
                "제목": video["snippet"].get("title", ""),
                "설명": video["snippet"].get("description", ""),
                "채널": ch.get("channel_title", ""),
                "channel_id": ch.get("channel_id", ""),
                "길이_초": dur,
                "길이": seconds_to_text(dur),
                "조회수": int(video.get("statistics", {}).get("viewCount", 0) or 0),
                "좋아요": int(video.get("statistics", {}).get("likeCount", 0) or 0),
                "댓글": int(video.get("statistics", {}).get("commentCount", 0) or 0),
                "업로드날짜": video["snippet"].get("publishedAt", "")[:10],
                "후보업로드일_dt": published,
                "영상링크": f"https://www.youtube.com/watch?v={video['id']}",
                "구독자수": ch.get("subscriber_count"),
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return {**ch, "videos": df}
        df = df.sort_values("후보업로드일_dt", ascending=False).reset_index(drop=True)
        return {**ch, "videos": df}

    def attach_reference_channel_metrics(self, channel_df: pd.DataFrame):
        """Calculate channel-relative baselines using the already-loaded channel catalog.

        This avoids re-scanning the same uploads playlist once per candidate.
        Historical view snapshots are unavailable, so ratios remain retrospective approximations.
        """
        if channel_df is None or channel_df.empty:
            return pd.DataFrame()
        df = channel_df.copy()
        if "후보업로드일_dt" not in df.columns:
            df["후보업로드일_dt"] = pd.to_datetime(df["업로드날짜"], utc=True, errors="coerce")
        df = df.sort_values(["channel_id", "후보업로드일_dt"], ascending=[True, False]).reset_index(drop=True)
        today = pd.Timestamp.now(tz="UTC")
        medians, ns, ratios, warnings = [], [], [], []
        for _, row in df.iterrows():
            candidate_date = row.get("후보업로드일_dt")
            if pd.isna(candidate_date):
                medians.append(None); ns.append(0); ratios.append(None); warnings.append("날짜 없음")
                continue
            history = df[
                (df["channel_id"] == row["channel_id"])
                & (df["후보업로드일_dt"] < candidate_date)
                & (df["후보업로드일_dt"] >= candidate_date - pd.Timedelta(days=365))
            ].sort_values("후보업로드일_dt", ascending=False).head(30)
            n = len(history)
            if n == 0:
                med, ratio, warning = None, None, "데이터 없음"
            else:
                med = float(history["조회수"].median())
                ratio = float(row.get("조회수", 0) or 0) / med if med > 0 else None
                warning = "표본 적음" if n < 5 else ""
            medians.append(med); ns.append(n); ratios.append(ratio); warnings.append(warning)
        df["baseline_중앙값"] = medians
        df["baseline_N"] = ns
        df["채널배수"] = ratios
        df["baseline_경고"] = warnings
        if "구독자수" not in df.columns:
            df["구독자수"] = None
        df["조회수_구독자배수"] = df.apply(
            lambda r: (float(r["조회수"]) / float(r["구독자수"])) if pd.notna(r.get("구독자수")) and float(r.get("구독자수")) > 0 else None,
            axis=1,
        )
        df["영상나이_일"] = (today - df["후보업로드일_dt"]).dt.days
        df["조회속도_일평균"] = df.apply(
            lambda r: float(r.get("조회수", 0) or 0) / max(int(r.get("영상나이_일", 0) or 0) + 1, 1), axis=1
        )
        s = self.settings
        def is_recent_breakout(r):
            age = int(r.get("영상나이_일", 99999) or 99999)
            views = int(r.get("조회수", 0) or 0)
            if age < 0 or age > s.recent_breakout_window_days or views < s.recent_breakout_min_views:
                return False
            n = int(r.get("baseline_N", 0) or 0)
            ratio = r.get("채널배수")
            sub_ratio = r.get("조회수_구독자배수")
            established = n >= 5 and pd.notna(ratio) and float(ratio) >= s.recent_breakout_min_channel_ratio
            emerging = n < 5 and pd.notna(sub_ratio) and float(sub_ratio) >= s.recent_breakout_min_subscriber_ratio and views >= max(s.recent_breakout_min_views, 10000)
            strong_absolute = views >= 50000 and ((pd.notna(ratio) and float(ratio) >= 2.0) or (pd.notna(sub_ratio) and float(sub_ratio) >= 3.0))
            return bool(established or emerging or strong_absolute)
        df["최근브레이크아웃"] = df.apply(is_recent_breakout, axis=1)
        return df

    def scan_reference_channels(self, reference_df: pd.DataFrame, months: int = 12, max_per_channel: int = 80):
        """Scan all enabled user-selected reference channels and preserve provenance."""
        if reference_df is None or reference_df.empty:
            return pd.DataFrame(), []
        frames = []
        diagnostics = []
        for _, refrow in reference_df.iterrows():
            ref = str(refrow.get("channel_ref") or refrow.get("channel_url") or refrow.get("channel_name") or "").strip()
            if not ref:
                continue
            try:
                snapshot = self.load_reference_channel_catalog(ref, months=months, max_items=max_per_channel)
                df = snapshot.get("videos", pd.DataFrame()).copy()
                if df.empty:
                    diagnostics.append({"channel_ref": ref, "status": "empty", "message": "조건에 맞는 롱폼 없음"})
                    continue
                df["seed_role"] = str(refrow.get("role") or "")
                df["seed_source"] = str(refrow.get("source") or "manual")
                df["seed_channel_ref"] = ref
                df["reference_language"] = str(refrow.get("language") or "")
                df["reference_country"] = str(refrow.get("country") or "")
                df["reference_notes"] = str(refrow.get("notes") or "")
                df["발견검색어"] = f"REF:{snapshot.get('channel_title') or ref}"
                df["발견검색어_목록"] = [[f"REF:{snapshot.get('channel_title') or ref}"] for _ in range(len(df))]
                frames.append(df)
                diagnostics.append({
                    "channel_ref": ref,
                    "channel_id": snapshot.get("channel_id"),
                    "channel_title": snapshot.get("channel_title"),
                    "subscriber_count": snapshot.get("subscriber_count"),
                    "status": "ok",
                    "videos": len(df),
                })
            except Exception as exc:
                diagnostics.append({"channel_ref": ref, "status": "error", "message": f"{type(exc).__name__}: {str(exc)[:250]}"})
        if not frames:
            return pd.DataFrame(), diagnostics
        combined = pd.concat(frames, ignore_index=True).drop_duplicates("video_id").reset_index(drop=True)
        combined = self.attach_reference_channel_metrics(combined)
        return combined, diagnostics

    def market_map_from_video_ids(self, video_ids, discovery_label="seed_video"):
        """Build candidate rows for explicit seed video ids without relying on search ranking."""
        ids = [str(x).strip() for x in (video_ids or []) if str(x).strip()]
        details = self.fetch_video_details(ids)
        rows = []
        for video in details:
            dur = safe_duration_seconds(video)
            if dur is None or not (self.settings.min_duration_seconds <= dur <= self.settings.max_duration_seconds):
                continue
            rows.append({
                "video_id": video["id"],
                "제목": video["snippet"].get("title", ""),
                "설명": video["snippet"].get("description", ""),
                "채널": video["snippet"].get("channelTitle", ""),
                "channel_id": video["snippet"].get("channelId", ""),
                "길이_초": dur,
                "길이": seconds_to_text(dur),
                "조회수": int(video.get("statistics", {}).get("viewCount", 0) or 0),
                "좋아요": int(video.get("statistics", {}).get("likeCount", 0) or 0),
                "댓글": int(video.get("statistics", {}).get("commentCount", 0) or 0),
                "업로드날짜": video["snippet"].get("publishedAt", "")[:10],
                "후보업로드일_dt": pd.to_datetime(video["snippet"].get("publishedAt"), utc=True, errors="coerce"),
                "영상링크": f"https://www.youtube.com/watch?v={video['id']}",
                "발견검색어": discovery_label,
                "발견검색어_목록": [discovery_label],
            })
        return pd.DataFrame(rows)
