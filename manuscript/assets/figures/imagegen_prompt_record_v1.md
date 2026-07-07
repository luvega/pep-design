# Manuscript Figure Imagegen Record v1/v2

Built-in `$imagegen` was used to regenerate the four manuscript figure PNG assets. The current project assets are raster PNG schematics copied from the Codex generated-image cache into `manuscript/assets/figures/`.

Current source of truth:

- QC report: `manuscript/assets/figures/manuscript_figure_imagegen_qc_v2.md`.
- Generated-image cache: `C:\Users\xsui\.codex\generated_images\019f1192-55d8-74d1-aee7-4f077c9bc8b6`.
- Project outputs: four PNG files under `manuscript/assets/figures/`.

Regenerated figure contracts:

- Figure 1: running example -> protocol pipeline -> claim gate.
- Figure 2: T1/T2/T3 task rows -> method gate labels -> control/scoring evidence columns.
- Figure 3: generation track -> ranking/rescoring track -> missing-measurement layer.
- Figure 4: inputs -> independent metric CSV modules -> `merged_run.csv` -> reporting boundary.

Prompt anchors:

- Figure 1: sophisticated multi-panel peptide-design Benchmark overview with the exact title `图 1 基准测试贯穿示例与总体流程`.
- Figure 2: task-method-target evidence matrix with T1/T2/T3 rows and evidence/scoring columns.
- Figure 3: two-track generation versus ranking/rescoring workflow plus missing-measurement layer.
- Figure 4: scoring architecture diagram with independent metric CSV modules and reportable/not-reportable boundary.

Boundary: these are conceptual manuscript figures and planning/readiness artifacts, not benchmark results and not evidence of local method reproducibility, dataset download, target-set freeze, GPU execution, or biological validation.
