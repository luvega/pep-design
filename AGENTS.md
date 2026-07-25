# Pep Design Benchmark KB Agent Rules

## Purpose

This repository is an independent protocol-first Benchmark knowledge base for recent peptide-design methods. It supports literature evidence management, readiness audits, Benchmark manuscript planning, and bounded server-side preparation.

- Current project version: `1.2.21` (unsigned harness checkpoint).
- Current scientific/execution plan: `ops/plans/updated_plan_v0.35.md`.
- Harness engineering plan: `ops/plans/harness_engineering_plan_v1.0.md`.
- Historical baselines include `ops/plans/updated_plan_v0.34.md`, `ops/plans/updated_plan_v0.33.md`, `ops/plans/updated_plan_v0.9.md`, and `ops/plans/updated_plan_v0.6.md`; none is current.
- Next scientific phase: obtain a new user decision on authorizing a fresh, non-overwriting PepGLAD execution after the v0.35 Docker API permission failure, or accept the infrastructure failure. Do not retry `attempt_001`, create `attempt_002`, run seed43, or start scoring without new authorization and an updated attempt policy.

Do not start clone, install, large download, broad GPU execution, generation, scoring, or ranking unless the user explicitly authorizes that phase. Large assets and runtime outputs stay in gitignored external roots.

## Harness Authority

- Machine contract: `harness/contracts/project_acceptance_v1.json`.
- Artifact/evidence boundaries: `harness/registry/artifacts_v1.json`.
- Claim rules: `harness/registry/claims_v1.json`.
- Migration parity: `harness/registry/migration_parity_v1.json`.
- Full pre-harness rules and artifact-role table: `harness/policies/legacy_agents_v1.md` (read-only historical policy source).
- Generated contract view: `harness/PROJECT_ACCEPTANCE.md`.
- Current report: `ops/acceptance/project_acceptance_report.md` and `.json`.

Use progressive disclosure: read this file first, then the current plan, the requested profile/report, and only the relevant registry/domain artifacts. The JSON contract and registries are authoritative when generated prose differs.

## Source Boundaries

- Never edit `E:\Endnote参考文献`, EndNote `.enl`, Zotero items, or upstream `PD-wiki`.
- Treat `sources/raw_snapshots/` as read-only.
- Treat `kb/references/`, `kb/tables/`, `kb/wiki/`, `manuscript/`, `ops/`, and `benchmark/` as generated project artifacts.
- Do not put third-party sources, datasets, weights, archives, batch structures, raw logs, Docker layers, or GPU results in the tracked KB.
- `benchmark/` is the protocol, readiness, bounded evidence, and future result-interface layer; artifact-specific meaning comes from the registry.

## Skill Routing

Use the smallest route that covers the task.

| task | required route |
|:---|:---|
| KB structure, indexes, logs, schema boundaries, or `AGENTS.md` | `building-llm-wiki` |
| Literature, citations, provenance, claim-evidence, manuscript pipeline | `academic-research-suite` |
| Benchmark manuscript structure and five-pillar audit | `benchmark-paper-template`; Supervisor-Skills `benchmark-paper-template is the primary route` |
| Introduction consistency after structure is fixed | Supervisor-Skills `intro-drafter is consistency-check only` |
| Figure planning | `figure-designer` plus `academic-plotting` / `nature-figure-compliance` as relevant |
| Near-submission audit | `pre-submission-reviewer` |
| Thesis-level reassessment | `idea-evaluator` |
| Chinese academic prose and overclaim control | `academic-chinese-style` / `nature-language-style` |
| Zotero/BibTeX access | `zotero:Zotero` and `citation-management`; writes require explicit approval |

For broad research-to-paper work, route through `academic-research-suite`, then `benchmark-paper-template`. Supervisor-Skills guidance is writing support, not Benchmark result, scoring evidence, method-ranking evidence, or biological validation.

## Execution Gates

Readiness order is fixed: `metadata_ready` -> `source_pinned` -> `license_checked` -> `weights_manifested` -> `input_contract_ready` -> `dry_run_ready` -> `smoke_test_ready`.

- Planning, source pins, imports, fixtures, parser rows, and bounded examples do not imply later gates.
- The latest v0.34 compact merge contains 13 method-manifest rows, 12 candidate/QC rows, 12 runtime-provenance records, and 14 run rows. Six primary jobs and their six eligible seed43 extensions are supported; the latest PepGLAD candidate is absent and PepGLAD seed43 was not run.
- PepGLAD seed42 `attempt_003` exited 0 but failed closed as parser `pepglad_seed42_replay_mismatch` and merge `evidence_incomplete`. Mixed chirality was observable in the pre-OpenMM snapshot (L6/D5) and changed after OpenMM (L4/D7); this does not establish the model as root cause or exclude an OpenMM effect.
- v0.35 prospectively permits mixed L/D residues for connectivity and records baseline mismatch as a warning, but its only authorized `attempt_001` failed before container startup because the execution environment could not access the Docker API socket. The host preflight passed; `exit_code=1`, parser/QC were not run, `raw/` contains no candidate, and no v0.35 connectivity bundle exists. This is infrastructure failure evidence, not PepGLAD method-failure or mixed-chirality evidence.
- Per the approved stop condition, `attempt_001` is immutable and cannot be retried. Further PepGLAD execution requires new explicit authorization and an updated execution/attempt policy; accepting the infrastructure failure leaves the Critical gate open.
- PepMLM produces `WWX` for both seeds and therefore passes with a noncanonical-residue warning. D-Flow uses a 3EQS fixture with known training overlap, so its rows are connectivity evidence only and are ineligible for fair scoring.
- Neither v0.34 nor v0.35 supports scoring, ranking, frozen-target, wet-lab, `smoke_test_ready`, `benchmark_ready`, or full reproducibility claims. `current.v035_bounded_connectivity` remains a Critical failure because no supported v0.35 PepGLAD candidate bundle exists.
- Generation ability, ranking/rescoring ability, developability proxies, structural confidence, and biological validation are separate evidence layers.
- `target_set_v0.csv` remains schema-only until controls, assay, license, leakage, and provenance are complete.
- `example_run.csv` rows remain `status=not_real_benchmark`.
- Download tables remain `download_performed=no` and approval remains pending until authorized external execution is recorded.

## Language And Claim Rules

Reader-facing prose is Chinese by default. Preserve English method/software/dataset names, commands, IDs, keys, URLs, and titles.

Prefer `提示`, `支持`, `表明`, `拟评估`, `仍需验证`, `metadata-level`, and `readiness findings`. Do not claim installed, reproduced, runnable, benchmark-completed, problem-free, best-performing, or experimentally validated without the complete contract-required evidence chain. Unsupported claims stay unsupported under `harness/registry/claims_v1.json`.

## Update Order

1. Inspect `index.md`, `ops/plans/updated_plan_v0.35.md`, the relevant acceptance report, and `ops/validation/wiki_validation_report.md`.
2. Refresh external metadata only when requested or required by current-state verification.
3. Update source tables before wiki/manuscript/ops derivatives; preserve historic paths.
4. Update Benchmark protocol/input/deployment/result interfaces within their registered evidence boundaries.
5. Update navigation, release notes, and append `ops/log.md`.
6. Run the acceptance check and project validation before claiming completion.

`check` is read-only; `render` updates only generated acceptance artifacts:

```bash
python scripts/run_project_acceptance.py check --profile current_phase
python scripts/run_project_acceptance.py render --profile current_phase
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

The existing validator must finish with 0 errors and 0 warnings. `ops/validation/wiki_validation_report.md` is generated; do not hand-edit its counts. Human signoff cannot waive a Critical/Major failure. The current v0.35 Critical failure blocks `current_phase` signoff. A production signoff counts only as a committed, clean, regular file under `harness/signoffs/`. Keep `VERSION=1.2.21` until digest-bound governance approval authorizes preparation of the 1.2.22 release candidate; engineering/scientific signoff is then repeated against the final 1.2.22 digest.

## Git And Safety

- The worktree may already be dirty; never revert unrelated user or prior-agent changes.
- Do not use destructive Git commands unless explicitly requested.
- Do not commit or push unless the user asks.
- Keep changes scoped, preserve source-library boundaries, and keep external/runtime artifacts outside the tracked KB.
