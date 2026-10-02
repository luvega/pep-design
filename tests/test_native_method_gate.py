import json
from pathlib import Path

import pytest

from harness.domains.project_state import _evaluate_native_method_acceptance
from harness.domains.project_state import GateVerdict
from scripts import evaluate_method_acceptance as replay

ROOT = Path(__file__).resolve().parents[1]


def configured_report():
    return {'schema_version': 'native_method_acceptance_v2', 'assessment_scope_sha256': 'scope', 'quality_passed_count': 9, 'criteria_sha256': 'criteria',
            'policy_sha256': 'policy', 'resource_ledger_sha256': 'ledger',
            'passed_count': 10, 'all_methods_accepted': True,
            'resources': {'gpu_seconds': {'remaining_unreserved': 1},
                          'cpu_heavy_wall_seconds': {'remaining_unreserved': 1},
                          'download_bytes': {'accounted': 1, 'limit': 2},
                          'disk_bytes': {'used': 1, 'limit': 2}},
            'methods': [{'method_id': k, 'status': 'pass', 'new_attempt_count': 1} for k in replay.METHODS]}


def invoke(tmp_path, monkeypatch, report, *, stale=False):
    gate = next(r for r in json.loads((ROOT / 'harness/contracts/project_acceptance_v1.json').read_text())['gates']
                if r['gate_id'] == 'current.native_method_acceptance')
    artifacts = {k: {'path': k + '.json'} for k in gate['inputs']}
    index = replay.evidence_index(report)
    if stale:
        index['replay_sha256'] = 'stale'
    (tmp_path / artifacts['method_acceptance_execution_index_v1']['path']).write_text(json.dumps(index))
    monkeypatch.setattr(replay, 'evaluate', lambda root: report)
    return _evaluate_native_method_acceptance(tmp_path, gate, artifacts)


def test_native_gate_requires_replayed_index(tmp_path, monkeypatch):
    report = configured_report()
    assert invoke(tmp_path, monkeypatch, report).verdict is GateVerdict.PASS
    assert invoke(tmp_path, monkeypatch, report, stale=True).verdict is GateVerdict.FAIL


@pytest.mark.parametrize('failure', ['one_method_missing', 'gpu', 'cpu', 'download', 'disk', 'attempts'])
def test_native_gate_never_waives_method_or_budget_failure(tmp_path, monkeypatch, failure):
    report = configured_report()
    if failure == 'one_method_missing':
        report.update(passed_count=9, all_methods_accepted=False)
        report['methods'][0]['status'] = 'not_passed'
    elif failure in ('gpu', 'cpu'):
        name = 'gpu_seconds' if failure == 'gpu' else 'cpu_heavy_wall_seconds'
        report['resources'][name]['remaining_unreserved'] = -1
    elif failure == 'download':
        report['resources']['download_bytes']['accounted'] = 3
    elif failure == 'disk':
        report['resources']['disk_bytes']['used'] = 3
    else:
        report['methods'][0]['new_attempt_count'] = 4
    result = invoke(tmp_path, monkeypatch, report)
    assert result.verdict is GateVerdict.FAIL
    assert result.reason_code == 'native_method_acceptance_incomplete'
