---
type: "reference_evidence_card"
version: "v8_fulltext_verified"
reference_number: 32
citation_key: "chen_target_2025"
paper_id: "2025-target-sequence-conditioned-design-of-peptide-binders-using-masked-langu-2880c6f0"
title: "Target sequence-conditioned design of peptide binders using masked language modeling"
doi: "10.1038/s41587-025-02761-2"
fulltext_md_path: "raw/fulltext_md/2025-target-sequence-conditioned-design-of-peptide-binders-using-masked-langu-2880c6f0.md"
pdf_path: "E:\Endnote参考文献\蛋白质分子设计.Data\PDF\3233058152\2025-Nature Biotechn-Target sequence-condition.pdf"
support_status: "fulltext_card_created"
---

# [32] Target sequence-conditioned design of peptide binders using masked language modeling

- citation_key: `chen_target_2025`
- paper_id: `2025-target-sequence-conditioned-design-of-peptide-binders-using-masked-langu-2880c6f0`
- DOI: `10.1038/s41587-025-02761-2`
- PDF exists: `true`
- Markdown exists: `true`
- Conversion quality: `medium`

## 研究任务

target sequence-conditioned de novo linear peptide binder design

## 输入

target protein sequence plus masked binder region

## 输出

linear peptide binder sequences and peptide-guided ubiquitin ligase fusions

## 模型/工具

PepMLM, ESM-2 fine-tuning with masked language modeling

## 实验验证

in silico benchmarks plus in vitro/cellular validation for selected target cases

## 结构证据

AlphaFold-Multimer co-folding and structural prediction; not primary experimental structure evidence

## 细胞/动物/PK 证据

cellular degradation/readout evidence; no animal efficacy claim used in v8

## 可复现性

code, data and model reported via GitHub/Hugging Face in full text

## 可引用结论

sequence-conditioned language modeling can generate peptide binders without requiring stable target 3D structures

## 不能外推的边界

does not prove animal efficacy, clinical translation, or universal target generalization

## 全文证据片段

- `raw/fulltext_md/2025-target-sequence-conditioned-design-of-peptide-binders-using-masked-langu-2880c6f0.md:51` The computational design of protein-based binders presents unique opportunities to access ‘undruggable’ targets, but effective binder design often relies on stable three-dimensional structures or structure-influenced latent spaces. Here we introduce PepMLM, a target sequence-conditioned designer of de novo linear peptide binders. Using a masking strategy that positions cognate peptide sequences at the C terminus of target protein sequences, PepMLM finetunes the ESM-2 protein language model to fully reconstruct the 
