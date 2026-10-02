import json
import csv

import pytest

from scripts.method_acceptance_bindcraft_replay import (accepted_lineage, capture, inventory,
    native_best_model, sha, verify)


def test_output_capture_is_immutable_and_detects_later_output_changes(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    (raw / 'candidate.pdb').write_text('retained native coordinates\n')
    (tmp_path / 'job.json').write_text('{}')
    (tmp_path / 'run_result.json').write_text(json.dumps({'method': 'bindcraft'}))
    snapshot = capture(tmp_path)
    assert snapshot['capture_role'] == 'post_execution_observer'
    assert snapshot['raw_sha256'] == inventory(tmp_path)
    with pytest.raises(FileExistsError):
        capture(tmp_path)
    (raw / 'candidate.pdb').write_text('changed coordinates\n')
    assert snapshot['raw_sha256'] != inventory(tmp_path)
    assert verify(tmp_path)['passed'] is False


def test_unfinished_run_cannot_be_captured_or_accepted(tmp_path):
    with pytest.raises(FileNotFoundError):
        capture(tmp_path)
    assert verify(tmp_path)['passed'] is False


def test_raw_output_symlink_is_rejected(tmp_path):
    (tmp_path / 'raw').mkdir()
    (tmp_path / 'outside.pdb').write_text('outside\n')
    (tmp_path / 'raw/candidate.pdb').symlink_to(tmp_path / 'outside.pdb')
    with pytest.raises(ValueError, match='symlink'):
        inventory(tmp_path)


def _write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def _atom(serial, name, residue_name, chain, residue, x, y, z):
    return (f'ATOM  {serial:5d} {name:^4s} {residue_name:3s} {chain}{residue:4d}    '
            f'{x:8.3f}{y:8.3f}{z:8.3f}{1.:6.2f}{0.:6.2f}          {name[0]:>2s}\n')


@pytest.fixture
def native_layout(tmp_path):
    """Synthetic lineage fixture: geometry qualification is tested separately."""
    designs=tmp_path/'raw/designs'
    for folder in ('Accepted','MPNN/Relaxed'):
        (designs/folder).mkdir(parents=True)
    target=tmp_path/'target.pdb'
    target_text=''.join(_atom(i,name,'ALA','A',1,*xyz) for i,(name,xyz) in enumerate(
        {'N':(-1.45,0,0),'CA':(0,0,0),'C':(.54,1.43,0),'O':(0,2.5,0),'CB':(.5,-.7,-1.2)}.items(),1))
    binder=''.join(_atom(i+10,'CA','GLY','B',i,100+i*4,0,0) for i in range(1,66))
    target.write_text(target_text)
    complex_text=target_text+binder
    for model in (1,2):
        (designs/f'MPNN/Relaxed/design_model{model}.pdb').write_text(complex_text)
    (designs/'Accepted/design_model2.pdb').write_text(complex_text)
    row={'Design':'design','Protocol':'4stage','Length':'65','Sequence':'G'*65,
         '1_pLDDT':'0.8','2_pLDDT':'0.9','3_pLDDT':'','4_pLDDT':'','5_pLDDT':''}
    _write_csv(designs/'mpnn_design_stats.csv',[row])
    _write_csv(designs/'final_design_stats.csv',[{'Rank':'1',**row}])
    return tmp_path, designs, target, row


def test_native_accepted_model_and_numeric_csv_rewrite_replay(native_layout):
    attempt,designs,target,row=native_layout
    _write_csv(designs/'final_design_stats.csv',[{'Rank':'1',**row,'Length':'65.0','1_pLDDT':'0.80'}])
    records=accepted_lineage(attempt,target,(1,2))
    assert records[0]['passed']
    assert records[0]['native_selected_model']==2


def test_native_ties_choose_first_model_and_reject_other_tied_copy(native_layout):
    attempt,designs,target,row=native_layout
    row['1_pLDDT']=row['2_pLDDT']='0.9'
    _write_csv(designs/'mpnn_design_stats.csv',[row])
    _write_csv(designs/'final_design_stats.csv',[{'Rank':'1',**row}])
    assert native_best_model(row,(1,2))==1
    assert not accepted_lineage(attempt,target,(1,2))[0]['passed']
    (designs/'Accepted/design_model2.pdb').rename(designs/'Accepted/design_model1.pdb')
    assert accepted_lineage(attempt,target,(1,2))[0]['passed']


@pytest.mark.parametrize('change',['wrong_model','extra_model','changed_accepted_bytes','changed_final_row','missing_mpnn_row','duplicate_final_row'])
def test_native_lineage_rejects_previously_unchecked_substitution(native_layout,change):
    attempt,designs,target,row=native_layout
    accepted=designs/'Accepted/design_model2.pdb'
    if change=='wrong_model':
        accepted.rename(designs/'Accepted/design_model1.pdb')
    elif change=='extra_model':
        (designs/'Accepted/design_model5.pdb').write_bytes(accepted.read_bytes())
    elif change=='changed_accepted_bytes':
        accepted.write_text(accepted.read_text()+'END\n')
    elif change=='changed_final_row':
        _write_csv(designs/'final_design_stats.csv',[{'Rank':'1',**row,'1_pLDDT':'0.99'}])
    elif change=='missing_mpnn_row':
        _write_csv(designs/'mpnn_design_stats.csv',[{**row,'Design':'other'}])
    else:
        _write_csv(designs/'final_design_stats.csv',[{'Rank':'1',**row},{'Rank':'2',**row}])
    assert not accepted_lineage(attempt,target,(1,2))[0]['passed']


@pytest.mark.parametrize('change',['missing_target','wrong_target_sequence','wrong_target_chain','missing_target_atom'])
def test_matching_relaxed_and_accepted_copies_still_require_complete_pinned_target(native_layout,change):
    attempt,designs,target,row=native_layout
    accepted=designs/'Accepted/design_model2.pdb'
    lines=accepted.read_text().splitlines(keepends=True)
    if change=='missing_target':
        lines=[line for line in lines if line[21]!='A']
    elif change=='wrong_target_sequence':
        lines=[line[:17]+'GLY'+line[20:] if line[21]=='A' else line for line in lines]
    elif change=='wrong_target_chain':
        lines=[line[:21]+'C'+line[22:] if line[21]=='A' else line for line in lines]
    else:
        lines=[line for line in lines if not(line[21]=='A' and line[12:16].strip()=='CB')]
    for path in (accepted,designs/'MPNN/Relaxed/design_model2.pdb'):
        path.write_text(''.join(lines))
    result=accepted_lineage(attempt,target,(1,2))[0]
    assert result['checks']['accepted_is_native_relaxed_copy']
    assert not result['checks']['complete_target_A_binding']
    assert not result['passed']


def test_verifier_rejects_changed_source_input_even_with_matching_output_capture(native_layout,monkeypatch):
    import scripts.method_acceptance_bindcraft_replay as replay
    from scripts.method_acceptance_quality import criteria
    attempt,designs,target,row=native_layout
    source=attempt/'source';(source/'example').mkdir(parents=True);(source/'settings_advanced').mkdir()
    source_target=source/'example/PDL1.pdb';source_target.write_bytes(target.read_bytes())
    (source/'bindcraft.py').write_text('# pinned native source\n')
    base={'use_multimer_design':True}
    (source/'settings_advanced/default_4stage_multimer.json').write_text(json.dumps(base))
    config={'source':str(source),'max_trajectories':12,'parameter_root':'/params'}
    config_path=attempt/'config.json';config_path.write_text(json.dumps(config))
    raw=attempt/'raw'
    settings={'design_path':str(designs)+'/', 'binder_name':'PDL1_native_acceptance',
        'starting_pdb':str(source_target),'chains':'A','target_hotspot_residues':'56',
        'lengths':[65,100],'number_of_final_designs':1}
    (raw/'settings.json').write_text(json.dumps(settings))
    advanced={**base,'max_trajectories':12,'save_design_animations':False,'save_design_trajectory_plots':False,
        'zip_animations':False,'zip_plots':False,'af_params_dir':'/params'}
    (raw/'advanced.json').write_text(json.dumps(advanced));(raw/'filters.json').write_text('{}')
    env={'config_sha256':sha(config_path),'entrypoint_sha256':sha(source/'bindcraft.py'),
         'filter_sha256':sha(raw/'filters.json'),'advanced_sha256':sha(raw/'advanced.json')}
    (raw/'environment.json').write_text(json.dumps(env))
    (raw/'native_completed.json').write_text(json.dumps({'completed':True,'settings_sha256':sha(raw/'settings.json'),
        'entrypoint_sha256':env['entrypoint_sha256']}))
    job={'argv':['--config',str(config_path)],'input_sha256':{str(source_target):sha(source_target),
         str(source/'bindcraft.py'):env['entrypoint_sha256']},'quality_contract':{
         'native_filters_sha256':env['filter_sha256'],'candidate_integrity':criteria()}}
    (attempt/'job.json').write_text(json.dumps(job))
    (attempt/'run_result.json').write_text(json.dumps({'method':'bindcraft','exit_code':0,'termination_reason':'completed'}))
    # Isolate the lineage gate: the shared structural evaluator has its own tests.
    monkeypatch.setattr(replay,'assess',lambda _: {'native_completed':True,'records':[{'design':'design','pass':True}]})
    capture(attempt)
    assert verify(attempt)['passed']
    source_target.write_text(source_target.read_text()+'END\n')
    result=verify(attempt)
    assert not result['passed']
    assert not result['checks']['target_source_input_sha256']
