# Pep Design Benchmark KB Agent Rules

## Purpose

This repository is an independent protocol-first Benchmark knowledge base for recent peptide-design methods. It supports literature evidence management, readiness audits, Benchmark manuscript planning, and bounded server-side preparation.

- Current project version: `1.2.21` (unsigned harness checkpoint).
- Current authorized execution plan: `ops/plans/method_runtime_acceptance_plan_v1.md`; the retained scientific protocol baseline is `ops/plans/updated_plan_v0.35.md`.
- Harness engineering plan: `ops/plans/harness_engineering_plan_v1.0.md`.
- Historical baselines include `ops/plans/updated_plan_v0.34.md`, `ops/plans/updated_plan_v0.33.md`, `ops/plans/updated_plan_v0.9.md`, and `ops/plans/updated_plan_v0.6.md`; none is current.
- Active authorized execution: `ops/plans/method_runtime_acceptance_plan_v1.md`, confirmed by the user on 2026-10-02. Complete bounded native end-to-end runtime acceptance for all 10 methods, with candidate quality reported separately under `benchmark/deployment/method_runtime_scope_v2.json`, reuse qualifying evidence, and fill gaps within its fixed phase budgets. Old v0.35 and fresh PepGLAD attempts remain immutable; new phase jobs use separate identities and an explicit resource ledger. Contract v1.2.0 now routes the active checkpoint through `current.native_method_acceptance`; historical connectivity evaluators and attempts are retained unchanged.
- Current phase outcome: 10/10 methods satisfy bounded native runtime checks; 9/10 satisfy the separate candidate-integrity checks. D-Flow produced 17 candidates across its 3 new attempts without a qualified candidate; its attempt budget is exhausted. Stop further D-Flow generation and do not add external relaxation or another attempt without a new user decision. Quality failure alone does not block this runtime-only phase. Consult `ops/acceptance/method_runtime_acceptance_v1.md` for evidence and task-specific limits, including DexDesign's single-IAS scope.

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

`grilling is the primary route` for project planning, decisions and next-step alignment, per the user's 2026-10-02 instruction. Read `/home/a/.codex/skills/grilling/SKILL.md` when applying it.
`superpowers workflow constraints are disabled` in this project. This includes `using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, mandatory worktree/TDD/review/branch-finishing sequences and other automatic superpowers skill triggers. Historical `REQUIRED SUB-SKILL` directives in `docs/superpowers/`, older plans and skill references no longer govern current work; retain them as history.

- Map new or materially changed plans as a decision tree. In each round, ask every question whose prerequisites are settled, numbered with a recommended answer; wait for answers before expanding that frontier.
- Find environment and evidence facts yourself; delegate fact-finding to subagents where useful. Ask the user for decisions, not facts available from files or tools.
- Before implementing a newly discussed plan, summarize the shared understanding and obtain the user's confirmation. Existing explicit decisions and authorizations persist; do not repeatedly reconfirm them. The present routing change is already authorized.
- Choose implementation, tests, reviews and delegation according to the task and evidence needed, without a mandatory skill sequence. Do not infer new execution budgets or scientific acceptance from a planning conversation.

Use the smallest supporting route needed after the planning decisions are settled:

| task | supporting route |
|:---|:---|
| KB structure, indexes, logs, schema boundaries, or `AGENTS.md` | Machine contract; optional `academic-research-suite`, the user-approved fallback for missing `building-llm-wiki` |
| Literature, citations, provenance, claim-evidence, manuscript support | `academic-research-suite` as needed; organize by research questions and evidence |
| Introduction consistency after structure is fixed | Optional `intro-drafter`; `intro-drafter is consistency-check only` |
| Figure planning | `figure-designer` plus `academic-plotting` / `nature-figure-compliance` as relevant |
| Near-submission audit | `pre-submission-reviewer` |
| Thesis-level reassessment | `idea-evaluator` |
| Chinese academic prose and overclaim control | `academic-chinese-style` / `nature-language-style` |
| Zotero/BibTeX access | `zotero:Zotero` and `citation-management`; writes require explicit approval |

`benchmark-paper-template is disabled` by the user's instruction. No skill installation is required. `HKUSTDial/Supervisor-Skills` is a distinct historical manuscript-support source; its installation records are not current mandatory workflow, Benchmark result, scoring evidence, method-ranking evidence, or biological validation.

## Execution Gates

Readiness order is fixed: `metadata_ready` -> `source_pinned` -> `license_checked` -> `weights_manifested` -> `input_contract_ready` -> `dry_run_ready` -> `smoke_test_ready`.

- Planning, source pins, imports, fixtures, parser rows, and bounded examples do not imply later gates.
- The latest v0.34 compact merge contains 13 method-manifest rows, 12 candidate/QC rows, 12 runtime-provenance records, and 14 run rows. Six primary jobs and their six eligible seed43 extensions are supported; the latest PepGLAD candidate is absent and PepGLAD seed43 was not run.
- PepGLAD seed42 `attempt_003` exited 0 but failed closed as parser `pepglad_seed42_replay_mismatch` and merge `evidence_incomplete`. Mixed chirality was observable in the pre-OpenMM snapshot (L6/D5) and changed after OpenMM (L4/D7); this does not establish the model as root cause or exclude an OpenMM effect.
- v0.35 prospectively permits mixed L/D residues for connectivity and records baseline mismatch as a warning, but its only authorized `attempt_001` failed before container startup because the execution environment could not access the Docker API socket. The host preflight passed; `exit_code=1`, parser/QC were not run, `raw/` contains no candidate, and no v0.35 connectivity bundle exists. This is infrastructure failure evidence, not PepGLAD method-failure or mixed-chirality evidence.
- Per the approved v0.35 stop condition, that `attempt_001` remains immutable. The separately authorized fresh PepGLAD execution and the current method-acceptance phase have their own policies and identities; their evidence does not repair or overwrite the v0.35 failure. Additional execution must stay within the current confirmed phase policy and remaining attempt budget.
- Historical v0.34 PepMLM produces `WWX` for both seeds and passed only the old connectivity parser with a noncanonical-residue warning; these candidates fail the current quality requirement. D-Flow uses a 3EQS fixture with known training overlap, so its rows are connectivity evidence only and are ineligible for fair scoring.
- Neither v0.34 nor v0.35 supports scoring, ranking, frozen-target, wet-lab, `smoke_test_ready`, `benchmark_ready`, or full reproducibility claims. The historical `current.v035_bounded_connectivity` evaluation remains a failure because no supported v0.35 PepGLAD candidate bundle exists; it has no active profile. Fresh PepGLAD is separate evidence, and the active Critical gate `current.native_method_acceptance` requires all 10 native runtime endpoints with replayable provenance under the user-amended scope; candidate-quality failures remain separately reported.
- Generation ability, ranking/rescoring ability, developability proxies, structural confidence, and biological validation are separate evidence layers.
- `target_set_v0.csv` remains schema-only until controls, assay, license, leakage, and provenance are complete.
- `example_run.csv` rows remain `status=not_real_benchmark`.
- Download tables remain `download_performed=no` and approval remains pending until authorized external execution is recorded.

## Language And Claim Rules

Reader-facing prose is Chinese by default. Preserve English method/software/dataset names, commands, IDs, keys, URLs, and titles.

Prefer `提示`, `支持`, `表明`, `拟评估`, `仍需验证`, `metadata-level`, and `readiness findings`. Do not claim installed, reproduced, runnable, benchmark-completed, problem-free, best-performing, or experimentally validated without the complete contract-required evidence chain. Unsupported claims stay unsupported under `harness/registry/claims_v1.json`.

## Update Order

1. Inspect `index.md`, `ops/plans/method_runtime_acceptance_plan_v1.md`, the relevant acceptance report, and `ops/validation/wiki_validation_report.md`; consult `ops/plans/updated_plan_v0.35.md` for its retained scientific baseline and historical execution boundaries.
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

The existing validator must finish with 0 errors and 0 warnings. `ops/validation/wiki_validation_report.md` is generated; do not hand-edit its counts. Human signoff cannot waive a Critical/Major failure. Any incomplete method or failed runtime/provenance/resource check in `current.native_method_acceptance` blocks `current_phase` signoff. A production signoff counts only as a committed, clean, regular file under `harness/signoffs/`. Keep `VERSION=1.2.21` until digest-bound governance approval authorizes preparation of the 1.2.22 release candidate; engineering/scientific signoff is then repeated against the final 1.2.22 digest.

## Git And Safety

- The worktree may already be dirty; never revert unrelated user or prior-agent changes.
- Do not use destructive Git commands unless explicitly requested.
- Do not commit or push unless the user asks.
- Keep changes scoped, preserve source-library boundaries, and keep external/runtime artifacts outside the tracked KB.
