import json
from pathlib import Path
import pytest
from scripts import method_acceptance_sequence_replay as observer


def write(path,value):path.write_text(json.dumps(value))


@pytest.fixture
def attempt(tmp_path,monkeypatch):
    root=tmp_path/'pepmlm';out=root/'job/attempt_001';(out/'raw').mkdir(parents=True)
    prior=root/'preparation';prior.mkdir()
    last={'method':'PepMLM','passed':True,'selected_candidate_id':'pepmlm_002'}
    write(out/'raw/native_candidates.json',[{'sequence':'ACD'}])
    result={**last,'raw_file_sha256':{'native_candidates.json':observer.sha(out/'raw/native_candidates.json')}}
    write(out/'raw/sequence_result.json',result)
    write(out/'job.json',{'job_id':observer.JOB_ID,'method':'pepmlm'})
    (out/'stdout.log').write_text('NVIDIA container banner\n\n'+json.dumps(last)+'\n')
    (out/'stderr.log').write_text('')
    write(out/'run_result.json',{'job_id':observer.JOB_ID,'method':'pepmlm','attempt_dir':str(out),
        'exit_code':0,'termination_reason':'completed','job_sha256':observer.sha(out/'job.json'),
        'stdout_sha256':observer.sha(out/'stdout.log'),'stderr_sha256':observer.sha(out/'stderr.log')})
    result_sha=observer.sha(out/'raw/sequence_result.json')
    write(prior/'replay_validation.json',{'raw_result_sha256':result_sha,'actual_replay':last})
    monkeypatch.setattr(observer,'EARLIER_RESULT_SHA256',result_sha)
    monkeypatch.setattr(observer,'EARLIER_VALIDATION_SHA256',observer.sha(prior/'replay_validation.json'))
    return out


def test_capture_is_explicit_post_execution_immutable_and_verifiable(attempt):
    before=observer.raw_hashes(attempt)
    assert observer.capture_pepmlm(attempt)['passed'] is True
    assert observer.verify_pepmlm_binding(attempt)['passed'] is True
    assert observer.raw_hashes(attempt)==before
    recorded=json.loads((attempt/'output_capture.json').read_text())
    assert recorded['captured_during_execution'] is False
    with pytest.raises(FileExistsError):observer.capture_pepmlm(attempt)


def test_self_consistent_raw_result_substitution_cannot_replace_earlier_digest(attempt):
    observer.capture_pepmlm(attempt)
    write(attempt/'raw/native_candidates.json',[{'sequence':'WWW'}])
    result=json.loads((attempt/'raw/sequence_result.json').read_text())
    result['raw_file_sha256']['native_candidates.json']=observer.sha(attempt/'raw/native_candidates.json')
    write(attempt/'raw/sequence_result.json',result)
    check=observer.verify_pepmlm_binding(attempt)
    assert check['passed'] is False
    assert check['checks']['native_candidate_binding'] is True
    assert check['checks']['summary_matches_raw'] is True
    assert check['checks']['earlier_raw_result_digest'] is False


def test_replacing_earlier_record_and_current_raw_still_fails_prior_anchor(attempt):
    observer.capture_pepmlm(attempt)
    result=json.loads((attempt/'raw/sequence_result.json').read_text());result['new']='replacement'
    write(attempt/'raw/sequence_result.json',result)
    prior=attempt.parent.parent/'preparation/replay_validation.json'
    old=json.loads(prior.read_text());old['raw_result_sha256']=observer.sha(attempt/'raw/sequence_result.json');write(prior,old)
    check=observer.verify_pepmlm_binding(attempt)
    assert check['passed'] is False
    assert check['checks']['earlier_validation_digest'] is False
    assert check['checks']['earlier_raw_result_digest'] is False


@pytest.mark.parametrize('suffix',['trailing output',json.dumps({'method':'PepMLM','passed':True,'selected_candidate_id':'pepmlm_002','extra':1})])
def test_summary_must_be_exact_last_nonempty_line(attempt,suffix):
    with (attempt/'stdout.log').open('a') as handle:handle.write(suffix+'\n')
    with pytest.raises(ValueError):observer.capture_pepmlm(attempt)


def test_original_run_record_change_invalidates_observation(attempt):
    observer.capture_pepmlm(attempt)
    run=json.loads((attempt/'run_result.json').read_text());run['extra']='changed';write(attempt/'run_result.json',run)
    check=observer.verify_pepmlm_binding(attempt)
    assert check['passed'] is False
    assert check['checks']['retained_evidence_unchanged'] is False


def test_raw_symlink_is_not_accepted_as_retained_evidence(attempt):
    (attempt/'raw/escape').symlink_to(attempt/'job.json')
    with pytest.raises(ValueError,match='symlink'):observer.capture_pepmlm(attempt)
