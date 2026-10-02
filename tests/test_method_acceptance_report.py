import copy
import json
import pytest

from scripts.evaluate_method_acceptance import aggregate, METHODS


def inputs():
    historical = {'records': [], 'limitations': []}
    ledger = {'runs': [], 'downloads': []}
    policy = {'limits': {'gpu_seconds': 86400, 'cpu_heavy_wall_seconds': 86400, 'download_bytes': 50 * 1024**3}}
    return historical, ledger, policy


def test_quality_and_execution_evidence_are_both_required():
    history, ledger, policy = inputs()
    row = {'method': 'pepmlm', 'job_id': 'new', 'status': 'finished',
           'provenance': {'passed': True}, 'endpoint': {'passed': True, 'qualified_candidate_count': 1}}
    for field in ('provenance', 'endpoint'):
        bad = copy.deepcopy(row)
        bad[field]['passed'] = False
        report = aggregate(history, [bad], ledger, policy)
        assert report['passed_count'] == 0
        assert report['methods'][0]['new_attempt_count'] == 1
    assert aggregate(history, [row], ledger, policy)['passed_count'] == 1


def test_historical_claim_alone_never_passes():
    history, ledger, policy = inputs()
    history['records'] = [{'method': 'PepGLAD', 'job_id': 'historic', 'method_acceptance_status': 'pass',
                           'provenance_status': 'fail', 'candidate_quality_status': 'pass'}]
    assert aggregate(history, [], ledger, policy)['passed_count'] == 0
    history['records'][0]['provenance_status'] = 'pass'
    report = aggregate(history, [], ledger, policy)
    assert report['passed_count'] == 1
    assert report['methods'][3]['evidence_origin'] == 'reused'
    assert report['methods'][3]['new_attempt_count'] == 0


def structural_runtime_row():
    return {'method': 'dflow', 'job_id': 'native', 'status': 'finished',
            'provenance': {'passed': True}, 'endpoint': {
                'passed': False, 'qualified_candidate_count': 0, 'provenance_status': 'pass',
                'errors': [], 'checks': {'execution_completed': True, 'native_batch_complete': True,
                    'native_schedule': True, 'candidate_digest': True},
                'candidates': [{'checks': {key: True for key in (
                    'structure_readable', 'unique_atom_identity', 'binder_present',
                    'structure_sequence_consistency', 'requested_length', 'complete_endpoint_atoms')},
                    'candidate_quality_status': 'fail'}]}}


def test_complete_native_runtime_does_not_relabel_quality_failure():
    history, ledger, policy = inputs()
    row = structural_runtime_row()
    report = aggregate(history, [row], ledger, policy)
    assert report['passed_count'] == 1
    assert report['quality_passed_count'] == 0
    method = next(m for m in report['methods'] if m['method_id'] == 'dflow')
    assert method['runtime_status'] == 'pass'
    assert method['candidate_quality_status'] == 'not_passed'
    assert method['runtime_job_ids'] == ['native']
    assert method['qualified_job_ids'] == []
    assert method['new_attempts'][0]['endpoint']['passed'] is False


@pytest.mark.parametrize('failure', ['supervisor', 'native_batch', 'empty_checks', 'no_outputs',
                                    'unreadable', 'incomplete_atoms', 'endpoint_errors', 'provenance'])
def test_runtime_requires_complete_bound_native_outputs(failure):
    history, ledger, policy = inputs()
    row = structural_runtime_row()
    endpoint = row['endpoint']
    if failure == 'supervisor':
        row['provenance']['passed'] = False
    elif failure == 'native_batch':
        endpoint['checks']['native_batch_complete'] = False
    elif failure == 'empty_checks':
        endpoint['checks'] = {}
    elif failure == 'no_outputs':
        endpoint['candidates'] = []
    elif failure in ('unreadable', 'incomplete_atoms'):
        key = 'structure_readable' if failure == 'unreadable' else 'complete_endpoint_atoms'
        endpoint['candidates'][0]['checks'][key] = False
    elif failure == 'endpoint_errors':
        endpoint['errors'] = ['unbound output']
    else:
        endpoint['provenance_status'] = 'fail'
    assert aggregate(history, [row], ledger, policy)['passed_count'] == 0


def test_exit_zero_alone_is_not_runtime_acceptance():
    history, ledger, policy = inputs()
    row = {'method': 'dflow', 'job_id': 'exit_only', 'status': 'finished', 'exit_code': 0,
           'provenance': {'passed': True}}
    assert aggregate(history, [row], ledger, policy)['passed_count'] == 0


def test_diffpepbuilder_generation_without_required_postprocessing_is_incomplete():
    history, ledger, policy = inputs()
    row = structural_runtime_row()
    row['method'] = 'diffpepbuilder'
    assert aggregate(history, [row], ledger, policy)['passed_count'] == 0
    row['endpoint']['checks'].update(native_endpoint_contract=True, all_native_stages=True,
                                      native_no_skipped_relaxation=True)
    assert aggregate(history, [row], ledger, policy)['passed_count'] == 1


def test_all_ten_methods_required_not_ten_candidates():
    history, ledger, policy = inputs()
    rows = [{'method': 'pepmlm', 'job_id': str(i), 'status': 'finished',
             'provenance': {'passed': True}, 'endpoint': {'passed': True, 'qualified_candidate_count': 1}} for i in range(10)]
    report = aggregate(history, rows, ledger, policy)
    assert report['passed_count'] == 1 and not report['all_methods_accepted']
    for row, method in zip(rows, METHODS):
        row['method'] = method
    assert aggregate(history, rows, ledger, policy)['all_methods_accepted']


def test_failed_compute_and_live_reservations_still_consume_budget():
    history, ledger, policy = inputs()
    ledger['runs'] = [
        {'resource': 'gpu', 'status': 'finished', 'elapsed_seconds': 30, 'exit_code': 1},
        {'resource': 'gpu', 'status': 'cleanup_unconfirmed', 'reserved_seconds': 400},
        {'resource': 'cpu', 'status': 'finished', 'elapsed_seconds': 12, 'exit_code': 0}]
    ledger['downloads'] = [{'received_bytes': 100, 'max_bytes': 200, 'status': 'failed'},
                           {'max_bytes': 500, 'status': 'running'}]
    resources = aggregate(history, [], ledger, policy)['resources']
    assert resources['gpu_seconds']['remaining_unreserved'] == 86400 - 430
    assert resources['cpu_heavy_wall_seconds']['finished'] == 12
    assert resources['download_bytes']['accounted'] == 600


@pytest.mark.parametrize('count', [None, 0, -1, True, '1'])
def test_endpoint_pass_flag_requires_positive_integer_qualified_count(count):
    history, ledger, policy = inputs()
    row = {'method': 'pepmlm', 'job_id': 'new', 'status': 'finished',
           'provenance': {'passed': True}, 'endpoint': {'passed': True, 'qualified_candidate_count': count}}
    assert aggregate(history, [row], ledger, policy)['passed_count'] == 0


@pytest.mark.parametrize('invalid', [-1, float('nan'), True])
def test_invalid_resource_numbers_cannot_reduce_budget_use(invalid):
    history, ledger, policy = inputs()
    ledger['downloads'] = [{'budget_charge_bytes': invalid, 'max_bytes': 10}]
    with pytest.raises(ValueError, match='accounting value'):
        aggregate(history, [], ledger, policy)
    ledger['downloads'] = []
    ledger['attempt_adjustments'] = [{'method': 'dexdesign', 'additional_method_attempts': invalid}]
    with pytest.raises(ValueError, match='accounting value'):
        aggregate(history, [], ledger, policy)


def test_sequence_result_cannot_be_replaced_with_self_consistent_raw_evidence(tmp_path):
    from scripts.evaluate_method_acceptance import bound_sequence_result
    (tmp_path / 'raw').mkdir()
    result = {'native_candidates': ['ACDE'], 'candidate_hash': 'original'}
    (tmp_path / 'stdout.log').write_text(json.dumps(result))
    output = tmp_path / 'raw' / 'sequence_result.json'
    output.write_text(json.dumps(result, indent=2))
    bound_sequence_result(tmp_path, output.name)
    output.write_text(json.dumps({'native_candidates': ['AAAA'], 'candidate_hash': 'replacement'}))
    with pytest.raises(ValueError, match='supervisor-bound stdout'):
        bound_sequence_result(tmp_path, output.name)


def test_auxiliary_cpu_consumes_budget_and_requires_original_measurement(tmp_path):
    from scripts.evaluate_method_acceptance import apply_auxiliary_cpu_accounting, sha
    history, ledger, policy = inputs()
    measurement = tmp_path / 'pytest.json'
    measurement.write_text(json.dumps({'measured_wall_seconds': 30}))
    receipt = tmp_path / 'auxiliary.json'
    receipt.write_text(json.dumps({'estimated_unmetered_seconds': 60, 'estimate_is_measured': False,
        'estimate_basis': 'explicit conservative allowance', 'measured_runs': [{
            'receipt_path': str(measurement), 'receipt_sha256': sha(measurement), 'measured_wall_seconds': 30}]}))
    report = aggregate(history, [], ledger, policy)
    apply_auxiliary_cpu_accounting(report, receipt)
    assert report['resources']['cpu_heavy_wall_seconds']['finished'] == 90
    assert report['resources']['cpu_heavy_wall_seconds']['remaining_unreserved'] == 86400 - 90
    measurement.write_text(json.dumps({'measured_wall_seconds': 1}))
    with pytest.raises(ValueError, match='does not replay'):
        apply_auxiliary_cpu_accounting(aggregate(history, [], ledger, policy), receipt)
