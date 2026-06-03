---
title: "ConPep: Prediction of peptide contact maps with pre-trained biological language model and multi-view feature extracting strategy"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:1ZQDNS3D"]
---

# ConPep: Prediction of peptide contact maps with pre-trained biological language model and multi-view feature extracting strategy

## Metadata
- Zotero item key: `1ZQDNS3D`
- BibTeX key: `wei_conpep_2023`
- Year: 2023
- Venue: Computers in Biology and Medicine
- DOI: 10.1016/j.compbiomed.2023.107631
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
The accurate prediction of peptide contact maps remains a challenging task due to the difficulty in obtaining the interactive information between residues on short sequences. To address this challenge, we propose ConPep, a deep learning framework designed for predicting the contact map of peptides based on sequences only. To sufficiently incorporate the sequential semantic information between residues in peptide sequences, we use a pre-trained biological language model and transfer prior knowledge from large scale databases. Additionally, to extract and integrate sequential local information and residue-based global correlations, our model incorporates Bidirectional Gated Recurrent Unit and attention mechanisms. They can obtain multi-view features and thus enhance the accuracy and robustness of our prediction. Comparative results on independent tests demonstrate that our proposed method
