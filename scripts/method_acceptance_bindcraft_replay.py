#!/usr/bin/env python3
"""Post-execution capture and read-only replay for the native BindCraft run.

The capture is explicitly made by the observer after execution, not represented
as a native runtime record. It binds the complete retained raw-output tree.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.method_acceptance_runner import sha
from scripts.method_acceptance_bindcraft import assess
from scripts.method_acceptance_quality import SIDECHAINS, _read_atoms, criteria
from scripts.v034_adapters.common import AA3_TO_1, parse_pdb_chain_sequences


def _csv_equivalent(left, right):
    """Replay pandas' numeric CSV rewrite, without tolerating changed values."""
    if left == right:
        return True
    try:
        a, b = float(left), float(right)
        return math.isfinite(a) and math.isfinite(b) and a == b
    except (ValueError, TypeError):
        return False


def native_best_model(row, active_models):
    # Upstream constructs pLDDT keys in model order 1..5; max keeps the first
    # encountered model on ties (bindcraft.py:369-379).
    values = {}
    for model in range(1, 6):
        value = row.get(f'{model}_pLDDT', '')
        if value not in ('', None):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError('nonfinite native model pLDDT')
            values[model] = number
    if set(values) != set(active_models):
        raise ValueError('native prediction model coverage differs from settings')
    return max(values, key=values.get)


def target_chain_binding(candidate, target):
    expected = parse_pdb_chain_sequences(target).get('A', '')
    sequences = parse_pdb_chain_sequences(candidate)
    if not expected or set(sequences) != {'A', 'B'} or sequences.get('A') != expected:
        return False
    residues = {}
    for atom in _read_atoms(candidate.read_bytes()):
        if atom.chain == 'A':
            row = residues.setdefault(atom.residue_key, {})
            if atom.atom_name in row:
                return False
            row[atom.atom_name] = atom
    for row in residues.values():
        names = {a.resname for a in row.values()}
        if len(names) != 1 or next(iter(names)) not in AA3_TO_1:
            return False
        aa = AA3_TO_1[next(iter(names))]
        required = {'N', 'CA', 'C', 'O'}
        required.update(atom for bond in SIDECHAINS[aa].split() for atom in bond.split('-'))
        if not required <= row.keys():
            return False
    return bool(residues)


def accepted_lineage(attempt, target, active_models):
    """Bind final rows to native MPNN rows, exact selected model and full target."""
    designs = attempt / 'raw/designs'
    with (designs / 'final_design_stats.csv').open(newline='') as stream:
        final_rows = list(csv.DictReader(stream))
    with (designs / 'mpnn_design_stats.csv').open(newline='') as stream:
        mpnn_rows = list(csv.DictReader(stream))
    records = []
    for row in final_rows:
        name = row.get('Design', '')
        checks = {}
        record = {'design': name, 'checks': checks}
        try:
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
                raise ValueError('invalid native design identity')
            matches = [r for r in mpnn_rows if r.get('Design') == name]
            checks['unique_native_mpnn_row'] = len(matches) == 1
            checks['unique_final_row'] = sum(r.get('Design') == name for r in final_rows) == 1
            if len(matches) != 1:
                raise ValueError('missing or duplicate native MPNN row')
            original = matches[0]
            comparable = {k: v for k, v in row.items() if k != 'Rank'}
            checks['final_row_matches_native_mpnn'] = (set(comparable) == set(original)
                and all(_csv_equivalent(comparable[k], original[k]) for k in original))
            selected = native_best_model(original, active_models)
            record['native_selected_model'] = selected
            filename = f'{name}_model{selected}.pdb'
            accepted = designs / 'Accepted' / filename
            original_pdb = designs / 'MPNN/Relaxed' / filename
            matches = list((designs / 'Accepted').glob(name + '_model*.pdb'))
            checks['exact_native_selected_model'] = matches == [accepted]
            checks['accepted_is_native_relaxed_copy'] = (accepted.is_file() and original_pdb.is_file()
                and sha(accepted) == sha(original_pdb))
            checks['complete_target_A_binding'] = accepted.is_file() and target_chain_binding(accepted, target)
            checks['native_binder_sequence_binding'] = (accepted.is_file()
                and parse_pdb_chain_sequences(accepted).get('B') == original.get('Sequence'))
            record['accepted_path'] = str(accepted)
            record['native_relaxed_path'] = str(original_pdb)
            if accepted.is_file():
                record['accepted_sha256'] = sha(accepted)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'
        record['passed'] = bool(checks) and all(checks.values()) and 'error' not in record
        records.append(record)
    return records


def inventory(attempt):
    attempt = Path(attempt)
    result = {}
    for path in sorted((attempt / 'raw').rglob('*')):
        if path.is_symlink():
            raise ValueError('Raw output symlink is not allowed')
        if path.is_file():
            result[str(path.relative_to(attempt))] = sha(path)
    return result


def capture(attempt):
    attempt = Path(attempt)
    run = json.loads((attempt / 'run_result.json').read_text())
    if run['method'] != 'bindcraft':
        raise ValueError('Wrong method')
    data = {'capture_role': 'post_execution_observer', 'captured_at': datetime.now(timezone.utc).isoformat(),
            'job_sha256': sha(attempt / 'job.json'), 'run_result_sha256': sha(attempt / 'run_result.json'),
            'raw_sha256': inventory(attempt)}
    with (attempt / 'output_capture.json').open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return data


def verify(attempt):
    attempt = Path(attempt).resolve()
    result = {'passed': False, 'checks': {}, 'records': [], 'qualified_candidate_count': 0}
    checks = result['checks']
    try:
        captured = json.loads((attempt / 'output_capture.json').read_text())
        run = json.loads((attempt / 'run_result.json').read_text())
        job = json.loads((attempt / 'job.json').read_text())
        raw = attempt / 'raw'
        checks['output_capture_binding'] = (captured['capture_role'] == 'post_execution_observer'
            and captured['run_result_sha256'] == sha(attempt / 'run_result.json')
            and captured['job_sha256'] == sha(attempt / 'job.json')
            and bool(captured['raw_sha256']) and captured['raw_sha256'] == inventory(attempt))
        checks['native_execution_success'] = run['exit_code'] == 0 and run['termination_reason'] == 'completed'
        completion = json.loads((raw / 'native_completed.json').read_text())
        checks['native_completion_binding'] = completion['completed'] is True and completion['settings_sha256'] == sha(raw / 'settings.json')
        env = json.loads((raw / 'environment.json').read_text())
        argv = job['argv']
        config_path = Path(argv[argv.index('--config') + 1])
        config = json.loads(config_path.read_text())
        checks['config_binding'] = env['config_sha256'] == sha(config_path)
        source = Path(config['source'])
        checks['entrypoint_binding'] = completion['entrypoint_sha256'] == env['entrypoint_sha256'] == sha(source / 'bindcraft.py')
        checks['entrypoint_prospective_pin'] = job['input_sha256'].get(str(source / 'bindcraft.py')) == env['entrypoint_sha256']
        checks['candidate_criteria_binding'] = job['quality_contract']['candidate_integrity'] == criteria()
        checks['native_filter_binding'] = env['filter_sha256'] == sha(raw / 'filters.json') == job['quality_contract']['native_filters_sha256']
        expected = json.loads((source / 'settings_advanced/default_4stage_multimer.json').read_text())
        expected.update(max_trajectories=config['max_trajectories'],save_design_animations=False,
            save_design_trajectory_plots=False,zip_animations=False,zip_plots=False,af_params_dir=config['parameter_root'])
        checks['complete_native_optimization_settings'] = (json.loads((raw / 'advanced.json').read_text()) == expected
                                                          and env['advanced_sha256'] == sha(raw / 'advanced.json'))
        settings = json.loads((raw / 'settings.json').read_text())
        target = source / 'example/PDL1.pdb'
        checks['target_source_input_sha256'] = target.is_file() and job['input_sha256'].get(str(target)) == sha(target)
        expected_settings = {'design_path':str(raw/'designs')+'/', 'binder_name':'PDL1_native_acceptance',
            'starting_pdb':str(target), 'chains':'A', 'target_hotspot_residues':'56',
            'lengths':[65,100], 'number_of_final_designs':1}
        checks['prospective_target_settings'] = settings == expected_settings
        native = assess(attempt)
        result['records'] = native['records']
        lineage = accepted_lineage(attempt, target, (1,2) if expected['use_multimer_design'] else (1,2,3,4,5))
        checks['native_candidate_record_alignment'] = (len(lineage) == len(result['records'])
            and all(a['design'] == b['design'] for a,b in zip(lineage,result['records'])))
        for record, binding in zip(result['records'], lineage):
            record['native_lineage'] = binding
            record['pass'] = record['pass'] and binding['passed']
        checks['all_reported_native_lineages'] = bool(lineage) and all(r['passed'] for r in lineage)
        result['qualified_candidate_count'] = sum(r['pass'] for r in result['records'])
        checks['native_accepted_candidate_with_integrity'] = native['native_completed'] and result['qualified_candidate_count'] > 0
        result['passed'] = all(checks.values())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture','verify'))
    parser.add_argument('attempt',type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.attempt) if args.action == 'capture' else verify(args.attempt), indent=2))


if __name__ == '__main__':
    main()
