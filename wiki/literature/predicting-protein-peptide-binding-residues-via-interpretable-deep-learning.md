---
title: "Predicting protein–peptide binding residues via interpretable deep learning"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:4EBXI8YS"]
---

# Predicting protein–peptide binding residues via interpretable deep learning

## Metadata
- Zotero item key: `4EBXI8YS`
- BibTeX key: `wang_predicting_2022`
- Year: 2022
- Venue: Bioinformatics
- DOI: 10.1093/bioinformatics/btac352
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: peptide/protein binder design
- Design modality: 
- Input: sequence or structure depending on method
- Output: designed peptide/miniprotein sequence or structure
- Availability: zotero metadata; runnable status not checked

## Evidence Note
Identifying the protein–peptide binding residues is fundamentally important to understand the mechanisms of protein functions and explore drug discovery. Although several computational methods have been developed, most of them highly rely on third-party tools or complex data preprocessing for feature design, easily resulting in low computational efficacy and suffering from low predictive performance. To address the limitations, we propose PepBCL, a novel BERT (Bidirectional Encoder Representation from Transformers) -based contrastive learning framework to predict the protein–peptide binding residues based on protein sequences only. PepBCL is an end-to-end predictive model that is independent of feature engineering. Specifically, we introduce a well pre-trained protein language model that can automatically extract and learn high-latent representations of protein sequences relevant for pro
