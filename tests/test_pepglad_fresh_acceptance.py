from pathlib import Path

import pytest

from scripts import parse_v035_pepglad_connectivity as parser
from tests.test_v035_merge import _bundle


def _runner():
    from scripts import run_pepglad_fresh_acceptance as runner
    return runner


def test_fresh_namespace_is_distinct_and_old_job_rejected(tmp_path):
    from scripts.run_v035_pepglad_connectivity import AUTHORIZED_JOB as old_job
    runner = _runner()
    assert runner.AUTHORIZED_JOB['job_id'] != old_job['job_id']
    assert runner.DEFAULT_RUN_ROOT.name == 'pepglad_fresh_v1'
    with pytest.raises(ValueError, match='authorized'):
        runner.validate_execution_request(old_job, run_root=tmp_path)


@pytest.mark.parametrize('field', ['job_id', 'random_seed', 'target_pdb_sha256',
                                  'length_min', 'chirality_constraint', 'baseline_replay_policy'])
def test_fresh_request_rejects_changed_authorization(tmp_path, field):
    runner = _runner()
    with pytest.raises(ValueError, match='authorized'):
        runner.validate_execution_request({**runner.AUTHORIZED_JOB, field: 'tampered'},
                                          run_root=tmp_path)


def test_failed_preflight_does_not_create_attempt(tmp_path, monkeypatch):
    runner = _runner()
    def fail():
        raise ValueError('Docker API unavailable')
    monkeypatch.setattr(runner, 'preflight', fail)
    with pytest.raises(ValueError, match='Docker'):
        runner.execute_authorized_job(runner.AUTHORIZED_JOB, execute=True, run_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('node', ['attempt_001', 'attempt_002'])
def test_recorded_attempt_prevents_further_execution(tmp_path, node):
    runner = _runner()
    (tmp_path / 'pepglad' / runner.AUTHORIZED_JOB['job_id'] / node).mkdir(parents=True)
    with pytest.raises(ValueError, match='already recorded'):
        runner.validate_execution_request(runner.AUTHORIZED_JOB, run_root=tmp_path)


def test_symlinked_run_root_rejected(tmp_path):
    runner = _runner()
    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        runner.validate_execution_request(runner.AUTHORIZED_JOB, run_root=link)


def test_fresh_bundle_accepted_only_under_explicit_policy():
    runner = _runner()
    bundle = _bundle()
    bundle['schema_version'] = runner.POLICY.schema_version
    bundle['job']['job_id'] = runner.POLICY.job_id
    bundle['candidate']['design_id'] = runner.POLICY.design_id
    bundle['execution']['attempt_dir'] = str(runner.DEFAULT_RUN_ROOT / 'pepglad' /
                                           runner.POLICY.job_id / 'attempt_001')
    parser.validate_bundle(bundle, policy=runner.POLICY)
    with pytest.raises(ValueError):
        parser.validate_bundle(bundle)
    from scripts import validate_benchmark_kb as validator
    assert validator._v035_bundle_schema_valid(bundle, policy=runner.POLICY)
    assert not validator._v035_bundle_schema_valid(bundle)


def test_fresh_build_and_independent_replay_reject_tamper(tmp_path):
    import json
    from tests.test_v035_merge import _write_build_fixture
    from scripts import validate_benchmark_kb as validator
    runner = _runner()
    run_root, old_attempt, historical = _write_build_fixture(tmp_path)
    new_job_root = old_attempt.parent.parent / runner.POLICY.job_id
    old_attempt.parent.rename(new_job_root)
    attempt = new_job_root / 'attempt_001'
    result_path = attempt / 'run_result.json'
    result = json.loads(result_path.read_text())
    result.update(job_id=runner.POLICY.job_id, design_id=runner.POLICY.design_id,
                  attempt_dir=str(attempt))
    result_path.write_text(json.dumps(result))
    for name, value in [('job.json', runner.AUTHORIZED_JOB),
                        ('execution.json', runner.AUTHORIZED_EXECUTION)]:
        (attempt / name).write_text(json.dumps(value))
    bundle = parser.build_bundle(run_root=run_root, job_manifest=runner.DEFAULT_JOB_MANIFEST,
                                 execution_matrix=runner.DEFAULT_EXECUTION_MATRIX,
                                 historical_paths=historical, policy=runner.POLICY)
    assert validator._v035_raw_replay_valid(bundle, policy=runner.POLICY)
    assert validator._v035_historical_bindings_valid(bundle, artifact_paths=historical)
    candidate = attempt / 'raw/pepglad_candidate.pdb'
    candidate.write_bytes(candidate.read_bytes() + b'REMARK altered\n')
    assert not validator._v035_raw_replay_valid(bundle, policy=runner.POLICY)


def test_preflight_then_single_execution_and_no_automatic_retry(tmp_path, monkeypatch):
    runner = _runner()
    calls = []
    monkeypatch.setattr(runner, 'preflight', lambda: calls.append('preflight') or {})
    def failed_run(*args, **kwargs):
        calls.append('run')
        (tmp_path / 'pepglad' / runner.POLICY.job_id / 'attempt_001').mkdir(parents=True)
        return {'status': 'execution_failed'}
    monkeypatch.setattr(runner.v034_runner, 'run_job', failed_run)
    result = runner.execute_authorized_job(runner.AUTHORIZED_JOB, execute=True, run_root=tmp_path)
    assert calls == ['preflight', 'preflight', 'run']
    assert result['status'] == 'execution_failed'


def test_preflight_parses_container_banner_and_pins_image(monkeypatch):
    runner = _runner()
    monkeypatch.setattr(runner, 'require_clean_git_checkout', lambda *args: None)
    monkeypatch.setattr(runner, 'require_file_sha256', lambda *args: None)
    outputs = iter([runner.IMAGE_ID, '28.0', 'CUDA banner\nPEPGLAD_PREFLIGHT_JSON={"torch":"1.13.1"}'])
    monkeypatch.setattr(runner, '_read_command', lambda *args, **kwargs: next(outputs))
    assert runner.preflight()['environment'] == {'torch': '1.13.1'}
    monkeypatch.setattr(runner, '_read_command', lambda *args, **kwargs: 'sha256:' + '0' * 64)
    with pytest.raises(ValueError, match='image identity'):
        runner.preflight()


def test_pinned_adapter_keeps_old_policy_default_rejecting_fresh_job(tmp_path):
    from scripts.v035_adapters import pepglad
    runner = _runner()
    with pytest.raises(ValueError, match='job policy'):
        pepglad._validate_job_policy(runner.AUTHORIZED_JOB)
    pepglad._validate_job_policy(runner.AUTHORIZED_JOB, authorized_job_id=runner.POLICY.job_id)


def test_policy_tamper_rejected_before_allocation(tmp_path, monkeypatch):
    runner = _runner()
    policy = tmp_path / 'policy.json'
    policy.write_text('{}')
    monkeypatch.setattr(runner, 'POLICY_PATH', policy)
    with pytest.raises(ValueError, match='authorization policy'):
        runner.validate_execution_request(runner.AUTHORIZED_JOB, run_root=tmp_path / 'runs')
    assert not (tmp_path / 'runs').exists()
