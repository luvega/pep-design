# Pep Design Benchmark Knowledge Base

This repository contains the first public version of a peptide-design method benchmark background knowledge base.

The current release focuses on literature and method triage, not on running benchmark jobs. It builds a project-local knowledge layer from Zotero metadata, selected existing PD-wiki evidence cards, and external repository/model route checks.

## Current Version

- Version: `0.1.0`
- Build date: 2026-06-03
- Literature window: 2021-06-03 to 2026-06-03
- Included first-wave candidate methods: 9
- Watchlist methods: 2

## What Is Included

- `references/`: BibTeX export, Zotero-to-BibTeX key map, search log, dedupe report.
- `tables/`: master literature manifest, method evidence matrix, candidate method scorecard.
- `wiki/`: literature cards, method cards, concept pages, benchmark candidate pages.
- `raw_sources/`: read-only local snapshots copied into the project for provenance.
- `reports/`: skill selection, literature scope, shortlist, build summary, validation report.
- `scripts/`: reproducible build and validation scripts.

## First-Wave Candidate Methods

The `include` set is:

- PepMLM
- SaLT&PepPr
- DiffPepBuilder
- PepGLAD
- D-Flow / PeptideDesign
- AfCycDesign / ColabDesign cyclic peptide
- DexDesign / OSPREY3
- RFdiffusion + ProteinMPNN
- BindCraft

PepFlow and BoltzDesign1 are retained as watchlist methods until their executable route, checkpoint use, and peptide/miniprotein task fit are confirmed.

## Rebuild And Validate

Run from the repository root on Windows PowerShell:

```powershell
$env:PYTHONUTF8='1'
python scripts/build_benchmark_kb.py
python scripts/validate_benchmark_kb.py
```

Expected validation for v0.1.0:

- `status`: `pass`
- `master_rows`: 432
- `included_methods`: 9
- `method_cards`: 11
- `literature_cards`: 120
- `bibtex_entries`: 432

## Source Boundary

This repository is the working project layer. Zotero, EndNote, and the prior PD-wiki remain upstream source systems. The files under `raw_sources/` are local project snapshots used for provenance and should be treated as read-only.

No model weights, downloaded PDFs, EndNote libraries, or benchmark execution outputs are included in this release.
