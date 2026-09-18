---
name: ars-revision-coach
description: >-
  Use this skill to parse unstructured reviewer comments into a structured,
  source-accounted revision roadmap and response letter skeleton.
---

# ARS Revision Coach Workflow (ars-revision-coach)

This workflow bridges raw, unstructured reviewer feedback into an actionable, priority-ordered revision strategy and drafting skeleton for authors.

## Procedures

1. **Unstructured Reviewer Ingestion**:
   - Ingest reviewer feedback from any text format (emails, PDF extracts, freeform lists, editorial letters).
   - Normalize and segment individual comments by reviewer source (`Reviewer 1`, `Reviewer 2`, `Reviewer 3`, `Editor`).

2. **Classification & Categorization**:
   - Tag each comment by severity (`Major`, `Minor`, `Editorial`, `Positive`).
   - Identify thematic clusters (Methodology, Literature/Related Work, Empirical Evaluation, Framing/Exposition).

3. **Revision Roadmap Construction**:
   - Generate an immutable, source-ordered Revision Roadmap core.
   - Specify required remediation actions, estimated effort/cost, and potential trade-offs for each item.

4. **Response Skeleton Generation**:
   - Build a point-by-point response template quoting each comment verbatim with designated placeholders for author actions and section anchors.
