# Target And Control Freeze Checklist v0.10

## Purpose

`target_set_v0.csv` remains the frozen target interface, but it must stay schema-only until each candidate closes governance requirements. Candidate datasets and literature examples are not frozen Benchmark targets.

## Required Before Promotion

| gate | required evidence | status before freeze |
|:---|:---|:---|
| license | dataset, structure, sequence and assay terms recorded | required |
| assay | affinity, success/failure, structural or functional readout identified | required |
| positive control | known binder or positive case with provenance | required |
| negative control | decoy, nonbinder, off-target, shuffled or matched negative route | required |
| leakage | sequence/structure homology and known training-overlap risk reviewed | required |
| provenance | source URL/DOI/version/file route and extraction log planned | required |
| task mapping | T1/T2/T3 and generation/ranking-rescoring track assigned | required |

## Current Decision

- Overath, PEPBI, PepBenchmark, GPCR peptide benchmark, TCRTransBench and Chang AF2 ranking cases remain candidate/reference sources.
- No row should be added to `target_set_v0.csv` until the gates above are closed.
- Any future row must preserve the existing `target_set_v0.csv` schema and record limitations in `notes`.
