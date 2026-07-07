# Environments

This directory records environment feasibility and assignment only. It does not
store conda environments, install packages, request licenses, download weights,
or test GPU execution.

`environment_feasibility_matrix.csv` is used to schedule v0.4 clone/install/smoke-test work and to keep license-heavy methods separate from lightweight checks.

v0.13 adds Docker image/environment assignment in
`benchmark/deployment/method_environment_assignment_v0.13.csv`. The shared
`pd-benchmark-methods-gpu:0.13` route is a multi-conda Dockerfile scaffold in
the external `/mnt/ssd4t/protein-design` workbench, not a tracked environment
or local reproducibility claim.
