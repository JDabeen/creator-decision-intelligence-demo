# Validation status — v1.8

**Offline:** `7_OFFLINE_TEST.bat` runs syntax checks, unit tests, mocked HTTP Hermes gateway tests and pipeline failure/recovery tests. `test_integration.py` uses a local mock server, **not NousResearch's live service**. Some tests skip when optional runtime libraries are not installed in the checker environment.

**Must verify on the user's Windows PC (not yet verified here):** fresh `.env` setup, Docker Desktop, Hermes API authentication and tool list, real `web_search` response with links, A and Hermes topic lists, a human topic selection, deep research, optional draft, cached state restore and sanitized portfolio export.

**Evidence meaning:** URLs are **observed during web-tool calls**; webpages, views, market size, instructional correctness, and viewer demand are not independently attested. A deterministic reference check rejects unrecognized citations and surfaces insufficiency. It is deliberately not a fake weighted AI score.

**A/B limitation:** A uses RAG and accumulated internal analysis; Hermes B uses frozen observable input and additional live web-tool calls. This is a comparison of workflows, not a model-only experiment. Real YouTube results are not measured by the offline suite.

**Privacy:** Docker isolation prevents intentional mounts of host personal folders and Chrome profile, but browser/web-enabled agents can send input context to outside services; the Hermes config folder and model credentials are in its container environment. Never export `.env`, private Studio reports, raw `evidence.json`, or unpublished scripts to a public repository.

**Reproducibility:** `requirements.txt` pins **top-level** versions observed to install on Windows CPython 3.14; transitives are not fully hash-locked. Docker image is pinned by digest. Longer-term improvements include full lockfiles per Python version, Windows CI and real multi-run topic evaluation with a documented selection rubric.
