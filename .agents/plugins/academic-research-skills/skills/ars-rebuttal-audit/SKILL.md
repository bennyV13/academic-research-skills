---
name: ars-rebuttal-audit
description: >-
  Use this skill to perform item-by-item QA audits on existing rebuttal and
  response drafts against reviewer critiques, verifying coverage and flagging unaddressed points.
---

# ARS Rebuttal Audit Workflow (ars-rebuttal-audit)

This workflow conducts a rigorous quality assurance audit of an author's drafted response letter against the original reviewer reports to identify coverage gaps, evasive arguments, tone risks, or unsubstantiated claims before submission.

## Procedures

1. **Bilateral Intake**:
   - Ingest the set of reviewer comments (from all reviewer seats and the editor).
   - Ingest the author's prepared response-to-reviewers draft.

2. **Item-by-Item Alignment Verification**:
   - Verify that every parsed reviewer critique $C_i$ has a corresponding, numbered response $R_i$.
   - Flag any missing, orphaned, or conflated points as `[UNADDRESSED_CRITIQUE]`.

3. **Substantive Adequacy & Evidence Check**:
   - Check whether responses provide direct, evidence-based answers rather than vague promises.
   - Verify that specific line numbers, sections, or table references are cited in the response.
   - Flag hand-waving or unsubstantiated claims as `[SUBSTANTIVE_GAP]`.

4. **Tone & Register Review**:
   - Screen author responses for defensive, confrontational, or dismissive phrasing.
   - Suggest constructive, collegial, and evidence-grounded alternative formulations.

5. **Deliverable**:
   - Produce a structured Rebuttal QA Audit Report with coverage percentage, gap inventory, and concrete remediation recommendations.
