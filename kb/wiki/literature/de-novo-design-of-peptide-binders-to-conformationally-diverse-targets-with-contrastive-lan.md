---
title: "De novo design of peptide binders to conformationally diverse targets with contrastive language modeling"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:6L3IXMYX"]
---

# De novo design of peptide binders to conformationally diverse targets with contrastive language modeling

## Metadata
- Zotero item key: `6L3IXMYX`
- BibTeX key: `bhat_novo_2025`
- Year: 2025
- Venue: Science Advances
- DOI: 10.1126/sciadv.adr8638
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: protein/peptide language model
- Design modality: sequence-conditioned generation
- Input: sequence or structure depending on method
- Output: designed peptide/miniprotein sequence or structure
- Availability: zotero metadata; runnable status not checked

## Evidence Note
Designing binders to target undruggable proteins presents a formidable challenge in drug discovery. In this work, we provide an algorithmic framework to design short, target-binding linear peptides, requiring only the amino acid sequence of the target protein. To do this, we propose a process to generate naturalistic peptide candidates through Gaussian perturbation of the peptidic latent space of the ESM-2 protein language model and subsequently screen these novel sequences for target-selective interaction activity via a contrastive language-image pretraining (CLIP)–based contrastive learning architecture. By integrating these generative and discriminative steps, we create a Peptide Prioritization via CLIP (PepPrCLIP) pipeline and validate highly ranked, target-specific peptides experimentally, both as inhibitory peptides and as fusions to E3 ubiquitin ligase domains. PepPrCLIP-derived c
