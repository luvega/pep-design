#!/usr/bin/env python3
"""One fresh, non-overwriting PepGLAD acceptance execution; no scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_v034_wave_a_generation as v034_runner
from scripts import run_v035_pepglad_connectivity as legacy
from scripts import parse_v035_pepglad_connectivity as parser
from scripts.v035_adapters import pepglad
from scripts.v034_adapters import pepglad as producer
from scripts.v034_adapters.common import require_clean_git_checkout, require_file_sha256

POLICY = parser.FRESH_POLICY
DEFAULT_RUN_ROOT = ROOT / 'benchmark_runs/pepglad_fresh_v1'
DEFAULT_JOB_MANIFEST = ROOT / 'benchmark/input_sets/pepglad_fresh_job_manifest_v1.csv'
DEFAULT_EXECUTION_MATRIX = ROOT / 'benchmark/deployment/pepglad_fresh_execution_matrix_v1.csv'
DEFAULT_OUTPUT = ROOT / 'benchmark/results/pepglad_fresh_connectivity_v1.json'
POLICY_PATH = ROOT / 'benchmark/deployment/pepglad_fresh_attempt_policy_v1.json'
POLICY_SHA256 = '35cfee09b066d8aa465a75f66cc02142e602d33c0f0a9c1d7589cdd77a82cca5'
IMAGE_ID = 'sha256:4e7936534ca8ec60d9d19ef267d6fb2444e8889973ed17be7cb1adba8d421af2'

AUTHORIZED_JOB = {
    **legacy.AUTHORIZED_JOB,
    'job_id': POLICY.job_id,
    'adapter_config': 'pepglad_fresh_v1_3eqs_adapter',
    'execution_wave': 'pepglad_fresh_v1',
    'notes': 'Fresh single-attempt connectivity acceptance; historical jobs immutable',
}
AUTHORIZED_EXECUTION = {
    **legacy.AUTHORIZED_EXECUTION,
    'execution_id': 'exec_' + POLICY.job_id,
    'job_id': POLICY.job_id,
    'execution_wave': 'pepglad_fresh_v1',
    'runner': 'pepglad_fresh_acceptance_adapter',
    'output_root': 'benchmark_runs/pepglad_fresh_v1/pepglad/' + POLICY.job_id,
    'container_image_id': IMAGE_ID,
}


def load_authorized_job(path=DEFAULT_JOB_MANIFEST):
    return legacy._load_exact_authorized_row(path, AUTHORIZED_JOB, 'fresh job manifest')


def load_authorized_execution(path=DEFAULT_EXECUTION_MATRIX):
    return legacy._load_exact_authorized_row(path, AUTHORIZED_EXECUTION, 'fresh execution matrix')


def validate_execution_request(job, *, run_root=DEFAULT_RUN_ROOT):
    if dict(job) != AUTHORIZED_JOB:
        raise ValueError('request does not match the authorized fresh job')
    require_file_sha256(POLICY_PATH, POLICY_SHA256, 'fresh single-attempt authorization policy')
    logical = Path(os.path.abspath(run_root))
    if any(part in {'v0.34', 'v0.35'} for part in logical.parts):
        raise ValueError('historical run roots are not authorized for fresh execution')
    for node in [logical, *logical.parents]:
        if node.is_symlink():
            raise ValueError('fresh run root cannot contain a symlink')
    # Inspect all topology before any allocation; an existing attempt is terminal.
    if logical.exists():
        if not logical.is_dir():
            raise ValueError('fresh run root is already recorded as a non-directory')
        for node in logical.rglob('*'):
            if node.is_symlink():
                raise ValueError('fresh run root cannot contain a symlink')
            if node.name.startswith('attempt_'):
                raise ValueError(f'fresh attempt is already recorded: {node}')


def _read_command(arguments, timeout=45):
    try:
        result = subprocess.run(arguments, check=True, text=True, capture_output=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f'PepGLAD preflight exit {exc.returncode}: {exc.stderr.strip()}') from exc
    return result.stdout.strip()


def preflight():
    """Verify actual API, pinned assets and small CUDA imports before allocation."""
    require_clean_git_checkout(producer.SOURCE_ROOT, producer.SOURCE_COMMIT, 'PepGLAD source')
    require_file_sha256(producer.SOURCE_ENTRYPOINT, producer.SOURCE_ENTRYPOINT_SHA256, 'PepGLAD entrypoint')
    require_file_sha256(producer.MODEL_WEIGHTS, producer.MODEL_WEIGHTS_SHA256, 'PepGLAD checkpoint')
    require_file_sha256(ROOT / AUTHORIZED_JOB['target_pdb_path'], pepglad.TARGET_INPUT_SHA256, '3EQS input')
    for payload, expected in [
        (producer.OBSERVER_SCRIPT, producer.OBSERVER_SCRIPT_SHA256),
        (producer.INSTRUMENTER_SCRIPT, producer.INSTRUMENTER_SCRIPT_SHA256),
        (producer.SEED_WRAPPER_SCRIPT, producer.SEED_WRAPPER_SCRIPT_SHA256),
    ]:
        if hashlib.sha256(payload.encode()).hexdigest() != expected:
            raise ValueError('PepGLAD instrumentation pin mismatch')
    image_id = _read_command(['docker', 'image', 'inspect', producer.DEFAULT_IMAGE, '--format', '{{.Id}}'])
    if image_id != IMAGE_ID:
        raise ValueError('PepGLAD Docker image identity mismatch')
    server = _read_command(['docker', 'version', '--format', '{{.Server.Version}}'])
    check_code = (
        'import json,torch,torch_scatter,openmm,numpy,Bio,ray,pdbfixer; '
        'assert torch.cuda.is_available(); '
        'x=torch.ones(1,device="cuda"); assert x.item()==1; '
        'print("PEPGLAD_PREFLIGHT_JSON="+json.dumps(dict(torch=torch.__version__,cuda=torch.version.cuda,'
        'gpu=torch.cuda.get_device_name(0),torch_scatter=torch_scatter.__version__,'
        'ray=ray.__version__,openmm=openmm.__version__,'
        'numpy=numpy.__version__,biopython=Bio.__version__)))'
    )
    output = _read_command([
        'docker', 'run', '--rm', '--network', 'none', '--read-only', '--tmpfs', '/tmp',
        '--gpus', 'all', IMAGE_ID, '/opt/conda/envs/bench-pepglad/bin/python', '-c', check_code,
    ])
    records = [line.removeprefix('PEPGLAD_PREFLIGHT_JSON=') for line in output.splitlines()
               if line.startswith('PEPGLAD_PREFLIGHT_JSON=')]
    if len(records) != 1:
        raise ValueError('PepGLAD preflight did not emit exactly one environment record')
    environment = json.loads(records[0])
    return {'image_id': image_id, 'docker_server': server, 'environment': environment,
            'source_commit': producer.SOURCE_COMMIT, 'model_sha256': producer.MODEL_WEIGHTS_SHA256,
            'target_sha256': pepglad.TARGET_INPUT_SHA256}


class _PinnedImageAdapter:
    def __getattr__(self, name):
        return getattr(pepglad, name)

    def parse(self, job, attempt):
        return pepglad.parse(job, attempt, authorized_job_id=POLICY.job_id)

    def evaluate_candidate(self, job, candidate, runtime, raw):
        return pepglad.evaluate_candidate(job, candidate, runtime, raw, authorized_job_id=POLICY.job_id)

    def prepare(self, job, execution, attempt):
        command = pepglad.prepare(job, execution, attempt, authorized_job_id=POLICY.job_id)
        script = attempt / 'command.sh'
        payload = script.read_text()
        needle = producer.DEFAULT_IMAGE + ' bash -lc '
        if payload.count(needle) != 1:
            raise ValueError('cannot bind PepGLAD launch to immutable image ID')
        script.write_text(payload.replace(needle, IMAGE_ID + ' bash -lc ', 1))
        return command


def execute_authorized_job(job, *, execute, run_root=DEFAULT_RUN_ROOT):
    validate_execution_request(job, run_root=run_root)
    execution = load_authorized_execution()
    first = preflight()
    if not execute:
        return {'job_id': job['job_id'], 'status': 'validated', 'preflight': first}
    # Repeat under the same identity immediately before creating the only attempt.
    second = preflight()
    if first != second:
        raise ValueError('PepGLAD execution identity changed between preflight and launch')
    validate_execution_request(job, run_root=run_root)
    result = v034_runner.run_job(job, execution, run_root=Path(run_root), execute=True,
                                retry_failed=False, adapter=_PinnedImageAdapter(),
                                qc_evaluator=_PinnedImageAdapter().evaluate_candidate)
    attempt = Path(run_root) / 'pepglad' / job['job_id'] / 'attempt_001'
    (attempt / 'host_preflight.json').write_text(json.dumps({
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'uid': os.getuid(),
        'gid': os.getgid(), 'preflight': second, 'attempt_policy_sha256': POLICY_SHA256,
    }, indent=2, sort_keys=True) + '\n')
    return result


def acceptance_checks(bundle):
    from scripts import validate_benchmark_kb as independent
    attempt = Path(bundle['execution']['attempt_dir'])
    expected = DEFAULT_RUN_ROOT / 'pepglad' / POLICY.job_id / 'attempt_001'
    if attempt != expected:
        raise ValueError('fresh acceptance bundle is outside the authorized execution root')
    host = parser._strict_json_bytes(parser._capture_path(attempt / 'host_preflight.json', root=attempt).payload,
                                    'host preflight')
    command = parser._capture_path(attempt / 'command.sh', root=attempt).payload.decode()
    return {
        'independent_schema': independent._v035_bundle_schema_valid(bundle, policy=POLICY),
        'independent_raw_replay': independent._v035_raw_replay_valid(bundle, policy=POLICY),
        'historical_bindings': independent._v035_historical_bindings_valid(bundle),
        'immutable_image_launch': host.get('preflight', {}).get('image_id') == IMAGE_ID
            and command.count(IMAGE_ID + ' bash -lc ') == 1,
        'attempt_policy_binding': host.get('attempt_policy_sha256') == POLICY_SHA256
            and hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest() == POLICY_SHA256,
    }


def main(argv=None):
    argparser = argparse.ArgumentParser()
    modes = argparser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--execute', action='store_true')
    modes.add_argument('--accept', action='store_true')
    modes.add_argument('--verify', action='store_true')
    args = argparser.parse_args(argv)
    if args.verify:
        bundle = parser._strict_json_bytes(parser._capture_path(DEFAULT_OUTPUT, root=ROOT).payload,
                                          'fresh acceptance bundle')
        parser.validate_bundle(bundle, policy=POLICY)
        checks = acceptance_checks(bundle)
        if not all(checks.values()):
            raise ValueError(f'PepGLAD independent verification failed: {checks}')
        result = {'status': 'verified_bounded_connectivity', 'checks': checks,
                  'bundle': str(DEFAULT_OUTPUT), 'qc': bundle['qc']}
    elif args.accept:
        bundle = parser.build_bundle(run_root=DEFAULT_RUN_ROOT, job_manifest=DEFAULT_JOB_MANIFEST,
                                     execution_matrix=DEFAULT_EXECUTION_MATRIX, policy=POLICY)
        checks = acceptance_checks(bundle)
        if not all(checks.values()):
            raise ValueError(f'PepGLAD independent acceptance failed: {checks}')
        if DEFAULT_OUTPUT.exists():
            raise ValueError('fresh acceptance bundle already exists; publication is immutable')
        parser.publish_bundle(bundle, output_path=DEFAULT_OUTPUT, policy=POLICY)
        result = {'status': 'accepted_bounded_connectivity', 'checks': checks,
                  'bundle': str(DEFAULT_OUTPUT), 'qc': bundle['qc']}
    else:
        result = execute_authorized_job(load_authorized_job(), execute=args.execute)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get('status') in {'validated', 'passed', 'accepted_bounded_connectivity',
                                       'verified_bounded_connectivity'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
