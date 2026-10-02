#!/usr/bin/env python3
"""Read-only replay and compact reporting of ten native method acceptance endpoints."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.method_acceptance_quality import criteria_sha256, review_existing

METHODS = {
    'pepmlm': 'PepMLM', 'saltnpeppr': 'SaLT&PepPr',
    'diffpepbuilder': 'DiffPepBuilder', 'pepglad': 'PepGLAD',
    'dflow': 'D-Flow / PeptideDesign', 'pepmirror': 'PepMirror',
    'colabdesign': 'AfCycDesign / ColabDesign cyclic peptide',
    'dexdesign': 'DexDesign / OSPREY3',
    'rfdiffusion_proteinmpnn': 'RFdiffusion + ProteinMPNN', 'bindcraft': 'BindCraft',
}
ENDPOINTS = {
    'pepmlm': '原生目标序列条件生成；合法序列、指定长度及原生 PPL',
    'saltnpeppr': '原生 PPI 界面预测、guide-peptide 提取和优先化',
    'diffpepbuilder': '原生生成、SS 与 Amber/Rosetta 后处理；最终 full-atom complex',
    'pepglad': '原生 full-atom 生成及后处理；允许声明范围内 mixed L/D',
    'dflow': '原生 D-peptide 生成、angle purification 与 inverse mirror；输入分别记录来源与重叠边界',
    'pepmirror': '原生 mirror generation 与 mirror-back 的 D-peptide complex',
    'colabdesign': '原生三阶段优化、cyclic offset 及闭环结构',
    'dexdesign': '单个独立 IAS 的原生 preprocess→confspace→K* 搜索及序列/构象；明确限定任务范围',
    'rfdiffusion_proteinmpnn': 'target-conditioned backbone/TRB → ProteinMPNN FASTA',
    'bindcraft': '原生完整优化及验证；实际 native filters 接受的候选',
}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def validate_resource_numbers(ledger):
    def number(value, *, integer=False, positive=False):
        if type(value) not in ((int,) if integer else (int, float)) or not math.isfinite(value) or value < (1 if positive else 0):
            raise ValueError('Invalid nonnegative resource or positive attempt accounting value')
    for row in ledger['runs']:
        for key in ('elapsed_seconds', 'reserved_seconds', 'timeout_seconds'):
            if key in row:
                number(row[key])
        for key in ('threads', 'memory_gib'):
            if key in row:
                number(row[key], integer=True, positive=True)
    for row in ledger.get('attempt_adjustments', []):
        number(row['additional_method_attempts'], integer=True, positive=True)
    for row in ledger['downloads']:
        for key in ('max_bytes', 'received_bytes', 'budget_charge_bytes'):
            if key in row:
                number(row[key], integer=True)


def validate_accounting_evidence(ledger, policy):
    validate_resource_numbers(ledger)
    runs = {r['job_id']: r for r in ledger['runs']}
    if len(runs) != len(ledger['runs']):
        raise ValueError('Duplicate execution identity')
    def receipt(row):
        if sha(row['receipt_path']) != row['receipt_sha256']:
            raise ValueError('Accounting receipt digest mismatch')
        return read(row['receipt_path'])
    adjusted = set()
    for row in ledger.get('attempt_adjustments', []):
        evidence = receipt(row)
        source = runs[row['source_job_id']]
        if (row['source_job_id'] in adjusted or source['kind'] != 'preparation' or source['method'] != row['method']
                or any(evidence[k] != row[k] for k in ('adjustment_id', 'source_job_id', 'method', 'additional_method_attempts'))):
            raise ValueError('Attempt adjustment source mismatch')
        adjusted.add(row['source_job_id'])
        parent = Path(source['attempt_dir'])
        if (evidence['original_run_result_sha256'] != sha(parent / 'run_result.json')
                or evidence['original_job_sha256'] != sha(parent / 'job.json')):
            raise ValueError('Attempt adjustment original execution changed')
    for row in ledger.get('incidents', []):
        evidence = receipt(row)
        if evidence['incident_id'] != row['incident_id']:
            raise ValueError('Incident identity mismatch')
    identities = set()
    for row in ledger['downloads']:
        if row['download_id'] in identities:
            raise ValueError('Duplicate download identity')
        identities.add(row['download_id'])
        if row['status'] == 'estimated_incident':
            evidence = receipt(row)
            if (evidence['source_job_id'] != row['source_job_id'] or row['source_job_id'] not in runs
                    or evidence['budget_charge_bytes'] != row['budget_charge_bytes']
                    or evidence['accounting_basis'] != row['accounting_basis']):
                raise ValueError('Estimated download incident binding mismatch')
            for item in evidence['evidence'].values():
                if sha(item['path']) != item['sha256']:
                    raise ValueError('Estimated download original evidence changed')
        elif row['status'] != 'running':
            path = Path(policy['asset_root']) / row['download_id'] / 'download_receipt.json'
            if read(path) != row:
                raise ValueError('Download receipt does not replay')


def supervisor_checks(row, policy_path):
    """Recompute supervisor bindings; a success flag alone never qualifies a run."""
    out = Path(row['attempt_dir'])
    job, result, launch = (read(out / name) for name in ('job.json', 'run_result.json', 'launch.json'))
    policy_sha = sha(policy_path)
    checks = {
        'ledger_finished': row['status'] == 'finished',
        'native_process_exit_zero': result['exit_code'] == row.get('exit_code') == 0,
        'normal_completion': result['termination_reason'] == row.get('termination_reason') == 'completed',
        'job_identity': job['job_id'] == result['job_id'] == row['job_id'],
        'method_identity': job['method'] == result['method'] == row['method'],
        'attempt_identity': Path(result['attempt_dir']).resolve() == out.resolve(),
        'job_hash': result['job_sha256'] == sha(out / 'job.json'),
        'policy_hash': result['policy_sha256'] == launch['policy_sha256'] == policy_sha,
        'policy_snapshot': read(out / 'policy.json') == read(policy_path),
        'stdout_hash': result['stdout_sha256'] == sha(out / 'stdout.log'),
        'stderr_hash': result['stderr_sha256'] == sha(out / 'stderr.log'),
        'elapsed_binding': result['elapsed_seconds'] == row.get('elapsed_seconds'),
        'prospective_quality_contract': bool(job.get('quality_contract')),
        'input_pins_present': bool(job.get('input_sha256')),
    }
    argv = [v.replace('{attempt_dir}', str(out)).replace('{asset_root}', read(policy_path)['asset_root'])
            .replace('{container_name}', 'pd-ma-' + job['job_id']) for v in job['argv']]
    checks['command_binding'] = launch['argv'] == argv
    if 'cleanup' in result or 'cleanup' in row:
        checks['recorded_cleanup_confirmed'] = result.get('cleanup') == row.get('cleanup') and result.get('cleanup', {}).get('confirmed') is True
    if (out / 'runner_snapshot.py').exists() or 'runner_snapshot' in launch:
        checks['runner_snapshot_binding'] = sha(out / 'runner_snapshot.py') == launch['runner_sha256']
    if argv[:2] == ['docker', 'run']:
        from scripts.method_acceptance_runner import parse_docker_run
        parsed = parse_docker_run(argv)
        checks['immutable_image'] = re.fullmatch(r'sha256:[0-9a-f]{64}', parsed['image']) is not None
        checks['offline_asset_binding'] = parsed['options'].get('--network') == ['none']
        checks['container_resource_binding'] = all(parsed['options'].get(key) == [value] for key, value in {
            '--name': 'pd-ma-' + job['job_id'], '--memory': f"{job['memory_gib']}g",
            '--cpus': str(job['threads']),
        }.items())
    pin_errors = []
    for path, expected in job.get('input_sha256', {}).items():
        try:
            if sha(path) != expected:
                pin_errors.append(path)
        except OSError:
            pin_errors.append(path)
    checks['input_pin_replay'] = not pin_errors
    return {'passed': all(checks.values()), 'checks': checks, 'pin_errors': pin_errors,
            'job_sha256': sha(out / 'job.json'), 'result_sha256': sha(out / 'run_result.json')}


def bound_sequence_result(out, filename):
    """Bind a sequence result to stdout covered by the supervisor's log digest."""
    if read(out / 'raw' / filename) != read(out / 'stdout.log'):
        raise ValueError('Sequence result does not match supervisor-bound stdout')


def endpoint_replay(row):
    out = Path(row['attempt_dir'])
    job = read(out / 'job.json')
    if row['method'] == 'pepmlm':
        from scripts.method_acceptance_sequence_replay import verify_pepmlm_binding
        binding = verify_pepmlm_binding(out)
        if binding['passed'] is not True:
            raise ValueError('PepMLM post-execution output capture does not replay')
        from scripts.method_acceptance_sequence import verify
        argv = job['argv']
        config = read(argv[argv.index('--config') + 1])
        result = verify(config, out / 'raw')
        result['output_binding'] = binding
        return result
    if row['method'] == 'saltnpeppr':
        bound_sequence_result(out, 'saltnpeppr_result.json')
        from scripts.method_acceptance_saltnpeppr import verify
        argv = job['argv']
        config = read(argv[argv.index('--config') + 1])
        return verify(config, out / 'raw')
    if row['method'] in ('diffpepbuilder', 'dflow', 'colabdesign'):
        from scripts.method_acceptance_structural import verify
        result = verify(out)
        result['passed'] = result['method_acceptance_status'] == 'pass'
        result['qualified_candidate_count'] = result['qualified_candidates']
        return result
    if row['method'] == 'bindcraft':
        from scripts.method_acceptance_bindcraft_replay import verify
        return verify(out)
    if row['method'] == 'dexdesign':
        if 'native_scope' in job['quality_contract']:
            from scripts.method_acceptance_dexdesign_collect import verify
        else:
            from scripts.method_acceptance_dexdesign import verify
        return verify(out)
    raise ValueError('Native endpoint verifier unavailable for ' + row['method'])


def quality_endpoint_passed(endpoint):
    count = endpoint.get('qualified_candidate_count')
    return endpoint.get('passed') is True and type(count) is int and count > 0


def runtime_endpoint_passed(method, endpoint):
    """A qualified endpoint suffices; structural QC failures need full native proof.

    Exit zero, a pass flag, or readable intermediate files alone never suffice.
    Geometry/chirality quality remains reported separately under unchanged QC.
    """
    if quality_endpoint_passed(endpoint):
        return True
    if method not in ('diffpepbuilder', 'dflow', 'colabdesign'):
        return False
    checks = endpoint.get('checks', {})
    if method == 'diffpepbuilder' and not all(checks.get(key) is True for key in
            ('native_endpoint_contract', 'all_native_stages', 'native_no_skipped_relaxation')):
        return False
    candidates = endpoint.get('candidates', [])
    output_checks = ('structure_readable', 'unique_atom_identity', 'binder_present',
                     'structure_sequence_consistency', 'requested_length', 'complete_endpoint_atoms')
    return (endpoint.get('provenance_status') == 'pass' and
            endpoint.get('errors') == [] and bool(checks) and
            checks.get('execution_completed') is True and
            all(value is True for value in checks.values()) and bool(candidates) and
            all(all(c.get('checks', {}).get(key) is True for key in output_checks)
                for c in candidates))


def aggregate(historical, new_runs, ledger, policy):
    """Separate native runtime completion from unchanged candidate-quality results."""
    validate_resource_numbers(ledger)
    methods = []
    for slug, name in METHODS.items():
        reused = [r for r in historical['records'] if r['method'] == name and
                  r.get('provenance_status') == 'pass' and r.get('candidate_quality_status') == 'pass' and
                  r.get('method_acceptance_status') == 'pass']
        attempts = [r for r in new_runs if r['method'] == slug]
        accepted = [r for r in attempts if r.get('status') == 'finished' and r.get('provenance', {}).get('passed') is True and
                    quality_endpoint_passed(r.get('endpoint', {}))]
        runtime = [r for r in attempts if r.get('status') == 'finished' and r.get('provenance', {}).get('passed') is True and
                   runtime_endpoint_passed(slug, r.get('endpoint', {}))]
        runtime_passed = bool(reused or runtime)
        qualified = bool(reused or accepted)
        running = any(r['status'] in ('running', 'cleanup_unconfirmed') for r in attempts)
        adjustments = [r for r in ledger.get('attempt_adjustments', []) if r['method'] == slug]
        adjusted_count = sum(r['additional_method_attempts'] for r in adjustments)
        methods.append({'method_id': slug, 'method': name, 'endpoint': ENDPOINTS[slug],
            'status': 'pass' if runtime_passed else ('running' if running else 'not_passed'),
            'runtime_status': 'pass' if runtime_passed else ('running' if running else 'not_passed'),
            'candidate_quality_status': 'pass' if qualified else 'not_passed',
            'evidence_origin': 'reused' if reused else ('new_native_execution' if runtime else 'none_complete'),
            'runtime_job_ids': [r['job_id'] for r in reused + runtime],
            'qualified_job_ids': [r['job_id'] for r in reused + accepted],
            'new_attempt_count': len(attempts) + adjusted_count, 'new_attempts': attempts,
            'attempt_adjustments': adjustments,
            'historical_reviews': [r for r in historical['records'] if r['method'] == name]})
        entry = methods[-1]
        if qualified:
            entry['detail'] = '执行链、原生终点与候选质量检查通过'
        elif runtime_passed:
            entry['detail'] = '执行链和原生终点通过；候选质量未通过，保留后续研究'
        elif running:
            entry['detail'] = '任务运行中或清理尚未确认'
        elif attempts:
            last = attempts[-1]
            entry['detail'] = (last.get('verification_error') or
                ('原生产物或证据尚未达到验收标准' if last.get('exit_code') == 0
                 else f"任务未完成，exit={last.get('exit_code')}; {last.get('termination_reason', '')}"))
        else:
            entry['detail'] = '尚无完整合格任务证据'
    resources = {}
    for resource, limit in [('gpu', 'gpu_seconds'), ('cpu', 'cpu_heavy_wall_seconds')]:
        rows = [r for r in ledger['runs'] if r['resource'] == resource]
        finished = sum(r.get('elapsed_seconds', 0) for r in rows if r['status'] == 'finished')
        reserved = sum(r['reserved_seconds'] for r in rows if r['status'] != 'finished')
        resources[limit] = {'finished': finished, 'active_reserved': reserved,
                            'limit': policy['limits'][limit], 'remaining_unreserved': policy['limits'][limit] - finished - reserved}
    resources['download_bytes'] = {'accounted': sum(r.get('budget_charge_bytes', r.get('received_bytes', r['max_bytes'])) for r in ledger['downloads']),
                                  'limit': policy['limits']['download_bytes'],
                                  'estimated_incidents': [r for r in ledger['downloads'] if r.get('status') == 'estimated_incident']}
    count = sum(row['status'] == 'pass' for row in methods)
    quality_count = sum(row['candidate_quality_status'] == 'pass' for row in methods)
    return {'schema_version': 'native_method_acceptance_v2', 'criteria_sha256': criteria_sha256(),
            'method_count': len(methods), 'passed_count': count, 'all_methods_accepted': count == 10,
            'quality_passed_count': quality_count, 'all_methods_quality_accepted': quality_count == 10,
            'scope': 'method_native_runtime_only_quality_reported_separately', 'methods': methods,
            'resources': resources, 'limitations': historical['limitations'] + [
                'Sequence and structural integrity checks do not establish affinity, biological activity or experimental validation.',
                'Inputs and endpoints differ by method; this is not a fair benchmark or method ranking.',
                'Host environments record interpreter, selected dependency versions and key-file hashes; the complete installed package trees are not content-pinned.',
                'PepMLM and BindCraft retained-output captures are explicitly post-execution observations, not producer-time captures or cryptographic signatures.',
                'Failed and incomplete attempts remain visible and consume the authorized attempt budget.']}


def apply_auxiliary_cpu_accounting(result, path):
    """Charge separately observed audits and explicitly estimated unmetered work."""
    if not path.is_file():
        result['limitations'].append('Method-ledger CPU wall excludes separately reported read-only audits and regression overhead.')
        return
    record = read(path)
    estimate = record['estimated_unmetered_seconds']
    values = [estimate] + [r['measured_wall_seconds'] for r in record['measured_runs']]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid auxiliary CPU charge')
    if record['estimate_is_measured'] is not False or not record['estimate_basis']:
        raise ValueError('Auxiliary CPU estimate must be disclosed')
    for row in record['measured_runs']:
        if (sha(row['receipt_path']) != row['receipt_sha256'] or
                read(row['receipt_path'])['measured_wall_seconds'] != row['measured_wall_seconds']):
            raise ValueError('Auxiliary CPU measurement receipt does not replay')
    measured = sum(values[1:])
    cpu = result['resources']['cpu_heavy_wall_seconds']
    cpu['method_ledger_finished'] = cpu['finished']
    cpu['measured_audit_seconds'] = measured
    cpu['estimated_unmetered_seconds'] = estimate
    cpu['finished'] += measured + estimate
    cpu['remaining_unreserved'] -= measured + estimate
    result['auxiliary_cpu_accounting'] = {'path': str(path), 'sha256': sha(path), 'record': record}


def evaluate(root=ROOT):
    root = Path(root)
    scope_path = root / 'benchmark/deployment/method_runtime_scope_v2.json'
    scope = read(scope_path)
    if scope['runtime_required'] is not True or scope['quality_required_for_runtime'] is not False:
        raise ValueError('Unsupported runtime assessment scope')
    policy_path = root / 'benchmark/deployment/method_acceptance_policy_v1.json'
    policy = read(policy_path)
    ledger_path = root / policy['run_root'] / 'resource_ledger.json'
    ledger_payload = ledger_path.read_bytes()
    ledger = json.loads(ledger_payload)
    if ledger['policy_sha256'] != sha(policy_path):
        raise ValueError('Ledger policy binding mismatch')
    validate_accounting_evidence(ledger, policy)
    historical = review_existing(root)
    new_runs = []
    for row in ledger['runs']:
        if row['kind'] != 'method':
            continue
        record = {key: row[key] for key in ('job_id', 'method', 'attempt_dir', 'status')}
        if row['status'] == 'finished':
            record.update(exit_code=row['exit_code'], elapsed_seconds=row['elapsed_seconds'],
                          termination_reason=row['termination_reason'])
            try:
                record['provenance'] = supervisor_checks(row, policy_path)
                if row['exit_code'] == 0:
                    record['endpoint'] = endpoint_replay(row)
            except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
                record['verification_error'] = f'{type(exc).__name__}: {exc}'
        new_runs.append(record)
    result = aggregate(historical, new_runs, ledger, policy)
    apply_auxiliary_cpu_accounting(result, root / policy['run_root'] / 'audit/auxiliary_cpu_accounting_v1.json')
    from scripts.method_acceptance_runner import disk_bytes
    result['resources']['disk_bytes'] = {'used': disk_bytes([root / policy['run_root'], Path(policy['asset_root'])]),
                                       'limit': policy['limits']['new_disk_bytes']}
    result['accounting_incidents'] = ledger.get('incidents', [])
    diagnostics = root / policy['run_root'] / 'diagnostics'
    for row in result['methods']:
        matches = sorted(diagnostics.glob(row['method_id'] + '*.json')) if diagnostics.is_dir() else []
        row['diagnostic_evidence'] = [{'path': str(p), 'sha256': sha(p), 'record': read(p)} for p in matches]
        if row['method_id'] == 'dflow' and matches and row['candidate_quality_status'] != 'pass':
            completed = [a for a in row['new_attempts'] if a.get('exit_code') == 0]
            candidates = [c for a in completed for c in a.get('endpoint', {}).get('candidates', [])]
            remaining = max(0, policy['limits']['attempts_per_method'] - row['new_attempt_count'])
            row['detail'] = (f"运行验收 {row['runtime_status']}；{len(completed)} 次原生运行退出 0；已重放 {len(candidates)} 个候选，尚无质量合格候选；"
                             f"剩余 {remaining} 次尝试，未追加外部算法")
            if row['status'] == 'running':
                row['detail'] += '；新任务运行中'
        if row['method_id'] == 'dexdesign' and row['status'] == 'pass':
            row['detail'] = 'ALA5 单个原生 IAS 搜索通过；1 个候选仅修正残基标签后通过质量检查，序列为 11 个 Ala；其余 10 组未完成'
    salt = next(r for r in result['methods'] if r['method_id'] == 'saltnpeppr')
    salt['preparation_evidence'] = {}
    for name in ('use_scope.json', 'native_source_final_v1.json', 'readiness.json', 'source_search_v2.json'):
        path = root / policy['run_root'] / 'saltnpeppr/preparation' / name
        if path.is_file():
            salt['preparation_evidence'][name] = {'path': str(path), 'sha256': sha(path), 'record': read(path)}
    result['limitations'].append('DexDesign acceptance covers one independent native IAS search (ALA5, 19 sequence outcomes), not all 11 IAS groups or the entire paper; residue-label-only repair retains original coordinates and raw files.')
    result['policy_sha256'] = sha(policy_path)
    if scope['execution_policy_sha256'] != result['policy_sha256']:
        raise ValueError('Runtime scope execution-policy binding mismatch')
    result['assessment_scope_sha256'] = sha(scope_path)
    result['resource_ledger_sha256'] = hashlib.sha256(ledger_payload).hexdigest()
    return result


def evidence_index(result):
    return {key: result[key] for key in ('schema_version', 'criteria_sha256', 'policy_sha256',
                                         'resource_ledger_sha256', 'assessment_scope_sha256',
                                         'quality_passed_count', 'passed_count', 'all_methods_accepted')} | {
        'replay_sha256': hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False,
                                                  separators=(',', ':')).encode()).hexdigest()}


def render(result, root=ROOT):
    root = Path(root)
    report = root / 'ops/acceptance/method_runtime_acceptance_v1'
    report.with_suffix('.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (root / 'benchmark/results/method_acceptance_execution_index_v1.json').write_text(
        json.dumps(evidence_index(result), indent=2, sort_keys=True) + '\n')
    lines = ['# 10 方法代码与环境运行验收', '',
             f"运行验收 **{result['passed_count']}/10**；另列候选完整性质量检查 **{result['quality_passed_count']}/10**。", '',
             '按用户“初步只需要跑通代码和环境，后续再大量比较”的修订，运行通过须有真实原生终点及完整执行证据；质量结果不阻塞本阶段。原执行政策与质量阈值保持原样。', '',
             '未完成公平 Benchmark、统一评分、方法排名或实验验证。', '',
             '| 方法 | 运行 | 候选质量 | 证据 | 新尝试 | 说明 |', '|:---|:---|:---|:---|---:|:---|']
    for row in result['methods']:
        detail = row['detail'].replace('|', '/').replace('\n', ' ')
        lines.append(f"| {row['method']} | `{row['runtime_status']}` | `{row['candidate_quality_status']}` | {row['evidence_origin']} | {row['new_attempt_count']} | {detail} |")
    lines += ['', '详细原始路径、逐项检查与失败记录见同名 JSON。历史 attempt 未覆盖。', '', '## 阶段资源', '']
    for name in ('gpu_seconds', 'cpu_heavy_wall_seconds'):
        data = result['resources'][name]
        lines.append(f"- `{name}`：已计入额度 {data['finished']:.3f} s；活动任务预留 {data['active_reserved']} s；上限 {data['limit']} s。")
        if 'method_ledger_finished' in data:
            lines.append(f"  - CPU 构成：方法/准备账本 {data['method_ledger_finished']:.3f} s；单独记录的审计/回归 {data['measured_audit_seconds']:.3f} s；未逐命令计时的辅助检查保守估计扣款 {data['estimated_unmetered_seconds']} s，后者不是实测耗时。")
        elif name == 'cpu_heavy_wall_seconds':
            lines.append('  - 此数为方法/准备账本，不含另列的只读审计与回归开销。')
    data = result['resources']['download_bytes']
    lines.append(f"- 下载：账本累计 {data['accounted']} bytes；上限 {data['limit']} bytes。")
    if data['estimated_incidents']:
        lines.append('- 下载额度包含 D-Flow 隐式下载的 3 GiB 保守估计扣款；实际传输字节与临时文件 SHA 未恢复，不表述为实测。')
    data = result['resources']['disk_bytes']
    lines.append(f"- 新增目录当前占用：{data['used']} bytes；上限 {data['limit']} bytes。")
    lines += ['', '报告由 `python scripts/evaluate_method_acceptance.py render` 生成；`check` 仅重放，不写文件。', '']
    report.with_suffix('.md').write_text('\n'.join(lines))
    fields = ['method_id', 'method', 'endpoint', 'status', 'runtime_status', 'candidate_quality_status', 'evidence_origin', 'new_attempt_count', 'runtime_job_ids', 'qualified_job_ids', 'detail']
    with (root / 'benchmark/results/method_acceptance_matrix_v1.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in result['methods']:
            writer.writerow({k: ';'.join(row[k]) if k in ('qualified_job_ids', 'runtime_job_ids') else row[k] for k in fields})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'render'))
    args = parser.parse_args()
    result = evaluate()
    if args.action == 'render':
        render(result)
    print(json.dumps({'passed_count': result['passed_count'], 'quality_passed_count': result['quality_passed_count'], 'all_methods_accepted': result['all_methods_accepted'],
                      'methods': [{k: r[k] for k in ('method_id', 'status', 'new_attempt_count')} for r in result['methods']]}, indent=2))
    return 0 if result['all_methods_accepted'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
