# PepGLAD v0.35 Mixed-Chirality Connectivity Design

Date: 2026-07-14

Status: approved in dialog

## Purpose

This design adds a prospective PepGLAD connectivity policy that accepts a
single peptide containing both L- and D-residues. The policy is limited to
bounded generation connectivity. It does not establish chemical validity,
reproducibility, scoring eligibility, method ranking, or biological validity.

The user approved two decisions:

- a mixed L/D candidate may satisfy generation connectivity;
- a byte-level mismatch against the historical seed42 baseline is a
  reproducibility warning rather than a connectivity parser failure.

The user also authorized one new bounded PepGLAD seed42 execution. PepGLAD
seed43, scoring, ranking, frozen targets, and wet-lab work remain unauthorized.

## Historical Boundary

All v0.34 artifacts remain unchanged. In particular, `attempt_003` remains a
historical failed diagnostic, the v0.34 result remains 6/7, and its failure-only
diagnostic must never be promoted or rewritten as candidate evidence.

v0.35 is an incremental evidence layer. It defines one new job,
`v035_pepglad_3eqs_seed42`, under `benchmark_runs/v0.35/`. It does not define a
seed43 job. The active connectivity decision combines six independently
validated v0.34 primary candidates with one independently validated v0.35
PepGLAD primary candidate.

## Policy Model

The v0.35 job declares:

```text
chirality_constraint=unrestricted
chirality_check_mode=report_only
baseline_replay_policy=warn_on_mismatch
```

`unrestricted` means the run may produce all-L, all-D, or mixed L/D geometry.
It does not predict the observed class before execution. The result records the
observed class and exact L/D/unknown counts.

The candidate receives `chirality_status=warn` when both L and D residues are
present and every residue is evaluable. It receives `chirality_status=pass`
when every residue is evaluable and the observed candidate is homochiral. An
unknown or unevaluable stereocentre remains a hard failure.

The historical baseline SHA remains recorded. A different, internally
self-consistent candidate SHA produces `baseline_replay_status=warn`. The
baseline is not replaced with the newly observed SHA.

## Hard Failures

The candidate cannot be promoted when any of these conditions fails:

- a required file is missing, empty, non-regular, a symlink, or outside its
  immutable attempt directory;
- captured bytes change during parsing or replay;
- the target SHA, target chain A, binder chain B, or target binding is wrong;
- the binder length is not 11;
- summary sequence and PDB binder sequence disagree;
- requested seed42 is not the recorded effective seed;
- source commit, source entrypoint, model weights, target, container,
  environment, observer, instrumenter, wrapper, or instrumented source pins
  disagree;
- runtime JSON has duplicate keys, non-finite values, extra fields, wrong
  types, or a semantic digest mismatch;
- chirality cannot be evaluated for all 11 binder residues or
  `unknown_count != 0`.

Only mixed chirality and historical baseline mismatch are warnings.

## Result Contract

A successful mixed candidate has these states:

```text
parser_status=parsed
observed_chirality_class=mixed
chirality_status=warn
baseline_replay_status=warn
overall_qc_status=pass_with_warning
supported_candidate=yes
```

The tracked v0.35 evidence is a single exact-schema JSON bundle. It binds the
job, execution result, candidate, QC, runtime provenance, immutable attempt
files and SHA-256 values, and the exact v0.34 artifacts used to supply the six
historical supported primary candidates. The bundle is candidate/connectivity
evidence only.

## Harness Model

The new `current.v035_bounded_connectivity` gate replaces the v0.34 gate in
active profiles. Its evaluator must:

1. independently replay the v0.34 snapshot and confirm exactly six supported
   primary methods plus the historical PepGLAD failure;
2. independently replay the v0.35 raw attempt and exact-schema bundle;
3. confirm that v0.35 contains exactly one PepGLAD seed42 primary and no
   extension, score, rank, or leaderboard evidence;
4. pass only when six v0.34 primary methods plus the v0.35 PepGLAD primary give
   seven supported methods.

The v0.34 gate remains available as historical truth and remains failed. The
v0.35 gate must not depend on that failed gate. The scoring guard depends on
the new gate and continues to prohibit scoring and ranking.

## Execution Boundary

The authorized execution is exactly one new immutable v0.35 PepGLAD seed42
attempt. The runner must reject extension jobs, seed43, other methods,
unlisted jobs, automatic failed retries, and a second execution after an
attempt has been recorded. A failed authorized run stops the phase and requires
another explicit user decision.

## Documentation And Claims

Allowed wording after a successful run is limited to:

> PepGLAD produced one parseable mixed-chirality candidate for the fixed 3EQS
> connectivity fixture under the v0.35 policy; the candidate passed bounded
> connectivity with chirality and byte-level replay warnings.

The project must continue to prohibit claims of full reproducibility, chemical
validity, scoring eligibility, ranking, superior performance, benchmark
completion, or biological validation.

## Non-Goals

- No PepGLAD seed43 execution.
- No rerun of the other six methods.
- No mutation or reclassification of v0.34 artifacts.
- No scoring, ranking, target freezing, wet-lab work, or version release.
- No commit, push, or production signoff in this work package.
