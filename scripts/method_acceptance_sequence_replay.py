#!/usr/bin/env python3
"""Explicit post-execution observation of the retained PepMLM acceptance run.

The producer printed a three-field summary after a container banner. This
observer does not claim that its raw-file hashes were captured during execution.
It additionally checks the earlier independent replay record and the raw result
digest reported in this session before this observer existed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EARLIER_RESULT_SHA256='74e74ffa411b8efe91c18a117d4d7f170bc02e711b3f0b65a44f1dd2072a2286'
EARLIER_VALIDATION_SHA256='c39acd0c92dd0c52be28f605454107ba30bc54d1bb3383a752f446a4d6dd670b'
JOB_ID='pepmlm_native_6vme_seed42_v1'
SUMMARY_FIELDS={'method','passed','selected_candidate_id'}
SCHEMA='pepmlm_post_execution_observer_v1'


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):digest.update(block)
    return digest.hexdigest()


def regular(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError(f'required regular evidence file: {path}')
    return path


def read(path):
    return json.loads(regular(path).read_text())


def summary(stdout):
    lines=regular(stdout).read_text().splitlines()
    nonempty=[line for line in lines if line.strip()]
    if not nonempty:raise ValueError('missing native stdout summary')
    try:payload=json.loads(nonempty[-1])
    except ValueError as exc:raise ValueError('last nonempty stdout line is not the native summary') from exc
    if (not isinstance(payload,dict) or set(payload)!=SUMMARY_FIELDS
            or payload['method']!='PepMLM' or payload['passed'] is not True
            or not isinstance(payload['selected_candidate_id'],str) or not payload['selected_candidate_id']):
        raise ValueError('native stdout must end with the exact successful three-field summary')
    return payload


def raw_hashes(attempt):
    raw=Path(attempt)/'raw'
    if raw.is_symlink() or not raw.is_dir():raise ValueError('raw evidence directory missing or symlinked')
    hashes={}
    for path in sorted(raw.rglob('*')):
        if path.is_symlink():raise ValueError('raw evidence contains a symlink')
        if path.is_file():hashes[str(path.relative_to(raw))]=sha(path)
    if not {'sequence_result.json','native_candidates.json'}.issubset(hashes):
        raise ValueError('required native PepMLM output missing')
    return hashes


def live_evidence(attempt):
    attempt=Path(attempt).resolve()
    prior=attempt.parent.parent/'preparation/replay_validation.json'
    job=read(attempt/'job.json');run=read(attempt/'run_result.json');raw=read(attempt/'raw/sequence_result.json')
    prior_data=read(prior);last=summary(attempt/'stdout.log');hashes=raw_hashes(attempt)
    checks={
        'original_job_identity':job.get('method')=='pepmlm' and job.get('job_id')==run.get('job_id')==JOB_ID,
        'original_native_success':run.get('method')=='pepmlm' and run.get('exit_code')==0 and run.get('termination_reason')=='completed',
        'original_attempt_binding':Path(run.get('attempt_dir','')).resolve()==attempt,
        'original_job_hash':run.get('job_sha256')==sha(attempt/'job.json'),
        'original_stdout_hash':run.get('stdout_sha256')==sha(attempt/'stdout.log'),
        'original_stderr_hash':run.get('stderr_sha256')==sha(attempt/'stderr.log'),
        'earlier_validation_digest':sha(prior)==EARLIER_VALIDATION_SHA256,
        'earlier_raw_result_digest':prior_data.get('raw_result_sha256')==hashes['sequence_result.json']==EARLIER_RESULT_SHA256,
        'summary_matches_raw':last=={key:raw.get(key) for key in SUMMARY_FIELDS},
        'summary_matches_earlier_replay':last=={key:prior_data.get('actual_replay',{}).get(key) for key in SUMMARY_FIELDS},
        'native_candidate_binding':raw.get('raw_file_sha256',{}).get('native_candidates.json')==hashes['native_candidates.json'],
    }
    snapshot={'attempt_dir':str(attempt),'job_sha256':sha(attempt/'job.json'),
              'run_result_sha256':sha(attempt/'run_result.json'),'stdout_sha256':sha(attempt/'stdout.log'),
              'stderr_sha256':sha(attempt/'stderr.log'),'raw_sha256':hashes,'stdout_summary':last,
              'earlier_validation_path':str(prior),'earlier_validation_sha256':sha(prior),
              'earlier_raw_result_sha256':prior_data.get('raw_result_sha256')}
    return snapshot,checks


def capture_pepmlm(attempt):
    attempt=Path(attempt).resolve()
    snapshot,checks=live_evidence(attempt)
    if not all(checks.values()):raise ValueError('PepMLM capture rejected: '+','.join(k for k,v in checks.items() if not v))
    captured={'schema_version':SCHEMA,'capture_kind':'post_execution_observer',
              'observed_at':datetime.now(timezone.utc).isoformat(),
              'observer_sha256':sha(__file__),'captured_during_execution':False,
              'evidence_boundary':'Retained-output observation plus earlier independent replay digest; not a producer-time capture or cryptographic signature.',
              'snapshot':snapshot,'checks_at_observation':checks}
    path=attempt/'output_capture.json'
    with path.open('x') as handle:
        json.dump(captured,handle,sort_keys=True,indent=2,allow_nan=False);handle.write('\n')
    return {'capture_path':str(path),'capture_sha256':sha(path),'passed':True,'checks':checks}


def verify_pepmlm_binding(attempt):
    attempt=Path(attempt).resolve();path=attempt/'output_capture.json';captured=read(path)
    snapshot,checks=live_evidence(attempt)
    checks.update(
        explicit_post_execution_observer=captured.get('schema_version')==SCHEMA and captured.get('capture_kind')=='post_execution_observer' and captured.get('captured_during_execution') is False,
        observer_source_binding=captured.get('observer_sha256')==sha(__file__),
        retained_evidence_unchanged=captured.get('snapshot')==snapshot,
        observation_checks_passed=bool(captured.get('checks_at_observation')) and all(v is True for v in captured['checks_at_observation'].values()),
    )
    return {'passed':all(checks.values()),'checks':checks,'capture_path':str(path),'capture_sha256':sha(path),
            'capture_kind':'post_execution_observer','earlier_validation_sha256':snapshot['earlier_validation_sha256']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['capture-pepmlm','verify-pepmlm'])
    parser.add_argument('--attempt',type=Path,required=True);args=parser.parse_args()
    result=capture_pepmlm(args.attempt) if args.action=='capture-pepmlm' else verify_pepmlm_binding(args.attempt)
    print(json.dumps(result,sort_keys=True,indent=2));return 0 if result['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
