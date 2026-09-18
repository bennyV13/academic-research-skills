---
name: ars-full
description: >-
  Use this skill to execute the end-to-end academic research, authoring, and review pipeline.
  Coordinates deep research, paper drafting, integrity auditing, and peer review.
---

# ARS Full Pipeline Workflow (ars-full)

This workflow triggers the end-to-end academic pipeline orchestrator (`academic-pipeline`), driving a research project across all 10 stages from initial inquiry to final publication-ready artifacts.

## Procedures

1. **Stage 1: Scope & Research Framing**:
   - Formulate and refine the central research question.
   - Invoke `research-architect-agent` to design the methodology blueprint (paradigm, methods, data strategy, and validity controls).

2. **Stage 2: Systematic Literature Investigation**:
   - Search scholarly databases, extract evidence, and verify citations.
   - Assemble the comprehensive Annotated Bibliography.

3. **Stage 3: Evidence Synthesis & Gap Mapping**:
   - Invoke `synthesis-agent` to integrate findings across sources, resolve contradictions, and identify research frontiers.

4. **Stage 4: Manuscript Authoring & Compilation**:
   - Invoke `report-compiler-agent` to generate structured APA 7.0 sections from verified evidence.

5. **Stage 5: Integrity Verification Gate**:
   - Run deterministic claim verification protocols, citation checks, and statistical consistency checks.

6. **Stage 6: Multi-Perspective Peer Review Panel**:
   - Run simulated double-blind review across 5 dimensions and compile an editorial decision package with `editorial-synthesizer-agent`.

7. **Stage 7–8: Guided Revision & Re-Review**:
   - Address reviewer critiques using `revision-coach-agent` and verify fixes with verification reviews.

8. **Stage 9–10: Final Quality Assurance & Packaging**:
   - Perform final citation integrity validation, generate AI disclosure statements, and compile final publication packages (Markdown, LaTeX, DOCX, or PDF).
