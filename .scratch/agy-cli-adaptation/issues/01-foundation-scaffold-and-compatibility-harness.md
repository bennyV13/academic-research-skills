# 01 — Foundation Scaffold & Automated AGY Compatibility Harness

**What to build:** The foundational target environment and an automated compatibility verifier that checks any converted skill, command, or agent for Antigravity CLI compliance. This enables confidence that converted assets satisfy AGY standards before packaging.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] Target plugin structure is established with isolated subdirectories for skills, rules, hooks, and migration tracking.
- [x] A migration ledger tracks the conversion lifecycle (`PENDING`, `IN_PROGRESS`, `ADAPTED`, `VALIDATED`) for all assets.
- [x] Automated verification script validates YAML frontmatter (ensuring lowercase kebab-case `name` and descriptive third-person `description` without deprecated Claude metadata).
- [x] Linter catches forbidden Claude tool references, deprecated environment variables, and multi-line shell command blocks.
