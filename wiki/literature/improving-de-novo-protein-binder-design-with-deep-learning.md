---
title: "Improving de novo protein binder design with deep learning"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:3AYIMQW5"]
---

# Improving de novo protein binder design with deep learning

## Metadata
- Zotero item key: `3AYIMQW5`
- BibTeX key: `bennett_improving_2023`
- Year: 2023
- Venue: Nature Communications
- DOI: 10.1038/s41467-023-38328-5
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: diffusion scaffold generation plus inverse folding sequence design
- Design modality: protein/miniprotein binder backbone generation and sequence assignment
- Input: target structure, hotspot or motif constraints, design length
- Output: miniprotein/protein binder backbones and sequences
- Availability: public GitHub repositories to verify

## Evidence Note
Recently it has become possible to de novo design high affinity protein binding proteins from target structural information alone. There is, however, considerable room for improvement as the overall design success rate is low. Here, we explore the augmentation of energy-based protein binder design using deep learning. We find that using AlphaFold2 or RoseTTAFold to assess the probability that a designed sequence adopts the designed monomer structure, and the probability that this structure binds the target as designed, increases design success rates nearly 10-fold. We find further that sequence design using ProteinMPNN rather than Rosetta considerably increases computational efficiency.
