# Adversarial Audit Report: Gate #4 (Deep Research & Synthesis Subagent)

## Executive Summary

- **Overall Verdict:** `DEFECTS_FOUND`
- **Severity Count:**
  - **HIGH:** 3
  - **MEDIUM:** 3
  - **LOW:** 1
  - **Total Findings:** 7

An adversarial audit of Issue #3 (02 — Deep Research & Synthesis Subagent Tracer) for Gate #4 on repository `bennyV13/academic-research-skills` revealed critical security vulnerabilities, broken cross-references, acceptance criteria violations, and ledger state desynchronization. While existing tests in [test_deep_research_synthesis_integration.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/test_deep_research_synthesis_integration.py) report passing, adversarial probing identified:
1. An arbitrary file read / directory traversal flaw in [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py).
2. A direct breach of the ticket's explicit acceptance criteria by hardcoding `"Workspace": "inherit"` instead of isolated workspaces (`"branch"` or `"share"`).
3. Pervasive relative path breakages in [deep-research/SKILL.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/SKILL.md) pointing to 12 unmigrated agents, non-existent `rules/AGENTS.md`, and repo-root `shared/` paths.
4. An unledgered phantom asset ([subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py)) and premature `VALIDATED` status in [migration_ledger.json](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/migration_ledger.json).
5. Fragile YAML frontmatter parsing susceptible to prompt leaks on multi-dash content.
6. A phase boundary write fence bypass where `enable_write_tools: True` grants shell execution (`run_command`), paired with a missing Antigravity `send_message` communication protocol.
7. An unlabeled code fence linter blind spot in reference files.

---

## Probing Vectors Evaluated

| Vector | Status | Findings Description |
| :--- | :--- | :--- |
| **1. Relative Reference & Document Seam Integrity** | `FAILED` | [SKILL.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/SKILL.md) contains dozens of broken relative links: `agents/synthesis_agent.md` uses wrong casing/delimiters and relative paths, 12 out of 13 deep-research subagents do not exist in the plugin layout, `rules/AGENTS.md` does not exist anywhere, and 13 `shared/` schemas/protocols are broken relative to the skill folder. Multiple reference documents link to non-existent scripts (`migrate_literature_corpus_to_v3_9_0.py`, `check_review_pathway_output.py`). |
| **2. Subagent Definition & Invocation Contract** | `FAILED` | Arbitrary file read / directory traversal in [load_agent_prompt](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L14-L24) allows reading files outside `agents/`. Acceptance criteria specifically mandated workspace isolation, but [get_synthesis_subagent_invocation](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L39-L47) sets `"Workspace": "inherit"`. Naive `split("---", 2)` corrupts prompts when YAML frontmatter contains dashes. Metadata in [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md) is duplicated and ignored by [get_synthesis_subagent_def](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L27-L36). |
| **3. Tool & Phase Boundary Fencing** | `FAILED` | [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md) prompt-level phase fence is advisory only. Subagent definition enables write tools (`enable_write_tools: True`), which equips `run_command` (arbitrary shell execution). In the absence of Ticket 05's `PreToolUse` hook, the subagent can execute arbitrary shell commands to write outside Phase 3. Subagent definition also lacks instructions for the Antigravity `send_message` protocol, causing generated synthesis reports to be dropped by caller agents. |
| **4. Command Invariants & Single-line Shell Compliance** | `ADVISORY` | [chinese_literature_api_protocol.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/references/chinese_literature_api_protocol.md#L25-L29) contains an untagged code fence with a shell command (`$ curl ...`) and raw multi-line output. [verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py) ignores unlabeled code blocks, representing a linter blind spot. |
| **5. Migration Ledger State Parity** | `FAILED` | [scripts/subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py) was introduced in Issue #3 but is completely missing from [migration_ledger.json](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/migration_ledger.json). `deep-research-skill` is marked as `VALIDATED` even though 10 of its 13 subagents are missing from the repository and untracked in the ledger. |

---

## Detailed Findings & Reproductions

### Finding 1: Arbitrary File Read / Directory Traversal in `subagents.load_agent_prompt`
- **Severity:** `HIGH`
- **Description:** [load_agent_prompt](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L14-L18) accepts a `filename` parameter and computes `agent_path = AGENTS_DIR / filename` without validating that the resolved path resides within `AGENTS_DIR`. An attacker or untrusted caller can supply relative path traversals (`../../../../<file>`) to read arbitrary files from the filesystem.
- **Affected File & Line:** [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L14-L18)
- **Exact Reproduction Command:**
```bash
python3 -c "import sys; sys.path.insert(0, '.agents/plugins/academic-research-skills/scripts'); import subagents; print('Escaped content:', repr(subagents.load_agent_prompt('../../../../README.md')[:40]))"
```
- **Observed Result:** `Escaped content: '# Academic Research Skills for Claude Co'`
- **Impact:** Security vulnerability allowing unauthorized file reading outside the subagents directory.

---

### Finding 2: Acceptance Criteria Violation — Synthesis Subagent Configured with `Workspace: "inherit"` Instead of Workspace Isolation
- **Severity:** `HIGH`
- **Description:** The issue specification ([02-deep-research-and-synthesis-subagent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.scratch/agy-cli-adaptation/issues/02-deep-research-and-synthesis-subagent.md#L10)) explicitly specifies: `Synthesis agent is defined as an Antigravity subagent with explicit role, model tier, and workspace isolation.` In Antigravity CLI, workspace isolation is achieved using `Workspace: "branch"` or `Workspace: "share"`. However, [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L46) sets `"Workspace": "inherit"`, and [test_deep_research_synthesis_integration.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/test_deep_research_synthesis_integration.py#L46) enshrines this violation by asserting `self.assertEqual(invocation["Workspace"], "inherit")`.
- **Affected File & Line:** [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L46) and [test_deep_research_synthesis_integration.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/test_deep_research_synthesis_integration.py#L46)
- **Exact Reproduction Command:**
```bash
python3 -c "import sys; sys.path.insert(0, '.agents/plugins/academic-research-skills/scripts'); import subagents; inv = subagents.get_synthesis_subagent_invocation('test'); print('Workspace mode:', inv['Workspace']); assert inv['Workspace'] in ('branch', 'share'), 'Workspace isolation violated!'"
```
- **Observed Result:** `Workspace mode: inherit` followed by `AssertionError: Workspace isolation violated!`
- **Impact:** Fails acceptance criteria. Subagent executions modify the parent working directory directly, creating dirty working tree state and concurrent file collision risks.

---

### Finding 3: Broken Relative References and Dangling Subagents in `deep-research/SKILL.md`
- **Severity:** `HIGH`
- **Description:** [deep-research/SKILL.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/SKILL.md#L440-L486) contains extensive relative path breakages:
  1. Lines 442–454 list 13 agent definitions as `agents/<name>.md`. Relative to `skills/deep-research/`, `agents/` does not exist.
  2. For the single ported agent, the file is named `synthesis-agent.md` on disk, but [SKILL.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/SKILL.md#L446) references `agents/synthesis_agent.md` (underscore vs hyphen and missing directory traversal).
  3. The other 12 agents do not exist anywhere inside `.agents/plugins/academic-research-skills/`.
  4. Lines 23 & 105 reference `rules/AGENTS.md` which does not exist anywhere on disk.
  5. Lines 472–486 reference 13 files under `shared/` (`shared/references/...`, `shared/contracts/...`) which assume the legacy repository root and do not resolve from the skill directory.
  6. Reference protocols ([crossref_api_protocol.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/references/crossref_api_protocol.md#L55), [irb_decision_tree.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/references/irb_decision_tree.md#L125)) point to non-existent scripts (`migrate_literature_corpus_to_v3_9_0.py`, `check_review_pathway_output.py`).
- **Affected File & Line:** [SKILL.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/SKILL.md#L440-L486)
- **Exact Reproduction Command:**
```bash
python3 -c "import pathlib; p = pathlib.Path('.agents/plugins/academic-research-skills/skills/deep-research'); missing = [f for f in ['agents/synthesis_agent.md', 'rules/AGENTS.md', 'shared/references/human_subjects_authority_protocol.md'] if not (p / f).exists()]; print('Missing relative paths:', missing); assert len(missing) == 3"
```
- **Observed Result:** `Missing relative paths: ['agents/synthesis_agent.md', 'rules/AGENTS.md', 'shared/references/human_subjects_authority_protocol.md']`
- **Impact:** Subagents or human operators navigating the deep research skill encounter immediate broken links and missing dependencies.

---

### Finding 4: Unledgered Phantom Asset (`subagents.py`) and Premature `VALIDATED` Status in Migration Ledger
- **Severity:** `MEDIUM`
- **Description:** In [migration_ledger.json](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/migration_ledger.json):
  1. [scripts/subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py) was added in Issue #3 to define the subagent interface, but it is not listed in `assets`.
  2. Asset `deep-research-skill` is marked `VALIDATED`, despite 10 of its 13 documented subagents (`research_question_agent`, `bibliography_agent`, `source_verification_agent`, `editor_in_chief_agent`, `devils_advocate_agent`, `ethics_review_agent`, `socratic_mentor_agent`, `risk_of_bias_agent`, `meta_analysis_agent`, `monitoring_agent`) not being migrated or even tracked as pending assets in the ledger.
- **Affected File & Line:** [migration_ledger.json](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/migration_ledger.json#L31-L38)
- **Exact Reproduction Command:**
```bash
python3 -c "import json, pathlib; ledger = json.loads(pathlib.Path('.agents/plugins/academic-research-skills/migration_ledger.json').read_text()); ids = [a['id'] for a in ledger['assets']]; print('subagents.py tracked:', 'subagents' in ids or any('subagents.py' in a.get('target_path','') for a in ledger['assets'])); print('research-question-agent tracked:', any('research-question' in i for i in ids))"
```
- **Observed Result:** `subagents.py tracked: False` and `research-question-agent tracked: False`
- **Impact:** Breaks auditability and provides a false metric of completion for Gate #4.

---

### Finding 5: Fragile YAML Frontmatter Parsing & Metadata Desynchronization in `subagents.py`
- **Severity:** `MEDIUM`
- **Description:**
  1. [load_agent_prompt](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L20-L24) parses YAML frontmatter using naive substring splitting: `parts = content.split("---", 2)`. If the frontmatter contains `---` inside a string value (e.g., in a description) or comment, `split` cuts the frontmatter prematurely, leaking remaining YAML tokens and closing fences into the system prompt. If the frontmatter is unclosed, it falls through silently and returns raw YAML as the prompt.
  2. [get_synthesis_subagent_def](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L27-L36) hardcodes `name`, `description`, and `capabilities` in Python rather than extracting them dynamically from the frontmatter of [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md), causing silent desynchronization when the markdown file is edited.
- **Affected File & Line:** [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L20-L36)
- **Exact Reproduction Command:**
```bash
python3 -c "content = '''---\nname: test\ndescription: A note --- with three dashes\n---\nPrompt body'''; parts = content.split('---', 2); print('Leaked fragment in prompt:', repr(parts[2].strip()))"
```
- **Observed Result:** `Leaked fragment in prompt: 'with three dashes\n---\nPrompt body'`
- **Impact:** System prompts can be corrupted with malformed frontmatter fragments, and configuration updates to agent markdown files have no effect.

---

### Finding 6: Phase Boundary Write Fence Bypass via `enable_write_tools` (`run_command`) & Missing `send_message` Protocol
- **Severity:** `MEDIUM`
- **Description:**
  1. [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md#L21-L31) specifies that the agent must not write outside Phase 3. However, [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L33) sets `enable_write_tools: True`. In Antigravity CLI, `enable_write_tools` equips the subagent with `run_command` (arbitrary shell execution). In Gate #4, Ticket 05 (`PreToolUse` write-scope hook) has not been implemented. An agent can execute shell commands (`bash`, `python`, etc.) to write to any file or directory, completely bypassing prompt fences.
  2. Antigravity subagents must invoke [send_message](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md) to report results back to the parent agent. Neither [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md) nor the prompt template in [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L39-L47) instructs the subagent to use `send_message`. As a result, caller agents never receive the synthesized findings.
- **Affected File & Line:** [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md#L21-L31) and [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L33-L47)
- **Exact Reproduction Command:**
```bash
python3 -c "import sys; sys.path.insert(0, '.agents/plugins/academic-research-skills/scripts'); import subagents; d = subagents.get_synthesis_subagent_def(); prompt = d['system_prompt']; print('Write tools enabled:', d['enable_write_tools']); print('Mentions send_message:', 'send_message' in prompt); assert d['enable_write_tools'] is True; assert 'send_message' not in prompt"
```
- **Observed Result:** `Write tools enabled: True` and `Mentions send_message: False`
- **Impact:** Write boundaries cannot be enforced at runtime, and subagent output cannot be communicated back to parent sessions.

---

### Finding 7: Unlabeled Shell Command Code Block in Reference Protocols Bypasses Command Linter
- **Severity:** `LOW`
- **Description:** In [chinese_literature_api_protocol.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/references/chinese_literature_api_protocol.md#L25-L29), lines 25–29 contain an untagged code fence with a shell command (`$ curl -s 'https://doi.org/doiRA/10.3760,10.3969,10.13209,10.1360'`) followed immediately by multi-line JSON output. [verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L243) checks only `valid_starters = ("```bash", "```sh", "```zsh", "```shell")`, allowing untagged blocks to bypass single-line command validation.
- **Affected File & Line:** [chinese_literature_api_protocol.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/references/chinese_literature_api_protocol.md#L25-L29)
- **Exact Reproduction Command:**
```bash
python3 -c "p = '.agents/plugins/academic-research-skills/skills/deep-research/references/chinese_literature_api_protocol.md'; text = open(p).read(); assert '$ curl' in text; from scripts.verify_agy_compatibility import check_single_line_commands; diags = check_single_line_commands(p, text); print('Caught by verifier (expected 0 due to blind spot):', len(diags))"
```
- **Observed Result:** `Caught by verifier (expected 0 due to blind spot): 0`
- **Impact:** Allows multi-line command/output combos to escape automated linting and violates single-line command discipline.

---

## Recommended Remediation

1. **Path Sanitization & Containment:**
   Update [load_agent_prompt](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py) to resolve paths and enforce containment:
   ```python
   target_path = (AGENTS_DIR / filename).resolve()
   if not target_path.is_relative_to(AGENTS_DIR.resolve()):
       raise ValueError(f"Access denied: path '{filename}' escapes agents directory.")
   ```

2. **Enforce Workspace Isolation Acceptance Criteria:**
   In [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py#L46), change `"Workspace": "inherit"` to `"Workspace": "branch"` (or `"share"`), and update [test_deep_research_synthesis_integration.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/test_deep_research_synthesis_integration.py#L46) to assert `"branch"`.

3. **Frontmatter Parser Hardening & Dynamic Metadata:**
   Use line-based frontmatter splitting (`re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)`). Extract metadata (`description`, `capabilities`) directly from the parsed frontmatter instead of hardcoding values in Python.

4. **Remediate Relative References in `SKILL.md`:**
   - Update `agents/synthesis_agent.md` to `../../agents/synthesis-agent.md`.
   - Add explicit notes in [SKILL.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/skills/deep-research/SKILL.md) clarifying which agents are implemented in AGY vs pending adaptation.
   - Resolve or bundle `shared/` schemas and references into the plugin structure.

5. **Update Migration Ledger State:**
   - Register [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py) as an asset in [migration_ledger.json](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/migration_ledger.json).
   - Downgrade `deep-research-skill` status to `IN_PROGRESS` or register the missing 10 subagents as tracked pending items in the ledger.

6. **Add `send_message` Protocol Instructions:**
   Include explicit instructions in [synthesis-agent.md](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/agents/synthesis-agent.md) and [subagents.py](file:///Users/user/Desktop/Research/AI-research-workspace/.agents/plugins/academic-research-skills/scripts/subagents.py) directing the synthesis agent to return its report to the caller using `send_message(Recipient="parent", Message=...)`.

7. **Close Code Block Linter Blind Spot:**
   Update `check_single_line_commands` in [verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py) to check untagged code blocks that contain command prefixes (`$ `, `curl `, `python `). Replace `$ curl` blocks in documentation with single-line commands separated from expected output.
