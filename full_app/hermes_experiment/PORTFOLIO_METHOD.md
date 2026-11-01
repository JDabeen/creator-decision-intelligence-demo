# Independent Research Agent Experiment (Hermes + YouTube Content Consultant)

## Research question
Can a tool-using, research-augmented Hermes agent generate an independently conceived Korean adult-English YouTube script from the same market packet used to create Draft A? Does independent evaluation identify material differences in topic framing, pedagogy, grammar accuracy and production feasibility?

## System boundary
- Baseline: fixed market search + YouTube API observations + transcript acquisition + RAG of competitors and owner's historical scripts → Draft A.
- Agent: same pre-frozen candidate/topic, competitor metadata, actual transcript excerpts and historical owner-script excerpts; separate Hermes web-tool verification; independent Draft B. **No Draft A, existing blueprint, or design_pack passed to the Draft B writer.**
- Evaluator: separate OpenAI API call sees only anonymous X and Y, common metadata/rubric. X/Y mapping is hashed deterministic; rubric is qualitative, not proof of watch-time improvements.
- Human user selects, modifies or rejects either output.

## Evidence provenance / caveats
- `manifest.json` hashes frozen evidence and A/B outputs, stores URL/tool trace, missing-evidence warnings, stages and model names.
- `evidence.json` contains raw market video observations and excerpts from existing A-pipeline. It is frozen before Hermes creates B.
- Prior run JSON may lack raw transcript excerpts; this is flagged. For full experiments, generate a NEW Draft A with this version first.
- B's additional Hermes internet investigation means this is an **end-to-end workflow comparison**, not a controlled model-only A/B or causal YouTube viewer experiment.
- Search tool returns and URLs show tool activity, but do not automatically validate truth/relevance. Human evidence review needed.
- YouTube search sample is non-random; views depend on channel, age, title, packaging etc. No future view-count ceiling is inferred.

## Offline test approach
- No actual paid calls in tests; mocked Hermes web call cannot be replaced by agent prose.
- Verify no A draft or A blueprint enters the blind prompt.
- Verify old run evidence limitation, deterministic anonymous comparison, stable manifest, fail-closed on 0 successful web calls.
- Verify RunStore records market evidence and owner's older script excerpts.

## Reproduction
1. In existing Windows app, configure keys and complete one Draft A.
2. Run `11_HERMES_독립_A_B_실험.bat`.
3. Inspect `experiments/<timestamp>_<evidence-hash>/manifest.json` and `comparison.md`.
4. Evaluate actual English grammar/learning impact with independent human review; do not claim market outcomes from text-based model scoring.

## Data and security
Docker bound to localhost port 8642, no personal Windows directories mounted. Only Hermes-specific data dir bound. API provider may receive provided text. Never commit `.env` or saved traces containing sensitive data. Inputs are treated as untrusted evidence, not instructions.

## Honest completion criteria
1. Hermes API connects; verified live web tool use and actual source URL recorded.
2. Hermes generates an independent Draft B, with frozen shared evidence and no exposure to Draft A.
3. Independent evaluator returns a comparison, anonymous labels reconciled; user chooses final.
4. Two human reviewers check grammar accuracy and value proposition before publication.
5. Future field test on YouTube could measure CTR/retention only after real audience exposure.
