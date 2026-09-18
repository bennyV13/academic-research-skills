---
name: ars-reviewer
description: >-
  Use this skill to run simulated peer-review panel workflows on academic paper
  drafts, scoring criteria across dimensions and flagging soundness and empirical gaps.
---

# ARS Peer Review Panel Workflow (ars-reviewer)

This workflow coordinates a multi-perspective simulated peer review panel to rigorously critique academic manuscripts before submission, identifying weaknesses, checking methodology rigor, and generating an actionable editorial verdict.

## Procedures

1. **Intake & Paper Profiling**:
   - Inspect the manuscript draft (title, abstract, main text, tables, references).
   - Identify discipline, methodology paradigm, empirical claims, and venue expectations.

2. **Multi-Perspective Reviewer Evaluation**:
   - Deploy reviewer perspectives (Journal Fit, Methodology, Domain/Literature, Cross-Disciplinary, Devil's Advocate).
   - Evaluate against the five core dimensions:
     - **Originality**: Defensibility of contribution relative to prior art.
     - **Methodological Rigor**: Validity of experimental design, statistical treatments, controls, and reproducibility.
     - **Evidence Sufficiency**: Empirical grounding, sample sizes, and identification of material empirical gaps.
     - **Argument Coherence**: Logical flow from hypotheses to conclusions.
     - **Writing Quality**: Clarity, academic register, and presentation.

3. **Gap & Defect Classification**:
   - Classify all issues into `Critical` (fatal block), `Major` (rework required), `Minor` (clarifications), and `Editorial`.
   - Anchor each finding with specific manuscript locations and concrete remedies.

4. **Editorial Synthesis & Decision**:
   - Aggregate reviewer findings, isolate consensus versus dissenting opinions, and arbitrate conflicts.
   - Issue an explicit Editorial Verdict (`Accept`, `Minor Revision`, `Major Revision`, `Reject`).
   - Emit an immutable, source-ordered Revision Roadmap core accounting for all reviewer concerns.
