#!/usr/bin/env python3
"""Antigravity CLI (agy) Compatibility Verifier and Linter.

Audits skills, commands, agents, hooks, and migration ledgers to ensure
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
    r"\b(Bash|Edit|Write|Read|Task|AskUser|AskFollowupQuestion)\s*\(",
    re.IGNORECASE,
)
DEPRECATED_CLAUDE_ENVS = re.compile(
    r"\$\{?CLAUDE_(PLUGIN_ROOT|PROJECT_DIR)\}?",
)
DEPRECATED_CLAUDE_COMMANDS = re.compile(
    r"(?<![a-zA-Z0-9_-])/compact\b",
)
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FORBIDDEN_CLAUDE_FRONTMATTER_FIELDS = {
    "disable-model-invocation",
    "argument-hint",
}


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
            val = val.strip()
            if val in (">-", ">", "|", "|-"):
                multi_line_val = []
            elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                data[current_key] = val[1:-1]
                current_key = None
            elif val.lower() == "true":
                data[current_key] = True
                current_key = None
            elif val.lower() == "false":
                data[current_key] = False
                current_key = None
            elif val:
                data[current_key] = val
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
    if model and isinstance(model, str) and model.lower() in {"sonnet", "opus", "haiku"}:
        diags.append(
            Diagnostic(
                path,
                1,
                "ERROR",
                f"Forbidden Claude-specific model '{model}' in frontmatter; use AGY model tiers ('inherit', 'flash', 'pro')",
            )
        )

    return diags


def check_tools_and_patterns(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        if FORBIDDEN_CLAUDE_TOOLS.search(line):
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
                    f"Deprecated Claude session command detected (/compact). Antigravity uses large context windows and subagents.",
                )
            )

    return diags


def check_single_line_commands(path: Path, content: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    lines = content.splitlines()

    in_bash_block = False
    block_start_line = 0
    code_lines: list[tuple[int, str]] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```bash") or stripped.startswith("```sh"):
            in_bash_block = True
            block_start_line = idx
            code_lines = []
        elif in_bash_block and stripped == "```":
            in_bash_block = False
            # Filter out comments and blank lines
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
                continue
            if event_name not in valid_events:
                diags.append(
                    Diagnostic(
                        path,
                        None,
                        "WARNING",
                        f"Unknown hook event '{event_name}' in hook '{hook_name}'. Valid events: {sorted(valid_events)}",
                    )
                )
                continue

            if event_name in {"PreToolUse", "PostToolUse"}:
                if not isinstance(handlers, list):
                    diags.append(Diagnostic(path, None, "ERROR", f"Event '{event_name}' must be an array of matcher groups"))
                    continue
                for group in handlers:
                    if not isinstance(group, dict) or "matcher" not in group or "hooks" not in group:
                        diags.append(
                            Diagnostic(
                                path,
                                None,
                                "ERROR",
                                f"Group under '{event_name}' in hook '{hook_name}' must have 'matcher' and 'hooks'",
                            )
                        )

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
        diags.append(Diagnostic(path, 1, "ERROR", "'assets' field in ledger must be a list"))
        return diags

    valid_statuses = {"PENDING", "IN_PROGRESS", "ADAPTED", "VALIDATED"}
    for idx, asset in enumerate(assets):
        if not isinstance(asset, dict):
            diags.append(Diagnostic(path, None, "ERROR", f"Asset at index {idx} must be a JSON object"))
            continue
        status = asset.get("status")
        if status not in valid_statuses:
            diags.append(
                Diagnostic(
                    path,
                    None,
                    "ERROR",
                    f"Asset '{asset.get('id', idx)}' has invalid status '{status}'. Must be one of: {sorted(valid_statuses)}",
                )
            )

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
            # Skip VCS and cache directories
            if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in p.parts):
                continue
            if p.suffix == ".md" or p.name in {"hooks.json", "migration_ledger.json"}:
                diags.extend(verify_file(p))

    return diags


def main() -> int:
    parser = argparse.ArgumentParser(description="Antigravity CLI (agy) Compatibility Verifier")
    parser.add_argument("--path", type=str, default=".", help="File or directory to verify")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    target = Path(args.path).resolve()

    if not target.exists():
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
