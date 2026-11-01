# v2.1 · Absolute Comment Intelligence & Public Portfolio Demo

Date: 2026-10-23

## Release focus

1. Creator-first **absolute public comment counts**, not per-view rates, added to the strategy workspace and a quick panel in the topic comparison view.
2. **Explicit opt-in** comment-text review: one `commentThreads.list` request per selected video, up to 60 public **top-level** comments in YouTube's relevance order; one OpenAI response classifies into a single primary category per sampled comment.
3. Only counts/metadata and AI status are stored under `Desktop/YT_Channel_Strategy/comment_reviews/`; texts/commenter identities are NOT stored by this new reviewer. Raw comments are still sent to OpenAI for classification, and the separate legacy research cache has its own handling.
4. A and Hermes can see bounded, source-labelled **public absolute comment metrics** and any existing tentative qualitative summaries as background evidence for independent 1–3 ranking, but **no buying-intent prediction** is asserted.
5. Independent GitHub-ready public demo uses entirely invented video metrics and hypothetical category counts, without credentials, live APIs, user Studio data or a real Hermes Agent.

## Limits

- `statistics.commentCount` is a public total that may include replies; sampled `commentThreads` are top-level only. These two counts do not share an exact denominator.
- The 60-comment sample is not representative of every viewer, and one category label per comment is provisional.
- Fewer comments can accompany valuable, converting content; the product does **not** declare content 'good' based only on count.
- YouTube comments do not establish actual purchases or teaching effectiveness. True conversion requires a separately tracked lead/order event.
- No running background service is added for automatic comment-text analysis. Public comment *totals* already follow the existing metadata snapshot cadence.
- Windows + live YouTube/OpenAI/Hermes and the Streamlit cloud deployment remain outside offline test coverage.

## Validation

- Existing and new offline suites via `python validate_release.py` (106 test cases; 105 passed, 1 skipped at packaging time).
- Standalone synthetic demo smoke test: 3 test cases passed.
- ZIP archives separately validated for integrity and absence of `.env` files.

## Files

- Private/local full installation: `0_START_WITH_HERMES.bat` to run, `3_RUN_PUBLIC_DEMO.bat` for simulation.
- Public GitHub repo: see the **separate demo ZIP** and its `PUBLISH_GUIDE_KO.md`.
