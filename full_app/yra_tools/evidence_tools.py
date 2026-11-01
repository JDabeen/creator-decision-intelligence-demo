import json
import time

import pandas as pd
from googleapiclient.errors import HttpError
from transcript_fallback import read_provider_key, fetch_native_transcript, TranscriptProviderError


class EvidenceTools:
    def __init__(self, youtube_client, transcript_client, cache_manager):
        self.youtube = youtube_client
        self.transcript = transcript_client
        self.cache = cache_manager
        self.transcript_blocked = False
        self.transcript_block_reason = ""

    def get_top_liked_comments(self, video_id, max_fetch=300, top_n=100):
        path = self.cache.root / "comments" / f"{video_id}_{max_fetch}_{top_n}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), True

        comments, page_token, request_failed = [], None, False
        while len(comments) < max_fetch:
            try:
                response = self.youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(100, max_fetch - len(comments)),
                    order="relevance",
                    textFormat="plainText",
                    pageToken=page_token,
                ).execute()
            except HttpError:
                request_failed = True
                break

            for item in response.get("items", []):
                top = item["snippet"]["topLevelComment"]["snippet"]
                comments.append(
                    {
                        "comment_id": item["snippet"]["topLevelComment"]["id"],
                        "댓글": top.get("textOriginal", top.get("textDisplay", "")),
                        "댓글_좋아요": top.get("likeCount", 0),
                        "댓글_작성일": top.get("publishedAt"),
                        "답글수": item["snippet"].get("totalReplyCount", 0),
                    }
                )
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        comments = sorted(comments, key=lambda x: x["댓글_좋아요"], reverse=True)[:top_n]
        if not request_failed:
            self.cache.safe_json_dump(comments, path)
        return comments, False

    def get_transcript(self, video_id, use_provider=False):
        path = self.cache.root / "transcripts" / f"{video_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), True

        payload = {
            "video_id": video_id,
            "상태": "실패",
            "언어": None,
            "언어코드": None,
            "자동자막": None,
            "대본글자수": 0,
            "전체대본": "",
            "segments": [],
            "오류": None,
        }
        provider_key = read_provider_key(self.cache.root) if use_provider else ""
        if self.transcript_blocked and not provider_key:
            payload["오류"] = "SkippedAfterIpBlock: " + (self.transcript_block_reason or "이 실행에서 IP 차단이 감지되어 추가 Transcript 요청을 중단했습니다.")
            return payload, False
        try:
            if self.transcript_blocked:
                raise RuntimeError("IpBlocked: 이번 실행에서 기본 자막 수집 차단")
            transcript_list = self.transcript.list(video_id)
            try:
                transcript = transcript_list.find_transcript(["ko", "en"])
            except Exception:
                available = list(transcript_list)
                if not available:
                    raise Exception("사용 가능한 자막 없음")
                transcript = available[0]

            fetched = transcript.fetch()
            segments = [
                {"시작초": float(s.start), "길이초": float(s.duration), "텍스트": s.text}
                for s in fetched
            ]
            full_text = " ".join(s["텍스트"].replace("\n", " ") for s in segments)
            payload.update(
                {
                    "상태": "성공",
                    "언어": transcript.language,
                    "언어코드": transcript.language_code,
                    "자동자막": bool(transcript.is_generated),
                    "대본글자수": len(full_text),
                    "전체대본": full_text,
                    "segments": segments,
                    "획득경로": "YouTube 기존 자막",
                }
            )
        except Exception as e:
            message = f"{type(e).__name__}: {str(e)[:700]}"
            payload["오류"] = message
            lower = message.lower()
            if "ipblocked" in lower or "blocking requests from your ip" in lower or "requestblocked" in lower:
                self.transcript_blocked = True
                self.transcript_block_reason = message[:300]

            if provider_key:
                try:
                    # 외부 경로는 실제 시장 영상에만 사용. 기본 모드는 native(음성인식 과금 없음).
                    payload = fetch_native_transcript(video_id, provider_key)
                except TranscriptProviderError as fallback_exc:
                    payload["오류"] = message[:220] + " | 외부자막: " + str(fallback_exc)[:120]

        # 일시 차단/실패를 영구 캐시하지 않고 성공 결과만 저장한다.
        if payload["상태"] == "성공":
            self.cache.safe_json_dump(payload, path)
            delay = float(getattr(self.cache.settings, "transcript_request_delay_seconds", 0.0) or 0.0)
            if delay > 0:
                time.sleep(delay)
        return payload, False

    def collect_market_evidence(self, candidate_df):
        all_comments, transcript_rows, segment_rows = [], [], []
        for _, video in candidate_df.iterrows():
            video_id, title = video["video_id"], video["제목"]
            comments, _ = self.get_top_liked_comments(video_id)
            all_comments.extend({**c, "video_id": video_id, "영상제목": title} for c in comments)

            tr, tr_cached = self.get_transcript(video_id, use_provider=True)
            transcript_rows.append(
                {
                    "video_id": video_id,
                    "영상제목": title,
                    "대본상태": tr["상태"],
                    "대본언어": tr["언어"],
                    "자동자막여부": tr["자동자막"],
                    "대본글자수": tr["대본글자수"],
                    "전체대본": tr["전체대본"],
                    "대본오류": tr["오류"],
                    "대본캐시": bool(tr_cached),
                    "대본출처": tr.get("획득경로") or ("저장된 자막" if tr_cached else "기본 자막 수집"),
                }
            )
            segment_rows.extend({"video_id": video_id, "영상제목": title, **s} for s in tr["segments"])

        comments_df = pd.DataFrame(all_comments)
        transcript_df = pd.DataFrame(transcript_rows)
        segments_df = pd.DataFrame(segment_rows)

        if not comments_df.empty:
            bundles = []
            for vid, group in comments_df.groupby("video_id"):
                group = group.sort_values("댓글_좋아요", ascending=False).reset_index(drop=True)
                formatted = [
                    f"{i+1}. [좋아요 {r['댓글_좋아요']} | 답글 {r['답글수']}]\n{r['댓글']}"
                    for i, r in group.iterrows()
                ]
                bundles.append({"video_id": vid, "수집댓글수": len(group), "좋아요상위댓글": "\n\n".join(formatted)})
            comment_bundle_df = pd.DataFrame(bundles)
        else:
            comment_bundle_df = pd.DataFrame(columns=["video_id", "수집댓글수", "좋아요상위댓글"])

        analysis_df = (
            candidate_df
            .merge(transcript_df[["video_id", "대본상태", "대본언어", "자동자막여부", "대본글자수", "전체대본", "대본오류", "대본캐시"]], on="video_id", how="left")
            .merge(comment_bundle_df, on="video_id", how="left")
        )
        analysis_df["수집댓글수"] = analysis_df["수집댓글수"].fillna(0).astype(int)
        analysis_df["좋아요상위댓글"] = analysis_df["좋아요상위댓글"].fillna("")
        return analysis_df, comments_df, transcript_df, segments_df

    def collect_my_content(self, catalog_df):
        transcript_rows, segment_rows = [], []
        for _, video in catalog_df.iterrows():
            tr, tr_cached = self.get_transcript(video["video_id"])
            transcript_rows.append(
                {
                    "video_id": video["video_id"],
                    "대본상태": tr["상태"],
                    "대본언어": tr["언어"],
                    "자동자막여부": tr["자동자막"],
                    "대본글자수": tr["대본글자수"],
                    "전체대본": tr["전체대본"],
                    "대본오류": tr["오류"],
                    "대본캐시": bool(tr_cached),
                }
            )
            segment_rows.extend({"video_id": video["video_id"], "제목": video["제목"], **s} for s in tr["segments"])

        transcript_df = pd.DataFrame(transcript_rows)
        segments_df = pd.DataFrame(segment_rows)
        content_df = catalog_df.merge(transcript_df, on="video_id", how="left")
        return content_df, transcript_df, segments_df
