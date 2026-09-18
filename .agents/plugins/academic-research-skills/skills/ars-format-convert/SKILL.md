---
name: ars-format-convert
description: >-
  Use this skill to convert academic papers between Markdown, LaTeX, DOCX, and PDF,
  and transpile citation styles across APA, Chicago, IEEE, and MLA formats.
---

# ARS Format Conversion Workflow (ars-format-convert)

This workflow converts completed academic manuscripts between document formats (Markdown, LaTeX, DOCX, PDF) and transforms bibliographic citations across standard styles.

## Procedures

1. **Input Analysis & Style Mapping**:
   Parse source manuscript markdown, identifying title metadata, heading hierarchies, tables, figures, footnotes, and citation markers (`<!--ref:slug-->`).

2. **Target Format Generation**:
   - **LaTeX**: Generate `.tex` document with structured preamble (`amsmath`, `hyperref`, `graphicx`) and clean `.bib` BibTeX entries.
   - **DOCX / PDF**: Utilize Pandoc with CSL citation formatting and reference templates.
   - **Markdown**: Normalize headings and format reference lists with hanging indents.

3. **Single-Line Pandoc CLI Conversion Commands**:

   - **Convert Markdown to DOCX with APA CSL**:
   ```bash
   pandoc paper.md -o output/paper.docx --bibliography=references.bib --csl=apa.csl
   ```

   - **Convert Markdown to LaTeX**:
   ```bash
   pandoc paper.md -o output/paper.tex --bibliography=references.bib --csl=apa.csl
   ```

   - **Convert Markdown to PDF via XeLaTeX**:
   ```bash
   pandoc paper.md -o output/paper.pdf --pdf-engine=xelatex --bibliography=references.bib --csl=apa.csl -V geometry:margin=1in
   ```

4. **Output Verification**:
   Ensure all tables, math equations, and citations convert cleanly without unrendered syntax artifacts.
