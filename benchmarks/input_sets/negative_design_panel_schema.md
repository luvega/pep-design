# Negative Design Panel Schema

Negative and off-target panels are planned controls for peptide binder, pMHC/TCR-like and degrader/interface tasks. They are not specificity evidence until methods are run and scored.

## Required Columns

`off_target_id,similarity_to_target,expected_nonbinder_reason,healthy_tissue_or_related_protein_flag,scoring_result,status`

## Additional pMHC/TCR-like Fields

For pMHC/TCR-like recognition tasks, append:

`hla_allele,peptide_antigen,near_neighbour_peptide_panel,cross_reactivity_risk`

## Status Values

- `planned`
- `to_be_generated`
- `scored`
- `not_applicable`
- `deferred`

## Claim Boundary

Negative design panels can support specificity assessment only after target/control provenance, sequence similarity, assay context and scoring outputs are documented. Before that point, manuscript language should use `planned negative-design panel` or `to be evaluated`.
