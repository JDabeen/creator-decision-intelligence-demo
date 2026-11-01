import hashlib
import json
import pickle
from pathlib import Path


class CacheManager:
    def __init__(self, openai_client, settings, root="data/cache"):
        self.client = openai_client
        self.settings = settings
        self.root = Path(root)
        (self.root / "transcripts").mkdir(parents=True, exist_ok=True)
        (self.root / "comments").mkdir(parents=True, exist_ok=True)
        (self.root / "llm").mkdir(parents=True, exist_ok=True)
        self.embedding_path = self.root / "embeddings.pkl"
        self.embedding_cache = self._load_embeddings()

    @staticmethod
    def sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def safe_json_dump(obj, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    def _load_embeddings(self):
        if not self.embedding_path.exists():
            return {}
        try:
            with open(self.embedding_path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return {}

    def structured_response(self, namespace, system_prompt, user_prompt, schema):
        material = json.dumps(
            {
                "model": self.settings.llm_model,
                "system": system_prompt,
                "user": user_prompt,
                "schema": schema,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        key = self.sha256(material)
        path = self.root / "llm" / f"{namespace}_{key}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload["result"], payload.get("usage", {}), True

        response = self.client.responses.create(
            model=self.settings.llm_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": namespace,
                    "strict": True,
                    "schema": schema,
                }
            },
            store=False,
        )
        result = json.loads(response.output_text)
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0),
            "output_tokens": getattr(response.usage, "output_tokens", 0),
            "total_tokens": getattr(response.usage, "total_tokens", 0),
        }
        self.safe_json_dump({"result": result, "usage": usage}, path)
        return result, usage, False

    def embed_texts(self, texts, batch_size=100):
        keys = [self.sha256(self.settings.embedding_model + "\n" + str(t)) for t in texts]
        missing = [i for i, k in enumerate(keys) if k not in self.embedding_cache]

        for start in range(0, len(missing), batch_size):
            idxs = missing[start : start + batch_size]
            batch = [str(texts[i]) for i in idxs]
            response = self.client.embeddings.create(
                model=self.settings.embedding_model,
                input=batch,
            )
            for idx, item in zip(idxs, response.data):
                self.embedding_cache[keys[idx]] = item.embedding

        if missing:
            with open(self.embedding_path, "wb") as f:
                pickle.dump(self.embedding_cache, f)

        return [self.embedding_cache[k] for k in keys]
