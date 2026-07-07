# Manuscript Figure Imagegen QC v2

## Scope

The four manuscript figures were regenerated with the built-in `$imagegen` tool on 2026-06-29. The generated bitmap outputs were copied from the Codex image-generation cache into the existing manuscript figure PNG paths.

## Built-In Imagegen Source Files

Default generated-image directory:

`C:\Users\xsui\.codex\generated_images\019f1192-55d8-74d1-aee7-4f077c9bc8b6`

| figure | generated source | project asset |
|:---|:---|:---|
| Figure 1 | `ig_0b2cc8128bae9645016a4235ac2e38819a87f3b698f976e008.png` | `manuscript/assets/figures/benchmark_figure1_overview_v1.png` |
| Figure 2 | `ig_0b2cc8128bae9645016a42366a5e5c819ab80e1c45b5907a56.png` | `manuscript/assets/figures/benchmark_figure2_task_method_matrix_v1.png` |
| Figure 3 | `ig_0b2cc8128bae9645016a4236c1d970819a8c74827378d70073.png` | `manuscript/assets/figures/benchmark_figure3_dual_track_v1.png` |
| Figure 4 | `ig_0b2cc8128bae9645016a42371a5db0819aa997b3e3bf9d1cd6.png` | `manuscript/assets/figures/benchmark_figure4_scoring_architecture_v1.png` |

## Figure Contracts

| figure | core conclusion | hierarchy generated |
|:---|:---|:---|
| Figure 1 | A protocol-first Benchmark must separate task interfaces, readiness gates and claim boundaries before execution. | running example -> protocol pipeline -> claim gate |
| Figure 2 | T1/T2/T3 methods require task-specific inputs, controls and metric applicability before comparison. | task rows -> method gate labels -> control/scoring evidence columns |
| Figure 3 | Generation, ranking/rescoring and biological success are separate evidence layers. | generation lane -> ranking/rescoring lane -> missing-measurement layer |
| Figure 4 | Independent metric CSVs should merge through explicit keys and not-applicable states. | inputs -> metric modules -> merged report -> reporting boundary |

## Manual Visual Check

- Figure 1 contains the running example, T1/T2/T3 task routes, protocol pipeline and claim gate.
- Figure 2 contains a task-method-target evidence matrix, method gates and the `target_set_v0.csv` boundary.
- Figure 3 separates generation and ranking/rescoring tracks and shows missing execution, parser, biological and chemistry measurements.
- Figure 4 shows `run.csv`, independent metric CSV modules, `merged_run.csv`, status vocabulary and reportable/not-reportable boundaries.
- The generated figures are raster PNG manuscript schematics. They are not editable vector figures.

## Boundary Checks

- No panel reports benchmark scores, method rankings, hit rates, local reproduction, wet-lab validation, dataset downloads or GPU execution.
- Frozen target rows remain 0 in the underlying KB validation state.
- These figures are protocol/readiness visuals only, not execution evidence or performance evidence.
