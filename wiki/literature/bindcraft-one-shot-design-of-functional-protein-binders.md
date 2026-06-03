---
title: "BindCraft: one-shot design of functional protein binders"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:QCD2DXXI"]
---

# BindCraft: one-shot design of functional protein binders

## Metadata
- Zotero item key: `QCD2DXXI`
- BibTeX key: `pacesa_bindcraft_2024`
- Year: 2024
- Venue: bioRxiv
- DOI: 10.1101/2024.09.30.615802
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: AF2 backpropagation plus MPNN/PyRosetta binder pipeline
- Design modality: one-shot protein/miniprotein binder design
- Input: target structure and binder design settings
- Output: protein/miniprotein binder sequences and structures
- Availability: public GitHub repository to verify

## Evidence Note
Protein–protein interactions (PPIs) are at the core of all key biological processes. However, the complexity of the structural features that determine PPIs makes their design challenging. We present BindCraft, an open-source and automated pipeline for de novo protein binder design with experimental success rates of 10-100%. BindCraft leverages the trained deep learning weights of AlphaFold21 to generate nanomolar binders without the need for high-throughput screening or experimental optimization, even in the absence of known binding sites. We successfully designed binders against a diverse set of challenging targets, including cell-surface receptors, common allergens, de novo designed proteins, and multi-domain nucleases, such as CRISPR-Cas9. We showcase their functional and therapeutic potential by demonstrating that designed binders can reduce IgE binding to birch allergen in patient-d
