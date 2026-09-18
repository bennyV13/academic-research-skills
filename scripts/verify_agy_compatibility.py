#!/usr/bin/env python3
"""Antigravity CLI (agy) Compatibility Verifier and Linter.

Audits skills, commands, agents, hooks, manifests, and migration ledgers to ensure
strict compliance with Antigravity CLI standards and user-defined constraints.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class Diagnostic:
    path: Path
    line: Optional[int]
    severity: str  # "ERROR" or "WARNING"
    message: str

    def __str__(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line is not None else str(self.path)
        return f"[{self.severity}] {loc} — {self.message}"


FORBIDDEN_CLAUDE_TOOLS = re.compile(
    r"\b(Bash|FileEdit|MultiEdit|StrReplace|str_replace|AskUser|AskFollowupQuestion|create_file|CreateFile)\b",
)
CLAUDE_GENERIC_TOOLS = re.compile(
    r"(\btools\s*:.*?\b(Read|Write|Edit|Grep|Glob)\b|\b(Read|Write|Edit|Grep|Glob)\s*\()",
)
DEPRECATED_CLAUDE_ENVS = re.compile(
    r"\$\{?CLAUDE_(PLUGIN_ROOT|PROJECT_DIR)\}?",
)
DEPRECATED_CLAUDE_COMMANDS = re.compile(
    r"(?<![a-zA-Z0-9_-])/(compact|clear|init)\b",
)
CLAUDE_MODEL_PATTERNS = re.compile(
    r"(sonnet|opus|haiku|claude)",
    re.IGNORECASE,
)
VALID_AGY_MODELS = {"inherit", "flash", "pro", "flash_lite", "auto"}
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VALID_ASSET_CATEGORIES = {"scaffold", "tool", "skill", "agent", "command", "hook", "rule"}
FORBIDDEN_CLAUDE_FRONTMATTER_FIELDS = {
    "disable-model-invocation",
    "argument-hint",
}


def _strip_inline_comment(val: str) -> str:
    """Safely strip inline comments from a scalar value."""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    # Remove trailing comment if preceded by whitespace
    return re.sub(r"\s+#.*$", "", val).strip()


def parse_simple_frontmatter(content: str) -> tuple[Optional[dict[str, Any]], str, Optional[int]]:
    """Extract YAML frontmatter without external dependencies."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, content, None

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return None, content, None

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])

    data: dict[str, Any] = {}
    current_key: Optional[str] = None
    multi_line_val: list[str] = []

    for line in fm_lines:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue

        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            if current_key and multi_line_val:
                data[current_key] = " ".join(multi_line_val).strip()
                multi_line_val = []

            key, val = line.split(":", 1)
            current_key = key.strip()
            val_clean = _strip_inline_comment(val)
            if val_clean in (">-", ">", "|", "|-"):
                multi_line_val = []
            elif val_clean.lower() == "true":
                data[current_key] = True
                current_key = None
            elif val_clean.lower() == "false":
                data[current_key] = False
                current_key = None
            elif val_clean:
                data[current_key] = val_clean
                current_key = None
        elif current_key is not None:
            multi_line_val.append(trimmed)

    if current_key and multi_line_val:
        data[current_key] = " ".join(multi_line_val).strip()

    return data, body, end_idx + 1


def check_frontmatter(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    fm, _, _ = parse_simple_frontmatter(content)

    if fm is None:
        if path.name == "SKILL.md":
            diags.append(
                Diagnostic(path, 1, "ERROR", "Missing YAML frontmatter block (enclosed in '---') in SKILL.md")
            )
        return diags

    name = fm.get("name")
    if not name or not isinstance(name, str):
        diags.append(Diagnostic(path, 1, "ERROR", "Frontmatter missing required 'name' field"))
    elif not KEBAB_CASE_PATTERN.match(name):
        diags.append(
            Diagnostic(
                path,
                1,
                "ERROR",
                f"Frontmatter 'name' ('{name}') must be lowercase kebab-case (e.g. 'deep-research')",
            )
        )

    desc = fm.get("description")
    if not desc or not isinstance(desc, str):
        diags.append(Diagnostic(path, 1, "ERROR", "Frontmatter missing required 'description' field"))
    elif len(desc.strip()) < 20:
        diags.append(
            Diagnostic(
                path,
                1,
                "ERROR",
                f"Frontmatter 'description' is too short ({len(desc.strip())} chars; min 20 required)",
            )
        )

    for field in FORBIDDEN_CLAUDE_FRONTMATTER_FIELDS:
        if field in fm:
            diags.append(
                Diagnostic(
                    path,
                    1,
                    "ERROR",
                    f"Forbidden Claude-specific frontmatter field '{field}' found; remove for AGY compatibility",
                )
            )

    model = fm.get("model")
    if model and isinstance(model, str):
        model_clean = _strip_inline_comment(model).lower()
        if CLAUDE_MODEL_PATTERNS.search(model_clean):
            diags.append(
                Diagnostic(
                    path,
                    1,
                    "ERROR",
                    f"Forbidden Claude-specific model '{model}' in frontmatter; use AGY model tiers ('inherit', 'flash', 'pro')",
                )
            )
        elif model_clean not in VALID_AGY_MODELS:
            diags.append(
                Diagnostic(
                    path,
                    1,
                    "ERROR",
                    f"Invalid AGY model tier '{model}'; must be one of: {sorted(VALID_AGY_MODELS)}",
                )
            )

    return diags


def check_tools_and_patterns(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            continue

        if FORBIDDEN_CLAUDE_TOOLS.search(line) or CLAUDE_GENERIC_TOOLS.search(line):
            diags.append(
                Diagnostic(
                    path,
                    idx,
                    "ERROR",
                    f"Forbidden Claude tool reference detected: '{line.strip()}'. Use AGY native tools (run_command, write_to_file, etc.)",
                )
            )

        if DEPRECATED_CLAUDE_ENVS.search(line):
            diags.append(
                Diagnostic(
                    path,
                    idx,
                    "ERROR",
                    f"Deprecated Claude environment variable detected: '{line.strip()}'. Use workspace-relative paths",
                )
            )

        if DEPRECATED_CLAUDE_COMMANDS.search(line):
            diags.append(
                Diagnostic(
                    path,
                    idx,
                    "ERROR",
                    f"Deprecated Claude session command detected in line: '{line.strip()}'. Antigravity uses large context windows and subagents.",
                )
            )

    return diags


def check_single_line_commands(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    lines = content.splitlines()

    in_bash_block = False
    block_start_line = 0
    code_lines: list[tuple[int, str]] = []
    valid_starters = ("```bash", "```sh", "```zsh", "```shell")

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if any(stripped.startswith(s) for s in valid_starters):
            in_bash_block = True
            block_start_line = idx
            code_lines = []
        elif in_bash_block and stripped == "```":
            in_bash_block = False
            executable_lines = [
                (l_idx, l_content)
                for l_idx, l_content in code_lines
                if l_content.strip() and not l_content.strip().startswith("#")
            ]
            if len(executable_lines) > 1:
                diags.append(
                    Diagnostic(
                        path,
                        block_start_line,
                        "ERROR",
                        f"Multi-line shell command block detected ({len(executable_lines)} lines). "
                        "User rule: Always provide shell commands as single-line code blocks without line numbers or line breaks.",
                    )
                )
            code_lines = []
        elif in_bash_block:
            code_lines.append((idx, line))

    if in_bash_block:
        diags.append(
            Diagnostic(
                path,
                block_start_line,
                "ERROR",
                "Unclosed code fence block detected at end of file.",
            )
        )

    return diags


def _validate_handler(path: Path, handler: Any, context: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if not isinstance(handler, dict):
        return [Diagnostic(path, None, "ERROR", f"Handler under {context} must be a JSON object")]

    command = handler.get("command")
    if not command or not isinstance(command, str):
        diags.append(Diagnostic(path, None, "ERROR", f"Handler under {context} missing required string 'command'"))

    h_type = handler.get("type", "command")
    if h_type != "command":
        diags.append(Diagnostic(path, None, "ERROR", f"Handler under {context} has unsupported type '{h_type}'. Only 'command' is supported."))

    timeout = handler.get("timeout")
    if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
        diags.append(Diagnostic(path, None, "ERROR", f"Handler under {context} has invalid timeout '{timeout}'. Must be a positive integer."))

    return diags


def check_hooks_json(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError as err:
        diags.append(Diagnostic(path, err.lineno, "ERROR", f"Invalid JSON syntax in hooks file: {err}"))
        return diags

    if not isinstance(data, dict):
        diags.append(Diagnostic(path, 1, "ERROR", "hooks.json must be a top-level JSON object"))
        return diags

    if "hooks" in data:
        diags.append(
            Diagnostic(
                path,
                1,
                "ERROR",
                "Claude-format 'hooks' wrapper detected. Antigravity requires top-level keys to be named hook groups.",
            )
        )
        return diags

    valid_events = {"PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}

    for hook_name, hook_spec in data.items():
        if not isinstance(hook_spec, dict):
            diags.append(Diagnostic(path, None, "ERROR", f"Hook '{hook_name}' must map to a JSON object"))
            continue

        for event_name, handlers in hook_spec.items():
            if event_name == "enabled":
                if not isinstance(handlers, bool):
                    diags.append(Diagnostic(path, None, "ERROR", f"'enabled' field in hook '{hook_name}' must be a boolean"))
                continue

            if event_name not in valid_events:
                diags.append(
                    Diagnostic(
                        path,
                        None,
                        "ERROR",
                        f"Invalid hook event '{event_name}' in hook '{hook_name}'. Valid events: {sorted(valid_events)}",
                    )
                )
                continue

            if event_name in {"PreToolUse", "PostToolUse"}:
                if not isinstance(handlers, list):
                    diags.append(Diagnostic(path, None, "ERROR", f"Event '{event_name}' must be an array of matcher groups"))
                    continue
                for g_idx, group in enumerate(handlers):
                    if not isinstance(group, dict):
                        diags.append(Diagnostic(path, None, "ERROR", f"Group #{g_idx} under '{event_name}' must be a JSON object"))
                        continue
                    matcher = group.get("matcher")
                    if matcher is None or not isinstance(matcher, str):
                        diags.append(Diagnostic(path, None, "ERROR", f"Group #{g_idx} under '{event_name}' missing required string 'matcher'"))
                    else:
                        try:
                            re.compile(matcher)
                        except re.error as err:
                            diags.append(Diagnostic(path, None, "ERROR", f"Invalid matcher regex '{matcher}' under '{event_name}': {err}"))

                    h_list = group.get("hooks")
                    if not isinstance(h_list, list) or not h_list:
                        diags.append(Diagnostic(path, None, "ERROR", f"Group #{g_idx} under '{event_name}' must have a non-empty 'hooks' list"))
                    else:
                        for h_idx, h in enumerate(h_list):
                            diags.extend(_validate_handler(path, h, f"'{hook_name}.{event_name}[{g_idx}].hooks[{h_idx}]'"))
            else:
                # PreInvocation, PostInvocation, Stop are flat arrays of handler objects
                if not isinstance(handlers, list):
                    diags.append(Diagnostic(path, None, "ERROR", f"Event '{event_name}' must be a flat array of handler objects"))
                    continue
                for h_idx, h in enumerate(handlers):
                    diags.extend(_validate_handler(path, h, f"'{hook_name}.{event_name}[{h_idx}]'"))

    return diags


def check_plugin_json(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError as err:
        diags.append(Diagnostic(path, err.lineno, "ERROR", f"Invalid JSON syntax in plugin manifest: {err}"))
        return diags

    if not isinstance(data, dict):
        return [Diagnostic(path, 1, "ERROR", "plugin.json must be a top-level JSON object")]

    name = data.get("name")
    if not name or not isinstance(name, str):
        diags.append(Diagnostic(path, 1, "ERROR", "plugin.json missing required 'name' field"))
    elif not KEBAB_CASE_PATTERN.match(name):
        diags.append(Diagnostic(path, 1, "ERROR", f"plugin.json 'name' ('{name}') must be lowercase kebab-case"))

    desc = data.get("description")
    if not desc or not isinstance(desc, str):
        diags.append(Diagnostic(path, 1, "ERROR", "plugin.json missing required 'description' field"))
    elif len(desc.strip()) < 20:
        diags.append(Diagnostic(path, 1, "ERROR", f"plugin.json 'description' is too short ({len(desc.strip())} chars; min 20 required)"))

    return diags


def check_migration_ledger(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError as err:
        diags.append(Diagnostic(path, err.lineno, "ERROR", f"Invalid JSON syntax in ledger: {err}"))
        return diags

    required_keys = {"version", "last_updated", "summary", "assets"}
    missing = required_keys - set(data.keys())
    if missing:
        diags.append(Diagnostic(path, 1, "ERROR", f"Ledger missing required keys: {sorted(missing)}"))
        return diags

    assets = data.get("assets", [])
    if not isinstance(assets, list):
        return [Diagnostic(path, 1, "ERROR", "'assets' field in ledger must be a list")]

    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        diags.append(Diagnostic(path, 1, "ERROR", "'summary' field in ledger must be a JSON object"))
    else:
        actual_total = len(assets)
        reported_total = summary.get("total")
        if reported_total != actual_total:
            diags.append(Diagnostic(path, 1, "ERROR", f"Summary 'total' ({reported_total}) does not match actual assets count ({actual_total})"))

        status_counts = {"PENDING": 0, "IN_PROGRESS": 0, "ADAPTED": 0, "VALIDATED": 0}
        for a in assets:
            if isinstance(a, dict) and a.get("status") in status_counts:
                status_counts[a["status"]] += 1

        for s_key, s_val in status_counts.items():
            reported_val = summary.get(s_key.lower())
            if reported_val is not None and reported_val != s_val:
                diags.append(Diagnostic(path, 1, "ERROR", f"Summary '{s_key.lower()}' ({reported_val}) does not match actual count ({s_val})"))

    valid_statuses = {"PENDING", "IN_PROGRESS", "ADAPTED", "VALIDATED"}
    seen_ids: set[str] = set()

    # Determine base directory (repo root)
    base_dir = path.parent
    curr = path.parent
    while curr != curr.parent:
        if (curr / ".git").exists() or (curr / ".agents").exists():
            base_dir = curr
            break
        curr = curr.parent

    for idx, asset in enumerate(assets):
        if not isinstance(asset, dict):
            diags.append(Diagnostic(path, None, "ERROR", f"Asset at index {idx} must be a JSON object"))
            continue

        a_id = asset.get("id")
        if not a_id or not isinstance(a_id, str):
            diags.append(Diagnostic(path, None, "ERROR", f"Asset at index {idx} missing required string 'id'"))
        elif a_id in seen_ids:
            diags.append(Diagnostic(path, None, "ERROR", f"Duplicate asset id '{a_id}' at index {idx}"))
        else:
            seen_ids.add(a_id)

        category = asset.get("category")
        if not category or category not in VALID_ASSET_CATEGORIES:
            diags.append(Diagnostic(path, None, "ERROR", f"Asset '{a_id}' has invalid category '{category}'. Valid: {sorted(VALID_ASSET_CATEGORIES)}"))

        status = asset.get("status")
        if status not in valid_statuses:
            diags.append(
                Diagnostic(
                    path,
                    None,
                    "ERROR",
                    f"Asset '{a_id}' has invalid status '{status}'. Must be one of: {sorted(valid_statuses)}",
                )
            )

        source_path = asset.get("source_path")
        if source_path and source_path != "N/A" and isinstance(source_path, str):
            if not (base_dir / source_path).exists():
                diags.append(Diagnostic(path, None, "ERROR", f"Asset '{a_id}' source_path '{source_path}' does not exist on disk"))

        target_path = asset.get("target_path")
        if status == "VALIDATED" and target_path and isinstance(target_path, str):
            if not (base_dir / target_path).exists():
                diags.append(Diagnostic(path, None, "ERROR", f"Asset '{a_id}' marked VALIDATED but target_path '{target_path}' does not exist on disk"))

    return diags


def verify_file(path: Path) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as err:
        return [Diagnostic(path, None, "ERROR", f"Unable to read file: {err}")]

    if path.name == "hooks.json":
        diags.extend(check_hooks_json(path, content))
        return diags

    if path.name == "plugin.json":
        diags.extend(check_plugin_json(path, content))
        return diags

    if path.name == "migration_ledger.json":
        diags.extend(check_migration_ledger(path, content))
        return diags

    if path.suffix == ".md":
        diags.extend(check_frontmatter(path, content))
        diags.extend(check_tools_and_patterns(path, content))
        diags.extend(check_single_line_commands(path, content))

    return diags


def scan_path(target: Path) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if target.is_file():
        return verify_file(target)

    for p in target.rglob("*"):
        if p.is_file():
            if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in p.parts):
                continue
            if p.suffix == ".md" or p.name in {"hooks.json", "plugin.json", "migration_ledger.json"}:
                diags.extend(verify_file(p))

    return diags


def main() -> int:
    parser = argparse.ArgumentParser(description="Antigravity CLI (agy) Compatibility Verifier")
    parser.add_argument("--path", type=str, default=".", help="File or directory to verify")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    target = Path(args.path).resolve()

    if not target.exists():
        if args.json:
            print(json.dumps({"error": f"Target path '{target}' does not exist", "errors": 1, "warnings": 0, "diagnostics": []}, indent=2))
        else:
            print(f"Error: Target path '{target}' does not exist", file=sys.stderr)
        return 2

    diags = scan_path(target)
    errors = [d for d in diags if d.severity == "ERROR"]
    warnings = [d for d in diags if d.severity == "WARNING"]

    if args.json:
        output = {
            "path": str(target),
            "errors": len(errors),
            "warnings": len(warnings),
            "diagnostics": [
                {"path": str(d.path), "line": d.line, "severity": d.severity, "message": d.message}
                for d in diags
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        for d in diags:
            print(str(d))

        if errors:
            print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s) found.", file=sys.stderr)
            return 1
        elif warnings:
            print(f"\nPASSED with {len(warnings)} warning(s).")
        else:
            print(f"All AGY compatibility checks passed for '{target}'.")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
