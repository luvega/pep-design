# Method Sources

This directory records source-code routes for candidate methods. v0.3 did not clone third-party repositories, install methods, download weights, or vendor external code into this project.

`method_source_manifest.csv` is the authoritative table for future clone/install planning. Any later local source mirror should live outside the tracked KB or in a gitignored directory, with the exact path and commit recorded here before smoke tests run.

## v0.4 Source Pin Audit

`source_pin_audit_v0.4.csv` records external-only shallow clone pins for priority repositories. The clones live outside this repository under `E:\Codex_Projects\Pep_design_external\method_sources_v0.4`.

Source pinning means commit/license/README/environment route inspection only. It does not mean installed, runnable, reproduced, or benchmarked.

## v0.5 Source Pin Audit

`source_pin_audit_v0.5.csv` extends source pinning to all 10 include methods using GitHub API and `git ls-remote` metadata only. No third-party repository is cloned into this KB. `pinned_no_install` means the remote repository and commit are recorded; it does not mean dependency resolution, checkpoint access, batch inference, or local execution has been confirmed.
