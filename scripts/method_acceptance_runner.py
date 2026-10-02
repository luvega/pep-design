#!/usr/bin/env python3
"""Budgeted native-method execution; immutable attempts, durable shared ledger."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time
import urllib.request
import urllib.parse
from contextlib import contextmanager
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'benchmark/deployment/method_acceptance_policy_v1.json'
# Bind the code actually loaded by this supervisor before any lengthy preflight.
RUNNER_SOURCE = Path(__file__).read_bytes()
RUNNER_SHA256 = hashlib.sha256(RUNNER_SOURCE).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    with temp.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    temp.replace(path)


def disk_bytes(paths):
    seen = set(); total = 0
    for root in paths:
        for base, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(base)/d).is_symlink()]
            for name in files:
                p = Path(base)/name
                if p.is_symlink():
                    continue
                try:
                    st = p.stat()
                except FileNotFoundError:
                    # Native databases may remove transient WAL files after walk.
                    continue
                key = (st.st_dev, st.st_ino)
                if key not in seen:
                    seen.add(key); total += st.st_size
    return total


def pending_download_disk_bytes(data, asset_root):
    """Space promised to active transfers, excluding bytes already on disk."""
    total = 0
    for row in data['downloads']:
        if row['status'] != 'running':
            continue
        target = Path(asset_root) / row['download_id'] / row['filename']
        on_disk = target.stat().st_size if target.is_file() else 0
        total += max(0, row['max_bytes'] - on_disk)
    return total


def download_budget_charge(row):
    # Incident estimates remain explicitly separate from measured transfer bytes.
    if 'budget_charge_bytes' in row:
        return row['budget_charge_bytes']
    measured = row.get('received_bytes')
    return measured if measured is not None else row['max_bytes']


def download_request(spec):
    """Use a local HF credential only for the initial, official HTTPS host."""
    request = urllib.request.Request(spec['url'], headers={'User-Agent':'PepDesign-MethodAcceptance/1.0'})
    authentication = spec.get('authentication')
    if authentication is None:
        return request
    if authentication != 'huggingface_cached_token':
        raise ValueError('Unsupported download authentication')
    parsed = urllib.parse.urlsplit(spec['url'])
    if (parsed.scheme != 'https' or parsed.hostname != 'huggingface.co'
            or parsed.port not in (None, 443) or parsed.username is not None or parsed.password is not None):
        raise ValueError('HF authentication requires the official HTTPS host')
    # Never copy credentials into the descriptor, receipt, exception, or logs.
    token = (Path.home() / '.cache/huggingface/token').read_text().strip()
    if not re.fullmatch(r'hf_[A-Za-z0-9]+', token):
        raise ValueError('Invalid cached HF credential format')
    # urllib's redirect handler copies headers, but not unredirected_hdrs.
    request.add_unredirected_header('Authorization', 'Bearer ' + token)
    return request


def docker_stopped(container):
    """Return positive evidence of a stopped/absent container, never assume it."""
    try:
        check = subprocess.run(
            ['docker', 'container', 'inspect', '--format', '{{.State.Running}}', container],
            capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f'inspect_failed:{type(exc).__name__}'
    if check.returncode == 0:
        state = check.stdout.strip().lower()
        return state == 'false', f'inspect_running={state}'
    message = check.stderr.lower()
    if ('no such object:' in message or 'no such container:' in message) and container.lower() in message:
        return True, 'container_absent'
    return False, f'inspect_failed_exit_{check.returncode}'


def proc_identity(pid):
    text = Path(f'/proc/{pid}/stat').read_text()
    fields = text[text.rfind(')') + 2:].split()
    return {'pid': int(pid), 'state': fields[0], 'pgid': int(fields[2]),
            'sid': int(fields[3]), 'start_ticks': int(fields[19])}


def process_group_state(identity):
    """Inspect the exact session created by this launch, excluding zombies."""
    if not identity or identity.get('pgid') != identity.get('sid') or identity['pgid'] <= 1:
        return {'owned': False, 'stopped': False, 'reason': 'missing_group_identity'}
    pgid = identity['pgid']
    if pgid == os.getpgrp():
        return {'owned': False, 'stopped': False, 'reason': 'refuse_supervisor_group'}
    members = []
    try:
        for path in Path('/proc').iterdir():
            if not path.name.isdecimal():
                continue
            try:
                row = proc_identity(int(path.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
            if row['pgid'] != pgid:
                continue
            if (row['sid'] != identity['sid'] or row['start_ticks'] < identity['start_ticks']
                    or (row['pid'] == pgid and row['start_ticks'] != identity['start_ticks'])):
                return {'owned': False, 'stopped': False, 'reason': 'group_identity_mismatch'}
            if row['state'] not in ('Z', 'X'):
                members.append(row['pid'])
    except (OSError, ValueError, IndexError):
        return {'owned': False, 'stopped': False, 'reason': 'group_inspection_failed'}
    return {'owned': True, 'stopped': not members, 'members': members}


def parse_docker_run(argv):
    """Parse supported Docker options only before the actual image boundary.

    Unknown options fail closed, so an option's value cannot be mistaken for an
    image or a command argument mistaken for a container isolation setting.
    """
    if not isinstance(argv, list) or argv[:2] != ['docker', 'run']:
        raise ValueError('Expected explicit docker run argv')
    aliases = {'-e':'--env', '-v':'--volume', '-w':'--workdir', '-u':'--user', '--net':'--network'}
    values = {'--name','--memory','--cpus','--network','--gpus','--shm-size',
              '--memory-swap','--user','--entrypoint','--env','--volume','--workdir',
              '--runtime','--mount','--tmpfs','--label','--pull'}
    flags = {'--rm','--init','--read-only'}
    options = {}; index = 2
    while index < len(argv):
        token = argv[index]
        if token == '--':
            index += 1
            break
        if not token.startswith('-'):
            break
        name, separator, inline = token.partition('=')
        name = aliases.get(name, name)
        if name in flags:
            if separator:
                raise ValueError('Boolean Docker options require explicit flag form')
            value = True
        elif name in values:
            if separator:
                value = inline
            else:
                index += 1
                if index >= len(argv):
                    raise ValueError('Docker option is missing its value')
                value = argv[index]
            if not value:
                raise ValueError('Docker option value must not be empty')
        else:
            raise ValueError(f'Unsupported Docker option: {name}')
        options.setdefault(name, []).append(value)
        index += 1
    if index >= len(argv) or argv[index].startswith('-'):
        raise ValueError('Docker image is missing')
    return {'image': argv[index], 'image_index': index, 'options': options, 'command': argv[index+1:]}


def cleanup_execution(process, container=None, group_identity=None):
    """Independent cleanup steps; an API failure cannot skip client cleanup."""
    evidence = []
    container_ok = container is None
    if container is not None:
        container_ok, state = docker_stopped(container)
        evidence.append(state)
        if not container_ok:
            try:
                killed = subprocess.run(['docker', 'kill', container], capture_output=True,
                                        timeout=10, check=False)
                evidence.append(f'container_kill_exit_{killed.returncode}')
            except (OSError, subprocess.SubprocessError) as exc:
                evidence.append(f'container_kill_failed:{type(exc).__name__}')
    process_ok = process is None or process.poll() is not None
    group = process_group_state(group_identity) if group_identity else {
        'owned': False, 'stopped': process is None, 'reason': 'no_launched_group_identity'}
    if not group['stopped'] and group['owned']:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            group = process_group_state(group_identity)
            if not group['owned'] or group['stopped']:
                break
            try:
                os.killpg(group_identity['pgid'], sig)
            except ProcessLookupError:
                pass
            except OSError as exc:
                evidence.append(f'process_signal_failed:{type(exc).__name__}')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if process is not None:
                    process.poll()  # reap the leader, including a terminated client
                group = process_group_state(group_identity)
                if not group['owned'] or group['stopped']:
                    break
                time.sleep(0.05)
            if not group['owned'] or group['stopped']:
                break
    process_ok = process is None or process.poll() is not None
    if container is not None and not container_ok:
        container_ok, state = docker_stopped(container)
        evidence.append(state)
    evidence.append(f'client_process_stopped={process_ok}')
    evidence.append(f'process_group_stopped={group["stopped"]}')
    if not group['owned'] and not group['stopped']:
        evidence.append(group.get('reason', 'group_ownership_unconfirmed'))
    return {'confirmed': bool(container_ok and process_ok and group['stopped']), 'evidence': evidence,
            'process_group': group}


class Stage:
    def __init__(self, policy=POLICY, root=ROOT):
        self.root = Path(root).resolve()
        self.policy_path = Path(policy)
        self.policy = json.loads(self.policy_path.read_text())
        self.policy_sha = sha(self.policy_path)
        self.limits = self.policy['limits']
        self.run_root = self.root / self.policy['run_root']
        self.asset_root = Path(self.policy['asset_root'])
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.asset_root.mkdir(parents=True, exist_ok=True)
        if self.run_root.is_symlink() or self.asset_root.is_symlink():
            raise ValueError('Stage roots must not be symlinks')
        self.ledger_path = self.run_root / 'resource_ledger.json'

    @contextmanager
    def ledger(self):
        with (self.run_root/'resource_ledger.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.ledger_path.exists():
                data = json.loads(self.ledger_path.read_text())
                if data['policy_sha256'] != self.policy_sha:
                    raise ValueError('Policy changed after ledger initialization')
            else:
                data = {'schema_version':'method_acceptance_v1', 'policy_sha256':self.policy_sha,
                        'created_at':stamp(), 'runs':[], 'downloads':[]}
            yield data
            atomic_json(self.ledger_path, data)

    def validate_job(self, job):
        if job['method'] not in self.policy['methods']:
            raise ValueError('Unknown method')
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{1,100}', job['job_id']):
            raise ValueError('Invalid job_id')
        if job['resource'] not in ('gpu','cpu'):
            raise ValueError('Invalid resource')
        for name, cap in [('threads',self.limits['concurrent_threads']),
                          ('memory_gib',self.limits['concurrent_memory_gib'])]:
            v=job[name]
            if type(v) is not int or not 1 <= v <= cap:
                raise ValueError(f'Invalid {name}')
        duration=job['timeout_seconds']
        if type(duration) is not int or duration<=0:
            raise ValueError('Invalid timeout')
        if not isinstance(job['argv'],list) or not job['argv'] or any(type(a) is not str for a in job['argv']):
            raise ValueError('argv must be a nonempty string list')
        if job.get('kind','method') not in ('method','preparation'):
            raise ValueError('Invalid kind')
        if job.get('kind','method')=='method' and not job.get('quality_contract'):
            raise ValueError('Missing predeclared quality contract')
        docker=job['argv'][:2]==['docker','run']
        if job['resource']=='gpu' and not docker:
            raise ValueError('GPU jobs must use explicit docker run argv')
        if docker:
            parsed = parse_docker_run(job['argv'])
            if not re.fullmatch(r'sha256:[0-9a-f]{64}', parsed['image']):
                raise ValueError('Docker image must be an immutable local SHA-256 ID')
            required={'--name':'{container_name}','--memory':f"{job['memory_gib']}g",'--cpus':str(job['threads']), '--network':'none'}
            for key,value in required.items():
                if parsed['options'].get(key) != [value]:
                    raise ValueError(f'Container must bind {key}={value}')
        for path, expected in job.get('input_sha256',{}).items():
            if sha(path)!=expected:
                raise ValueError(f'Preflight hash mismatch: {path}')

    def reserve(self, job):
        self.validate_job(job)
        with self.ledger() as d:
            if any(r['status']=='cleanup_unconfirmed' for r in d['runs']):
                raise ValueError('Unreconciled cleanup; inspect process/container before resuming')
            active=[r for r in d['runs'] if r['status']=='running']
            if any(not Path(f"/proc/{r['supervisor_pid']}").exists() for r in active):
                raise ValueError('Unreconciled interrupted run; inspect process/container before resuming')
            if any(r['job_id']==job['job_id'] for r in d['runs']):
                raise ValueError('Job identity already used')
            corrections = [a['additional_method_attempts'] for a in d.get('attempt_adjustments', [])
                           if a['method'] == job['method']]
            if any(type(value) is not int or value < 1 for value in corrections):
                raise ValueError('Invalid method attempt adjustment')
            ordinal=1+sum(r['method']==job['method'] and r['kind']=='method' for r in d['runs'])+sum(corrections)
            kind=job.get('kind','method')
            if kind=='method' and ordinal>self.limits['attempts_per_method']:
                raise ValueError('Method attempt budget spent')
            if sum(r['threads'] for r in active)+job['threads']>self.limits['concurrent_threads']:
                raise ValueError('Concurrent CPU allocation exceeded')
            if sum(r['memory_gib'] for r in active)+job['memory_gib']>self.limits['concurrent_memory_gib']:
                raise ValueError('Concurrent memory allocation exceeded')
            if job['resource']=='gpu' and any(r['resource']=='gpu' for r in active):
                raise ValueError('GPU already reserved')
            used=sum(r.get('elapsed_seconds',r['reserved_seconds']) for r in d['runs'] if r['resource']==job['resource'])
            cap=self.limits['gpu_seconds' if job['resource']=='gpu' else 'cpu_heavy_wall_seconds']
            if used+job['timeout_seconds']+45>cap:
                raise ValueError('Cumulative compute budget exceeded')
            if disk_bytes([self.run_root,self.asset_root])+pending_download_disk_bytes(d,self.asset_root)>=self.limits['new_disk_bytes']:
                raise ValueError('New disk budget spent')
            name=f'attempt_{ordinal:03d}' if kind=='method' else 'preparation'
            out=self.run_root/job['method']/job['job_id']/name
            out.mkdir(parents=True, exist_ok=False)
            r={k:job[k] for k in ['job_id','method','resource','timeout_seconds','threads','memory_gib']}
            r.update(kind=kind,status='running',supervisor_pid=os.getpid(),started_at=stamp(),attempt_dir=str(out),reserved_seconds=job['timeout_seconds']+45)
            d['runs'].append(r)
            atomic_json(out/'job.json',job)
            atomic_json(out/'policy.json',self.policy)
        return out

    def run(self, job):
        out=self.reserve(job)
        container='pd-ma-'+job['job_id']
        argv=[v.replace('{attempt_dir}',str(out)).replace('{asset_root}',str(self.asset_root)).replace('{container_name}',container) for v in job['argv']]
        # GPU runs are containerized so timeout cleanup and hard RAM/CPU limits apply.
        docker=argv[:2]==['docker','run']
        if job['resource']=='gpu' and not docker:
            raise ValueError('GPU jobs must use explicit docker run argv')
        if docker:
            parsed = parse_docker_run(argv)
            required={'--name':container,'--memory':f"{job['memory_gib']}g",'--cpus':str(job['threads']), '--network':'none'}
            for key,value in required.items():
                if parsed['options'].get(key) != [value]:
                    raise ValueError(f'Container must bind {key}={value}')
        with (out/'runner_snapshot.py').open('xb') as handle:
            handle.write(RUNNER_SOURCE)
        atomic_json(out/'launch.json',{'argv':argv,'policy_sha256':self.policy_sha,'runner_sha256':RUNNER_SHA256,
                                      'runner_snapshot':'runner_snapshot.py'})
        env=os.environ.copy()
        for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
            env[key]=str(job['threads'])
        env.update({str(k):str(v) for k,v in job.get('env',{}).items()})
        env['METHOD_ACCEPTANCE_ATTEMPT_DIR']=str(out)
        env['METHOD_ACCEPTANCE_POLICY_SHA256']=self.policy_sha
        for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
            env[key]=str(job['threads'])
        before=time.monotonic(); process=None; reason='completed'; exit_code=127; group_identity=None
        cleanup = {'confirmed': False, 'evidence': ['cleanup_not_reached']}
        def child_setup():
            os.setsid()
            # Record identity before exec, including fast exits and orphaned children.
            atomic_json(out/'process_group_identity.json',proc_identity(os.getpid()))
            if hasattr(os,'sched_getaffinity'):
                os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:job['threads']])
            if not docker:
                memory_bytes=job['memory_gib']*1024**3
                resource.setrlimit(resource.RLIMIT_AS,(memory_bytes,memory_bytes))
        try:
            with (out/'stdout.log').open('wb') as stdout, (out/'stderr.log').open('wb') as stderr:
                process=subprocess.Popen(argv,cwd=job.get('cwd',str(self.root)),env=env,stdout=stdout,stderr=stderr,preexec_fn=child_setup)
                group_identity=json.loads((out/'process_group_identity.json').read_text())
                atomic_json(out/'process.json',{'pid':process.pid,'container_name':container if docker else None})
                next_disk=0
                while process.poll() is None:
                    elapsed=time.monotonic()-before
                    if elapsed>=job['timeout_seconds']:
                        reason='timeout';break
                    if elapsed>=next_disk:
                        next_disk=elapsed+10
                        # Active downloads retain their promised remaining space.
                        # The ledger is atomically replaced, so this read sees one
                        # consistent snapshot without holding its lock during IO.
                        current_ledger=json.loads(self.ledger_path.read_text())
                        committed_disk=(disk_bytes([self.run_root,self.asset_root])
                                        +pending_download_disk_bytes(current_ledger,self.asset_root))
                        if committed_disk>self.limits['new_disk_bytes']:
                            reason='disk_budget_exceeded';break
                    time.sleep(0.2)
                if process.poll() is None:
                    exit_code=124 if reason=='timeout' else 125
                else:exit_code=process.returncode
        except BaseException as e:
            reason=f'{type(e).__name__}: {e}'
            raise
        finally:
            try:
                cleanup = cleanup_execution(process, container if docker else None, group_identity)
            except BaseException as exc:
                cleanup = {'confirmed': False, 'evidence': [f'cleanup_internal_error:{type(exc).__name__}']}
            if not cleanup['confirmed'] and exit_code == 0:
                exit_code = 125
            elapsed=time.monotonic()-before
            result={'job_id':job['job_id'],'method':job['method'],'attempt_dir':str(out),'exit_code':exit_code,
                    'elapsed_seconds':elapsed,'termination_reason':reason,'finished_at':stamp(),
                    'job_sha256':sha(out/'job.json'),'policy_sha256':self.policy_sha,
                    'stdout_sha256':sha(out/'stdout.log') if (out/'stdout.log').exists() else None,
                    'stderr_sha256':sha(out/'stderr.log') if (out/'stderr.log').exists() else None,
                    'cleanup':cleanup}
            atomic_json(out/'run_result.json',result)
            with self.ledger() as d:
                r=next(r for r in d['runs'] if r['job_id']==job['job_id'])
                r.update(status='finished' if cleanup['confirmed'] else 'cleanup_unconfirmed',
                         elapsed_seconds=elapsed,exit_code=exit_code,termination_reason=reason,
                         finished_at=result['finished_at'],cleanup=cleanup)
        return result

    def download(self, spec):
        if not re.fullmatch(r'[a-z0-9_-]+',spec['download_id']):
            raise ValueError('Invalid download_id')
        if not spec['url'].startswith('https://'):
            raise ValueError('Downloads require HTTPS')
        request = download_request(spec)
        maximum=spec['max_bytes']
        if type(maximum) is not int or maximum<=0:
            raise ValueError('Invalid download cap')
        folder=self.asset_root/spec['download_id']
        filename=spec['filename']
        if Path(filename).name!=filename or filename in ('','.','..'):
            raise ValueError('Invalid filename')
        with self.ledger() as d:
            if any(r['download_id']==spec['download_id'] for r in d['downloads']):
                raise ValueError('Download identity already used; preserve failed attempts')
            spent=sum(download_budget_charge(r) for r in d['downloads'])
            if spent+maximum>self.limits['download_bytes']:
                raise ValueError('Cumulative download budget exceeded')
            if (disk_bytes([self.run_root,self.asset_root])+pending_download_disk_bytes(d,self.asset_root)
                    +maximum>self.limits['new_disk_bytes']):
                raise ValueError('Download exceeds disk budget')
            folder.mkdir(exist_ok=False)
            record=dict(spec,status='running',started_at=stamp(),supervisor_pid=os.getpid())
            d['downloads'].append(record)
        received=0; result='failed'; target=folder/filename
        try:
            with urllib.request.urlopen(request,timeout=45) as response, target.open('xb') as output:
                length=response.headers.get('Content-Length')
                if length is not None and int(length)>maximum:
                    raise ValueError('Content-Length exceeds reserved download cap')
                while True:
                    block=response.read(min(65536,maximum-received))
                    if not block:break
                    output.write(block);received+=len(block)
                    if received==maximum and (length is None or int(length)>received):
                        raise ValueError('Reached download cap; refusing additional bytes')
            digest=sha(target)
            if spec.get('sha256') and spec['sha256']!=digest:
                raise ValueError('Downloaded SHA-256 mismatch')
            result='complete'
            return {'path':str(target),'sha256':digest,'received_bytes':received}
        finally:
            with self.ledger() as d:
                row=next(r for r in d['downloads'] if r['download_id']==spec['download_id'])
                row.update(status=result,received_bytes=received,finished_at=stamp(),path=str(target),sha256=sha(target) if target.exists() else None)
                atomic_json(folder/'download_receipt.json',row)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','run','validate','download'])
    parser.add_argument('--job',type=Path)
    args=parser.parse_args();stage=Stage()
    if args.action=='status':
        with stage.ledger() as d: print(json.dumps(d,indent=2))
        return 0
    if args.job is None:parser.error('--job is required')
    job=json.loads(args.job.read_text())
    if args.action=='download':print(json.dumps(stage.download(job),indent=2));return 0
    if args.action=='validate':stage.validate_job(job);print('valid');return 0
    result=stage.run(job);print(json.dumps(result,indent=2));return 0 if result['exit_code']==0 else 1

if __name__=='__main__':
    raise SystemExit(main())
