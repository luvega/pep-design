# Literature Scope Report

## Scope
- Time window: 2021-06-03 to 2026-06-03
- Primary source: Zotero local API collections and targeted query blocks.
- Source layer reused: `E:\Endnote参考文献\PD-wiki` and `_kb\review_projects\03_ai_drug_design_protein_peptide_methods`.
- Project layer: `E:\Codex_Projects\Pep_design`.

## Counts
- Unique Zotero-derived records after DOI/PMID/arXiv/title dedupe: 432
- Imported PD-wiki/_kb source files: 49
- Method evidence rows: 11
- First-wave included benchmark methods: 9

## Screening Status
- background-only: 26
- included: 125
- needs-manual-check: 281

## Method Family Counts
- AF2 backpropagation plus MPNN/PyRosetta binder pipeline: 1
- AlphaFold/ColabDesign cyclic peptide design: 1
- D-peptide or chirality-aware design: 5
- all-atom structure-prediction inversion: 1
- cyclic/macrocyclic peptide design: 15
- diffusion scaffold generation plus inverse folding sequence design: 1
- energy/search-based D-peptide design: 1
- flow matching for hetero-chiral peptide design: 1
- full-atom geometric latent diffusion: 1
- full-atom multi-modal flow matching: 1
- generative full-atom or diffusion model: 24
- interface-predicting protein language model: 1
- miniprotein/protein binder design: 35
- peptide/protein binder design: 70
- protein/peptide language model: 10
- sequence-conditioned peptide language model: 1
- unclassified: 263

## Notes
- Rows marked `needs-manual-check` are not rejected; they need full-text or repository verification.
- Rows marked `background-only` can support Benchmark article background but do not count toward method candidates.
