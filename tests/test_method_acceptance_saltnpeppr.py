import ast
import copy
import json
from pathlib import Path
import pytest
from scripts import method_acceptance_saltnpeppr as salt

NOTEBOOK=Path('/mnt/ssd4t/protein-design/data/method_acceptance_v1/saltnpeppr_notebook_usercontent_v1/official_notebook.ipynb')


@pytest.fixture
def notebook():
    if not NOTEBOOK.is_file():pytest.skip('external pinned author notebook is not installed')
    return NOTEBOOK


def candidate():
    return {'Peptide_Name':'partner_SnP_1','Peptide_Sequence':'ACDEF','Peptide_Length':5,
            'SnP_Score':0.6,'Partner_Label':'partner','Partner_Sequence':'ACDEFGHIKLMN'}


def config():
    return {'partner_label':'partner','partner_sequence':'ACDEFGHIKLMN','peptide_length':5}


@pytest.mark.parametrize('field,value',[('Peptide_Sequence','WWWWW'),('Partner_Label','wrong'),
    ('Partner_Sequence','WRONG'),('Peptide_Length',4),('SnP_Score',float('nan')),('SnP_Score',1.1)])
def test_candidate_qc_fails_unbound_or_invalid_outputs(field,value):
    c=candidate();c[field]=value
    assert salt.candidate_qc(c,config())['passed'] is False


def test_canonical_native_partner_subsequence_passes_only_sequence_qc():
    assert salt.candidate_qc(candidate(),config())['passed'] is True


def test_notebook_tampering_rejected_before_importing_model(tmp_path):
    p=tmp_path/'notebook';p.write_text('{}')
    with pytest.raises(ValueError,match='notebook pin'):salt.native_sources(p)


def test_replay_matches_exact_original_function_with_fake_model(notebook):
    # Only this small fixture executes the author function; no model is loaded.
    import numpy as np
    probabilities=np.asarray([.7,.3,.8,.2,.5,.9,.1,.8,.4,.2,.7,.1],dtype=np.float32)
    class Array:
        def __init__(self,value):self.value=value
        def detach(self):return self
        def numpy(self):return self.value
        def __getitem__(self,key):return Array(self.value[key])
    class Softmax:
        def __init__(self,dim):assert dim==1
        def __call__(self,scores):return Array(np.column_stack([1-probabilities,probabilities]))
    from contextlib import nullcontext
    from types import SimpleNamespace
    ns=salt.namespace();ns.update(torch=SimpleNamespace(no_grad=nullcontext,nn=SimpleNamespace(Softmax=Softmax)),
        model=lambda *args:Array(None),batch_converter=lambda value:(None,None,None))
    _,node,_=salt.native_sources(notebook)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(notebook),'exec'),ns)
    expected=ns['run_inference']('partner','ACDEFGHIKLMN',5,6)
    replay=salt.replay_native_extraction(notebook,'partner','ACDEFGHIKLMN',5,6,probabilities.tolist())
    assert expected[0:2]==replay[0:2]
    assert np.array_equal(expected[2],replay[2])
    assert expected[1]==['FGHIK','CDEFG']  # preserve np.less, not a repaired maximum selector


def test_original_cell9_ordering_is_replayed(notebook):
    rows=salt.ranked_candidates(notebook,'partner','ACDEFGHIKLMN',
                               ['partner_2','partner_1'],['ACDEF','DEFGH'],[.2,.8])
    assert [r['Peptide_Name'] for r in rows]==['partner_SnP_1','partner_SnP_2']
    assert [r['SnP_Score'] for r in rows]==[.8,.2]


def test_policy_copy_formatting_is_not_a_policy_change(tmp_path):
    original=tmp_path/'original.json';duplicate=tmp_path/'copy.json'
    value={'limits':{'threads':4},'name':'test'}
    original.write_text(json.dumps(value));duplicate.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    sha=salt.sha256_file(original)
    assert salt.policy_binding(duplicate,original,sha)==sha
    duplicate.write_text(json.dumps({'limits':{'threads':5},'name':'test'}))
    with pytest.raises(ValueError,match='policy binding'):salt.policy_binding(duplicate,original,sha)
