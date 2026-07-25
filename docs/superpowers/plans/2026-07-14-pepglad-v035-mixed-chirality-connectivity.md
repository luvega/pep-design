# PepGLAD v0.35 Mixed-Chirality Connectivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a prospective v0.35 PepGLAD-only connectivity lane that accepts fully evaluable mixed L/D geometry and treats historical byte-level replay mismatch as a warning while preserving every v0.34 artifact.

**Architecture:** A one-row v0.35 job and execution matrix drive a dedicated adapter/runner. A dedicated parser publishes one exact-schema JSON evidence bundle. The Harness combines six independently replayed v0.34 primary candidates with one independently replayed v0.35 PepGLAD candidate; it leaves the historical v0.34 6/7 failure intact and keeps scoring disabled.

**Tech Stack:** Python 3.13 standard library, existing v0.34 bounded-process and PDB/QC primitives, canonical JSON and SHA-256, pytest, Harness contracts/registries/evaluators, existing KB validator.

---

## File Map

| responsibility | files |
|:---|:---|
| prospective protocol | `ops/plans/updated_plan_v0.35.md`, `benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv`, `benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv` |
| method execution | `scripts/v035_adapters/__init__.py`, `scripts/v035_adapters/pepglad.py`, `scripts/run_v035_pepglad_connectivity.py` |
| compact evidence | `scripts/parse_v035_pepglad_connectivity.py`, `benchmark/results/pilot_pepglad_connectivity_v0.35.json` |
| governance | `harness/registry/artifacts_v1.json`, `harness/contracts/project_acceptance_v1.json`, `harness/engine/loader.py`, `harness/domains/project_state.py`, `scripts/validate_benchmark_kb.py` |
| tests | `tests/test_v035_pepglad_policy.py`, `tests/test_v035_runner.py`, `tests/test_v035_merge.py`, `tests/test_v035_validator.py`, focused additions to `tests/test_harness_contract.py` and `tests/test_harness_domains.py` |
| reader-facing state | `ops/audits/v035_pepglad_connectivity_audit.md`, claim map, README files, `index.md`, `RELEASE_NOTES.md`, `ops/log.md`, `AGENTS.md` and migration parity |

Implementation agents must not stage, commit, push, sign off, run seed43, or
touch unrelated dirty files.

### Task 1: Freeze The v0.35 Red-Test Contract

**Files:**
- Create: `tests/test_v035_pepglad_policy.py`
- Create: `tests/test_v035_runner.py`
- Create: `tests/test_v035_merge.py`
- Create: `tests/test_v035_validator.py`
- Modify: `tests/test_harness_contract.py`
- Modify: `tests/test_harness_domains.py`

- [ ] **Step 1: Add report-only chirality tests**

Create fixtures whose PDB geometry yields L6/D5, L4/D7, all-L, and one unknown
residue. Assert this interface:

```python
qc = evaluate_v035_candidate(job, candidate, runtime, raw_root)
assert qc["observed_chirality_class"] == "mixed"
assert qc["chirality_status"] == "warn"
assert qc["overall_qc_status"] == "pass_with_warning"
assert (qc["chirality_l_count"], qc["chirality_d_count"]) == (4, 7)
assert qc["chirality_unknown_count"] == 0
```

The unknown fixture must return `chirality_status=fail` and cannot be
supported. A homochiral fully evaluable candidate may return `pass`.

- [ ] **Step 2: Add replay-warning and integrity tests**

Assert that a post-PDB SHA different from the historical baseline parses when
all self-bindings agree:

```python
candidate, runtime = adapter.parse(V035_JOB, attempt)
assert candidate["parse_status"] == "parsed"
assert runtime["baseline_replay_status"] == "mismatch"
```

Parameterize tampering of actual candidate bytes, runtime semantic digest,
target SHA, seed, source commit, source entrypoint, model weights, environment,
observer, instrumenter, wrapper and instrumented source. Every mutation must
fail closed. Add duplicate-key, non-finite JSON, path escape, symlink and
capture-change cases.

- [ ] **Step 3: Add runner authorization tests**

Assert the v0.35 manifest contains exactly one method/job/seed tuple:

```python
assert [(row["method"], row["random_seed"], row["seed_stage"]) for row in jobs] == [
    ("PepGLAD", "42", "primary")
]
```

Assert seed43, extension, another method, an unlisted job, `--retry-failed`, and
a second attempt after any recorded attempt are rejected before execution.

- [ ] **Step 4: Add bundle and historical immutability tests**

Snapshot the bytes of every governed v0.34 artifact before v0.35 publication
and compare them afterward. Assert the v0.35 bundle contains one supported
candidate and binds exact v0.34 SHA values without copying or mutating old
rows. Reject extra keys, stale SHA values, a second job, or any score/rank key.

- [ ] **Step 5: Add Harness transition tests**

Keep the existing v0.34 evaluator at six of seven. Add a v0.35 evaluator test
that passes only for six valid historical primaries plus one valid v0.35
PepGLAD primary. Assert active profiles require
`current.v035_bounded_connectivity`, the new gate does not depend on the failed
v0.34 gate, and `current.scoring_guard` remains required.

- [ ] **Step 6: Run red tests**

Run:

```bash
pytest -q \
  tests/test_v035_pepglad_policy.py \
  tests/test_v035_runner.py \
  tests/test_v035_merge.py \
  tests/test_v035_validator.py \
  tests/test_harness_contract.py \
  tests/test_harness_domains.py
```

Expected: new v0.35 tests fail because the modules, artifacts and gate do not
exist. Existing v0.34 tests must remain green.

### Task 2: Add The Prospective Protocol And Bounded Runner

**Files:**
- Create: `ops/plans/updated_plan_v0.35.md`
- Create: `benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv`
- Create: `benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv`
- Create: `scripts/v035_adapters/__init__.py`
- Create: `scripts/v035_adapters/pepglad.py`
- Create: `scripts/run_v035_pepglad_connectivity.py`
- Modify only shared v0.34 primitives when a red test proves reuse is needed.

- [ ] **Step 1: Define the exact one-job manifest**

The row must use `v035_pepglad_3eqs_seed42`, seed42, primary stage, target 3EQS,
chains A/B, length 11, and these exact policy fields:

```text
chirality_constraint=unrestricted
chirality_check_mode=report_only
baseline_replay_policy=warn_on_mismatch
```

Do not add a seed43 row.

- [ ] **Step 2: Implement v0.35 parsing semantics**

Reuse v0.34 fixed pins and stable file parsing, but expose v0.35 policy as a
separate module. Baseline mismatch must not return a failed candidate. The
adapter must return the observed chirality class in the candidate:

```python
candidate.update(
    chirality=observed_class,
    parse_status="parsed",
    status_reason="pepglad_standard_output_parsed_with_replay_warning",
)
```

Candidate SHA, runtime SHA, target, seed and producer bindings remain exact.

- [ ] **Step 3: Implement the one-shot runner**

The wrapper may reuse hardened v0.34 attempt creation and stable capture, but
must inject the v0.35 manifest/matrix/adapter and run root. Validate the
allowlist before creating a directory. Refuse `--retry-failed`, refuse an
existing attempt, and expose only `--dry-run` and `--execute` for the single
authorized primary.

- [ ] **Step 4: Run policy and runner tests**

Run:

```bash
pytest -q tests/test_v035_pepglad_policy.py tests/test_v035_runner.py
```

Expected: pass; all v0.34 adapter and runner tests also pass.

### Task 3: Publish One Exact-Schema v0.35 Evidence Bundle

**Files:**
- Create: `scripts/parse_v035_pepglad_connectivity.py`
- Create after execution: `benchmark/results/pilot_pepglad_connectivity_v0.35.json`
- Test: `tests/test_v035_merge.py`

- [ ] **Step 1: Implement stable raw replay**

Read the immutable attempt with no-follow regular-file checks, capture each
file once, replay adapter parse and QC from a temporary snapshot, then recapture
and compare identity and bytes. Reuse the v0.34 stable-capture primitives where
their interfaces are exact.

- [ ] **Step 2: Define the bundle schema**

The top-level keys are exact:

```python
{
    "schema_version": "v0.35",
    "evidence_boundary": "bounded_connectivity_only_not_scoring_or_ranking",
    "historical_v034_bindings": {...},
    "job": {...},
    "execution": {...},
    "candidate": {...},
    "qc": {...},
    "runtime_provenance": {...},
}
```

`historical_v034_bindings` records SHA-256 values for every v0.34 artifact used
by the new gate and the expected historical primary count `6`. Reject any key
whose name or value implies scoring, ranking, leaderboard or benchmark result.

- [ ] **Step 3: Publish atomically**

Write canonical JSON with `sort_keys=True`, `allow_nan=False`, a terminal
newline, and an atomic replace in the tracked results directory. Never write a
v0.34 path.

- [ ] **Step 4: Run bundle tests**

Run:

```bash
pytest -q tests/test_v035_merge.py
```

Expected: valid warning candidate publishes; tampered, extra-job, scoring, and
historical-mutation fixtures fail closed.

### Task 4: Add Independent Harness And Validator Enforcement

**Files:**
- Modify: `harness/registry/artifacts_v1.json`
- Modify: `harness/contracts/project_acceptance_v1.json`
- Modify: `harness/engine/loader.py`
- Modify: `harness/domains/project_state.py`
- Modify: `scripts/validate_benchmark_kb.py`
- Modify: `tests/test_harness_contract.py`
- Modify: `tests/test_harness_domains.py`
- Modify: `tests/test_v035_validator.py`

- [ ] **Step 1: Register the v0.35 inputs and bundle**

Register the plan, job manifest, execution matrix and evidence bundle with
bounded-connectivity evidence classes. Permit generated-candidate wording only
inside the gate boundary and prohibit scoring, ranking, full reproducibility
and biological claims.

- [ ] **Step 2: Add the active v0.35 gate**

Create `current.v035_bounded_connectivity`, replace the v0.34 gate in active
profiles, and update the scoring guard dependency. Keep the v0.34 gate and
evaluator as historical truth.

- [ ] **Step 3: Implement independent replay in Harness**

Do not trust the bundle's support boolean. Independently validate the exact
schema, v0.34 artifact digests and six-primary state, raw attempt confinement,
adapter parse/QC replay, fixed pins, candidate/QC/provenance cross-bindings and
the absence of seed43/scoring content.

- [ ] **Step 4: Implement an independent validator path**

The KB validator must reproduce the same decision without delegating to the
Harness boolean. It must report zero errors and zero warnings for the expected
`pass_with_warning` scientific state; the scientific warning belongs in the
artifact, not as a validator defect.

- [ ] **Step 5: Run governance tests**

Run:

```bash
pytest -q \
  tests/test_v035_validator.py \
  tests/test_harness_contract.py \
  tests/test_harness_domains.py \
  tests/test_harness_pipeline.py
```

Expected: active v0.35 gate passes only for a valid bundle; scoring remains
disabled; all historical v0.34 tests remain green.

### Task 5: Execute The One Authorized Attempt And Update Project State

**Files:**
- Create externally: `benchmark_runs/v0.35/pepglad/v035_pepglad_3eqs_seed42/attempt_001/`
- Create: `benchmark/results/pilot_pepglad_connectivity_v0.35.json`
- Create: `ops/audits/v035_pepglad_connectivity_audit.md`
- Modify: `README.md`, `index.md`, relevant Benchmark README files,
  `RELEASE_NOTES.md`, `ops/log.md`, claim map, `AGENTS.md`, migration parity.

- [ ] **Step 1: Run all pre-execution focused tests**

Run all v0.35 tests plus all v0.34 adapter, runner and merge tests. Do not run
the GPU job while any test fails.

- [ ] **Step 2: Execute exactly one seed42 attempt**

Run:

```bash
python scripts/run_v035_pepglad_connectivity.py --execute
```

Expected: exactly one new immutable attempt. Do not retry on failure. Do not
run seed43.

- [ ] **Step 3: Publish and inspect the bundle**

Run:

```bash
python scripts/parse_v035_pepglad_connectivity.py
```

Confirm the observed sequence, pre/post chirality counts, baseline status,
candidate SHA, runtime/pin bindings and final supported state. Claims must
reflect the actual result; a failed attempt stays failed.

- [ ] **Step 4: Update derived prose and claims**

Write plain Chinese. State connectivity only, preserve v0.34 6/7 history, and
explicitly retain prohibitions on scoring, ranking, reproducibility, chemical
validity and biological validity. Update migration parity after all governed
source changes.

### Task 6: Verify And Review End To End

**Files:**
- Generated only: `ops/acceptance/project_acceptance_report.md`,
  `ops/acceptance/project_acceptance_report.json`,
  `ops/validation/wiki_validation_report.md`

- [ ] **Step 1: Run focused and full tests**

```bash
pytest -q tests/test_v035_pepglad_policy.py tests/test_v035_runner.py \
  tests/test_v035_merge.py tests/test_v035_validator.py
pytest -q
```

- [ ] **Step 2: Run validator and acceptance**

```bash
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py
python scripts/run_project_acceptance.py render --profile current_phase
python scripts/run_project_acceptance.py check --profile current_phase
git diff --check
git status -sb
```

The validator must report 0 errors and 0 warnings. Acceptance may become
machine-pass for connectivity, but any remaining independent gate or required
human signoff remains visible and cannot be waived.

- [ ] **Step 3: Run independent reviews**

Use separate scientific-policy, spec-compliance and code-quality reviewers.
Resolve every Critical or Major issue and rerun affected verification.

- [ ] **Step 4: Stop without release operations**

Leave `VERSION=1.2.21`. Do not sign, commit, push, score, rank, or run seed43.
