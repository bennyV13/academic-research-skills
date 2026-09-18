# Implementation Plan: Adapt Academic Research Skills to Antigravity (agy) CLI

This plan outlines the phases, tasks, and TDD steps required to adapt the Academic Research Skills suite into a native Antigravity CLI plugin.

## Phase 1: Plugin Architecture Scaffolding & Manifest
- [ ] Task: Write tests for plugin manifest and rule schema validation
    - [ ] Create `tests/test_agy_plugin_manifest.py` to validate `plugin.json` schema
    - [ ] Add assertions checking required fields: `name`, `version`, and valid paths
- [ ] Task: Scaffold plugin directory structure, manifest, and rules
    - [ ] Create directory tree `.agents/plugins/academic-research-skills/`
    - [ ] Author `plugin.json` with metadata and declarations
    - [ ] Create `rules/AGENTS.md` specifying academic rigor, citation policies, and tool constraints
    - [ ] Verify manifest tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Plugin Architecture Scaffolding & Manifest' (Protocol in workflow.md)

## Phase 2: Core Skills Transpilation & Tool Alignment
- [ ] Task: Write tests for skill frontmatter and Claude token sanitization
    - [ ] Create `tests/test_agy_skills.py` to lint `SKILL.md` frontmatter
    - [ ] Assert that `name` is kebab-case and `description` is third-person
    - [ ] Assert absence of Claude tokens (`CLAUDE_PLUGIN_ROOT`, `Bash(`, `StrReplace`, `AskUser`)
- [ ] Task: Transpile the 4 core pipeline skills
    - [ ] Transpile `academic-paper` to AGY skill format with `run_command`, `replace_file_content`, and single-line bash blocks
    - [ ] Transpile `academic-paper-reviewer` to AGY skill format
    - [ ] Transpile `academic-pipeline` to AGY skill format
    - [ ] Transpile `deep-research` to AGY skill format
- [ ] Task: Transpile supporting references and file paths
    - [ ] Update relative markdown links to point inside the plugin directory
    - [ ] Verify skill linting tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Core Skills Transpilation & Tool Alignment' (Protocol in workflow.md)

## Phase 3: Slash Commands to AGY Skills Conversion
- [ ] Task: Write tests for slash command conversion
    - [ ] Create `tests/test_agy_commands.py` validating command frontmatter and triggers
    - [ ] Assert that all 18 commands map to discoverable skills
- [ ] Task: Convert 18 slash commands to AGY skills
    - [ ] Convert planning commands (`ars-plan`, `ars-outline`, `ars-3w`)
    - [ ] Convert research commands (`ars-lit-review`, `ars-cache-invalidate`, `ars-mark-read`, `ars-unmark-read`)
    - [ ] Convert review & audit commands (`ars-reviewer`, `ars-rebuttal-audit`, `ars-citation-check`, `ars-disclosure`)
    - [ ] Convert revision & output commands (`ars-revision`, `ars-revision-coach`, `ars-abstract`, `ars-format-convert`, `ars-full`)
    - [ ] Verify command tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Slash Commands to AGY Skills Conversion' (Protocol in workflow.md)

## Phase 4: Subagent Architecture & Multi-Agent Dispatch
- [ ] Task: Write tests for AGY subagent definitions
    - [ ] Create `tests/test_agy_subagents.py` testing subagent generation
    - [ ] Assert subagent configs have required fields (`name`, `description`, `system_prompt`, `enable_write_tools`)
- [ ] Task: Port agent specifications to AGY subagents
    - [ ] Port `report_compiler_agent.md` to AGY subagent definition
    - [ ] Port `research_architect_agent.md` to AGY subagent definition
    - [ ] Port `synthesis_agent.md` to AGY subagent definition
    - [ ] Port simulated peer-review panel roles into `define_subagent` templates
    - [ ] Implement dispatch helpers utilizing `invoke_subagent` with `branch` and `inherit` workspace policies
    - [ ] Verify subagent tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Subagent Architecture & Multi-Agent Dispatch' (Protocol in workflow.md)

## Phase 5: Native AGY Lifecycle Hooks & Write-Scope Guard Refactoring
- [ ] Task: Write unit tests for AGY hook JSON contracts
    - [ ] Create `tests/test_agy_hooks.py` with mock AGY camelCase protojson inputs
    - [ ] Assert hook script returns valid JSON stdout (`decision`: `allow` | `deny` | `ask`)
    - [ ] Test edge cases: prohibited directories, read-only modes, and allowed writes
- [ ] Task: Implement AGY-native write-scope guard
    - [ ] Create `hooks/run_guard_agy.py` parsing AGY `stdin` payload (`toolCall`, `stepIdx`, `conversationId`)
    - [ ] Implement decision logic mapping to AGY permissions
    - [ ] Create `.agents/plugins/academic-research-skills/hooks.json` configuring `PreToolUse` for `run_command`, `write_to_file`, and `replace_file_content`
    - [ ] Verify hook tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Native AGY Lifecycle Hooks & Write-Scope Guard Refactoring' (Protocol in workflow.md)

## Phase 6: End-to-End Integration, Validation & Documentation
- [ ] Task: Run full regression and integration test suite
    - [ ] Execute pytest across all new AGY test suites
    - [ ] Validate entire plugin directory structure against AGY discovery rules
- [ ] Task: Update documentation and user guide
    - [ ] Update `README.md` with AGY CLI installation and quickstart commands
    - [ ] Add `docs/AGY_INTEGRATION.md` detailing subagent dispatch and hook architecture
- [ ] Task: Conductor - User Manual Verification 'Phase 6: End-to-End Integration, Validation & Documentation' (Protocol in workflow.md)
