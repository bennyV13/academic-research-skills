# Adversarial Audit Report: Gate #10 (AGY Lifecycle Hooks & Write-Scope Guard)

## Executive Summary

- **Target Ticket**: Issue #9 (05 — AGY Lifecycle Hooks & Write-Scope Guard)
- **Target Gate**: Issue #10 (Verify: 05 — AGY Lifecycle Hooks & Write-Scope Guard)
- **Overall Verdict**: `DEFECTS_FOUND`
- **Severity Count**:
  - **HIGH**: 2
  - **MEDIUM**: 2
  - **LOW**: 1
  - **Total Findings**: 5

An adversarial audit of Ticket 05 on `bennyV13/academic-research-skills` was conducted across all newly added assets (`hooks.json`, `run_guard_agy.sh`, `ars_write_scope_guard_agy.py`, `ars_phase_scope_manifest.json`, and test suites). While initial compatibility and integration tests passed, adversarial stress-testing identified critical gaps in agent identity normalization (case-sensitivity allowing fence bypasses), missing infrastructure protection for `rules/AGENTS.md` and `migration_ledger.json`, unvalidated output JSON forwarding in the launcher shell script, and lack of whitespace sanitization on target paths.

---

## Audit Vectors & Status

| Vector ID | Target Area | Description | Status |
|-----------|-------------|-------------|--------|
| **V1** | Shell & Launcher Robustness | Probed `run_guard_agy.sh` against non-JSON outputs, tracebacks, and interpreter failures. | `FAIL` (Launcher forwards non-JSON stdout without schema validation) |
| **V2** | Agent Identity Fence Bypass | Tested casing variations (`Synthesis-Agent`, `PEER_REVIEWER_AGENT`) and trailing whitespace in `agent_type`. | `FAIL` (Casing/whitespace causes false-negative Bucket A classification, bypassing write fences) |
| **V3** | Infrastructure Tampering Coverage | Probed whether all security invariants (`rules/AGENTS.md`, `migration_ledger.json`) are in `INFRA_PROTECTED_GLOBS`. | `FAIL` (`rules/*.md` and `migration_ledger.json` unprotected) |
| **V4** | Target Path Sanitization | Tested `TargetFile` arguments with leading/trailing whitespace and relative traversal components. | `WARN` (Missing `.strip()` on extracted target paths) |
| **V5** | Test Suite Adversarial Depth | Checked whether `test_agy_lifecycle_hooks_integration.py` probes casing, whitespace, and rules protection. | `FAIL` (Coverage gaps on adversarial inputs and malformed outputs) |

---

## Detailed Findings

### Finding 1 [HIGH] — Case-Sensitivity and Whitespace in Subagent Identity Allows Write-Scope Fence Bypass
- **Location**: `.agents/plugins/academic-research-skills/scripts/ars_write_scope_guard_agy.py` (lines 150–165)
- **Description**: In `evaluate_agy_decision`, `agent_type` is checked directly and with a hyphen-to-underscore replacement (`alt_agent = agent_type.replace("-", "_")`). If the model or runtime supplies an agent type with differing capitalization (e.g., `"Synthesis-Agent"`, `"Peer-Reviewer-Agent"`, `"SYNTHESIS_AGENT"`) or trailing whitespace, both lookups fail. `is_bucket_a` evaluates to `False`, allowing a single-phase subagent to execute out-of-scope writes and shell commands unconstrained.
- **Remediation**: Normalize `agent_type` by stripping whitespace and lowercasing (`norm = agent_type.strip().lower().replace("-", "_")`) and build a case-normalized lookup table over manifest agent names.

### Finding 2 [HIGH] — Missing Infrastructure Self-Protection for Plugin Rules and Migration Ledger
- **Location**: `.agents/plugins/academic-research-skills/scripts/ars_write_scope_guard_agy.py` (lines 33–44)
- **Description**: `INFRA_PROTECTED_GLOBS` protects hook scripts, python guards, and agent definitions, but omits `rules/*.md` (`rules/AGENTS.md`) and `migration_ledger.json`. Any subagent or external tool call could overwrite the system rules or corrupt the migration audit ledger without triggering a guard block.
- **Remediation**: Add `"rules/*.md"`, `"**/rules/*.md"`, and `"migration_ledger.json"` to `INFRA_PROTECTED_GLOBS`.

### Finding 3 [MEDIUM] — Launcher Script Lacks Output JSON Schema Validation Before Forwarding
- **Location**: `.agents/plugins/academic-research-skills/hooks/run_guard_agy.sh` (lines 37–43)
- **Description**: If the Python guard subprocess crashes or outputs non-JSON content (e.g. an unexpected deprecation warning or unhandled exception trace), `run_guard_agy.sh` checks only `[ -n "$GUARD_OUT" ]` and forwards raw stdout to AGY CLI. This can crash the AGY protojson parser and wedge the session.
- **Remediation**: In `run_guard_agy.sh`, validate that `$GUARD_OUT` is valid JSON containing `"decision"` (using a quick python snippet similar to the canonical launcher) before printing; otherwise fall back to `{"decision":"allow"}`.

### Finding 4 [MEDIUM] — Untrimmed Whitespace in `TargetFile` Argument
- **Location**: `.agents/plugins/academic-research-skills/scripts/ars_write_scope_guard_agy.py` (lines 175–182)
- **Description**: The extracted `TargetFile` string is not stripped of leading or trailing whitespace before being passed to `os.path` functions.
- **Remediation**: Call `.strip()` on extracted target file path strings.

### Finding 5 [LOW] — Integration Test Suite Lacks Coverage for Casing Variations and Rules Protection
- **Location**: `scripts/test_agy_lifecycle_hooks_integration.py`
- **Description**: The test suite only tests lowercase, well-formed agent names and standard file paths, leaving case-insensitivity and `rules/AGENTS.md` protection unverified.
- **Remediation**: Expand `scripts/test_agy_lifecycle_hooks_integration.py` to assert protection of `rules/AGENTS.md`, `migration_ledger.json`, case-insensitive agent type enforcement, and launcher non-JSON fallback.

---

## Remediation Plan

1. In `ars_write_scope_guard_agy.py`:
   - Add `rules/*.md`, `**/rules/*.md`, and `migration_ledger.json` to `INFRA_PROTECTED_GLOBS`.
   - Normalize `agent_type` with `.strip().lower().replace("-", "_")` and match against normalized manifest keys.
   - Strip whitespace on `TargetFile`.
2. In `run_guard_agy.sh`:
   - Add validation that output is valid JSON with `"decision"` before printing.
3. In `scripts/test_agy_lifecycle_hooks_integration.py`:
   - Add tests for case-insensitive agent type gating, rules file protection, ledger protection, and launcher non-JSON fallback.
4. Verify all tests pass cleanly.
