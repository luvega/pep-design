# Pep Design Benchmark KB Agent Rules

## Purpose

This project is an independent protocol-first Benchmark knowledge base for recent peptide-design methods. It supports literature evidence management, method and dataset readiness audits, Benchmark manuscript planning, and later server-side smoke-test preparation.

Current authoritative plan: `ops/plans/updated_plan_v0.9.md`.

Current version: `1.2.1`.

Next planned phase: v0.10 server-side preflight package planning. Do not start clone, download, install, or GPU execution unless the user explicitly requests that later phase.

## Source Boundaries

- Do not edit `E:\Endnote参考文献`, EndNote `.enl` files, Zotero items, or the upstream `PD-wiki`.
- Treat `sources/raw_snapshots/` as a local read-only mirror/snapshot layer.
- Treat `kb/references/`, `kb/tables/`, `kb/wiki/`, `manuscript/`, `ops/`, and `benchmark/` as generated project artifacts.
- Treat `benchmark/` as the Benchmark protocol, readiness-audit, smoke-test planning, and future run-result interface layer.
- Do not place third-party source trees, downloaded datasets, model weights, batch PDB outputs, large archives, or GPU run results in this repository.
- Future server-side clones, downloads, weights, and results must live outside the tracked KB or in explicitly gitignored external roots.

## Skill Routing

Use the smallest skill set that covers the task.

| task | required skill route |
|:---|:---|
| Maintain KB structure, indexes, logs, raw/kb/wiki/schema boundaries, or `AGENTS.md` | `building-llm-wiki` |
| Literature review, Zotero/BibTeX provenance, citation checks, claim-evidence review, manuscript pipeline or integrity gate | `academic-research-suite` |
| Benchmark manuscript structure, Introduction logic, five-pillar audit, section skeleton, pre-submission checklist | `benchmark-paper-template` |
| Chinese academic prose, hedging, overclaim control, or reader-facing report style | `academic-chinese-style` / `nature-language-style` when relevant |
| Zotero library access or BibTeX export | `zotero:Zotero` and `citation-management`; Zotero writes remain forbidden unless the user explicitly approves |
| External literature or dataset freshness checks | use web/API verification and cite authoritative sources; keep source libraries read-only |

For broad research-to-paper or multi-stage review tasks, route through `academic-research-suite` first and then use `benchmark-paper-template` for Benchmark-paper-specific structure.

## Current Artifact Roles

| artifact | role | boundary |
|:---|:---|:---|
| `ops/plans/updated_plan_v0.9.md` | current plan | planning artifact only |
| `ops/plans/updated_plan_v0.6.md` | historical ARS baseline | not the current plan |
| `ops/audits/license_schema_input_contract_review_v0.8.md` | readiness evidence | not download/install/run evidence |
| `benchmark/deployment/download_manifest_v0.8.csv` | future server download route | all rows must keep `download_performed=no` until approved server execution |
| `benchmark/deployment/preflight_download_approval_v0.10.csv` | future download approval table | all rows must keep `download_performed=no` and `approved_by=pending` until approved server execution |
| `benchmark/deployment/method_preflight_status_v0.10.csv` | priority method preflight state | planning-only; no clone/install/run evidence |
| `benchmark/deployment/source_clone_manifest_v0.12.csv` | external source checkout evidence | source-only clone evidence; not install/run/weight evidence |
| `benchmark/deployment/method_readiness_review_v0.8.csv` | method license/env/checkpoint/input-contract audit | not local reproducibility evidence |
| `benchmark/method_sources/method_landscape_watchlist_v0.9.csv` | method landscape and Related Work coverage | not an include scorecard or source pin audit |
| `benchmark/input_sets/target_set_v0.csv` | frozen target interface | remains schema-only until controls, assay, license, leakage, and provenance are complete |
| `benchmark/input_sets/target_control_freeze_checklist_v0.10.md` | target/control freeze gate | checklist only; not target promotion |
| `benchmark/input_sets/example_run.csv` | artificial input-contract example | rows must remain `status=not_real_benchmark` |
| `manuscript/support/benchmark_manuscript_claim_evidence_map.csv` | claim gate | unsupported claims must stay unsupported |
| `ops/validation/wiki_validation_report.md` | latest machine validation result | regenerate through validator, do not hand-edit counts |

## Execution Gates

Method and dataset readiness must move through explicit gates:

1. `metadata_ready`
2. `source_pinned`
3. `license_checked`
4. `weights_manifested`
5. `input_contract_ready`
6. `dry_run_ready`
7. `smoke_test_ready`

Current KB artifacts do not support `smoke_test_ready` for any method. PepMirror remains dependency-blocked until PyRosetta/license and checkpoint/dependency routes are resolved.

## Language And Claim Rules

- Reader-facing prose is Chinese by default.
- Preserve English method names, software commands, paper titles, Zotero item keys, BibTeX keys, URLs, model names, and dataset names.
- Prefer `提示`, `支持`, `表明`, `拟评估`, `仍需验证`, `metadata-level`, and `readiness findings`.
- Do not write that a method is installed, reproduced, runnable, benchmark-completed, problem-free, best-performing, or experimentally validated unless a later phase records environment, commit, command, input, output, runtime, logs, parser result, and validation artifacts.
- Do not treat source pinning, source checkouts, method contracts, availability checks, download manifests, or schema reviews as installation, smoke-test, Benchmark-result, or local-reproducibility evidence.
- Do not treat watchlist datasets, target candidates, review-only methods, or literature examples as frozen Benchmark targets.
- Generation ability, ranking/rescoring ability, developability proxies, structural confidence, and biological validation are separate evidence layers.

## Update Order

1. Inspect `index.md`, `ops/plans/updated_plan_v0.9.md`, and `ops/validation/wiki_validation_report.md`.
2. Refresh source metadata only when the user requests it or the task depends on current external state.
3. Update `kb/references/` and `kb/tables/` before regenerating wiki, manuscript, or ops artifacts.
4. Regenerate or update `kb/wiki/` cards and `_index.md` files when source tables change.
5. Update `benchmark/` protocol, input-set, deployment, method-source, scoring, or availability artifacts.
6. Update `manuscript/`, `ops/`, `index.md`, `README.md`, `RELEASE_NOTES.md`, and append `ops/log.md`.
7. Run validation before claiming completion:

```powershell
$env:PYTHONUTF8='1'
python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

## Validation Rules

- Windows commands that read or write Chinese text should set `PYTHONUTF8=1`.
- `scripts/validate_benchmark_kb.py` is the project validator and must pass with 0 errors and 0 warnings before a release-style update is considered complete.
- `ops/validation/wiki_validation_report.md` is generated by the validator.
- `git diff --check` may report CRLF-to-LF normalization warnings; whitespace errors still need fixing.
- If validator and documentation disagree, update the source artifact or validator expectation, then rerun validation.

## Git And Safety

- The worktree may contain staged or unstaged protocol/manuscript artifacts from v0.6-v1.2. Do not revert unrelated user or prior-agent changes.
- Do not run destructive commands such as `git reset --hard` or `git checkout --` unless explicitly requested.
- Do not commit or push unless the user asks.
- Keep edits scoped to the requested phase and maintain source-library boundaries.
