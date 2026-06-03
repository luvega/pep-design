---
title: "Peptide-binding specificity prediction using fine-tuned protein structure prediction networks"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:RKD929FM"]
---

# Peptide-binding specificity prediction using fine-tuned protein structure prediction networks

## Metadata
- Zotero item key: `RKD929FM`
- BibTeX key: `motmaen_peptide-binding_2023`
- Year: 2023
- Venue: Proceedings of the National Academy of Sciences
- DOI: 10.1073/pnas.2216697120
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
Peptide-binding proteins play key roles in biology, and predicting their binding specificity is a long-standing challenge. While considerable protein structural information is available, the most successful current methods use sequence information alone, in part because it has been a challenge to model the subtle structural changes accompanying sequence substitutions. Protein structure prediction networks such as AlphaFold model sequence-structure relationships very accurately, and we reasoned that if it were possible to specifically train such networks on binding data, more generalizable models could be created. We show that placing a classifier on top of the AlphaFold network and fine-tuning the combined network parameters for both classification and structure prediction accuracy leads to a model with strong generalizable performance on a wide range of Class I and Class II peptide-MHC
