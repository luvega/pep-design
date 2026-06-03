---
title: "Target sequence-conditioned design of peptide binders using masked language modeling"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:U2VXH3ID"]
---

# Target sequence-conditioned design of peptide binders using masked language modeling

## Metadata
- Zotero item key: `U2VXH3ID`
- BibTeX key: `chen_target_2025`
- Year: 2025
- Venue: Nature Biotechnology
- DOI: 10.1038/s41587-025-02761-2
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: sequence-conditioned peptide language model
- Design modality: target-sequence conditioned sequence generation
- Input: target protein sequence plus design constraints
- Output: linear peptide sequences
- Availability: public GitHub repository and Hugging Face model card to verify

## Evidence Note
The computational design of protein-based binders presents unique opportunities to access ‘undruggable’ targets, but effective binder design often relies on stable three-dimensional structures or structure-influenced latent spaces. Here we introduce PepMLM, a target sequence-conditioned designer of de novo linear peptide binders. Using a masking strategy that positions cognate peptide sequences at the C terminus of target protein sequences, PepMLM finetunes the ESM-2 protein language model to fully reconstruct the binder region, achieving low perplexities matching or improving upon validated peptide–protein sequence pairs. After successful in silico benchmarking with AlphaFold-based docking, we experimentally validate the efficacy of PepMLM through both binding and degradation assays. PepMLM-derived peptides demonstrate sequence-specific binding to cancer and reproductive targets, includ
