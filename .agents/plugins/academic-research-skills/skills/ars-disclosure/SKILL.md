---
name: ars-disclosure
description: >-
  Use this skill to generate venue-compliant AI assistance disclosure statements and policy anchors.
---

# ARS AI Assistance Disclosure Generator (ars-disclosure)

This workflow evaluates AI tool assistance across the research and drafting lifecycle, mapping usage against target publication venue policies and generating formal, transparent disclosure statements.

## Procedures

1. **Venue Policy Target Selection**:
   - Identify target submission venue or journal family (e.g., ICLR, NeurIPS, Nature, Science, ACL, EMNLP, ICMJE, NEJM, The Lancet, JAMA, BMJ, PLOS, Frontiers).
   - Retrieve venue-specific policies regarding generative AI, assistive editing, coding assistance, and literature search.

2. **Assistance Ledger Verification**:
   - Audit AI involvement across research stages:
     - Conceptualization & brainstorming
     - Literature discovery & reference querying
     - Code development & statistical scripts
     - Copy-editing & language refinement
     - Synthesis or drafting assistance
   - Flag any disallowed generative contributions per target venue guidelines.

3. **Disclosure Synthesis & Classification**:
   - Determine disclosure applicability status (`REQUIRED`, `ACTION_ONLY`, `NOT_REQUIRED`, `UNKNOWN`).
   - Format transparency statements matching venue requirements (e.g., dedicated "AI Use Statement" section, acknowledgments, or methodology disclosures).

4. **Deliverable**:
   - Emit publication-ready AI disclosure text and structured compliance metadata.
