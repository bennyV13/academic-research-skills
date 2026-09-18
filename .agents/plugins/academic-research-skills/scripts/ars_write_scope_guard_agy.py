#!/usr/bin/env python3
"""ARS write-scope guard — Antigravity CLI PreToolUse hook adapter.

Enforces deterministic write-scope boundaries for single-phase Bucket A subagents
and infrastructure self-protection under Google Antigravity CLI (agy).

Interprets AGY protojson tool payloads on stdin and emits standard AGY decision JSON:
  {"decision": "allow"}
  {"decision": "deny", "reason": "..."}
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MANIFEST_FILENAME = "ars_phase_scope_manifest.json"

# AGY file modification tools and command execution
STRUCTURED_WRITE_TOOLS = {
    "write_to_file",
    "replace_file_content",
    "Write",
    "Edit",
    "MultiEdit",
}
SHELL_TOOLS = {"run_command", "Bash"}
INSPECTED_TOOLS = STRUCTURED_WRITE_TOOLS | SHELL_TOOLS

INFRA_PROTECTED_GLOBS = [
    "hooks.json",
    "hooks/*.sh",
    "plugin.json",
    ".claude-plugin/plugin.json",
    "**/ars_write_scope_guard*.py",
    "ars_write_scope_guard*.py",
    "**/ars_phase_scope_manifest.json",
    "ars_phase_scope_manifest.json",
    "agents/*.md",
    "**/agents/*.md",
]


def _normalize_target(raw_path: str, cwd: str, workspace_root: str) -> Tuple[Optional[str], bool]:
    """Resolve target path relative to workspace_root. Returns (rel_path, escaped)."""
    if not os.path.isabs(raw_path):
        raw_path = os.path.join(cwd, raw_path)
    normalized = os.path.realpath(raw_path)
    real_ws = os.path.realpath(workspace_root)
    try:
        common = os.path.commonpath([normalized, real_ws])
    except ValueError:
        return None, True
    if common != real_ws:
        return None, True
    rel = os.path.relpath(normalized, real_ws)
    if rel == ".":
        return None, True
    return rel, False


def _match_segments(path_segs: List[str], pat_segs: List[str]) -> bool:
    """Path-segment-aware glob match."""
    n, m = len(path_segs), len(pat_segs)
    stack = [(0, 0)]
    seen = set()
    while stack:
        i, j = stack.pop()
        if (i, j) in seen:
            continue
        seen.add((i, j))
        if j == m:
            if i == n:
                return True
            continue
        head = pat_segs[j]
        if head == "**":
            if i < n:
                stack.append((i + 1, j + 1))
                stack.append((i + 1, j))
            continue
        if i < n and fnmatch.fnmatch(path_segs[i], head):
            stack.append((i + 1, j + 1))
    return False


def _matches_any(rel_path: str, globs: List[str]) -> bool:
    """Workspace-root-anchored glob match against normalized relative path."""
    if os.sep == "\\":
        rel_path = rel_path.replace("\\", "/")
    segs = [s for s in rel_path.split("/") if s not in ("", ".")]
    for g in globs:
        pat = [s for s in g.split("/") if s != ""]
        if _match_segments(segs, pat):
            return True
    return False


def _infra_protected_target(raw_path: str, cwd: str, plugin_root: Optional[str]) -> bool:
    """Check if target resolves to plugin infrastructure enforcement files."""
    if not plugin_root:
        return False
    rp = raw_path
    if not os.path.isabs(rp):
        rp = os.path.join(cwd, rp)
    normalized = os.path.realpath(rp)
    real_plugin = os.path.realpath(plugin_root)
    try:
        common = os.path.commonpath([normalized, real_plugin])
    except ValueError:
        return False
    if common != real_plugin:
        return False
    rel = os.path.relpath(normalized, real_plugin)
    if rel == ".":
        return False
    return _matches_any(rel, INFRA_PROTECTED_GLOBS)


def extract_agy_payload(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Optional[str], List[str]]:
    """Extract tool name, args, agent identity, and workspace paths from AGY payload."""
    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict):
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})
    else:
        tool_name = payload.get("tool_name", "")
        args = payload.get("tool_input", {})

    agent_type = (
        payload.get("agent_type")
        or payload.get("agentName")
        or payload.get("role")
        or payload.get("subagent")
        or payload.get("TypeName")
    )
    workspace_paths = payload.get("workspacePaths") or []
    if isinstance(workspace_paths, str):
        workspace_paths = [workspace_paths]

    return tool_name, args, agent_type, workspace_paths


def evaluate_agy_decision(
    payload: Dict[str, Any],
    manifest: Dict[str, Any],
    workspace_root: str,
    plugin_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Pure decision function evaluating AGY tool execution against write-scope rules."""
    if not isinstance(payload, dict):
        return {"decision": "allow"}

    tool_name, args, agent_type, workspace_paths = extract_agy_payload(payload)
    if workspace_paths:
        workspace_root = workspace_paths[0]

    cwd = args.get("Cwd") or payload.get("cwd") or workspace_root
    if not plugin_root:
        plugin_root = workspace_root

    # Uninspected tools pass through automatically
    if tool_name not in INSPECTED_TOOLS:
        return {"decision": "allow"}

    agents = (manifest or {}).get("agents", {})
    # Normalize agent_type name: handle hyphens vs underscores (e.g. synthesis-agent vs synthesis_agent)
    canonical_agent = None
    if agent_type:
        alt_agent = agent_type.replace("-", "_")
        if agent_type in agents:
            canonical_agent = agent_type
        elif alt_agent in agents:
            canonical_agent = alt_agent

    is_bucket_a = canonical_agent is not None

    # Shell execution gating
    if tool_name in SHELL_TOOLS:
        if is_bucket_a:
            return {
                "decision": "deny",
                "reason": (
                    f"ARS write-scope guard: {agent_type} (a single-phase Bucket A agent) "
                    "may not execute shell commands directly. Use native file and search tools instead."
                ),
            }
        return {"decision": "allow"}

    # Structured write tools gating
    raw_path = (
        args.get("TargetFile")
        or args.get("target_file")
        or args.get("targetFile")
        or args.get("file_path")
    )
    if not raw_path or not isinstance(raw_path, str):
        return {
            "decision": "deny",
            "reason": (
                f"ARS write-scope guard: {tool_name} carried no TargetFile/file_path parameter "
                "— denying execution to avoid silent fail-open."
            ),
        }

    # Step 1: Infrastructure self-protection (plugin enforcement files)
    if _infra_protected_target(raw_path, cwd, plugin_root):
        return {
            "decision": "deny",
            "reason": (
                f"ARS write-scope guard: target '{raw_path}' is part of the ARS plugin enforcement "
                "infrastructure and may not be modified by any agent."
            ),
        }

    # Step 2: Normalize target against workspace root & check path traversal
    rel, escaped = _normalize_target(raw_path, cwd, workspace_root)
    if escaped:
        if is_bucket_a:
            return {
                "decision": "deny",
                "reason": (
                    f"ARS write-scope guard: {agent_type} write target {raw_path!r} escapes the "
                    "workspace root (path traversal violation) — denied."
                ),
            }
        return {"decision": "allow"}

    # Step 3: Unconstrained actor (main session / un-fenced agents)
    if not is_bucket_a:
        return {"decision": "allow"}

    # Step 4: Bucket A allowed globs verification
    allowed = agents[canonical_agent].get("allowed_write_globs", [])
    if not _matches_any(rel, allowed):
        return {
            "decision": "deny",
            "reason": (
                f"ARS write-scope guard: {agent_type} may not write to '{rel}' "
                f"(outside declared allowed_write_globs {allowed})."
            ),
        }

    return {"decision": "allow"}


def load_scope_manifest() -> Dict[str, Any]:
    """Load scope manifest from plugin scripts or repo root."""
    candidate_paths = [
        Path(__file__).resolve().parent / MANIFEST_FILENAME,
        Path(__file__).resolve().parents[2] / "scripts" / MANIFEST_FILENAME,
        Path(__file__).resolve().parents[3] / "scripts" / MANIFEST_FILENAME,
    ]
    for p in candidate_paths:
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {"version": 1, "agents": {}}


def main() -> int:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return 0
        payload = json.loads(raw_input)
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return 0

    if not isinstance(payload, dict):
        print(json.dumps({"decision": "allow"}))
        return 0

    workspace_paths = payload.get("workspacePaths") or []
    workspace_root = workspace_paths[0] if workspace_paths else payload.get("cwd") or os.getcwd()
    plugin_root = os.environ.get("AGY_PLUGIN_ROOT") or str(Path(__file__).resolve().parents[1])

    manifest = load_scope_manifest()
    decision = evaluate_agy_decision(payload, manifest, workspace_root, plugin_root)
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
