---
title: "Peptide binder design with inverse folding and protein structure prediction"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:BEJRRDMV"]
---

# Peptide binder design with inverse folding and protein structure prediction

## Metadata
- Zotero item key: `BEJRRDMV`
- BibTeX key: `bryant_peptide_2023`
- Year: 2023
- Venue: Communications Chemistry
- DOI: 10.1038/s42004-023-01029-7
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: miniprotein/protein binder design
- Design modality: structure or sequence conditioned binder design
- Input: sequence or structure depending on method
- Output: designed peptide/miniprotein sequence or structure
- Availability: zotero metadata; runnable status not checked

## Evidence Note
The computational design of peptide binders towards a specific protein interface can aid diagnostic and therapeutic efforts. Here, we design peptide binders by combining the known structural space searched with Foldseek, the protein design method ESM-IF1, and AlphaFold2 (AF) in a joint framework. Foldseek generates backbone seeds for a modified version of ESM-IF1 adapted to protein complexes. The resulting sequences are evaluated with AF using an MSA representation for the receptor structure and a single sequence for the binder. We show that AF can accurately evaluate protein binders and that our bind score can select these (ROC AUC = 0.96 for the heterodimeric case). We find that designs created from seeds with more contacts per residue are more successful and tend to be short. There is a relationship between the sequence recovery in interface positions and the plDDT of the designs, whe
