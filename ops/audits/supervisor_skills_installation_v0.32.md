# Supervisor-Skills Installation Audit v0.32

Date: 2026-07-09

## Scope

This audit records installation of selected Supervisor-Skills for the
Pep_design Benchmark manuscript workflow. It updates project memory only. It is
not Benchmark result, not scoring evidence, and not method-ranking evidence.

## Source

- Repository: `HKUSTDial/Supervisor-Skills`
- URL: `https://github.com/HKUSTDial/Supervisor-Skills`
- Source path: `plugins/phd-research/skills/`
- Installed source commit: `0b77a1b98794f8341d57685a0e829a3fa175d05f`
- License boundary: `CC BY-NC-SA 4.0`

The repository describes Supervisor-Skills as a Guide plus Skills system for
research idea evaluation, paper writing, figure design and pre-submission
review. The selected skills are installed for academic, non-commercial project
support with attribution and boundary tracking.

## Installed Skills

| skill | local path | project use |
|:---|:---|:---|
| `benchmark-paper-template` | `/home/a/.codex/skills/benchmark-paper-template` | Primary Benchmark manuscript structure, five-pillar audit, section skeleton and checklist |
| `intro-drafter` | `/home/a/.codex/skills/intro-drafter` | Consistency-check only after Benchmark structure is fixed |
| `figure-designer` | `/home/a/.codex/skills/figure-designer` | Manuscript figure planning and figure-quality audit |
| `pre-submission-reviewer` | `/home/a/.codex/skills/pre-submission-reviewer` | Near-submission macro/writing/grammar/LaTeX/figure review |
| `idea-evaluator` | `/home/a/.codex/skills/idea-evaluator` | Scope and idea-level reassessment before changing the manuscript thesis |

## Commands

```bash
git ls-remote https://github.com/HKUSTDial/Supervisor-Skills refs/heads/main
python /home/a/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo HKUSTDial/Supervisor-Skills --ref main --path plugins/phd-research/skills/idea-evaluator
python /home/a/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo HKUSTDial/Supervisor-Skills --ref main --path plugins/phd-research/skills/benchmark-paper-template
python /home/a/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo HKUSTDial/Supervisor-Skills --ref main --path plugins/phd-research/skills/intro-drafter
python /home/a/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo HKUSTDial/Supervisor-Skills --ref main --path plugins/phd-research/skills/figure-designer
python /home/a/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo HKUSTDial/Supervisor-Skills --ref main --path plugins/phd-research/skills/pre-submission-reviewer
```

The multi-path install attempt installed only `idea-evaluator`, so the remaining
skills were installed one at a time.

## Project Memory Updates

- `AGENTS.md` now routes Benchmark manuscript work to Supervisor-Skills
  `benchmark-paper-template` as the primary route.
- `AGENTS.md` records that `intro-drafter` is consistency-check only.
- `ops/audits/skill_selection.md` records the source, commit, installed skills,
  license and no-overclaim boundary.

## Boundary

Supervisor-Skills improves manuscript planning and review discipline. It does
not convert v0.31 bounded pilot parser rows into complete Benchmark results. It
does not support scoring, method ranking, wet-lab validation, `smoke_test_ready`
or `benchmark_ready`.

Restart Codex to pick up new skills.
