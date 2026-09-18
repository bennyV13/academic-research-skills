---
name: ars-abstract
description: >-
  Use this skill to generate pair-dependent bilingual academic abstracts and
  structured keyword sets from completed manuscripts or section drafts.
---

# ARS Abstract & Keywords Generator (ars-abstract)

This workflow produces publication-grade bilingual or single-language abstracts with structured keyword lists aligned to journal length regimes and formatting guidelines.

## Procedures

1. **Manuscript Ingestion**:
   Analyze the completed paper draft, extracting core background, research gap, methods, primary empirical findings, and theoretical/practical contributions.

2. **Language Pair Resolution**:
   Identify the target language pair from `output_language_pair` (defaults to `zh-tw-en`: Traditional Chinese + English).

3. **Independent Dual Composition**:
   - Compose the Primary Language Abstract (e.g. Traditional Chinese) adhering to standard academic syntax.
   - Independently compose the Secondary Language Abstract (e.g. English) ensuring structural parallelism without mechanical machine translation artifacts.

4. **Regime Word Budget & Keywords**:
   - Enforce word limits per venue regime (typically 150–250 words English / 300–500 characters Chinese).
   - Select 4–6 high-impact discipline keywords reflecting core indexing terms.

5. **Pattern Protection Verification**:
   Verify preservation of budget-protected hedging phrases and ensure explicit temporal bounds.

6. **Deliverables**:
   Produce `phase5b_abstract/bilingual_abstract.md`.
