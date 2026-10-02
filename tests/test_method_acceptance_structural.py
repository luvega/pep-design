import pytest

from scripts.method_acceptance_structural import (_context_composite, _diff_fullatom_quality,
    _replay_postprocess_stages, _same_chain_coordinates, native_inner, postprocess_contract, sha)


def test_diffpepbuilder_uses_native_steps_and_keeps_disulfide_postprocess():
    inner = 'cp -a /data/source/. "$work/"\npython inference inference.denoising.num_t=2 inference.ss_bond.build_ss_bond=False'
    restored = native_inner("diffpepbuilder", inner)
    assert "inference.denoising.num_t=200 " in restored
    assert "inference.ss_bond.build_ss_bond=True" in restored
    assert "num_t=2 " not in restored
    assert 'tar -xzf "$work/SSbuilder/SSBLIB.tar.gz"' in restored


@pytest.mark.parametrize("inner", ["python inference", "num_t=2 num_t=2"])
def test_upstream_control_marker_change_fails_closed(inner):
    with pytest.raises(ValueError, match="marker changed"):
        native_inner("diffpepbuilder", inner)


def _ca(serial, name, chain, residue, xyz):
    x,y,z=xyz
    return f"ATOM  {serial:5d}  CA  {name:3s} {chain}{residue:4d}    {x:8.3f}{y:8.3f}{z:8.3f}{1.:6.2f}{0.:6.2f}           C\n"


def test_context_reconstruction_requires_verified_translation(tmp_path):
    context=tmp_path/'context.pdb'; candidate=tmp_path/'candidate.pdb'; output=tmp_path/'qc.pdb'
    context.write_text(_ca(1,'ALA','A',1,(0,0,0))+_ca(2,'GLY','A',2,(3.8,0,0)))
    candidate.write_text(_ca(1,'ALA','A',1,(2,3,4))+_ca(2,'GLY','A',2,(5.8,3,4))+_ca(3,'LYS','B',1,(5,6,7)))
    original=candidate.read_bytes()
    result=_context_composite(candidate,context,'B',output)
    assert result['translation_angstrom']==(2,3,4)
    assert result['maximum_ca_residual_angstrom']<.001
    assert candidate.read_bytes()==original
    assert 'LYS B' in output.read_text()
    candidate.write_text(_ca(1,'ALA','A',1,(2,3,4))+_ca(2,'GLY','A',2,(6.3,3,4)))
    with pytest.raises(ValueError,match='coordinate frame'):
        _context_composite(candidate,context,'B',output)


def test_missing_target_anchors_cannot_be_filled_by_unbound_context(tmp_path):
    context=tmp_path/'context.pdb';candidate=tmp_path/'candidate.pdb'
    context.write_text(_ca(1,'ALA','A',1,(0,0,0)))
    candidate.write_text(_ca(1,'ALA','B',1,(0,0,0)))
    with pytest.raises(ValueError,match='coverage mismatch'):
        _context_composite(candidate,context,'B',tmp_path/'qc.pdb')


def test_full_native_target_replays_selected_alternative_without_substitution(tmp_path):
    context=tmp_path/'context.pdb'; candidate=tmp_path/'candidate.pdb'; output=tmp_path/'qc.pdb'
    ca=_ca(1,'ALA','A',1,(0,0,0))
    cb=_ca(2,'ALA','A',1,(1,1,0)).replace(' CA ', ' CB ')
    alternate=cb[:16]+'B'+cb[17:]
    primary=cb[:16]+'A'+cb[17:30]+f'{9.:8.3f}{9.:8.3f}{0.:8.3f}'+cb[54:]
    context.write_text(ca+primary+alternate)
    candidate.write_text(ca+cb+_ca(3,'GLY','B',1,(5,5,5)))
    result=_context_composite(candidate,context,'B',output)
    assert result['target_altloc_policy']=='native_full_target_atoms_verified_against_context'
    assert output.read_bytes()==candidate.read_bytes()
    candidate.write_text(ca+cb[:30]+f'{2.:8.3f}{2.:8.3f}{0.:8.3f}'+cb[54:])
    with pytest.raises(ValueError,match='full target atom'):
        _context_composite(candidate,context,'B',output)


def test_final_full_atom_endpoint_rejects_backbone_only_sidechain(tmp_path):
    from tests.test_method_acceptance_quality import monomer
    path=monomer(tmp_path,resname='LYS')
    qc=_diff_fullatom_quality(path,'K',1,1,'B')
    assert qc['method']=='DiffPepBuilder'
    assert 'complete_endpoint_atoms' in qc['failed_checks']


def test_final_full_atom_endpoint_still_requires_l_chirality(tmp_path):
    from tests.test_method_acceptance_quality import monomer
    qc=_diff_fullatom_quality(monomer(tmp_path,mirror=True),'A',1,1,'B')
    assert 'chirality' in qc['failed_checks']


def test_native_postprocess_cannot_silently_skip_amber_or_rosetta(tmp_path):
    stages={}
    for name in postprocess_contract()['required_stages']+['score','summary']:
        path=tmp_path/(name+'.pdb');path.write_text(name)
        stages[name]={'path':path.name,'sha256':sha(path)}
    checks=_replay_postprocess_stages(tmp_path,stages)
    assert checks['all_native_stages']
    assert not checks['native_no_skipped_relaxation']
    del stages['amber_relaxed']
    assert not _replay_postprocess_stages(tmp_path,stages)['all_native_stages']
    stages['final']['path']='../outside.pdb'
    with pytest.raises(ValueError):
        _replay_postprocess_stages(tmp_path,stages)


def test_reconstruction_must_preserve_source_coordinates(tmp_path):
    source=tmp_path/'source.pdb';recon=tmp_path/'recon.pdb'
    source.write_text(_ca(1,'ALA','B',1,(0,0,0)))
    recon.write_bytes(source.read_bytes())
    assert _same_chain_coordinates(source,recon,'B')
    recon.write_text(_ca(1,'ALA','B',1,(0,0,.5)))
    assert not _same_chain_coordinates(source,recon,'B')


@pytest.mark.parametrize('target_chain,binder_chain',[('A','C'),('B','X')])
def test_batch_context_preserves_native_non_ab_chain_ids(tmp_path,target_chain,binder_chain):
    context=tmp_path/'context.pdb';candidate=tmp_path/'candidate.pdb';output=tmp_path/'qc.pdb'
    context.write_text(_ca(1,'ALA',target_chain,10,(0,0,0)))
    candidate.write_text(_ca(1,'ALA',target_chain,10,(2,3,4))+_ca(2,'GLY',binder_chain,1,(10,10,10)))
    result=_context_composite(candidate,context,binder_chain,output,target_chain=target_chain)
    assert result['translation_angstrom']==(2,3,4)
    assert output.read_bytes()==candidate.read_bytes()
    with pytest.raises(ValueError,match='must differ'):
        _context_composite(candidate,context,binder_chain,output,target_chain=binder_chain)


def test_native_batch_requires_all_twelve_outputs_and_records_each_failure(tmp_path):
    import json
    from scripts.method_acceptance_structural import _verify_dflow_batch
    from scripts.v034_adapters import dflow
    cases=[]
    mapping={}
    for ident,target_chain,binder_chain in [('one','A','B'),('two','B','X'),('three','A','C')]:
        folder=tmp_path/'inputs'/ident;folder.mkdir(parents=True)
        pocket=_ca(1,'ALA',target_chain,10,(0,0,0));(folder/'pocket.pdb').write_text(pocket)
        cases.append({'case_id':ident,'length':1,'binder_chain':binder_chain,'target_chain':target_chain,
                      'input_sha256':{'pocket.pdb':sha(folder/'pocket.pdb')}})
        for i in range(4):
            relative=f'raw/dflow_native/dflow.pt_400_4_False_x_mirror/{ident}/sample_{i}.pdb'
            path=tmp_path/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(pocket+_ca(2,'GLY',binder_chain,1,(10,10,10)))
            mapping[relative]=sha(path)
    entry=tmp_path/'work/PeptideDesign/dflow/experiments/inference_pep.py';entry.parent.mkdir(parents=True);entry.write_text('native fixture')
    cache=tmp_path/'work/pep_cache/pep_pocket_test_structure_x_cache.lmdb';cache.parent.mkdir();cache.write_text('cached fixture')
    for name in ('batch_config.json','selection.json'):(tmp_path/name).write_text('{}')
    settings={'num_steps':400,'samples':4,'angle_purify':True,'llm':False,'x_mirror':True}
    runtime={'native_invocations':1,'batch_config_sha256':sha(tmp_path/'batch_config.json'),
        'selection_sha256':sha(tmp_path/'selection.json'),'native_settings':settings,'requested_seed':44,
        'source_commit':dflow.SOURCE_COMMIT,'checkpoint_sha256':dflow.CHECKPOINT_SHA256,
        'entrypoint_patched_sha256':sha(entry),'native_cache_sha256':sha(cache),'native_completed':True,
        'cases':cases,'native_candidates':mapping,'native_dataset_iteration_order':sorted(c['case_id'] for c in cases),
        'native_cache_inputs':{c['case_id']:{'generated_residues':1,'binder_chains':[c['binder_chain']],
                                         'target_chains':[c['target_chain']]} for c in cases}}
    (tmp_path/'raw/runtime_evidence.json').write_text(json.dumps(runtime))
    job={**runtime,'random_seed':44,'argv':['python -m dflow.experiments.inference_pep sample.num_steps=400']}
    result={'checks':{},'candidates':[]}
    _verify_dflow_batch(tmp_path,job,result)
    assert all(result['checks'].values())
    assert len(result['candidates'])==12
    assert all(r['candidate_quality_status']=='fail' for r in result['candidates']) # incomplete synthetic binder atoms
    (tmp_path/next(iter(mapping))).unlink()
    result={'checks':{},'candidates':[]}
    _verify_dflow_batch(tmp_path,job,result)
    assert not result['checks']['all_twelve_native_outputs']
    assert len(result['candidates'])==12 # missing output stays explicitly visible
