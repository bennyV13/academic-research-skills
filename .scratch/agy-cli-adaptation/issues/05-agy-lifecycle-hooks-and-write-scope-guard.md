# 05 — AGY Lifecycle Hooks & Write-Scope Guard

**What to build:** Real-time tool execution gating and write-scope security for Antigravity CLI. Hooks intercept tool calls before execution, enforcing workspace boundaries and preventing unintended disk modifications.

**Blocked by:** 01 — Foundation Scaffold & Automated AGY Compatibility Harness

**Status:** ready-for-agent

- [ ] Lifecycle hook configuration is adapted into AGY `hooks.json` schema with named hook groups and tool matchers.
- [ ] Guard launcher script parses AGY camelCase protojson input on stdin and emits standard AGY JSON decision output on stdout.
- [ ] Tool calls to file-modification and shell tools are intercepted and audited against write-scope rules.
- [ ] Dry-run tests verify that permitted actions pass silently and out-of-scope write actions are denied with an informative reason.
