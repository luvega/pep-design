# D-Flow Input Contract Fixture Audit v0.24

## Scope

This audit records a fixture-level resolution for the D-Flow / PeptideDesign
PepMerge/LMDB input contract blocker. It does not record a full PepMerge
release download, a D-Flow design run, scoring evidence, method ranking, or a
Benchmark result.

## Root Cause

D-Flow's `PepDataset` does not accept an arbitrary receptor PDB directly. The
method expects a PepMerge-style directory containing one subdirectory per case,
with `pocket.pdb` and `peptide.pdb`, plus a hard-coded `../names.txt` split
file relative to the D-Flow source working directory. With `reset=False`, it
then expects an existing LMDB cache such as
`pep_pocket_test_structure_cache.lmdb`. In v0.23 the structure directory was
absent, so `PepDataset` raised `FileNotFoundError` before any method inference
could be attempted.

## Resolution

`scripts/prepare_dflow_input_contract.py` now prepares a D-Flow-compatible
fixture from the 3EQS MDM2/p53 case:

- downloads or reuses `data/dflow/pdbs/3EQS.pdb`;
- extracts receptor pocket residues from chain A within 10 A of peptide chain B;
- writes `data/dflow/pepmerge/mdm2_p53_3eqs_fixture/pocket.pdb`;
- writes `data/dflow/pepmerge/mdm2_p53_3eqs_fixture/peptide.pdb`;
- writes `method_sources/dflow/names.txt`;
- runs `PepDataset(reset=True)` to create
  `data/dflow/pep_cache/pep_pocket_test_structure_cache.lmdb`;
- reruns `PepDataset(reset=False)` and records a passing load test.

The runtime log is kept outside git at
`logs/v0.24/dflow_input_contract_fixture_smoke.json`. The tracked summary is
`benchmark/deployment/dflow_input_contract_fixture_v0.24.csv`.

## Evidence

The v0.24 smoke loaded one LMDB entry:

- `fixture_case_id`: `mdm2_p53_3eqs_fixture`
- `lmdb_entries`: `1`
- `first_total_residues`: `62`
- `first_generated_residues`: `11`
- `pep_dataset_reset_false_status`: `passed`

The 3EQS chain B parser result has 11 generated residues in the D-Flow parser,
so target chain/sequence review remains required before using this case for
scoring or target-set promotion.

## Boundary

This resolves the D-Flow fixture-level input contract needed for a bounded
dry-run. It does not resolve full PepMerge dataset access from Google Drive and
does not promote D-Flow to `smoke_test_ready`.
