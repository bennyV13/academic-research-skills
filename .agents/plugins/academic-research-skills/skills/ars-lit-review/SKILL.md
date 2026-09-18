---
name: ars-lit-review
description: >-
  Use this skill to run an academic literature review workflow. Produces an
  annotated bibliography and evidence synthesis report across scholarly sources.
---

# ARS Literature Review Workflow

This workflow executes an academic literature review by coordinating systematic paper searches, source verification, and multi-source synthesis.

## Procedures

1. **Intake & Scope Definition**:
   Define the target research topic, core concepts, inclusion/exclusion criteria, and discipline conventions.

2. **Literature Retrieval & Verification**:
   Search scholarly databases (Crossref, OpenAlex, Semantic Scholar, arXiv). Verify metadata, DOI/arXiv links, and retraction status.

3. **Evidence Synthesis**:
   Invoke the `synthesis-agent` subagent to cross-analyze findings, resolve evidence conflicts, and map thematic convergence and knowledge gaps.

4. **Deliverables**:
   - Annotated Bibliography (`phase2_investigation/annotated_bibliography.md`)
   - Evidence Synthesis Report (`phase3_analysis/synthesis_report.md`)
