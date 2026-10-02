from scripts.method_acceptance_bindcraft import check_filters

def test_native_filters_reject_missing_nonfinite_and_below_threshold():
    rules={'confidence':{'threshold':0.8,'higher':True},'clashes':{'threshold':0,'higher':False}}
    assert check_filters({'confidence':'0.85','clashes':'0'},rules)==[]
    assert 'confidence' in check_filters({'confidence':'0.7','clashes':'0'},rules)
    assert 'confidence' in check_filters({'confidence':'nan','clashes':'0'},rules)
    assert 'clashes:missing_or_invalid' in check_filters({'confidence':'0.9'},rules)

def test_disabled_native_rules_do_not_invent_cutoffs():
    assert check_filters({}, {'optional':{'threshold':None,'higher':True}})==[]

def test_only_unpredicted_models_are_not_applicable():
    rules={f'{i}_Binder_pLDDT':{'threshold':0.8,'higher':True} for i in range(1,6)}
    assert check_filters({'1_Binder_pLDDT':'.9','2_Binder_pLDDT':'.85'},rules,active_models=(1,2))==[]
    assert '2_Binder_pLDDT:missing_or_invalid' in check_filters({'1_Binder_pLDDT':'.9'},rules,active_models=(1,2))
