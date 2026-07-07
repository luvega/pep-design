# Adapter Replay Contract v0.16

## Purpose

This contract defines the minimum replay metadata required before a v0.15 minimal smoke test can become a repeatable Batch B adapter/parser run. It is a planning and interface artifact only. It is not a run log and does not promote any method to `smoke_test_ready`.

## Required Replay Fields

Every future replayable method job must provide:

- `job_id`
- `method`
- `source_commit`
- `image_tag`
- `model_or_weight_revision`
- `input_manifest_path`
- `adapter_command`
- `raw_output_root`
- `stdout_log`
- `stderr_log`
- `exit_code`
- `runtime_seconds`
- `parser_name`
- `parser_version`
- `candidate_outputs_path`
- `run_csv_path`
- `failure_state`

Large files remain external. KB rows may store paths and summaries only.

## Parser Contract

Parsers must emit:

- one row per candidate in `candidate_outputs.csv`
- one linked row per candidate in `run.csv`
- parse status from `parsed`, `partial`, `failed`, or `not_applicable`
- failure reason when sequence, structure, rank, chain, topology, chirality or cyclic metadata is missing
- no scoring fields unless metric CSVs were actually produced

## Batch B Gate

A method may enter controlled Batch B only when:

1. source commit and image tag are pinned;
2. input adapter is deterministic for one reviewed candidate target;
3. raw output parser has a small fixture and documented failure state;
4. output rows can join on `design_id`;
5. target/control queue has no unresolved license, assay, leakage or control blocker for the chosen target.

## Boundaries

- No new execution is recorded by this contract.
- v0.15 minimal smoke tests remain minimal example evidence.
- A parser fixture is not performance evidence.
- A Batch B target review row is not a frozen target.
- `smoke_test_ready` requires later command, input, output, runtime, logs, parser result and validation artifacts.

