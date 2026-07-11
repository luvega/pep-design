# Pep Design Harness Engineering Design

Date: 2026-07-10

Status: approved design

## Purpose

This design adds a contract-driven governance harness to the peptide-design
Benchmark knowledge base. The harness makes project intent, evidence limits,
stage transitions, and acceptance decisions inspectable and mechanically
enforceable without turning planning or readiness records into Benchmark
results.

The first release accepts the governance system itself. It does not require the
scientific project to be complete. In particular, it must classify the v0.33
baseline as an honest blocker checkpoint with ten failed method-specific
adapter rows and zero generated candidates.

## Design Decisions

- The harness has its own `contract_version=1.0.0`; it does not consume the
  planned v0.34 real-generation phase number.
- JSON is the machine-authoritative format. Markdown acceptance documents and
  reports are rendered from JSON and are not edited independently.
- Existing v0.6-v0.33 artifacts stay at their current paths. A registry maps
  them into the new control plane.
- Validation is local and standard-library-only in v1. CI integration is a
  later work package.
- Agents may run read-only checks, fixture/replay checks, and package commands.
  Clone, download, Docker/GPU generation, and scoring remain approval-gated.
- Machine checks run before human signoff. Human signoff cannot override a
  Critical failure and becomes stale whenever its bound evidence changes.

## Control Plane

The top-level `harness/` directory is the governance system of record:

- `contracts/` defines profiles, domains, gates, dependencies, severity, and
  signoff policy.
- `registry/` maps artifact IDs to paths, evidence classes, mutability, and
  allowed or forbidden uses.
- `engine/` loads the contract and registry, evaluates domain checks, resolves
  the dependency graph, attaches valid signoffs, and renders reports.
- `signoffs/` contains append-only human decisions bound to contract and
  evidence digests.
- `PROJECT_ACCEPTANCE.md` is a generated human-readable rendering of the
  normative contract.

Current machine reports live under `ops/acceptance/`. Their JSON and Markdown
forms share one deterministic evaluation ID.

## Acceptance Model

The harness exposes two distinct axes:

- `harness_status` states whether contracts, registries, evaluators, reports,
  and signoffs are internally valid.
- `project_status` states whether scientific and operational evidence satisfies
  the requested acceptance profile.

Four profiles are evaluated independently:

| profile | meaning |
|:---|:---|
| `governance` | Contract, registry, evaluator, report, and migration integrity. |
| `current_phase` | The current project state is complete and honest for its declared phase. |
| `release_checkpoint` | A versioned planning/readiness checkpoint is consistent and signed. |
| `full_project` | All required scientific, execution, scoring, manuscript, and release gates pass. |

Gate verdicts are `pass`, `fail`, `pending`, `not_applicable`, or `error`.
Rolled-up verdicts are `accepted`, `not_accepted`, `blocked`,
`pending_human_signoff`, or `not_applicable`. Severity is `Critical`, `Major`,
or `Advisory`. Critical failures always fail closed.

## Domains

1. `repository_provenance`: source boundaries, citation integrity, immutable
   snapshots, historic path stability, and the existing KB validator.
2. `method_dataset_readiness`: per-method and per-dataset evidence through
   `metadata_ready`, `source_pinned`, `license_checked`,
   `weights_manifested`, `input_contract_ready`, `dry_run_ready`, and
   `smoke_test_ready`.
3. `target_control_governance`: provenance, positive/negative controls,
   license, train leakage, homology, topology, and chirality policy.
4. `execution_provenance`: approval, revisions, environment, command, input,
   seed, resource budget, logs, runtime, exit status, and raw output pointer.
5. `output_representation`: unified candidate schema, chain mapping,
   sequence/structure consistency, cyclic/D/ncAA handling, and multi-stage
   handoff records.
6. `scoring_validation`: scoring eligibility, generation/ranking separation,
   explicit non-applicability, and validation boundaries.
7. `manuscript_claims`: structured claim-evidence mapping, citations,
   allowed/forbidden wording, four mandatory Benchmark-paper pillars, and
   claim-triggered wet-lab gates.
8. `release_operations`: version consistency, plan pointers, indexes, logs,
   generated-report freshness, tests, validator, whitespace, and signoff.

Dependencies are explicit. Readiness is required before executable packaging;
execution plus parsed output yields only bounded-generation evidence; target,
control, leakage, and controlled multi-case gates are required before scoring;
validated scoring is required before empirical findings become supported.

## Scientific Semantic Gates

The first contract records three known high-value semantic checks:

- D-Flow maps the MDM2 fixture to PepMerge entry `3eqs_B`, which appears in the
  observed training-name list. The fixture may exercise the harness but cannot
  support an independent-test or scoring claim until leakage governance is
  resolved.
- An RFdiffusion cyclic command containing only `[12-18]` is unconditional even
  if an input PDB is present. A target-conditioned job must record a target
  contig and/or approved hotspot contract.
- A PepMirror row marked D-peptide requires explicit mirror/enantiomer
  transformation evidence. A normal `LinearPeptide` template alone is not
  chirality evidence.

These are input/adapter semantics, not algorithm-performance findings.

## Contract Interfaces

Every gate contains a stable ID, domain, title, severity, evaluator name,
artifact inputs, dependency IDs, profile membership, pass criterion, failure
reason code, claim effects, owner role, and signoff policy.

Every artifact contains a stable ID, path, role, format, mutability, evidence
class, verification scope, freshness policy, allowed uses, and forbidden uses.
Tracked files, external pointers, and gitignored runtime artifacts are distinct
verification scopes.

A signoff binds its decision to the contract digest, gate or profile, evidence
digests, reviewer role, reviewer ID, rationale, timestamp, and optional
superseded signoff. Git history is the accountability mechanism; v1 does not
add cryptographic identity infrastructure. Production approval therefore
requires a committed, clean, non-symlink signoff under `harness/signoffs/`.

An evaluation result contains a deterministic ID computed from the contract,
registry, evaluator version, and evidence digests. Rendering timestamps do not
participate in this identity. Generated acceptance reports, signoff files, and
their rendering timestamps are excluded from the evidence digest so rendering
or signing cannot invalidate the evaluation being signed. The evidence digest
does include the Git-visible evaluator/validator source and input surface, so a
code or governed-source change invalidates prior signoffs even if a version
string was not manually bumped.

## Evaluation Flow

The flow is fixed:

1. Validate the contract and registry structure.
2. Resolve artifact paths without changing them.
3. Run allowlisted read-only evaluators.
4. Resolve gate dependencies and profiles.
5. Attach only digest-matched signoffs.
6. Roll up domain and profile verdicts.
7. Render machine JSON and human Markdown from the same result.

`check` is read-only. `render` writes generated acceptance artifacts. A missing
required artifact never becomes a pass. An unavailable external pointer does
not erase a historical audit, but it cannot support a new availability or
reproducibility promotion.

## Agent Workflow

Agents orient from a concise `AGENTS.md`, the current acceptance report, and the
relevant domain contract. They run governance/current-phase preflight, prepare
bounded packages, wait for explicit approval before external execution, ingest
compact evidence, reevaluate, and request digest-bound signoff. Evaluator
errors and timeouts are recorded and are not silently retried.

The existing long artifact-role and claim-boundary rules move into registries
and policy documents. A migration-parity gate prevents this progressive
disclosure change from dropping constraints.

## Verification

Tests cover contract structure, dependency cycles, evaluator allowlists,
registry paths, historical immutability, v0.33 golden status, adversarial state
promotion, stale signoffs, report parity, deterministic evaluation IDs, and
existing-validator compatibility. Governance tests do not use network,
Docker, GPU, generation, or scoring.

The expected unsigned baseline is:

- `governance=machine_pass` with human signoff pending;
- `current_phase=machine_pass` with human signoff pending;
- `release_checkpoint=pending_human_signoff` until release checks and approval;
- `full_project=not_accepted`.

For this baseline, "zero generated candidates" means zero rows whose
`parse_status` is `parsed` or whose run status is `generated`. The ten compact
failure rows remain required evidence rows and are not counted as candidates.
The observed `3eqs_B` training overlap is preserved as a small tracked
derivation containing the source path, source SHA-256, match rule, matched
value, split, and conclusion; clean-clone validation does not depend on the
large gitignored PepMerge assets.

Governance acceptance requires `governance_owner`. A release checkpoint
requires separate `engineering_reviewer` and `scientific_reviewer` roles.
Signoff proves review of an existing machine evaluation and is never a waiver.

## Non-Goals

- No real-generation entrypoint is implemented or run in this work package.
- No target set is frozen.
- No scoring, ranking, or method comparison is performed.
- No wet-lab evidence is created.
- No CI service, database, web application, or remote API is added.
