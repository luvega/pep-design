---
type: agent_guide
title: PD-wiki Agent Guide
sources:
  - raw/manifests/pd_literature_manifest.csv
---

# PD-wiki Agent Guide

This vault follows the LLM Wiki pattern: raw sources are provenance records, wiki pages are the editable synthesis layer, and schema files define rules.

Rules:
- Do not copy or move PDFs into this vault.
- Do not mutate Zotero, EndNote, or `_kb` source manifests unless explicitly requested.
- Every generated claim should preserve `sources` frontmatter or link back to a source card.
- Use Chinese for review-facing notes unless a citation/title requires English.
- Prefer small, linked pages over one long undifferentiated summary.
