# License, Schema And Input-Contract Review v0.8

## Summary

本轮将数据源和方法从“可记录/已 pin”推进到 **license/schema/input-contract 可审计**。审计仍保持 no-download/no-clone/no-install/no-run 边界：只读取公开 API、HEAD/metadata、已有本地外部 shallow clone 和项目内 artifact，不把任何数据、权重或第三方源码写入本仓库。

## Data-Source Gate Results

| source | v0.8 gate result | reason |
|:---|:---|:---|
| Overath binder-success dataset | calibration schema auditable | Zenodo API 确认 `cc-by-4.0`、6 个文件、`final_dataset.csv` size 和 md5；仍需下载后清洗 row-count discrepancy 与 blank target rows。 |
| PEPBI Dryad | metadata/license auditable, schema pending | Dryad API 确认 CC0-1.0 和 version 4，但顶层 API 未暴露文件列表；仍需确认文件 endpoint/UI route 与 thermodynamic label columns。 |
| PepBenchmark / PepBenchData | partial schema auditable, license pending | Hugging Face dataset API 不 gated，暴露 PpI 子集的 `label.csv`、`fasta.csv`、`pep_smiles.csv`、`pep_helm.csv` 与 cold split files；API cardData 未声明 license。 |
| GPCR peptide benchmark | paper metadata auditable, data route pending | bioRxiv API 确认 `cc_by` license、2026-03-02 v1、124 GPCR-peptide complexes 的 abstract-level benchmark 信息；外部 target/control table 和 data route 未确认。 |
| TCRTransBench | background metadata auditable | arXiv 页面确认 TCR2PEP/PEP2TCR、validated TCR-peptide pairs 和 biological-plausibility metrics；未找到官方 code/data route，不能作为 generic binder target source。 |
| Chang AF2 ranking cases | calibration concept auditable, extraction pending | Sciety/DOI metadata 支持 six receptor / multiple peptide affinity cases 和 medium-to-strong binder applicability；仍需抽取 article supplement tables。 |

No row is promoted to `target_set_v0.csv`. All remain candidate, calibration, property/developability or background sources.

## Method Gate Results

| method | v0.8 gate result | reason |
|:---|:---|:---|
| PepMLM | model license and input contract auditable | Hugging Face model API reports `license=mit`, snapshot SHA and non-gated access, but model-card extra use fields require a human decision; repo license file remains absent in local clone. |
| RFdiffusion | source license and checkpoint route auditable | Local `LICENSE` is BSD and states code plus README-referenced weights are covered; README lists checkpoint URLs and SE3nv environment with Python 3.9 / PyTorch 1.9 / CUDA 11.1. Sizes/checksums and contig/hotspot contract remain pending. |
| ProteinMPNN | source license and second-stage input flags auditable | Local `LICENSE` is MIT; README maps `protein_mpnn_run.py`, `--pdb_path`, `--out_folder`, model weights folders and PyTorch/CUDA example. RFdiffusion-to-ProteinMPNN handoff remains unvalidated. |
| PepMirror | checkpoint manifest auditable but dependency-blocked | Repo license is MIT; Zenodo checkpoint record is CC-BY-4.0 with 8 checkpoint files and md5 hashes; environment uses Python 3.9 / PyTorch 1.13.1 / CUDA 11.7. PyRosetta license/install route blocks promotion beyond `source_pinned`. |

## New Artifacts

- `benchmarks/input_sets/dataset_supplement_schema_review_v0.8.csv`
- `benchmarks/deployment/method_readiness_review_v0.8.csv`
- `benchmarks/deployment/download_manifest_v0.8.csv`

## Claim Boundary

- `download_manifest_v0.8.csv` is a future server manifest. It records URLs, expected sizes/checksum status where known, and target server paths; it does not record downloads.
- `method_readiness_review_v0.8.csv` is not installation evidence.
- `dataset_supplement_schema_review_v0.8.csv` is not target-set promotion evidence.
- No current artifact supports method ranking, local reproducibility, or completed benchmark wording.

## Next Actions

1. Resolve PepMLM model-card terms and repo entrypoint before server clone/model download.
2. HEAD selected RFdiffusion checkpoint URLs and define one minimal contig/hotspot contract.
3. Map ProteinMPNN fixed-chain settings for RFdiffusion outputs.
4. Confirm PyRosetta institutional license before promoting PepMirror to input-contract work.
5. Use approved server download only for Overath `final_dataset.csv`, then write a cleaning log before any calibration use.
