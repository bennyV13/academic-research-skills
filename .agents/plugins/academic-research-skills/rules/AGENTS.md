# Academic Research Skills — Workspace Guidelines & Rules

A contract-audited suite of skills for academic research, paper authoring, peer review, and pipeline orchestration adapted for Google Antigravity CLI (agy).

## Core Principles & Human-in-the-Loop Posture

1. **AI is your copilot, not the pilot**: This pipeline handles research legwork (source gathering, citation verification, evidence mapping, consistency checks). Definitional questions, methodology choices, interpretation, and synthesis conclusions remain human-led.
2. **Evidence-based writing**: Every factual claim must be traceable to a source in the Annotated Bibliography. Flag claims lacking support as `[MATERIAL GAP]` rather than hedging them or hallucinating citations.
3. **No Unchecked Output**: Downstream phases depend on upstream phase deliverables. Phase 3 (Analysis) synthesizes findings from Phase 2 (Investigation); Phase 4 (Drafting) compiles reports from Phase 3 synthesis.

## Routing Discipline & Intent Clarification

- Explicit user triggers (e.g. `/ars-plan`, `/ars-lit-review`, `/ars-reviewer`) route directly into their designated skill mode.
- When intent is ambiguous across research vs authoring vs reviewing, ask clarifying questions using `ask_question` before initiating multi-phase pipelines.
- Single-phase agents stay strictly within their assigned phase for write operations.

## Antigravity CLI Conventions

- **Tool Calling**: Native Antigravity tools (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `grep_search`, `find_by_name`, `invoke_subagent`, `send_message`).
- **Shell Commands**: All shell commands must be provided as single-line code blocks without line numbers or line breaks to enable easy copying and execution.
- **Subagents**: Specialized agents (`synthesis-agent`, `report-compiler-agent`, `research-architect-agent`) run in isolated workspaces (`"branch"`) and communicate back to callers via `send_message`.
