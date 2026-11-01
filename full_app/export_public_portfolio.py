"""Export only non-sensitive evaluation metadata for a public portfolio.

Do not publish raw evidence.json, API requests, script excerpts or Studio records.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def data_dir() -> Path:
    override = os.environ.get('YRA_DATA_DIR', '').strip()
    if override:
        return Path(override).expanduser()
    desktop = Path.home() / 'Desktop'
    return (desktop / 'youtube_consultant_data') if desktop.exists() else (ROOT / 'data')


def export_latest(root: Path, output: Path) -> Path:
    source = root / 'topic_experiments'
    for folder in sorted((p for p in source.glob('*') if p.is_dir()), reverse=True):
        manifest = folder / 'manifest.json'
        comparison = folder / 'comparison.json'
        if not manifest.is_file() or not comparison.is_file():
            continue
        m = json.loads(manifest.read_text(encoding='utf-8'))
        c = json.loads(comparison.read_text(encoding='utf-8'))
        if m.get('status') != 'COMPLETE':
            continue
        audits = c.get('evidence_audit') or {}
        payload = {
            'kind': 'anonymized_topic_workflow_report',
            'generated_utc': datetime.now(timezone.utc).isoformat(),
            'workflow_version': m.get('version'),
            'evidence_sha256': m.get('evidence_sha256'),
            'result': 'topic_candidates_ready',
            'baseline_topics_count': len(c.get('a_topics') or []),
            'agent_topics_count': len(c.get('b_topics') or []),
            'web_tool_success_count': m.get('web_completed', 0),
            'web_discovered_url_count': m.get('web_source_count', 0),
            'evaluation': {
                'kind': audits.get('comparison_kind', 'workflow comparison, not randomized A/B'),
                'baseline_evidence_status': [t.get('status') for t in audits.get('a', [])],
                'agent_evidence_status': [t.get('status') for t in audits.get('b', [])],
            },
            'real_view_performance': 'not_observed',
            'limits': ['No raw transcripts, private Studio analytics, URLs, topics, drafts, or API keys exported.',
                       'One run cannot establish expected views or causal lift.'],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return output
    raise FileNotFoundError('완료된 A/B 주제 비교 기록이 없습니다. 먼저 앱에서 한 번 완주해 주세요.')


if __name__ == '__main__':
    try:
        dest = export_latest(data_dir(), ROOT / 'portfolio_public' / 'evaluation_summary.json')
        print('Safe public summary:', dest)
    except (FileNotFoundError, OSError, ValueError) as err:
        print('Not exported:', err)
        raise SystemExit(1)
