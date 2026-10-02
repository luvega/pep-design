#!/usr/bin/env python3
"""Execute the author's pinned SaLT&PepPr notebook peptide endpoint on CPU."""
from __future__ import annotations
import argparse
import ast
import contextlib
import copy
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.method_acceptance_quality import evaluate_candidate, criteria_sha256
from scripts.run_saltnpeppr_local import load_vendor_model, parse_fasta, validate_records, sha256_file

METHOD = 'SaLT&PepPr'
NOTEBOOK_SHA = '359183acb3e4573ef1540f9392d50ca103dfe58d17e11ee365a887e137288cac'
NATIVE_NOTES = {
    'extrema': 'Original notebook uses argrelextrema(..., np.less), despite local-maxima comments; preserved unchanged.',
    'windows': 'Original range(len(npscores)-peptide_length) omits the final possible window; preserved unchanged.',
    'scoring': 'Original mean excludes two residues at each peptide edge; duplicate sequences keep last score.',
    'ranking': 'Original cell 9 descending Partner_Label/SnP_Score ordering; no method-comparison or binding claim.',
    'model_mode': 'Constructor training mode retained, as in notebook; seed fixes stochastic dropout for this one run.',
}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def write_new(path, value):
    with Path(path).open('x') as handle:
        json.dump(value,handle,sort_keys=True,indent=2,allow_nan=False)
        handle.write('\n')


def native_sources(notebook):
    path = Path(notebook)
    if sha256_file(path) != NOTEBOOK_SHA:
        raise ValueError('official notebook pin changed')
    cells = json.loads(path.read_text())['cells']
    source = ''.join(cells[8]['source'])
    functions = [node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='run_inference']
    if len(functions)!=1:
        raise ValueError('native inference function missing or ambiguous')
    return source, functions[0], ''.join(cells[9]['source'])


def namespace():
    import numpy as np
    import pandas as pd
    from scipy.signal import argrelextrema
    return {'np':np,'pd':pd,'argrelextrema':argrelextrema}


def replay_native_extraction(notebook, name, sequence, length, count, probabilities):
    """Replay exact original extraction AST using captured model probabilities."""
    source,node,_ = native_sources(notebook)
    node=copy.deepcopy(node)
    index=next(i for i,statement in enumerate(node.body) if isinstance(statement,ast.Assign)
               and isinstance(statement.targets[0],ast.Name) and statement.targets[0].id=='pep_scores_mean')
    node.body=node.body[index:]
    node.args.args.append(ast.arg(arg='npscores'))
    module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    ns=namespace()
    exec(compile(module,str(notebook),'exec'),ns)
    return ns['run_inference'](name,sequence,length,count,ns['np'].asarray(probabilities,dtype=ns['np'].float32))


def ranked_candidates(notebook, name, sequence, names, peptides, scores):
    _,_,source=native_sources(notebook)
    ns=namespace()
    ns.update(partner_labels_col=[name]*len(peptides), selected_peptides=peptides,
              selected_scores=scores, pep_names=names,
              all_partners_db=ns['pd'].DataFrame({'Partner_Label':[name],'Partner_Sequence':[sequence]}))
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(source,str(notebook)+':cell9','exec'),ns)
    return ns['peptides_df'].to_dict(orient='records')


def validate_config(config):
    if config.get('method')!=METHOD or config.get('device')!='cpu':
        raise ValueError('this endpoint must use the native CPU route')
    for path,expected in config['file_sha256'].items():
        path=Path(path)
        if not path.is_file() or path.is_symlink() or sha256_file(path)!=expected:
            raise ValueError(f'predeclared file hash mismatch: {path}')
    required={config[k] for k in ('notebook','source','checkpoint','input_fasta','use_scope','license_path','loader')}
    if not required.issubset(config['file_sha256']):
        raise ValueError('incomplete source/input/license pins')
    native_sources(config['notebook'])
    records=parse_fasta(Path(config['input_fasta']));validate_records(records)
    if len(records)!=1 or records[0][1]!=config['partner_sequence'] or 'P06730' not in records[0][0]:
        raise ValueError('canonical UniProt partner input binding mismatch')
    if config['ppi_provenance'].get('target')!='4E-BP2' or config['ppi_provenance'].get('partner_uniprot')!='P06730':
        raise ValueError('declared real PPI case mismatch')
    scope=json.loads(Path(config['use_scope']).read_text())
    if not scope.get('execution_scope_cleared') or scope['license_sha256']!=sha256_file(Path(config['license_path'])):
        raise ValueError('current phase use scope is not cleared')
    if (type(config['peptide_length']) is not int or not 5<=config['peptide_length']<len(records[0][1])
            or type(config['n_peptides']) is not int or not 1<=config['n_peptides']<=20):
        raise ValueError('invalid bounded peptide extraction parameters')
    if config['quality_contract']['criteria_sha256']!=criteria_sha256():
        raise ValueError('quality criteria changed after declaration')


def candidate_qc(candidate, config):
    peptide=candidate['Peptide_Sequence'];score=candidate['SnP_Score']
    native=(candidate['Partner_Label']==config['partner_label']
            and candidate['Partner_Sequence']==config['partner_sequence']
            and peptide in config['partner_sequence']
            and candidate['Peptide_Length']==config['peptide_length']
            and math.isfinite(score) and 0<=score<=1)
    quality=evaluate_candidate(method=METHOD,sequence=peptide,length_min=config['peptide_length'],length_max=config['peptide_length'])
    return {'native_input_and_output_sanity':native,'quality':quality,
            'passed':native and quality['candidate_quality_status']=='pass'}


def policy_binding(copy_path, policy_path, expected_sha):
    if (sha256_file(Path(policy_path))!=expected_sha
            or json.loads(Path(copy_path).read_text())!=json.loads(Path(policy_path).read_text())):
        raise ValueError('policy binding mismatch')
    return expected_sha


def run(config, config_path, output):
    validate_config(config)
    attempt=Path(os.environ['METHOD_ACCEPTANCE_ATTEMPT_DIR']).resolve()
    output=Path(output).resolve()
    if output!=attempt/'raw':raise ValueError('output must be the reserved raw directory')
    job=json.loads((attempt/'job.json').read_text())
    if job.get('method')!='saltnpeppr' or job.get('kind','method')!='method':raise ValueError('not a native method reservation')
    if job['quality_contract']!=config['quality_contract']:raise ValueError('quality declaration mismatch')
    for path in (Path(config_path).resolve(),Path(__file__).resolve()):
        if job['input_sha256'].get(str(path))!=sha256_file(path):raise ValueError('producer/config launch pin missing')
    policy_sha=policy_binding(attempt/'policy.json',ROOT/'benchmark/deployment/method_acceptance_policy_v1.json',
                              os.environ['METHOD_ACCEPTANCE_POLICY_SHA256'])
    output.mkdir(exist_ok=False)
    import numpy as np
    import random
    import torch
    random.seed(config['seed']);np.random.seed(config['seed']);torch.manual_seed(config['seed'])
    torch.set_num_threads(job['threads'])
    model,alphabet=load_vendor_model(Path(config['source']),Path(config['checkpoint']),'cpu')
    model.train()  # original notebook never calls eval(); preserve native dropout
    captured=[]
    hook=model.register_forward_hook(lambda module,inputs,result:captured.append(result.detach().cpu().clone()))
    _,node,_=native_sources(config['notebook'])
    ns=namespace();ns.update(torch=torch,model=model,batch_converter=alphabet.get_batch_converter())
    exec(compile(ast.Module(body=[node],type_ignores=[]),config['notebook'],'exec'),ns)
    names,peptides,scores=ns['run_inference'](config['partner_label'],config['partner_sequence'],config['peptide_length'],config['n_peptides'])
    hook.remove()
    if len(captured)!=1 or tuple(captured[0].shape)!=(len(config['partner_sequence']),2):
        raise ValueError('unexpected native model inference count or shape')
    probabilities=torch.nn.Softmax(dim=1)(captured[0])[:,1].numpy().tolist()
    candidates=ranked_candidates(config['notebook'],config['partner_label'],config['partner_sequence'],names,peptides,scores)
    raw={'logits':captured[0].tolist(),'probabilities':probabilities,'candidates':candidates}
    write_new(output/'native_outputs.json',raw)
    qcs=[candidate_qc(candidate,config) for candidate in candidates]
    qualified=sum(qc['passed'] for qc in qcs)
    result={'method':METHOD,'config_digest':digest(config),'config_path':str(Path(config_path).resolve()),
            'producer_sha256':sha256_file(Path(__file__)),'job_sha256':sha256_file(attempt/'job.json'),
            'policy_sha256':policy_sha,'native_outputs_sha256':sha256_file(output/'native_outputs.json'),
            'notebook_sha256':NOTEBOOK_SHA,'native_notes':NATIVE_NOTES,'native_completed':True,
            'candidate_qc':qcs,'qualified_candidate_count':qualified,
            'selected_candidate_id':next((c['Peptide_Name'] for c,q in zip(candidates,qcs) if q['passed']),None),
            'environment':{'python':sys.version,'executable':sys.executable,
                'packages':{p:importlib.metadata.version(p) for p in ['torch','fair-esm','pytorch-lightning','numpy','pandas','scipy','torchmetrics']}}}
    write_new(output/'saltnpeppr_result.json',result)
    return result


def verify(config, output):
    validate_config(config);output=Path(output)
    result=json.loads((output/'saltnpeppr_result.json').read_text())
    if result['config_digest']!=digest(config) or result['producer_sha256']!=sha256_file(Path(__file__)):
        raise ValueError('producer or input binding changed')
    if result['native_outputs_sha256']!=sha256_file(output/'native_outputs.json'):
        raise ValueError('native output hash changed')
    attempt=output.parent;job=json.loads((attempt/'job.json').read_text())
    if result['job_sha256']!=sha256_file(attempt/'job.json') or job['quality_contract']!=config['quality_contract']:
        raise ValueError('job binding changed')
    for path in (Path(result['config_path']),Path(__file__).resolve()):
        if job.get('input_sha256',{}).get(str(path))!=sha256_file(path):
            raise ValueError('declared producer/config pin changed')
    policy_binding(attempt/'policy.json',ROOT/'benchmark/deployment/method_acceptance_policy_v1.json',result['policy_sha256'])
    if result['notebook_sha256']!=NOTEBOOK_SHA:
        raise ValueError('policy or notebook binding changed')
    raw=json.loads((output/'native_outputs.json').read_text())
    if len(raw['probabilities'])!=len(config['partner_sequence']) or len(raw['logits'])!=len(raw['probabilities']):
        raise ValueError('model per-residue output length mismatch')
    for logits,prob in zip(raw['logits'],raw['probabilities']):
        if len(logits)!=2 or not all(math.isfinite(x) for x in logits) or not math.isfinite(prob) or not 0<=prob<=1:
            raise ValueError('invalid native logits/probability')
        expected=1/(1+math.exp(max(-700,min(700,logits[0]-logits[1]))))
        if abs(expected-prob)>1e-6:raise ValueError('softmax output mismatch')
    names,peptides,scores=replay_native_extraction(config['notebook'],config['partner_label'],config['partner_sequence'],config['peptide_length'],config['n_peptides'],raw['probabilities'])
    candidates=ranked_candidates(config['notebook'],config['partner_label'],config['partner_sequence'],names,peptides,scores)
    if candidates!=raw['candidates']:raise ValueError('native extraction/ranking replay mismatch')
    qcs=[candidate_qc(c,config) for c in candidates];qualified=sum(q['passed'] for q in qcs)
    selected=next((c['Peptide_Name'] for c,q in zip(candidates,qcs) if q['passed']),None)
    if (qcs!=result['candidate_qc'] or qualified!=result['qualified_candidate_count']
            or selected!=result['selected_candidate_id'] or not result['native_completed']
            or result['native_notes']!=NATIVE_NOTES):raise ValueError('candidate qualification binding mismatch')
    return {'method':METHOD,'passed':qualified>0,'candidate_count':len(candidates),
            'qualified_candidate_count':qualified,'selected_candidate_id':selected}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['validate','run','verify'])
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args();config=json.loads(args.config.read_text())
    if args.action=='validate':validate_config(config);print('valid');return 0
    result=run(config,args.config,args.output) if args.action=='run' else verify(config,args.output)
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result.get('qualified_candidate_count',0)>0 else 2

if __name__=='__main__':raise SystemExit(main())
