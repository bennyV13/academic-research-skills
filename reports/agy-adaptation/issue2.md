# Adversarial Audit Report: Gate #2 (Scaffold & Compatibility Harness)

## Executive Summary

- **Overall Verdict:** `DEFECTS_FOUND`
- **Severity Count:**
  - **HIGH:** 3
  - **MEDIUM:** 2
  - **LOW:** 1
  - **Total Findings:** 6

An adversarial audit of Ticket 01 (Foundation Scaffold & Automated AGY Compatibility Harness) revealed critical parser blind spots, incomplete pattern matching, and schema conformance gaps. While the base test suite (`scripts/test_verify_agy_compatibility.py`) passes 8/8 tests under developer assumptions, adversarial probing identified bypass vectors where forbidden Claude tools (e.g., `StrReplace`, `FileEdit`, `create_file`, `Grep`, `Glob`), full Claude model identifiers (`claude-3-5-sonnet-20241022`), invalid hook structures (`PreInvocation` payload corruptions), and desynchronized or phantom migration ledger entries slip past Gate #2 completely undetected. Furthermore, the compatibility verifier completely omits auditing `.agents/plugins/academic-research-skills/plugin.json`, the primary root manifest of the adapted plugin suite.

---

## Probing Vectors Evaluated

| Vector | Status | Description |
| :--- | :--- | :--- |
| **1. Frontmatter Parser Robustness & Edge Cases** | `FAILED` | YAML parser lacks inline comment stripping leading to false positives on valid keys (`name: my-skill # comment`), discards multi-line folded scalars when comments follow indicator (`>- # comment`), and checks a hardcoded 3-element set for models (`{"sonnet", "opus", "haiku"}`), allowing real Claude model IDs (`claude-3-5-sonnet-20241022`) to bypass detection completely. |
| **2. Tool & Command Detection Coverage** | `FAILED` | `FORBIDDEN_CLAUDE_TOOLS` requires a trailing opening parenthesis `(` and omits standard Claude tools (`StrReplace`, `FileEdit`, `MultiEdit`, `create_file`, `ReadDir`, `Grep`, `Glob`). Tool references in prose or YAML lists are completely missed. `DEPRECATED_CLAUDE_COMMANDS` omits `/clear` and `/init`. `check_single_line_commands` misses `zsh` code blocks. |
| **3. Hook Schema Conformance vs AGY Docs** | `FAILED` | Deviates from Antigravity lifecycle hook specification in `docs/hooks.md`. Validates only `PreToolUse` and `PostToolUse`, completely skipping schema validation for `PreInvocation`, `PostInvocation`, and `Stop` flat handler lists. Does not validate handler `type`, `command` presence, or regex safety. Downgrades misspelled hook events to `WARNING`, allowing invalid hook configs to exit `0` (pass open). |
| **4. Migration Ledger Schema Integrity** | `FAILED` | `check_migration_ledger` performs shallow validation. It does not verify that `summary` statistics match the actual status counts in `assets`, does not validate `category` values, does not verify whether `source_path` exists on disk, does not verify `target_path` existence for `VALIDATED` assets, and ignores duplicate asset IDs. |
| **5. CLI Robustness & Error Handling** | `FAILED` | Scanned file traversal ignores `plugin.json` entirely; passing `plugin.json` explicitly returns 0 diagnostics even if malformed. Running `--path nonexistent --json` outputs unstructured stderr and exits code 2 without emitting machine-readable JSON to stdout. |

---

## Detailed Findings & Reproductions

### Finding 1: Incomplete Forbidden Tool Regex Bypasses Standard Claude Tools and Invocations
- **Severity:** `HIGH`
- **Description:** `FORBIDDEN_CLAUDE_TOOLS` regex `r"\b(Bash|Edit|Write|Read|Task|AskUser|AskFollowupQuestion)\s*\("` requires a trailing opening parenthesis `\s*\(` and omits core Claude tools: `StrReplace`, `FileEdit`, `MultiEdit`, `create_file`, `ReadDir`, `Grep`, and `Glob`. Because `\bEdit` requires a word boundary before `Edit`, compound identifiers like `FileEdit(` or `MultiEdit(` do not match. Furthermore, references in prose (e.g. `Use the Bash tool to execute tests`) or YAML arrays (`tools: [Bash, Edit]`) are missed because no parenthesis is present.
- **Affected File & Line:** [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L30-L33)
- **Exact Reproduction Command:**
```bash
python3 -c "import scripts.verify_agy_compatibility as v, pathlib; p = pathlib.Path('test.md'); samples = ['StrReplace(path=\"x\")', 'FileEdit(file=\"x\")', 'MultiEdit(file=\"x\")', 'create_file(path=\"x\")', 'ReadDir(\"/\")', 'Grep(pattern=\"foo\")', 'Glob(pattern=\"*.py\")', 'Please run the Bash tool']; diags = [v.check_tools_and_patterns(p, s) for s in samples]; print('Total caught (expected 8):', sum(len(d) for d in diags))"
```
- **Observed Result:** `Total caught (expected 8): 0`.
- **Impact:** Converted skills containing Claude-native tools like `StrReplace`, `FileEdit`, `Grep`, and `Glob` pass Gate #2 verification and fail catastrophically at runtime when dispatched to Antigravity agents.

---

### Finding 2: Incomplete Hook Schema Validation & Failing Open on Misspelled Hook Events
- **Severity:** `HIGH`
- **Description:** In `check_hooks_json`:
  1. According to AGY Customization docs (`docs/hooks.md`), `PreInvocation`, `PostInvocation`, and `Stop` are flat arrays of handler objects. The verifier checks `if event_name in {"PreToolUse", "PostToolUse"}:` and performs zero structural or type validation on `PreInvocation`, `PostInvocation`, or `Stop`.
  2. Individual handler objects are never checked for the required `command` field, unsupported `type` (only `"command"` is supported by AGY), or numeric `timeout`.
  3. `matcher` regex compilation safety is never verified.
  4. Misspelled event names (e.g., `preToolUse`, `pre_tool_use`, `OnStop`) are flagged with severity `"WARNING"`. Because `main()` only exits with an error code if `errors` is non-empty (`return 0 if not errors else 1`), misspelled hook events pass Gate #2 with exit code 0.
- **Affected File & Line:** [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L267-L303) and [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L417-L422)
- **Exact Reproduction Command:**
```bash
python3 -c "import subprocess, tempfile, pathlib, sys; td = tempfile.TemporaryDirectory(); r = pathlib.Path(td.name); (r / 'hooks.json').write_text('{\"guard\": {\"preToolUse\": [{\"matcher\": \"run_command\", \"hooks\": [{\"type\": \"command\"}]}], \"PreInvocation\": \"corrupted_string\"}}', encoding='utf-8'); res = subprocess.run([sys.executable, 'scripts/verify_agy_compatibility.py', '--path', str(r / 'hooks.json')], capture_output=True, text=True); print('Exit code:', res.returncode, '| Output:', res.stdout.strip())"
```
- **Observed Result:** `Exit code: 0 | Output: [WARNING] .../hooks.json — Unknown hook event 'preToolUse' in hook 'guard'. Valid events: ['PostInvocation', 'PostToolUse', 'PreInvocation', 'PreToolUse', 'Stop'] \n\n PASSED with 1 warning(s).`
- **Impact:** Safety guards (such as the ARS write-scope guard planned in Ticket 05) can be completely bypassed if event names are misspelled or payloads are malformed, as CI passes open with exit code 0.

---

### Finding 3: Shallow Migration Ledger Verification & Desynchronization Blind Spots
- **Severity:** `HIGH`
- **Description:** `check_migration_ledger` only checks for the presence of four top-level keys (`version`, `last_updated`, `summary`, `assets`) and confirms `status` is one of four enum strings. It suffers from major verification omissions:
  1. `summary` counts (`total`, `pending`, `in_progress`, `adapted`, `validated`) are never verified against actual asset status counts.
  2. Asset `category` is completely unvalidated (allows arbitrary strings or non-strings).
  3. `source_path` is never checked for existence on disk (allowing phantom source references).
  4. For assets marked `VALIDATED`, `target_path` is never checked for actual existence on disk.
  5. Duplicate asset `id`s are not detected.
- **Affected File & Line:** [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L306-L342)
- **Exact Reproduction Command:**
```bash
python3 -c "import scripts.verify_agy_compatibility as v, pathlib; content = '''{\"version\": \"1.0.0\", \"last_updated\": \"2026-09-18T15:00:00Z\", \"summary\": {\"total\": 9999, \"pending\": 0, \"in_progress\": 0, \"adapted\": 0, \"validated\": 0}, \"assets\": [{\"id\": \"dup\", \"category\": \"fake_cat\", \"source_path\": \"phantom.md\", \"target_path\": \"nonexistent.md\", \"status\": \"VALIDATED\"}, {\"id\": \"dup\", \"category\": \"fake_cat\", \"source_path\": \"phantom.md\", \"target_path\": \"nonexistent.md\", \"status\": \"VALIDATED\"}]}'''; print('Diagnostics count (expected > 0):', len(v.check_migration_ledger(pathlib.Path('migration_ledger.json'), content)))"
```
- **Observed Result:** `Diagnostics count (expected > 0): 0`.
- **Impact:** Broken migration paths, phantom assets, duplicate IDs, and fabricated completion metrics pass verification, defeating the auditability of the migration ledger.

---

### Finding 4: Claude Model Detection Bypass & Frontmatter Comment False Positives
- **Severity:** `MEDIUM`
- **Description:**
  1. **Claude Model Bypass:** In `check_frontmatter`, the check `model.lower() in {"sonnet", "opus", "haiku"}` only catches exact matches to those three short names. Full model strings like `claude-3-5-sonnet-20241022`, `claude-3-opus`, or `claude-sonnet-4-preview` fail the equality test and bypass detection. Furthermore, inline comments (e.g. `model: sonnet # fast`) evade the check.
  2. **Inline Comment False Positive:** `parse_simple_frontmatter` does not strip inline `#` comments on key-value lines. For example, `name: my-skill # primary skill` parses `name` as `"my-skill # primary skill"`, which fails `KEBAB_CASE_PATTERN` with an invalid error diagnostic.
  3. **Folded Scalar Truncation:** When comments appear on folded scalar lines (e.g. `description: >- # folded description`), `val` is evaluated as `">- # folded description"`, failing the tuple check `val in (">-", ">", "|", "|-")`. The parser assigns the raw string to `description` and discards all subsequent lines.
- **Affected File & Line:** [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L79-L96) and [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L153-L163)
- **Exact Reproduction Command:**
```bash
python3 -c "import scripts.verify_agy_compatibility as v, pathlib; p = pathlib.Path('SKILL.md'); c1 = '---\nname: my-skill\ndescription: A valid description that exceeds minimum length.\nmodel: claude-3-5-sonnet-20241022\n---\n'; c2 = '---\nname: my-skill # comment\ndescription: A valid description that exceeds minimum length.\n---\n'; print('c1 diags (Claude model bypass):', len(v.check_frontmatter(p, c1))); print('c2 diags (Inline comment false positive):', len(v.check_frontmatter(p, c2)))"
```
- **Observed Result:** `c1 diags (Claude model bypass): 0` and `c2 diags (Inline comment false positive): 1`.
- **Impact:** Claude-specific model targets slip past linter checks, and standard YAML skills with inline comments fail CI erroneously.

---

### Finding 5: Complete Blind Spot for `plugin.json` Manifest
- **Severity:** `MEDIUM`
- **Description:** `verify_agy_compatibility.py` contains zero validation logic for `plugin.json`.
  1. In `scan_path`, directory traversal checks `if p.suffix == ".md" or p.name in {"hooks.json", "migration_ledger.json"}:`, completely omitting `plugin.json`.
  2. In `verify_file`, there is no branch for `plugin.json`. Direct invocation with `--path plugin.json` returns 0 diagnostics even if `plugin.json` contains malformed JSON or lacks required fields (`name`, `version`, `description`).
  This violates FR-1 and the Ticket 01 specification which mandated scaffolding and automated verification for the plugin manifest.
- **Affected File & Line:** [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L351-L364) and [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L377-L380)
- **Exact Reproduction Command:**
```bash
python3 -c "import subprocess, tempfile, pathlib, sys; td = tempfile.TemporaryDirectory(); r = pathlib.Path(td.name); (r / 'plugin.json').write_text('INVALID MALFORMED JSON {{{{', encoding='utf-8'); res = subprocess.run([sys.executable, 'scripts/verify_agy_compatibility.py', '--path', str(r), '--json'], capture_output=True, text=True); print('Scanned dir with broken plugin.json -> Errors:', res.stdout.strip())"
```
- **Observed Result:** `Scanned dir with broken plugin.json -> Errors: { ... "errors": 0, "warnings": 0, "diagnostics": [] }`.
- **Impact:** Corrupted or invalid plugin manifests will be deployed to AGY plugins without detection, causing silent plugin discovery failures in the Antigravity CLI.

---

### Finding 6: Command & CLI Edge Cases: Missed Shell Types (`zsh`), Unclosed Blocks, and `--json` on Missing Paths
- **Severity:** `LOW`
- **Description:**
  1. `check_single_line_commands` matches `stripped.startswith("```bash") or stripped.startswith("```sh")`. Blocks written as ```` ```zsh ```` are ignored.
  2. Unclosed code blocks (e.g. ```` ```bash ```` at the end of a file without closing ```` ``` ````) are never checked because line validation only fires on the closing fence.
  3. When `--json` is supplied with a non-existent path, `main()` prints plain text to `stderr` and exits code 2 without outputting valid JSON to `stdout`.
  4. `DEPRECATED_CLAUDE_COMMANDS` only checks `/compact\b`, missing other Claude session commands like `/clear` and `/init`.
- **Affected File & Line:** [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L37-L39), [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L214-L239), and [scripts/verify_agy_compatibility.py](file:///Users/user/Desktop/Research/AI-research-workspace/scripts/verify_agy_compatibility.py#L391-L394)
- **Exact Reproduction Command:**
```bash
python3 -c "import subprocess, sys; res = subprocess.run([sys.executable, 'scripts/verify_agy_compatibility.py', '--path', 'nonexistent_path', '--json'], capture_output=True, text=True); print('Exit code:', res.returncode, '| stdout:', repr(res.stdout), '| stderr:', repr(res.stderr))"
```
- **Observed Result:** `Exit code: 2 | stdout: '' | stderr: 'Error: Target path ... does not exist\n'`.
- **Impact:** Tooling and subagents expecting JSON output receive empty stdout and fail to parse errors; multi-line `zsh` code blocks violate the single-line command rule undetected.

---

## Recommended Remediation

### 1. Expand Claude Tool & Command Regex Patterns
Update `FORBIDDEN_CLAUDE_TOOLS` and `DEPRECATED_CLAUDE_COMMANDS` in `scripts/verify_agy_compatibility.py` to match all Claude tools and variants, including standalone mentions and compound names:
```python
FORBIDDEN_CLAUDE_TOOLS = re.compile(
    r"\b(Bash|Edit|FileEdit|MultiEdit|StrReplace|str_replace|Write|Read|ReadDir|create_file|CreateFile|Task|AskUser|AskFollowupQuestion|Grep|Glob)\b",
    re.IGNORECASE,
)
DEPRECATED_CLAUDE_COMMANDS = re.compile(
    r"(?<![a-zA-Z0-9_-])/(compact|clear|init)\b",
)
```

### 2. Comprehensive Hook Schema Enforcement
Refactor `check_hooks_json` to strictly enforce the Antigravity Hook specification:
1. Validate flat handler lists for `PreInvocation`, `PostInvocation`, and `Stop`:
   - Must be `list[dict]`.
   - Each handler must contain required string `command`.
   - If `type` is present, it must equal `"command"`.
   - If `timeout` is present, it must be an integer > 0.
2. In `PreToolUse` and `PostToolUse`, validate that `matcher` is a string that compiles as a valid regular expression, and `hooks` is a list of valid handler objects.
3. Promote unknown or misspelled hook events to `ERROR` severity so invalid configurations fail verification immediately.

### 3. Deep Ledger Validation
Extend `check_migration_ledger` to verify:
1. Summary sync:
   - `summary["total"] == len(assets)`
   - `summary["pending"] == count(status == "PENDING")`
   - `summary["in_progress"] == count(status == "IN_PROGRESS")`
   - `summary["adapted"] == count(status == "ADAPTED")`
   - `summary["validated"] == count(status == "VALIDATED")`
2. Unique asset `id` validation.
3. Allowed asset `category` enum: `{"scaffold", "tool", "skill", "agent", "command", "hook", "rule"}`.
4. Disk existence checks:
   - If `source_path != "N/A"`, verify `(base_dir / source_path).exists()`.
   - If `status == "VALIDATED"`, verify `(base_dir / target_path).exists()`.

### 4. Robust Frontmatter & Model Validation
1. Strip trailing inline comments (`# ...`) before validating values:
   ```python
   val = re.sub(r"\s+#.*$", "", val).strip()
   ```
2. For model verification, check both explicit Claude model keywords and validate against AGY allowed tiers:
   ```python
   CLAUDE_MODEL_PATTERNS = re.compile(r"(sonnet|opus|haiku|claude)", re.IGNORECASE)
   VALID_AGY_MODELS = {"inherit", "flash", "pro", "flash_lite"}
   ```
   Flag an error if `CLAUDE_MODEL_PATTERNS.search(model)` or `model not in VALID_AGY_MODELS`.

### 5. Add Plugin Manifest Verification
Add `check_plugin_json` function to validate `.agents/plugins/*/plugin.json`:
- Must be valid JSON object.
- Required fields: `name` (kebab-case string), `version` (semver string), `description` (min length 20 chars).
- Include `plugin.json` in `scan_path` traversal and `verify_file`.

### 6. Shell Command & JSON Output Hardening
1. In `check_single_line_commands`, support ```` ```zsh ````, ```` ```shell ````, ```` ```bash ````, and ```` ```sh ````.
2. Check for unclosed code fence blocks at EOF.
3. When `--json` is supplied and `--path` does not exist, output structured JSON to stdout:
   ```python
   if args.json:
       print(json.dumps({"error": f"Target path '{target}' does not exist"}, indent=2))
   ```
