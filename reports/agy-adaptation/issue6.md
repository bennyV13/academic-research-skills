# Adversarial Audit Report: Gate #6 (Academic Paper Authoring & Report Compiler Subagent)

## Executive Summary

- **Target Ticket**: Issue #5 (03 — Academic Paper Authoring & Report Compiler Subagent)
- **Target Gate**: Issue #6 (Verify: 03 — Academic Paper Authoring & Report Compiler Subagent)
- **Overall Verdict**: `DEFECTS_FOUND`
- **Severity Count**:
  - **HIGH**: 2
  - **MEDIUM**: 3
  - **LOW**: 1
  - **Total Findings**: 6

An adversarial audit of Ticket 03 on `bennyV13/academic-research-skills` was conducted across all newly added assets (`academic-paper/`, `report-compiler-agent.md`, `ars-plan`, `ars-outline`, `ars-abstract`, `ars-format-convert`, `subagents.py`, and test suites). While initial compatibility checks passed, adversarial probing identified broken relative markdown links pointing across plugin boundaries, APA 7.0 specification violations in heading structures, unhandled edge cases in subagent loading, and test coverage gaps.

---

## Audit Vectors & Status

| Vector ID | Target Area | Description | Status |
|-----------|-------------|-------------|--------|
| **V1** | Shell Formatting | Probed 55 markdown files and 245 code blocks for multi-line bash, backslash continuations, and untagged commands. | `PASS` (0 violations) |
| **V2** | Cross-Reference Integrity | Probed relative markdown links across `skills/academic-paper/` and supporting guides. | `FAIL` (6 broken links to `../shared`) |
| **V3** | APA 7.0 Specification | Checked report compiler prompt against official APA 7th edition formatting rules. | `FAIL` (Numbered headings in APA template) |
| **V4** | Subagent Security & Edge Cases | Tested directory traversal, directory inputs (`.`), and dynamic metadata parsing in `subagents.py`. | `FAIL` (Unhandled `IsADirectoryError`) |
| **V5** | Capability Manifesting | Verified tool enablement flags in `subagents.py` vs agent frontmatter. | `WARN` (Static capability assignment) |
| **V6** | Integration Test Rigor | Checked whether tests verify filesystem writing, error conditions, and APA standards. | `FAIL` (Coverage gaps on edge cases and disk writes) |

---

## Detailed Findings

### Finding 1 [HIGH] — Broken Relative Links to `shared/` Documentation
- **Location**:
  - `.agents/plugins/academic-research-skills/skills/academic-paper/SKILL.md` (lines 24, 504)
  - `skills/academic-paper/references/anti_leakage_protocol.md`
  - `skills/academic-paper/references/abstract_writing_guide.md`
  - `skills/academic-paper/templates/bilingual_abstract_template.md`
- **Description**: Relative links point to `../shared/output_language_pair.md`, `../../shared/compliance_checkpoint_protocol.md`, and `../../shared/references/word_count_conventions.md`. In the adapted plugin structure, these resolve to `.agents/plugins/academic-research-skills/skills/shared/`, which does not exist.
- **Remediation**: Update relative links to point to the repository root `../../../../shared/...` or resolve them to internal references. Fix `references/intent_clarification_protocol.md` in `SKILL.md` to point to `../../../../shared/references/intent_clarification_protocol.md`.

### Finding 2 [HIGH] — APA 7.0 Numbered Headings Violation in `report-compiler-agent.md`
- **Location**: `.agents/plugins/academic-research-skills/agents/report-compiler-agent.md` (lines 93–120)
- **Description**: The full report structure template in `report-compiler-agent.md` specifies numbered headings (e.g. `## 1. Introduction`, `## 2. Literature Review`, `## 3. Methodology`). The APA 7th edition manual explicitly prohibits numbering section headings. Furthermore, in APA 7.0, the manuscript title acts as the de facto Level 1 heading, and the opening section does not carry an explicit "Introduction" heading.
- **Remediation**: Remove numbered prefixes from the report structure template and document APA 7th edition unnumbered heading rules accurately.

### Finding 3 [MEDIUM] — Unhandled Directory Input in `subagents.load_agent_spec`
- **Location**: `.agents/plugins/academic-research-skills/scripts/subagents.py` (lines 17–23)
- **Description**: When `load_agent_spec` is provided with `.` or a subfolder name, `target_path.exists()` returns `True`, but `target_path.read_text()` subsequently crashes with an unhandled `IsADirectoryError`.
- **Remediation**: Add `if not target_path.is_file(): raise FileNotFoundError(...)` to ensure directories cannot be read as agent specs.

### Finding 4 [MEDIUM] — Hardcoded Tool Capabilities in `get_report_compiler_subagent_def`
- **Location**: `.agents/plugins/academic-research-skills/scripts/subagents.py` (lines 83–86)
- **Description**: The function hardcodes `enable_write_tools=True`, `enable_subagent_tools=False`, and `enable_mcp_tools=False` rather than extracting the values declared in the agent's frontmatter metadata.
- **Remediation**: Dynamically parse `enable_write_tools`, `enable_subagent_tools`, and `enable_mcp_tools` from `meta` with appropriate boolean defaults.

### Finding 5 [MEDIUM] — Integration Test Lacks End-to-End File Generation & Edge-Case Probing
- **Location**: `scripts/test_academic_paper_authoring_integration.py`
- **Description**: The integration test verifies in-memory strings but does not test `subagents.load_agent_spec` directory rejection, capability parsing, or actual artifact emission to the workspace filesystem.
- **Remediation**: Add unit tests for `load_agent_spec` edge cases (`.` directory error handling), dynamic capability parsing, and a test writing and verifying a compiled section artifact.

### Finding 6 [LOW] — Broken Template Relative References to `references/`
- **Location**: `skills/academic-paper/templates/bilingual_abstract_template.md`, `credit_statement_template.md`, `funding_statement_template.md`
- **Description**: Templates reference `references/abstract_writing_guide.md` instead of `../references/abstract_writing_guide.md`.
- **Remediation**: Update template relative links to `../references/`.

---

## Remediation Plan

1. Remediate broken relative paths in `SKILL.md`, `references/`, and `templates/`.
2. Update `report-compiler-agent.md` to remove numbered headings and enforce strictly compliant APA 7.0 structure.
3. Patch `subagents.py` to check `target_path.is_file()` and dynamically parse frontmatter capabilities.
4. Expand `scripts/test_academic_paper_authoring_integration.py` with tests for directory error handling, capability extraction, and disk artifact drafting.
5. Re-run compatibility verification and full test suite to confirm green state.
