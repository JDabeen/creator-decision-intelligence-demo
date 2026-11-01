import math
import re
from collections import Counter

import numpy as np
import pandas as pd


def cosine_similarity(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def tokenize_for_bm25(text):
    return re.findall(r"[가-힣]+|[a-zA-Z]+(?:'[a-zA-Z]+)?|\d+", str(text).lower())


def bm25_scores(documents, query, k1=1.5, b=0.75):
    docs = [tokenize_for_bm25(x) for x in documents]
    q_tokens = tokenize_for_bm25(query)
    n_docs = len(docs)
    if n_docs == 0 or not q_tokens:
        return np.zeros(n_docs)
    avgdl = sum(len(d) for d in docs) / max(n_docs, 1)
    df = Counter()
    for doc in docs:
        for t in set(doc):
            df[t] += 1
    scores = np.zeros(n_docs, dtype=float)
    for i, doc in enumerate(docs):
        tf, dl = Counter(doc), len(doc)
        for term in q_tokens:
            if term not in tf:
                continue
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf[term]
            denom = freq + k1 * (1 - b + b * dl / max(avgdl, 1e-9))
            scores[i] += idf * (freq * (k1 + 1) / denom)
    return scores


class RetrievalTools:
    def __init__(self, cache_manager, settings):
        self.cache = cache_manager
        self.settings = settings

    def make_chunks(self, content_df, prefix="my"):
        rows = []
        step = self.settings.chunk_size - self.settings.chunk_overlap
        for _, row in content_df.iterrows():
            transcript = str(row.get("전체대본", "") or "")
            if not transcript.strip() or transcript.lower() == "nan":
                continue
            start, chunk_no = 0, 1
            while start < len(transcript):
                chunk_text = transcript[start : start + self.settings.chunk_size]
                if len(chunk_text.strip()) < 100:
                    break
                rows.append(
                    {
                        "video_id": row["video_id"],
                        "제목": row["제목"],
                        "chunk_id": f"{prefix}_{row['video_id']}_{chunk_no}",
                        "chunk번호": chunk_no,
                        "텍스트": chunk_text,
                        "embedding_text": f"영상 제목: {row['제목']}\n내용: {chunk_text}",
                    }
                )
                chunk_no += 1
                start += step
        return pd.DataFrame(rows)

    def build_index(self, content_df, prefix="my"):
        chunks = self.make_chunks(content_df, prefix=prefix)
        if chunks.empty:
            raise ValueError("Transcript 기반 Chunk가 0개입니다. Transcript 수집 결과를 확인하세요.")
        chunks["embedding"] = self.cache.embed_texts(chunks["embedding_text"].tolist())
        return chunks

    @staticmethod
    def lexical_retrieve(corpus_df, query, top_k=20):
        docs = (corpus_df["제목"].fillna("") + " " + corpus_df["텍스트"].fillna("")).tolist()
        scores = bm25_scores(docs, query)
        out = corpus_df[["chunk_id", "video_id", "제목", "chunk번호", "텍스트"]].copy()
        out["bm25_score"] = scores
        return out[out["bm25_score"] > 0].sort_values("bm25_score", ascending=False).head(top_k).reset_index(drop=True)

    def semantic_retrieve(self, corpus_df, query, top_k=20):
        q_vec = self.cache.embed_texts([query])[0]
        out = corpus_df[["chunk_id", "video_id", "제목", "chunk번호", "텍스트", "embedding"]].copy()
        out["semantic_similarity"] = out["embedding"].apply(lambda e: cosine_similarity(q_vec, e))
        return out.sort_values("semantic_similarity", ascending=False).head(top_k).reset_index(drop=True)

    def hybrid_retrieve(self, corpus_df, query, top_k=10, rrf_k=60):
        lexical_df = self.lexical_retrieve(corpus_df, query, top_k=20)
        semantic_df = self.semantic_retrieve(corpus_df, query, top_k=20)
        fused = {}

        def ensure(row):
            cid = row["chunk_id"]
            if cid not in fused:
                fused[cid] = {
                    "chunk_id": cid,
                    "video_id": row["video_id"],
                    "제목": row["제목"],
                    "chunk번호": row["chunk번호"],
                    "텍스트": row["텍스트"],
                    "bm25_rank": None,
                    "semantic_rank": None,
                    "RRF_score": 0.0,
                }
            return cid

        for rank, (_, row) in enumerate(lexical_df.iterrows(), start=1):
            cid = ensure(row)
            fused[cid]["bm25_rank"] = rank
            fused[cid]["RRF_score"] += 1 / (rrf_k + rank)
        for rank, (_, row) in enumerate(semantic_df.iterrows(), start=1):
            cid = ensure(row)
            fused[cid]["semantic_rank"] = rank
            fused[cid]["RRF_score"] += 1 / (rrf_k + rank)

        cols = ["chunk_id", "video_id", "제목", "chunk번호", "텍스트", "bm25_rank", "semantic_rank", "RRF_score"]
        if not fused:
            return pd.DataFrame(columns=cols)
        return pd.DataFrame(fused.values()).sort_values("RRF_score", ascending=False).head(top_k).reset_index(drop=True)

    def hybrid_retrieve_diverse(self, corpus_df, query, top_k=14, max_per_video=2, rrf_k=60):
        """Hybrid retrieval 결과가 한 영상에 과도하게 몰리지 않도록 영상별 상한을 둔다."""
        pool = self.hybrid_retrieve(corpus_df, query, top_k=max(top_k * 3, 24), rrf_k=rrf_k)
        if pool.empty:
            return pool
        kept = []
        counts = {}
        for _, row in pool.iterrows():
            vid = row["video_id"]
            if counts.get(vid, 0) >= max_per_video:
                continue
            kept.append(row.to_dict())
            counts[vid] = counts.get(vid, 0) + 1
            if len(kept) >= top_k:
                break
        return pd.DataFrame(kept, columns=pool.columns)
