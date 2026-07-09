# D-Flow Full PepMerge Download Audit v0.25

## Scope

This audit records resolution of the Google Drive access blocker for the
D-Flow / PeptideDesign PepMerge assets. It covers download, archive integrity,
local extraction, split-name bridging, and `PepDataset(reset=False)` loading.
It does not record a D-Flow generation run, scoring, method ranking, or a
complete Benchmark result.

## Root Cause

The previous failure was not caused by a missing Drive folder. Local DNS
resolution sent Google hostnames to non-Google addresses, causing folder access
and `gdown`/`curl` routes to time out. The Drive folder became reachable after
forcing `drive.google.com` to a working Google IP for folder metadata, while
the file downloads completed from `drive.usercontent.google.com`.

## Assets

Official source folder:
`https://drive.google.com/drive/folders/1bHaKDF3uCDPtfsihjZs0zmjwF6UU1uVl?usp=sharing`

Resolved files:

| file | Google Drive file id | local path | bytes | sha256 |
|:---|:---|:---|---:|:---|
| `PepMerge_release.zip` | `1WKw5eQh_jDLFes1g6wkSW9KfijwoO7_1` | `data/dflow/downloads/PepMerge_release.zip` | 1337791497 | `eb0c9f6f81b85c399a32fe38e7f79274584805d7cafaac774a8d091792d0410c` |
| `PepMerge_lmdb.zip` | `1vaFAO6ONmghVGsr288x8eQaIqr4eoPqI` | `data/dflow/downloads/PepMerge_lmdb.zip` | 191932930 | `452240f8d60227c0959f7f3a8cf43a2f8a63e53806f4f47bdf8ccb1cb1f5ef08` |

Both archives passed `unzip -t`.

## Local Extraction And Contract

- `PepMerge_release.zip` was extracted to `data/dflow/pepmerge_release`.
- The extracted structure directory contains 10,348 case directories and
  72,471 files.
- All 10,348 case directories contain `pocket.pdb`, `peptide.pdb`,
  `receptor.pdb`, `receptor.fasta`, and `peptide.fasta`.
- `PepMerge_lmdb.zip` was extracted to `data/dflow/pepmerge_lmdb`.
- The official LMDB package contains `test_names.txt` with 154 entries,
  `train_names.txt` with 9,849 entries, `pep_pocket_test_structure_cache.lmdb`,
  and `pep_pocket_train_structure_cache.lmdb`.
- All 154 official test names are present in the extracted structure directory.
- Because D-Flow hard-codes `../names.txt`, the local bridge copies official
  `test_names.txt` to `method_sources/dflow/names.txt`; the previous fixture
  name file is preserved as `method_sources/dflow/names.v0.24_fixture.txt`
  when present.

## Load Evidence

Using the project-local D-Flow environment `.venv/dflow-v023` from
`method_sources/dflow/PeptideDesign`, `PepDataset(reset=False)` loaded:

| dataset name | entries | first id |
|:---|---:|:---|
| `pep_pocket_test` | 154 | `1aze_B` |
| `pep_pocket_train` | 9,849 | `1a0n_A` |

The compact runtime log is in gitignored
`logs/v0.25/dflow_full_pepmerge_load_smoke.json`.

## Boundary

This v0.25 evidence resolves the full PepMerge download/input-contract blocker
for D-Flow local preparation only. It is not a D-Flow design run, not target-set
evidence, not scoring evidence, not method-ranking evidence, not
`smoke_test_ready`, and not `benchmark_ready`.

Next action: prepare a bounded D-Flow dry-run command and output parser before
any controlled multi-case execution.
