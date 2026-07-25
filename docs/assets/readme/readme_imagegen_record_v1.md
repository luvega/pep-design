# README Imagegen Record v1

## Scope

The built-in `$imagegen` tool generated two README communication assets on
2026-07-25. These files support navigation and protocol explanation. They are
not Benchmark results, runnability evidence, scoring evidence, method-ranking
evidence, or biological validation.

## Generated assets

| asset | built-in generated source | project output | mode |
|:---|:---|:---|:---|
| project icon | `/home/a/.codex/generated_images/019f9454-fdfa-72b0-944e-9446f6744fee/call_uQmBM2pSQhxhpTNLPci5chJK.png` | `docs/assets/readme/pep_design_icon_v1.png` | built-in generation plus local chroma-key removal |
| homepage workflow | `/home/a/.codex/generated_images/019f9454-fdfa-72b0-944e-9446f6744fee/call_gwPD7KIAnW0VXdiK2BeZMv9J.png` | `docs/assets/readme/pep_design_homepage_workflow_v1.png` | built-in generation |

## Final prompts

### Project icon

```text
Use case: logo-brand
Asset type: GitHub README project icon
Primary request: Create an original minimal scientific logo mark for a protocol-first peptide-design benchmark. Show one abstract peptide chain as a sequence of connected rounded molecular nodes weaving cleanly through three parallel benchmark lanes that represent T1, T2, and T3 task classes. The mark should suggest method taxonomy, standardized comparison, and evidence gates without resembling a medical product logo.
Style/medium: vector-like flat raster logo; precise geometric construction; strong silhouette; minimal; publication-grade scientific identity
Composition/framing: single centered square mark with generous padding; no border; visually balanced at small sizes
Color palette: deep navy #0B1F3A, scientific blue #1769AA, teal #128C8C, restrained green #2E8B57, one small orange #E58A2B evidence-gate accent
Scene/backdrop: perfectly flat solid #FF00FF chroma-key background for local background removal
Constraints: no text, no letters, no numbers, no gradients, no mockup, no 3D, no shadows, no reflections, no watermark; the background must be one perfectly uniform #FF00FF color with no texture or lighting variation; do not use #FF00FF anywhere in the logo; crisp closed edges and generous separation from the background; keep the symbol simple enough to remain legible at 96 pixels
```

### Homepage workflow

```text
Use case: scientific-educational
Asset type: GitHub README homepage workflow infographic
Primary request: Create a clean landscape scientific workflow for a protocol-first peptide-design benchmark knowledge base. The visual must show a left-to-right evidence pipeline with a central three-lane task taxonomy.
Scene/backdrop: white background with generous whitespace
Style/medium: publication-grade vector-like scientific infographic; crisp flat icons; restrained academic design; consistent line weights and rounded rectangular modules
Composition/framing: wide 16:9 landscape; five main stages connected by clear single-direction arrows. Stage 1 is literature papers plus pinned source repositories. Stage 2 is a three-lane taxonomy: T1 sequence binder, T2 structure peptide, T3 miniprotein baseline. Stage 3 is standardized input records and method adapters. Stage 4 is bounded generation followed by parser and QC. Stage 5 splits into current readiness evidence and future scoring/ranking, ending at a visible claim gate. Show generation and ranking as separate evidence layers. Use an orange warning marker beside the current open Critical gate, without naming a method.
Text (verbatim, short labels only): "SOURCES", "T1 SEQUENCE", "T2 STRUCTURE", "T3 MINIPROTEIN", "STANDARD INPUT", "ADAPTER", "GENERATION", "PARSER + QC", "READINESS", "SCORING", "CLAIM GATE", "CURRENT", "FUTURE"
Color palette: deep navy #0B1F3A for structure, scientific blue #1769AA for T1 and generation, teal #128C8C for T2, restrained green #2E8B57 for T3 and readiness, muted violet #6B5FB5 for metric modules, orange #E58A2B for warning/open gate, light gray dividers
Constraints: render every requested label exactly once and no other words; no numerical results, no leaderboard, no method ranking, no performance claims, no biological validation iconography, no logos, no trademarks, no watermark; avoid tiny text, dense paragraphs, gradients, decorative molecules, or photorealism; keep arrows unambiguous and all modules fully inside the canvas
```

## Post-processing

The icon used a flat magenta background because its subject contains blue,
teal, and green. The installed imagegen helper removed the key locally:

```bash
python /home/a/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py \
  --input tmp/imagegen/pep_design_icon_chroma_v1.png \
  --out docs/assets/readme/pep_design_icon_v1.png \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

## Quality control

- Icon: `1254 × 1254`, RGBA, transparent corners, alpha range `0–255`.
- Workflow: `1672 × 941`, RGB, aspect ratio `1.78`.
- All requested workflow labels are present and legible.
- Arrows run from sources to the claim gate without ambiguous reversals.
- The workflow separates current readiness evidence from future scoring.
- Neither asset reports scores, rankings, biological success, or completed
  Benchmark status.
