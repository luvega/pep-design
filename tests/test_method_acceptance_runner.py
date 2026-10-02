import json
from pathlib import Path
import sys
import hashlib
import io
import os
import subprocess
import itertools
from unittest.mock import MagicMock
import pytest
from scripts import method_acceptance_runner as runner
from scripts.method_acceptance_runner import Stage

@pytest.fixture
def stage(tmp_path):
    original=json.loads(Path('benchmark/deployment/method_acceptance_policy_v1.json').read_text())
    original['run_root']='runs';original['asset_root']=str(tmp_path/'assets')
    p=tmp_path/'policy.json';p.write_text(json.dumps(original))
    return Stage(p,tmp_path)

def job(identifier='test1'):
    return dict(job_id=identifier,method='pepmlm',resource='cpu',timeout_seconds=2,
                threads=1,memory_gib=1,argv=[sys.executable,'-c','print("native process")'],
                quality_contract={'canonical_sequence':True})

def test_run_captures_raw_output_and_rejects_identity_reuse(stage):
    result=stage.run(job());out=Path(result['attempt_dir'])
    assert result['exit_code']==0
    assert (out/'stdout.log').read_text()=='native process\n'
    assert json.loads((out/'job.json').read_text())['job_id']=='test1'
    with pytest.raises(ValueError,match='identity already used'):stage.run(job())

def test_failed_launch_consumes_attempt_and_preserves_result(stage):
    value=job();value['argv']=['/not-a-real-executable']
    with pytest.raises(FileNotFoundError):stage.run(value)
    with stage.ledger() as d:
        assert d['runs'][0]['status']=='finished'
        assert d['runs'][0]['exit_code']==127
        assert Path(d['runs'][0]['attempt_dir'],'run_result.json').is_file()

def test_rejects_fourth_method_attempt(stage):
    for n in range(3):stage.run(job(f'test{n}'))
    with pytest.raises(ValueError,match='attempt budget'):stage.run(job('test3'))

def test_resource_validation_precedes_attempt_creation(stage):
    value=job();value['resource']='gpu'
    with pytest.raises(ValueError,match='explicit docker'):stage.run(value)
    assert not stage.ledger_path.exists()

def test_reservations_prevent_overcommit(stage):
    value=job();value['threads']=24
    stage.reserve(value)
    with pytest.raises(ValueError,match='CPU allocation'):stage.reserve(job('test2'))

def test_timeout_kills_process_and_records_failure(stage):
    value=job();value['argv']=[sys.executable,'-c','import time; time.sleep(30)'];value['timeout_seconds']=1
    result=stage.run(value)
    assert result['exit_code']==124
    assert result['elapsed_seconds']<15
    with stage.ledger() as d:assert d['runs'][0]['status']=='finished'

def test_preflight_pin_mismatch_does_not_start_attempt(stage,tmp_path):
    p=tmp_path/'source';p.write_text('altered')
    value=job();value['input_sha256']={str(p):'0'*64}
    with pytest.raises(ValueError,match='hash mismatch'):stage.run(value)
    assert not stage.ledger_path.exists()

def test_compute_budget_is_reserved_before_launch(stage):
    value=job();value['timeout_seconds']=86400
    with pytest.raises(ValueError,match='compute budget'):stage.run(value)

def test_policy_cannot_change_after_first_execution(stage):
    stage.run(job());d=json.loads(stage.policy_path.read_text());d['limits']['attempts_per_method']=10
    stage.policy_path.write_text(json.dumps(d))
    replacement=Stage(stage.policy_path,stage.root)
    with pytest.raises(ValueError,match='Policy changed'):replacement.run(job('test2'))


def docker_job(identifier='docker_test'):
    value=job(identifier)
    value['resource']='gpu'
    value['argv']=['docker','run','--name','{container_name}','--memory','1g','--cpus','1',
                   '--network','none','sha256:'+'a'*64,'command']
    return value


@pytest.mark.parametrize('resource',['gpu','cpu'])
def test_all_docker_jobs_require_offline_network_before_reservation(stage,resource):
    value=docker_job();value['resource']=resource
    index=value['argv'].index('--network');del value['argv'][index:index+2]
    with pytest.raises(ValueError,match='--network=none'):stage.run(value)
    assert not stage.ledger_path.exists()


@pytest.mark.parametrize('extra',[['--network','host'],['--network=host'],['--net','host'],['--net=host']])
def test_docker_network_override_is_rejected(stage,extra):
    value=docker_job();value['argv'][2:2]=extra
    with pytest.raises(ValueError):stage.validate_job(value)


def test_docker_cleanup_failure_still_kills_client_and_keeps_reservation(stage,monkeypatch):
    process=MagicMock();process.pid=987654;process.poll.return_value=None
    def launch(*args,**kwargs):
        path=stage.run_root/'pepmlm/docker_test/attempt_001/process_group_identity.json'
        path.write_text(json.dumps({'pid':process.pid,'pgid':process.pid,'sid':process.pid,'start_ticks':100}))
        return process
    monkeypatch.setattr(runner.subprocess,'Popen',launch)
    monkeypatch.setattr(runner,'process_group_state',lambda identity:{'owned':True,'stopped':process.poll() is not None})
    def api_failure(*args,**kwargs):raise subprocess.TimeoutExpired('docker',5)
    monkeypatch.setattr(runner.subprocess,'run',api_failure)
    signaled=[]
    def signal_group(pid,sig):
        signaled.append((pid,sig));process.poll.return_value=-15
    monkeypatch.setattr(runner.os,'killpg',signal_group)
    times=itertools.count(0,3);monkeypatch.setattr(runner.time,'monotonic',lambda:next(times))
    result=stage.run(docker_job())
    assert result['exit_code']==124
    assert result['cleanup']['confirmed'] is False
    assert signaled
    assert json.loads(stage.ledger_path.read_text())['runs'][0]['status']=='cleanup_unconfirmed'
    with pytest.raises(ValueError,match='Unreconciled cleanup'):stage.reserve(job('following'))


def test_container_absence_is_positive_cleanup_evidence(monkeypatch):
    def absent(argv,**kwargs):
        return subprocess.CompletedProcess(argv,1,stdout='',stderr='Error: No such object: test_container')
    monkeypatch.setattr(runner.subprocess,'run',absent)
    assert runner.cleanup_execution(None,'test_container')['confirmed'] is True


def test_docker_api_error_is_not_mistaken_for_absence(monkeypatch):
    def unavailable(argv,**kwargs):
        return subprocess.CompletedProcess(argv,1,stdout='',stderr='Cannot connect to the Docker daemon')
    monkeypatch.setattr(runner.subprocess,'run',unavailable)
    assert runner.cleanup_execution(None,'test_container')['confirmed'] is False


def test_concurrent_download_disk_reservation_rejected_before_network(stage,monkeypatch):
    stage.limits['new_disk_bytes']=100_000
    with stage.ledger() as data:
        data['downloads'].append({'download_id':'first','filename':'first.bin',
                                  'status':'running','max_bytes':60_000})
    def no_network(*args,**kwargs):raise AssertionError('network must not be reached')
    monkeypatch.setattr(runner.urllib.request,'urlopen',no_network)
    with pytest.raises(ValueError,match='disk budget'):
        stage.download({'download_id':'second','filename':'second.bin','url':'https://example.invalid/file','max_bytes':60_000})
    assert not (stage.asset_root/'second').exists()


def test_disk_reservation_does_not_double_count_written_bytes(stage):
    folder=stage.asset_root/'first';folder.mkdir();(folder/'first.bin').write_bytes(b'x'*20)
    data={'downloads':[{'download_id':'first','filename':'first.bin','status':'running','max_bytes':60}]}
    assert runner.pending_download_disk_bytes(data,stage.asset_root)==40


def test_incident_estimate_charges_budget_without_claiming_measured_bytes(stage):
    with stage.ledger() as data:
        data['downloads'].append({'download_id':'incident','status':'estimated_incident',
                                  'max_bytes':stage.limits['download_bytes'],
                                  'budget_charge_bytes':stage.limits['download_bytes'],
                                  'actual_received_bytes':None})
    with pytest.raises(ValueError,match='download budget'):
        stage.download({'download_id':'after_incident','filename':'x','url':'https://example.invalid/x','max_bytes':1})


def test_native_preparation_adjustment_consumes_one_method_attempt(stage):
    with stage.ledger() as data:
        data['attempt_adjustments']=[{'method':'pepmlm','additional_method_attempts':1,
                                      'reason':'native preparation was a method invocation'}]
    first=stage.run(job('after_adjustment'))
    assert Path(first['attempt_dir']).name=='attempt_002'
    stage.run(job('last_attempt'))
    with pytest.raises(ValueError,match='attempt budget'):stage.run(job('fourth_attempt'))


def test_sha_streams_without_whole_file_read_bytes(tmp_path,monkeypatch):
    path=tmp_path/'large';content=b'abc'*1000;path.write_bytes(content)
    def forbid(*args,**kwargs):raise AssertionError('whole-file read_bytes is forbidden')
    monkeypatch.setattr(Path,'read_bytes',forbid)
    assert runner.sha(path)==hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize('url', [
    'https://huggingface.co.evil.invalid/file', 'http://huggingface.co/file',
    'https://huggingface.co:444/file', 'https://user@huggingface.co/file',
    'https://evil.invalid/file',
])
def test_cached_hf_auth_rejects_other_hosts_before_reading_token(url,monkeypatch):
    def forbid(*args,**kwargs):raise AssertionError('credential must not be read')
    monkeypatch.setattr(Path,'read_text',forbid)
    with pytest.raises(ValueError,match='official HTTPS host'):
        runner.download_request({'url':url,'authentication':'huggingface_cached_token'})


def test_cached_hf_auth_is_not_forwarded_on_redirect_or_recorded(tmp_path,monkeypatch):
    cached=tmp_path/'.cache/huggingface';cached.mkdir(parents=True)
    token='hf_FAKEunitTESTtoken123';(cached/'token').write_text(token+'\n')
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    spec={'url':'https://huggingface.co/owner/repo/resolve/pin/source.zip',
          'authentication':'huggingface_cached_token'}
    request=runner.download_request(spec)
    assert request.get_header('Authorization')=='Bearer '+token
    assert 'Authorization' not in request.headers
    redirect=runner.urllib.request.HTTPRedirectHandler().redirect_request(
        request,None,302,'Found',{},'https://cdn.example.invalid/signed/file')
    assert redirect.get_header('Authorization') is None
    assert token not in json.dumps(spec)


def test_authenticated_download_receipt_excludes_credential(stage,tmp_path,monkeypatch):
    cached=tmp_path/'.cache/huggingface';cached.mkdir(parents=True)
    token='hf_FAKEunitTESTtoken123';(cached/'token').write_text(token)
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    response=io.BytesIO(b'official source');response.headers={'Content-Length':'15'}
    def download(request,**kwargs):
        assert request.get_header('Authorization')=='Bearer '+token
        return response
    monkeypatch.setattr(runner.urllib.request,'urlopen',download)
    result=stage.download({'download_id':'hf_source','url':'https://huggingface.co/o/r/resolve/pin/source',
                           'filename':'source','max_bytes':100,'authentication':'huggingface_cached_token'})
    assert result['received_bytes']==15
    assert token not in stage.ledger_path.read_text()
    assert token not in (stage.asset_root/'hf_source/download_receipt.json').read_text()


def test_cleanup_stops_orphaned_child_after_leader_exits():
    code=('import subprocess,sys,time; '
          'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); '
          'print(p.pid,flush=True); time.sleep(0.2)')
    process=subprocess.Popen([sys.executable,'-c',code],start_new_session=True,
                             stdout=subprocess.PIPE,text=True)
    identity=runner.proc_identity(process.pid)
    try:
        child=int(process.stdout.readline())
        assert process.wait(timeout=3)==0
        assert runner.proc_identity(child)['state'] not in ('Z','X')
        assert runner.process_group_state(identity)['stopped'] is False
        result=runner.cleanup_execution(process,group_identity=identity)
        assert result['confirmed'] is True
        assert runner.process_group_state(identity)['stopped'] is True
    finally:
        group=runner.process_group_state(identity)
        if group['owned'] and not group['stopped']:
            os.killpg(identity['pgid'],runner.signal.SIGKILL)
        process.stdout.close()


def test_group_cleanup_refuses_reused_leader_identity(monkeypatch):
    identity={'pid':987654,'pgid':987654,'sid':987654,'start_ticks':100}
    monkeypatch.setattr(Path,'iterdir',lambda self:iter([Path('/proc/987654')]))
    monkeypatch.setattr(runner,'proc_identity',lambda pid:{**identity,'start_ticks':101,'state':'S'})
    def forbid(*args,**kwargs):raise AssertionError('unrelated group must not receive a signal')
    monkeypatch.setattr(runner.os,'killpg',forbid)
    process=MagicMock();process.poll.return_value=0
    result=runner.cleanup_execution(process,group_identity=identity)
    assert result['confirmed'] is False
    assert result['process_group']['reason']=='group_identity_mismatch'


def test_group_cleanup_refuses_own_supervisor_group():
    identity={'pid':os.getpgrp(),'pgid':os.getpgrp(),'sid':os.getpgrp(),'start_ticks':1}
    result=runner.process_group_state(identity)
    assert result['owned'] is False
    assert result['stopped'] is False


def test_launch_snapshots_loaded_runner_source_even_if_live_file_changes(stage,monkeypatch):
    original_sha=runner.sha
    def simulated_later_source(path):
        return '0'*64 if Path(path)==Path(runner.__file__) else original_sha(path)
    monkeypatch.setattr(runner,'sha',simulated_later_source)
    result=stage.run(job('snapshot_test'));out=Path(result['attempt_dir'])
    launch=json.loads((out/'launch.json').read_text())
    assert (out/'runner_snapshot.py').read_bytes()==runner.RUNNER_SOURCE
    assert launch['runner_sha256']==hashlib.sha256(runner.RUNNER_SOURCE).hexdigest()
    assert launch['runner_sha256']!='0'*64


def test_disk_walk_allows_native_transient_file_unlink(tmp_path,monkeypatch):
    transient=tmp_path/'complex.confdb.wal.0';transient.write_bytes(b'wal')
    stable=tmp_path/'stable';stable.write_bytes(b'12345')
    def walk(*args,**kwargs):
        files=[transient.name,stable.name]
        transient.unlink()  # native writer removes it after directory enumeration
        yield str(tmp_path),[],files
    monkeypatch.setattr(runner.os,'walk',walk)
    assert runner.disk_bytes([tmp_path])==5


def test_disk_walk_does_not_suppress_permission_errors(tmp_path,monkeypatch):
    path=tmp_path/'database';path.write_bytes(b'12345')
    monkeypatch.setattr(Path,'is_symlink',lambda self:False)
    def denied(*args,**kwargs):raise PermissionError('protected')
    monkeypatch.setattr(Path,'stat',denied)
    with pytest.raises(PermissionError):runner.disk_bytes([tmp_path])


def test_docker_command_flags_do_not_count_as_container_options(stage):
    value=docker_job()
    index=value['argv'].index('--network')
    del value['argv'][index:index+2]
    value['argv'].extend(['--network','none'])
    with pytest.raises(ValueError,match='--network=none'):stage.validate_job(value)


def test_mutable_actual_image_cannot_hide_behind_command_digest(stage):
    value=docker_job();index=value['argv'].index('sha256:'+'a'*64)
    value['argv'][index]='some-image:mutable';value['argv'].append('sha256:'+'a'*64)
    with pytest.raises(ValueError,match='immutable'):stage.validate_job(value)


def test_parser_tracks_image_boundary_and_repeated_mounts_environment():
    argv=['docker','run','--rm','--name','container','--memory','32g','--cpus','4',
          '--network=none','--gpus','device=0','-e','ONE=1','--env','TWO=2',
          '-v','/a:/a:ro','--volume','/b:/b','--user','1000:1000','-w','/repo',
          '--shm-size','4g','--entrypoint','/bin/python','sha256:'+'b'*64,'script.py','--network','host']
    parsed=runner.parse_docker_run(argv)
    assert parsed['image']=='sha256:'+'b'*64
    assert parsed['options']['--network']==['none']
    assert parsed['options']['--env']==['ONE=1','TWO=2']
    assert parsed['options']['--volume']==['/a:/a:ro','/b:/b']
    assert parsed['command']==['script.py','--network','host']


@pytest.mark.parametrize('extra',[['--unrecognized','value'],['--detach'],['--memory']])
def test_parser_rejects_ambiguous_or_unsupported_options(extra):
    with pytest.raises(ValueError):runner.parse_docker_run(['docker','run',*extra])
