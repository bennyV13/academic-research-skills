---
name: ars-citation-check
description: >-
  Use this skill to run deterministic citation integrity checks, identifying missing references, mismatched citations, and formatting errors.
---

# ARS Citation Integrity Check (ars-citation-check)

This workflow performs strict deterministic validation of in-text citations against the paper's bibliography and source database, catching hallucinations, orphaned references, and format discrepancies before submission.

## Procedures

1. **In-Text Citation Extraction**:
   - Scan manuscript prose for narrative and parenthetical citations across standard styles (APA 7th, Chicago, IEEE, MLA).
   - Identify all citation keys, author-date tokens, or numeric indices.

2. **Bibliography Reconciliation**:
   - Parse reference section / `.bib` file entries into structured reference records.
   - Verify bidirectional matching:
     - Detect **Orphaned Citations**: in-text citations lacking corresponding bibliography entries.
     - Detect **Unused References**: bibliography entries never cited in the manuscript text.

3. **Deterministic Source Validation**:
   - Cross-check citation keys against verified academic databases (Crossref, PubMed, arXiv).
   - Detect retracted papers, DOI mismatches, author name misspellings, and phantom dates.

4. **Deliverables**:
   - Produce a structured Citation Error Report categorizing errors by severity (`Critical`, `Major`, `Minor`), with concrete line references and proposed corrections.
