---
title: "SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:2GGHXKS1"]
---

# SaLT&PepPr is an interface-predicting language model for designing peptide-guided protein degraders

## Metadata
- Zotero item key: `2GGHXKS1`
- BibTeX key: `brixi_saltpeppr_2023`
- Year: 2023
- Venue: Communications Biology
- DOI: 10.1038/s42003-023-05464-z
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: interface-predicting protein language model
- Design modality: sequence/interface-conditioned degrader peptide design
- Input: target sequence and degrader/interface design context
- Output: peptide-guided protein degrader candidates
- Availability: public GitHub repository and Hugging Face model card to verify

## Evidence Note
Protein-protein interactions (PPIs) are critical for biological processes and predicting the sites of these interactions is useful for both computational and experimental applications. We present a Structure-agnostic Language Transformer and Peptide Prioritization (SaLT&PepPr) pipeline to predict interaction interfaces from a protein sequence alone for the subsequent generation of peptidic binding motifs. Our model fine-tunes the ESM-2 protein language model (pLM) with a per-position prediction task to identify PPI sites using data from the PDB, and prioritizes motifs which are most likely to be involved within inter-chain binding. By only using amino acid sequence as input, our model is competitive with structural homology-based methods, but exhibits reduced performance compared with deep learning models that input both structural and sequence features. Inspired by our previous results
