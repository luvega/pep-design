#!/usr/bin/env python3
"""Run the pinned BindCraft native pipeline and independently recheck native filters."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import runpy
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.method_acceptance_quality import evaluate_candidate

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_filters(row,filters,*,active_models=(1,2,3,4,5)):
    failures=[]
    for key,rule in filters.items():
        model=re.match(r'^([1-5])_',key)
        if model and int(model.group(1)) not in active_models:
            continue
        if isinstance(rule,dict) and 'threshold' in rule and rule['threshold'] is not None:
            try:value=float(row[key]);threshold=float(rule['threshold'])
            except (KeyError,TypeError,ValueError):failures.append(key+':missing_or_invalid');continue
            if not math.isfinite(value) or (value<threshold if rule['higher'] else value>threshold):failures.append(key)
        elif isinstance(rule,dict) and 'threshold' not in rule:
            # Native nested InterfaceAAs rules require all enabled subthresholds.
            enabled={aa:sub for aa,sub in rule.items() if isinstance(sub,dict) and sub.get('threshold') is not None}
            if enabled:
                import ast
                try:values=ast.literal_eval(row[key])
                except (KeyError,ValueError,SyntaxError):failures.append(key+':missing');continue
                for aa,sub in enabled.items():
                    try:value=float(values[aa]);threshold=float(sub['threshold'])
                    except (KeyError,TypeError,ValueError):failures.append(key+':'+aa);continue
                    if not math.isfinite(value) or (value<threshold if sub['higher'] else value>threshold):failures.append(key+':'+aa)
    return failures

def run(config,attempt):
    attempt=Path(attempt);job=json.loads((attempt/'job.json').read_text())
    if job['method']!='bindcraft':raise ValueError('Wrong authorized method')
    config_path=Path(config);c=json.loads(config_path.read_text())
    raw=attempt/'raw';raw.mkdir(exist_ok=False)
    source=Path(c['source']);advanced=json.loads((source/'settings_advanced/default_4stage_multimer.json').read_text())
    advanced.update(max_trajectories=c['max_trajectories'],save_design_animations=False,save_design_trajectory_plots=False,zip_animations=False,zip_plots=False,af_params_dir=c['parameter_root'])
    settings={'design_path':str(raw/'designs')+'/', 'binder_name':'PDL1_native_acceptance','starting_pdb':str(source/'example/PDL1.pdb'), 'chains':'A','target_hotspot_residues':'56','lengths':[65,100],'number_of_final_designs':1}
    filters=json.loads((source/'settings_filters/default_filters.json').read_text())
    for name,obj in [('settings.json',settings),('advanced.json',advanced),('filters.json',filters)]:
        (raw/name).write_text(json.dumps(obj,indent=2)+'\n')
    (raw/'filters.json').write_bytes((source/'settings_filters/default_filters.json').read_bytes())
    env={'source_commit':c['source_commit'],'config_sha256':sha(config_path),'seed':c['seed'],'packages':{name:importlib.metadata.version(name) for name in ['jax','jaxlib','colabdesign','numpy','biopython']},'entrypoint_sha256':sha(source/'bindcraft.py'),'filter_sha256':sha(raw/'filters.json'),'advanced_sha256':sha(raw/'advanced.json')}
    (raw/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    import numpy as np
    import random
    np.random.seed(c['seed']);random.seed(c['seed'])
    sys.path.insert(0,str(source))
    sys.argv=[str(source/'bindcraft.py'),'--settings',str(raw/'settings.json'),'--filters',str(raw/'filters.json'),'--advanced',str(raw/'advanced.json')]
    runpy.run_path(str(source/'bindcraft.py'),run_name='__main__')
    (raw/'native_completed.json').write_text(json.dumps({'completed':True,'entrypoint_sha256':sha(source/'bindcraft.py'),'settings_sha256':sha(raw/'settings.json')},indent=2)+'\n')

def assess(attempt):
    attempt=Path(attempt);raw=attempt/'raw';designs=raw/'designs'
    job=json.loads((attempt/'job.json').read_text())
    if sha(raw/'filters.json')!=job['quality_contract']['native_filters_sha256']:
        raise ValueError('Native filters changed after prospective binding')
    filters=json.loads((raw/'filters.json').read_text())
    advanced=json.loads((raw/'advanced.json').read_text())
    active_models=(1,2) if advanced['use_multimer_design'] else (1,2,3,4,5)
    stats=designs/'final_design_stats.csv'
    rows=list(csv.DictReader(stats.open())) if stats.is_file() else []
    records=[]
    for row in rows:
        name=row.get('Design','');paths=sorted((designs/'Accepted').glob(name+'_model*.pdb'))
        errors=check_filters(row,filters,active_models=active_models)
        if not paths:errors.append('accepted_structure_missing')
        qc=[evaluate_candidate(method='BindCraft',sequence=row.get('Sequence',''),length_min=65,length_max=100,structure_path=p,binder_chain='B') for p in paths]
        records.append({'design':name,'sequence':row.get('Sequence'),'native_filter_failures':errors,'structures':[str(p) for p in paths],'quality':qc,'pass':not errors and any(v['candidate_quality_status']=='pass' for v in qc)})
    return {'method':'BindCraft','native_completed':(raw/'native_completed.json').is_file(),'records':records,'quality_pass_count':sum(r['pass'] for r in records)}

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','assess']);p.add_argument('--config',type=Path);p.add_argument('--attempt',type=Path,required=True);a=p.parse_args()
    if a.action=='run':run(a.config,a.attempt)
    else:print(json.dumps(assess(a.attempt),indent=2))
if __name__=='__main__':main()
