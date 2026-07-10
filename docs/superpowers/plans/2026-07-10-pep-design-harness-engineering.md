# Pep Design Harness Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standard-library, contract-driven project acceptance harness that classifies the current v0.33 state honestly and prevents unsupported phase or claim promotion.

**Architecture:** A top-level `harness/` control plane stores JSON contracts, artifact and claim registries, domain evaluators, append-only signoffs, and generated human documentation. A thin script exposes read-only check and explicit render commands while preserving the existing validator and all historic paths.

**Tech Stack:** Python 3 standard library, JSON, CSV, Markdown, pytest.

---

### Task 1: Persist the approved specification

**Files:**
- Create: `docs/superpowers/specs/2026-07-10-pep-design-harness-engineering-design.md`
- Create: `docs/superpowers/plans/2026-07-10-pep-design-harness-engineering.md`

- [ ] Confirm the design has no placeholders, contradictions, or unresolved scope choices.
- [ ] Confirm both documents describe contract v1 independently of Benchmark v0.34.
- [ ] Commit only the two planning documents; do not include existing v0.33 changes.

### Task 2: Define contract and registry fixtures test-first

**Files:**
- Create: `tests/test_harness_contract.py`
- Create: `harness/contracts/project_acceptance_v1.json`
- Create: `harness/registry/artifacts_v1.json`
- Create: `harness/registry/claims_v1.json`
- Create: `harness/registry/migration_parity_v1.json`
- Create: `harness/signoffs/README.md`

- [ ] Write failing tests for contract version, four profiles, eight domains, unique gate IDs, allowlisted evaluators, valid severity, valid dependencies, and dependency-cycle rejection.
- [ ] Run `pytest -q tests/test_harness_contract.py` and confirm failure because the loader and contract do not exist.
- [ ] Add the minimum JSON contract and registries needed by the tests.
- [ ] Record all authoritative v0.33 artifacts, the existing validation report, claim map, target/control manifests, and the three semantic gate facts.
- [ ] Run the contract tests and confirm they pass.

### Task 3: Implement the evaluation kernel test-first

**Files:**
- Create: `harness/__init__.py`
- Create: `harness/engine/__init__.py`
- Create: `harness/engine/models.py`
- Create: `harness/engine/loader.py`
- Create: `harness/engine/evaluator.py`
- Create: `harness/engine/report.py`
- Create: `harness/engine/cli.py`
- Create: `scripts/run_project_acceptance.py`
- Test: `tests/test_harness_engine.py`

- [ ] Write failing tests for deterministic evaluation IDs, dependency rollup, Critical fail-closed behavior, profile selection, exit codes 0/1/2, and check/render separation.
- [ ] Run the focused tests and confirm they fail for missing engine symbols.
- [ ] Implement immutable dataclasses/enums, canonical JSON hashing, contract loading, dependency evaluation, and report models.
- [ ] Implement CLI commands `check --profile ...` and `render`; check must not write files.
- [ ] Run focused tests, then refactor only after green.

### Task 4: Add read-only domain evaluators test-first

**Files:**
- Create: `harness/domains/__init__.py`
- Create: `harness/domains/project_state.py`
- Create: `harness/domains/repository.py`
- Modify: `scripts/validate_benchmark_kb.py`
- Test: `tests/test_harness_domains.py`

- [ ] Write failing golden tests for ten v0.33 failed rows, zero parsed/generated rows, empty target set, unresolved controls, and full-project non-acceptance.
- [ ] Write adversarial tests for D-Flow train overlap, unconditional RFdiffusion target jobs, missing PepMirror mirror evidence, score-before-controls, unsupported Benchmark-result claims, and wet-lab claim triggers.
- [ ] Add `--no-write-report` to the existing validator without changing its default behavior or JSON result.
- [ ] Implement read-only CSV/JSON/Markdown evaluators and the validator subprocess adapter.
- [ ] Verify external-pointer absence blocks new promotion without rewriting historical evidence.
- [ ] Run all domain tests and the legacy validator.

### Task 5: Implement signoffs and generated acceptance artifacts

**Files:**
- Create: `harness/signoffs/signoff.schema.json`
- Create: `harness/signoffs/signoff_request_v1.json`
- Create: `harness/PROJECT_ACCEPTANCE.md`
- Create: `ops/acceptance/project_acceptance_report.json`
- Create: `ops/acceptance/project_acceptance_report.md`
- Test: `tests/test_harness_signoffs_reports.py`

- [ ] Write failing tests for digest matching, stale signoff rejection, Critical override rejection, append-only supersession, JSON/Markdown evaluation-ID parity, and report freshness.
- [ ] Implement signoff validation and report rendering.
- [ ] Render the unsigned baseline; governance and current phase must be machine-pass/pending-signoff while full project remains not accepted.
- [ ] Confirm rerendering unchanged inputs preserves the evaluation ID and content model.

### Task 6: Migrate project navigation and acceptance policy

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `index.md`
- Modify: `benchmark/README.md`
- Modify: `VERSION`
- Modify: `RELEASE_NOTES.md`
- Modify: `ops/log.md`
- Create: `ops/plans/harness_engineering_plan_v1.0.md`
- Test: `tests/test_harness_migration.py`

- [ ] Write failing parity tests proving every legacy artifact-role and claim-boundary key is represented by the new registry or policy.
- [ ] Reduce AGENTS to a progressive-disclosure map while preserving safety, source boundaries, authorization limits, skill routing, and validation commands.
- [ ] Add governance-plan and acceptance-report navigation while leaving v0.33 as the execution baseline and v0.34 as the next generation phase.
- [ ] Update the project checkpoint to 1.2.22 without claiming full-project acceptance.
- [ ] Run parity tests and inspect the diff for accidental deletion of constraints.

### Task 7: Verify and review the complete implementation

**Files:**
- Modify only files required to resolve verified defects.

- [ ] Run `pytest -q` and require all tests to pass.
- [ ] Run `python scripts/run_project_acceptance.py check --profile governance` and expect unsigned pending status with exit 1, not engine error.
- [ ] Run `python scripts/run_project_acceptance.py check --profile current_phase` and expect unsigned pending status with exit 1.
- [ ] Run `python scripts/run_project_acceptance.py check --profile full_project` and expect not accepted with exit 1.
- [ ] Run `python scripts/validate_benchmark_kb.py` and require 0 errors and 0 warnings.
- [ ] Run `git diff --check` and inspect `git status -sb`.
- [ ] Request independent spec and code-quality review; fix all Critical and Important findings and rerun verification.

### Task 8: Human acceptance handoff

**Files:**
- Create only after explicit approval: `harness/signoffs/signoff_governance_v1.json`

- [ ] Present the machine report and exact evidence digest to the project owner.
- [ ] Do not synthesize or assume approval.
- [ ] After explicit approval, add the digest-bound signoff and rerender reports.
- [ ] Recheck governance/current-phase/release-checkpoint profiles; full-project must remain not accepted.
