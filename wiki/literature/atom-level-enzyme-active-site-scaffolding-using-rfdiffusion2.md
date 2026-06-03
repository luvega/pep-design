---
title: "Atom level enzyme active site scaffolding using RFdiffusion2"
type: literature_card
status: included
created: 2026-06-03
wiki_role: evidence_card
source_count: 1
last_reviewed: 2026-06-03
claims: ["metadata-level screening only; full-text claims require later extraction"]
relations: ["derived_from:zotero:ZYFCZKMH"]
---

# Atom level enzyme active site scaffolding using RFdiffusion2

## Metadata
- Zotero item key: `ZYFCZKMH`
- BibTeX key: `ahern_atom_2025`
- Year: 2025
- Venue: bioRxiv
- DOI: 10.1101/2025.04.09.648075
- PMID: 
- arXiv: 

## Screening
- Status: included
- Method family: generative full-atom or diffusion model
- Design modality: structure/sequence generative modeling
- Input: sequence or structure depending on method
- Output: designed peptide/miniprotein sequence or structure
- Availability: zotero metadata; runnable status not checked

## Evidence Note
De novo enzyme design starts from ideal active site descriptions consisting of constellations of catalytic residue functional groups around reaction transition state(s), and seeks to generate protein structures that can accurately hold the site in place. Highly active enzymes have been designed starting from such descriptions using the generative AI method RFdiffusion [1–3], but there are two current methodological limitations. First, the geometry of the active site can only be specified at the residue level, so for each catalytic residue functional group placed around the reaction transition state, the possible locations of the residue backbone must be enumerated by building side chain rotamers back from the functional group. Second, the location of the catalytic residues along the sequence must be specified in advance, which considerably limits the space of solutions which can be sampl
