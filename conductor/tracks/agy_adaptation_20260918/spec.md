# Specification: Adapt Academic Research Skills (ARS) to Antigravity (agy) CLI

## 1. Overview
This track adapts the entire Academic Research Skills (ARS) suite into a native Antigravity (`agy` CLI) plugin. The adapted suite will reside as an in-tree plugin under `.agents/plugins/academic-research-skills/` featuring native `plugin.json`, AGY-compliant `skills/`, lifecycle `hooks.json`, rules in `rules/AGENTS.md`, and programmatic subagent definitions leveraging AGY's `define_subagent` and `invoke_subagent` capabilities with workspace isolation.

## 2. Functional Requirements
- **FR-1: Plugin Structure & Manifest**:
  - Establish `.agents/plugins/academic-research-skills/plugin.json` declaring plugin identity, version, and metadata.
  - Establish `rules/AGENTS.md` defining ARS core constraints, citation integrity policies, and tool usage rules for AGY agents.
- **FR-2: Skill Adaptation (Core Pipeline)**:
  - Adapt the 4 core pipeline skills: `academic-paper`, `academic-paper-reviewer`, `academic-pipeline`, and `deep-research`.
  - Rewrite YAML frontmatter to AGY standards: kebab-case `name` and descriptive third-person `description` optimized for progressive disclosure.
  - Transpile Claude tool calls (`Bash`, `Write`, `Edit`, `Grep`, `Glob`) to AGY equivalents (`run_command`, `write_to_file`, `replace_file_content`, `grep_search`, `find_by_name`).
  - Guarantee that all shell commands provided in instructions or scripts are formatted as single-line code blocks without line breaks.
- **FR-3: Slash Commands Transpilation**:
  - Port the 18 Claude slash commands in `commands/*.md` (e.g., `ars-plan`, `ars-lit-review`, `ars-reviewer`, `ars-revision`) into invocable AGY skills or entry-point commands under the plugin's `skills/` directory.
- **FR-4: Multi-Agent Orchestration via AGY Subagents**:
  - Port all 39 prompt roles and the primary agents (`research_architect_agent`, `report_compiler_agent`, `synthesis_agent`, simulated peer review panel) to AGY subagents.
  - Implement subagent dispatch schemas utilizing `define_subagent` and `invoke_subagent` with explicit `Model` selection (`inherit`, `pro`, `flash`) and workspace isolation (`inherit` vs `branch`).
- **FR-5: Pure AGY Lifecycle Hooks & Write-Scope Guard**:
  - Implement `.agents/plugins/academic-research-skills/hooks.json` following the AGY specification (`PreToolUse`, `PostToolUse`, `Stop`).
  - Refactor the write-scope guard (`run_guard.sh`) to natively consume AGY camelCase protojson on `stdin` (`toolCall`, `stepIdx`, `conversationId`) and output conforming JSON decisions on `stdout` (`{"decision": "allow" | "deny" | "ask"}`).
  - Target AGY tool matchers: `"matcher": "run_command|write_to_file|replace_file_content"`.
- **FR-6: Context & Verification Architecture**:
  - Update workflow references to leverage Gemini 1M–2M context windows while preserving ARS stage gates and Material Passports.
  - Adapt L3 claim-faithfulness gates and citation verification scripts to operate cleanly in AGY environment without dependency on Claude-specific environment variables.

## 3. Non-Functional Requirements
- **NFR-1: Sandbox & Platform Portability**: Comply with macOS Seatbelt sandbox constraints (no on-the-fly `uvx` caching in restricted paths; rely on virtualenvs or host-installed binaries).
- **NFR-2: Backward Compatibility**: Existing Claude Code files (`.claude/`, `.claude-plugin/`) remain intact and unmodified.
- **NFR-3: Zero Shell Formatting Violations**: All shell commands must be emitted as single-line blocks without line numbers.

## 4. Acceptance Criteria
- [ ] `.agents/plugins/academic-research-skills/plugin.json` is valid and successfully discovered by `agy`.
- [ ] All 4 core skills and 18 slash commands exist in `.agents/plugins/academic-research-skills/skills/` with valid YAML frontmatter.
- [ ] No remaining references to Claude-specific tools (`Bash`, `FileEdit`, `CLAUDE_PLUGIN_ROOT`) exist in the adapted skills.
- [ ] `hooks.json` successfully intercepts `write_to_file` and `run_command` in a test run, evaluating write-scope permissions and outputting valid decision JSON.
- [ ] Subagents can be registered via `define_subagent` and dispatched via `invoke_subagent` with `branch` or `inherit` workspaces.
- [ ] Test suite executes and validates skill structure and hook payload contracts.

## 5. Out of Scope
- Deprecating or modifying existing Claude Code plugin infrastructure.
- Re-architecting underlying academic citation verification APIs (Semantic Scholar, Crossref).
