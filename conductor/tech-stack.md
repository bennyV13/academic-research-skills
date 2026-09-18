# Technology Stack

## Core Execution & Scripting
- **Python (3.10+):** Primary language for integrity verification scripts, citation validation, data access level enforcement, and automated tests.
  - **Testing Framework:** `pytest` configured via `pyproject.toml`.
  - **Key Libraries:** `ruamel.yaml` (YAML preservation), `jsonschema` (schema validation), `pypdf` (PDF verification), `defusedxml` (safe XML parsing), `markdown-it-py` / `linkify-it-py` (Markdown AST analysis and link extraction).
- **Node.js / JavaScript:** Runtime for Pi adapter (`pi/wrapper.js`) and cross-platform extensions.

## Agent Orchestration & Packaging
- **Claude Code CLI:** Native plugin manifest and slash commands (`/ars-plan`, `/ars-lit-review`, etc.).
- **Pi Adapter:** In-tree wrapper (`pi/`) maintaining compatibility with Pi CLI.
- **Antigravity (`agy` CLI):** Adaptation layer for Antigravity skill invocation, subagents, and tools.

## Document Compilation & Tooling
- **Markdown & Frontmatter:** Native format for all prompt templates, guidelines, and generated academic chapters.
- **Tectonic / XeLaTeX (Optional):** Automated PDF compilation with APA 7.0 typesetting and multi-language support.
- **Pandoc (Optional):** Conversion between Markdown, DOCX, and other academic manuscript formats.

## External Services & APIs
- **Bibliographic Resolvers:** Semantic Scholar API, Crossref, arXiv, and PubMed for citation anchor verification and DOI resolution.
- **Data Persistence:** File-system based artifacts with structured Material Passports and reproducibility locks.
