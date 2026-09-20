#!/usr/bin/env python3
"""ARS Deterministic Report Path Allocator.

Allocates sequentially numbered report file paths within dated folders
under `reports/ars/YYYY-MM-DD/`.

Can be used as:
  1. CLI tool:
     python3 scripts/allocate_report_path.py "Literature Review"
     python3 scripts/allocate_report_path.py --title "Methodology" --json
  2. Python module:
     from scripts.allocate_report_path import allocate_report_path
     path = allocate_report_path("My Topic")
  3. Antigravity CLI PreToolUse hook (--stdin-hook):
     Reads AGY protojson payload on stdin, rewrites TargetFile to canonical
     numbered path in reports/ars/YYYY-MM-DD/ via `overwrite`.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPORTS_SUBDIR = os.path.join("reports", "ars")
SEQ_FILE_PATTERN = re.compile(r"^(\d+)_([^\.]+)\.([a-zA-Z0-9]+)$")
CANONICAL_PATH_PATTERN = re.compile(
    r"^reports/ars/(\d{4}-\d{2}-\d{2})/(\d{2,})_([^\./]+)\.([a-zA-Z0-9]+)$"
)


def find_workspace_root(start_dir: Optional[str] = None) -> Path:
    """Find the root of the workspace by locating .git or .agents markers."""
    env_root = os.environ.get("WORKSPACE_ROOT")
    if env_root and os.path.isdir(env_root):
        return Path(env_root).resolve()

    current = Path(start_dir or os.getcwd()).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").is_dir() or (parent / ".agents").is_dir():
            return parent
    return current


def slugify(text: str, max_length: int = 60) -> str:
    """Normalize text into a filesystem-safe snake_case slug."""
    if not text:
        return "report"
    # Remove file extension if present
    base, _ = os.path.splitext(text)
    clean = base if base.strip() else text

    # Strip non-alphanumeric characters (keep alphanumeric, space, hyphens, underscores)
    clean = re.sub(r"[^\w\s-]", "", clean.lower())
    # Replace whitespace and hyphens with single underscore
    clean = re.sub(r"[-\s]+", "_", clean).strip("_")

    if not clean:
        clean = "report"

    if len(clean) > max_length:
        clean = clean[:max_length].rstrip("_")

    return clean or "report"


def get_next_sequence_number(dated_dir: Path) -> int:
    """Inspect directory and return next 1-based sequential number."""
    if not dated_dir.exists():
        return 1

    highest = 0
    try:
        for entry in os.scandir(dated_dir):
            if not entry.is_file():
                continue
            m = SEQ_FILE_PATTERN.match(entry.name)
            if m:
                try:
                    num = int(m.group(1))
                    if num > highest:
                        highest = num
                except ValueError:
                    continue
    except OSError:
        return 1

    return highest + 1


def format_sequence_prefix(seq_num: int) -> str:
    """Format sequence number with leading zeros (at least 2 digits)."""
    return f"{seq_num:02d}" if seq_num < 100 else str(seq_num)


def allocate_report_path(
    title: str,
    workspace_root: Optional[Path] = None,
    date_str: Optional[str] = None,
    ext: str = "md",
    ensure_dir: bool = True,
) -> Path:
    """Allocate a deterministic, sequentially numbered path for an ARS report."""
    root = (workspace_root or find_workspace_root()).resolve()
    target_date = date_str or datetime.date.today().isoformat()
    dated_dir = root / REPORTS_SUBDIR / target_date

    if ensure_dir:
        dated_dir.mkdir(parents=True, exist_ok=True)

    seq_num = get_next_sequence_number(dated_dir)
    seq_prefix = format_sequence_prefix(seq_num)
    slug = slugify(title)
    clean_ext = ext.lstrip(".") or "md"

    filename = f"{seq_prefix}_{slug}.{clean_ext}"
    return dated_dir / filename


def evaluate_report_tool_call(
    payload: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Inspect AGY tool payload and return AGY decision JSON with optional overwrite."""
    if not isinstance(payload, dict):
        return {"decision": "allow"}

    # Extract tool name & arguments
    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict):
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})
    else:
        tool_name = payload.get("tool_name", "")
        args = payload.get("tool_input", {})

    if tool_name != "write_to_file":
        return {"decision": "allow"}

    raw_target = (
        args.get("TargetFile")
        or args.get("target_file")
        or args.get("targetFile")
        or args.get("file_path")
    )
    if not raw_target or not isinstance(raw_target, str) or not raw_target.strip():
        return {"decision": "allow"}

    raw_path = raw_target.strip()

    # Determine workspace root
    ws_paths = payload.get("workspacePaths") or []
    if ws_paths:
        root = Path(ws_paths[0]).resolve()
    else:
        root = (workspace_root or find_workspace_root()).resolve()

    cwd = args.get("Cwd") or payload.get("cwd") or str(root)
    full_target = Path(raw_path) if os.path.isabs(raw_path) else (Path(cwd) / raw_path).resolve()

    # Check relative path to workspace root
    try:
        rel_target = str(full_target.relative_to(root)).replace("\\", "/")
    except ValueError:
        return {"decision": "allow"}

    agent_type = str(
        payload.get("agent_type")
        or payload.get("agentName")
        or payload.get("role")
        or payload.get("subagent")
        or payload.get("TypeName")
        or ""
    ).strip().lower().replace("-", "_")

    is_report_compiler = "report_compiler" in agent_type
    is_ars_report_dir = rel_target.startswith("reports/ars/")
    is_general_reports_dir = (
        rel_target.startswith("reports/") and not rel_target.startswith("reports/agy-adaptation/")
    )

    should_route = is_ars_report_dir or (is_report_compiler and not rel_target.startswith(".gemini")) or (
        is_general_reports_dir and not is_ars_report_dir
    )

    if not should_route:
        return {"decision": "allow"}

    # Check if target already satisfies canonical numbered format: reports/ars/YYYY-MM-DD/NN_slug.ext
    m = CANONICAL_PATH_PATTERN.match(rel_target)
    if m:
        # Already canonical, ensure directory exists and allow
        full_target.parent.mkdir(parents=True, exist_ok=True)
        return {"decision": "allow"}

    # Extract title and extension from intended target filename
    target_filename = full_target.name
    base_name, file_ext = os.path.splitext(target_filename)
    clean_ext = file_ext.lstrip(".") or "md"

    # Allocate next sequence path
    allocated = allocate_report_path(
        title=base_name,
        workspace_root=root,
        ext=clean_ext,
        ensure_dir=True,
    )

    return {
        "decision": "allow",
        "overwrite": {
            "TargetFile": str(allocated),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ARS Deterministic Report Path Allocator")
    parser.add_argument("title", nargs="?", default=None, help="Report title or topic")
    parser.add_argument("-t", "--title-opt", dest="opt_title", help="Explicit title option")
    parser.add_argument("-e", "--ext", default="md", help="File extension (default: md)")
    parser.add_argument("-d", "--date", default=None, help="Date override (YYYY-MM-DD)")
    parser.add_argument("-w", "--workspace", default=None, help="Workspace root directory")
    parser.add_argument("--json", action="store_true", help="Output details as JSON")
    parser.add_argument("--stdin-hook", action="store_true", help="Run as Antigravity PreToolUse hook")

    args = parser.parse_args()

    if args.stdin_hook:
        try:
            raw = sys.stdin.read()
            if not raw.strip():
                print(json.dumps({"decision": "allow"}))
                return 0
            payload = json.loads(raw)
        except Exception:
            print(json.dumps({"decision": "allow"}))
            return 0

        decision = evaluate_report_tool_call(payload)
        print(json.dumps(decision))
        return 0

    chosen_title = args.opt_title or args.title or "report"
    ws = Path(args.workspace).resolve() if args.workspace else find_workspace_root()

    allocated = allocate_report_path(
        title=chosen_title,
        workspace_root=ws,
        date_str=args.date,
        ext=args.ext,
        ensure_dir=True,
    )

    if args.json:
        target_date = args.date or datetime.date.today().isoformat()
        dated_dir = ws / REPORTS_SUBDIR / target_date
        m = SEQ_FILE_PATTERN.match(allocated.name)
        seq_num = int(m.group(1)) if m else 1
        seq_str = format_sequence_prefix(seq_num)
        slug = m.group(2) if m else slugify(chosen_title)

        data = {
            "workspace_root": str(ws),
            "date": target_date,
            "seq": seq_num,
            "seq_str": seq_str,
            "slug": slug,
            "filename": allocated.name,
            "dir": str(dated_dir),
            "path": str(allocated),
        }
        print(json.dumps(data, indent=2))
    else:
        print(str(allocated))

    return 0


if __name__ == "__main__":
    sys.exit(main())
