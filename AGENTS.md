# Pep Design Benchmark KB Operating Rules

## Purpose
This project is an independent Benchmark background knowledge base for recent peptide-design methods.

## Source Boundaries
- Do not edit `E:\Endnote参考文献`, EndNote `.enl` files, Zotero items, or the upstream `PD-wiki`.
- Treat `raw_sources/` as a local read-only mirror/snapshot layer.
- Treat `wiki/`, `tables/`, `references/`, and `reports/` as generated project artifacts.
- Treat `benchmarks/` as the Benchmark protocol, smoke-test planning, and future run-result interface layer.

## Language And Claims
- Reader-facing prose is Chinese by default.
- Preserve English method names, paper titles, Zotero item keys, BibTeX keys, URLs, model names, and command names.
- Do not claim local reproducibility until a method has been installed and run in a later Benchmark phase.
- Use `提示/支持/表明/仍需验证` rather than overclaiming when evidence is only metadata-level.

## Update Order
1. Refresh Zotero/API snapshots.
2. Update `references/` and `tables/`.
3. Regenerate `wiki/` cards and `_index.md` files.
4. Update `reports/` and append `log.md`.
5. Run `python scripts/validate_benchmark_kb.py`.
