# Adversarial Audit Report: Gate #8 (Peer Reviewer Panel & Rebuttal Engine)

## Executive Summary

- **Target Ticket**: Issue #7 (04 — Peer Reviewer Panel & Rebuttal Engine)
- **Target Gate**: Issue #8 (Verify: 04 — Peer Reviewer Panel & Rebuttal Engine)
- **Overall Verdict**: `DEFECTS_FOUND`
- **Severity Count**:
  - **HIGH**: 1
  - **MEDIUM**: 3
  - **LOW**: 1
  - **Total Findings**: 5

An adversarial audit of Ticket 04 on `bennyV13/academic-research-skills` was conducted across all newly added assets (`academic-paper-reviewer/`, `peer-reviewer-agent.md`, `editorial-synthesizer-agent.md`, `revision-coach-agent.md`, `ars-reviewer/`, `ars-revision/`, `ars-rebuttal-audit/`, `ars-revision-coach/`, `subagents.py`, and test suites). While initial compatibility checks passed, adversarial probing identified edge cases in subagent frontmatter metadata parsing (trailing YAML comments breaking boolean capability checks), lack of test coverage for Devil's Advocate CRITICAL issue arbitration, absence of automated tone/defensiveness verification in the rebuttal audit test suite, and unhandled empty or malformed inputs in rebuttal processing.

---

## Audit Vectors & Status

| Vector ID | Target Area | Description | Status |
|-----------|-------------|-------------|--------|
| **V1** | Shell & Tool Invariants | Probed 31 files and all code blocks in `academic-paper-reviewer/` and reviewer commands for multi-line bash and Claude tool references. | `PASS` (0 violations) |
| **V2** | Cross-Reference Integrity | Probed relative markdown links and backticked shared paths across reviewer files. | `PASS` (0 broken links) |
| **V3** | Frontmatter Metadata Robustness | Probed `subagents.load_agent_spec` against YAML trailing comments, casing, and nested capability formats. | `FAIL` (Trailing inline comments corrupt boolean capability evaluation) |
| **V4** | Editorial Arbitration & DA Invariant | Probed synthesis and decision logic against Devil's Advocate CRITICAL issue blocking requirements. | `FAIL` (Integration test lacks DA CRITICAL veto/escalation test) |
| **V5** | Rebuttal Audit Tone & Evasion Detection | Probed rebuttal audit against adversarial author responses (defensive tone, dismissive framing, hand-waving). | `FAIL` (Integration test lacks tone screening and evasion detection) |
| **V6** | Edge Cases & Malformed Inputs | Tested edge cases: empty critique list, empty author response, and mismatched ID sets. | `WARN` (Boundary conditions not asserted in integration test) |

---

## Detailed Findings

### Finding 1 [HIGH] — Trailing YAML Comments Break Capability Evaluation in `subagents.py`
- **Location**: `.agents/plugins/academic-research-skills/scripts/subagents.py` (lines 30–35)
- **Description**: In `load_agent_spec`, lines are split on `:` without stripping inline comments (`# ...`). If a YAML frontmatter entry contains an inline comment (e.g. `enable_write_tools: true # required for review cards`), `clean_v` becomes `"true # required for review cards"`. Comparison with `.lower() == "true"` subsequently evaluates to `False`, unexpectedly revoking tools for the subagent.
- **Remediation**: Strip trailing comments with `v.split("#")[0].strip()` before normalizing strings in `load_agent_spec`. Also support standard YAML boolean representations (`"true"`, `"1"`, `"yes"`).

### Finding 2 [MEDIUM] — Missing Integration Verification for Devil's Advocate CRITICAL Issue Blocking
- **Location**: `scripts/test_peer_reviewer_rebuttal_integration.py`
- **Description**: The Iron Rules in `academic-paper-reviewer/SKILL.md` and `editorial-synthesizer-agent.md` mandate that any Devil's Advocate CRITICAL finding that is VALIDATED or UNRESOLVED must prevent silent `Accept` decisions. `test_peer_reviewer_rebuttal_integration.py` currently only verifies empirical gaps on standard dimensions, but lacks a test proving that a DA CRITICAL finding blocks an otherwise acceptable manuscript.
- **Remediation**: Add explicit test cases in `test_peer_reviewer_rebuttal_integration.py` verifying that validated/unresolved Devil's Advocate CRITICAL issues trigger `[DA-CRITICAL-VS-ACCEPT]` escalation and prevent unconditioned acceptance.

### Finding 3 [MEDIUM] — Rebuttal Audit Test Lacks Tone Screening & Evasive Phrasing Detection
- **Location**: `scripts/test_peer_reviewer_rebuttal_integration.py`
- **Description**: `revision-coach-agent.md` and `ars-rebuttal-audit/SKILL.md` specify that author responses must be screened for defensive, dismissive, or confrontational phrasing (e.g., "The reviewer clearly misunderstood", "The reviewer failed to grasp"). The test suite currently only tests structural anchor presence, leaving tone screening unverified.
- **Remediation**: Implement tone screening logic in the rebuttal audit test suite and verify that defensive phrasing is detected and flagged with `[TONE_RISK]`.

### Finding 4 [MEDIUM] — Rebuttal Audit Boundary Edge Cases Unhandled in Test Suite
- **Location**: `scripts/test_peer_reviewer_rebuttal_integration.py`
- **Description**: The audit test does not assert behavior on boundary conditions such as empty critique sets (which should report 100% coverage with zero gaps) or orphaned author responses that don't match any reviewer comment ID (which should be flagged as `[ORPHANED_RESPONSE]`).
- **Remediation**: Add unit tests asserting proper handling of empty critique sets and orphaned author responses.

### Finding 5 [LOW] — Migration Ledger Timestamp Outdated
- **Location**: `.agents/plugins/academic-research-skills/migration_ledger.json` (line 3)
- **Description**: The `last_updated` timestamp in `migration_ledger.json` is set to `2026-09-18T16:20:00+03:00`, which predates the Ticket 04 updates.
- **Remediation**: Bump the timestamp to reflect the completion of Ticket 04.

---

## Remediation Plan

1. Patch `load_agent_spec` in `subagents.py` to strip inline comments and handle YAML boolean variants robustly.
2. Expand `scripts/test_peer_reviewer_rebuttal_integration.py` with:
   - Robustness tests for trailing inline comments in frontmatter capabilities.
   - Devil's Advocate CRITICAL arbitration and Accept-blocking tests.
   - Tone screening and defensive language detection tests.
   - Edge case tests for empty inputs and orphaned response IDs.
3. Update `migration_ledger.json` timestamp.
4. Run full compatibility scan and integration test suite to verify all checks pass.
