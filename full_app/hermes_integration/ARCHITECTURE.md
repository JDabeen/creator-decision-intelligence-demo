# Technical architecture / risk register

## Trust boundary

Windows data ingestion and retrieval stay entirely on host. A narrow API adapter POSTs only the already selected candidate/draft/context as text to authenticated Hermes API on loopback; no host filesystem or Docker socket mount exists.

Hermes uses a separate on-host persistent directory mounted to /opt/data, never a volume containing app data. Hermes gateway key is outside that mounted directory. No public API/dashboard. Tool policy in config.yaml plus live /v1/toolsets inspection denies terminal, file write, browser, memory, skills, delegation, cron, computer use, etc.

Note: sending draft/transcript text through Hermes to the selected cloud LLM provider still transfers that text to the provider. Search tools may transfer queries to configured search vendors. Docker is isolation, not a confidentiality guarantee.

## Failure policy

1. Any Hermes unavailability/security policy failure raises explicit error; no disguised OpenAI Critic fallback.
2. Manual user selection of existing OpenAI Critic is available without modifying research.
3. Transcript Coverage Gate retains original behavior; no research bypass.
4. No existing BAT or persistent cache changes.
5. Toolset API must exist and active tool list must be subset of {web_search,web_extract,tool_search}.

## Future improvements after live run

- Image digest pinned to the observed successfully-booting `main` build; verify real API/model behavior on Windows and deliberately upgrade when tested.
- Collect structured tool progress and true source URLs more precisely for web citations.
- Limit request cost/token quota at app/provider level, not just tool count and timeout.
- Consider moving image execution to a purpose-built network-restricted ephemeral VM for stronger isolation.
- Add a user-visible confirmation before paid agent calls, optional cost budget and web research audit trail.
