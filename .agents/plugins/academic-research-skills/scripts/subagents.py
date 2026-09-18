"""Antigravity CLI Subagent definitions for Academic Research Skills.

Provides declarative and programmatic configurations to define and invoke
specialized academic research subagents using Antigravity CLI APIs.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

AGENTS_DIR = (Path(__file__).resolve().parent.parent / "agents").resolve()


def load_agent_spec(filename: str) -> tuple[Dict[str, Any], str]:
    """Load agent frontmatter and system prompt, preventing directory traversal."""
    target_path = (AGENTS_DIR / filename).resolve()
    if not target_path.is_relative_to(AGENTS_DIR):
        raise ValueError(f"Access denied: path '{filename}' escapes agents directory.")
    if not target_path.exists() or not target_path.is_file():
        raise FileNotFoundError(f"Agent definition '{filename}' not found or is not a regular file at {target_path}")

    content = target_path.read_text(encoding="utf-8")
    match = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)
    if len(match) >= 3:
        raw_fm, prompt = match[1], match[2]
        # Parse basic frontmatter key-values
        meta: Dict[str, Any] = {}
        for line in raw_fm.splitlines():
            line_str = line.strip()
            if ":" in line_str and not line_str.startswith("#"):
                k, v = line_str.split(":", 1)
                # Strip inline comments and quotes
                clean_v = v.split("#")[0].strip().strip('"').strip("'")
                meta[k.strip()] = clean_v
        return meta, prompt.strip()
    return {}, content.strip()


def parse_bool_meta(meta: Dict[str, Any], key: str, default: bool = False) -> bool:
    """Parse a boolean metadata flag cleanly from frontmatter key."""
    val = meta.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).split("#")[0].strip().lower() in ("true", "1", "yes")


def load_agent_prompt(filename: str) -> str:
    """Return stripped system prompt for an agent."""
    _, prompt = load_agent_spec(filename)
    return prompt


def get_synthesis_subagent_def() -> Dict[str, Any]:
    """Return dictionary matching define_subagent parameters for synthesis-agent."""
    meta, prompt = load_agent_spec("synthesis-agent.md")
    return {
        "name": meta.get("name", "synthesis-agent"),
        "description": meta.get(
            "description",
            "Integrates findings across sources, resolves evidence conflicts, and maps knowledge gaps",
        ),
        "system_prompt": prompt,
        "enable_write_tools": parse_bool_meta(meta, "enable_write_tools", default=True),
        "enable_subagent_tools": parse_bool_meta(meta, "enable_subagent_tools", default=False),
        "enable_mcp_tools": parse_bool_meta(meta, "enable_mcp_tools", default=False),
    }


def get_synthesis_subagent_invocation(prompt: str, model: str = "inherit") -> Dict[str, Any]:
    """Return invocation dictionary for invoke_subagent with isolated workspace."""
    meta, _ = load_agent_spec("synthesis-agent.md")
    return {
        "TypeName": meta.get("name", "synthesis-agent"),
        "Role": "Evidence Synthesis Specialist",
        "Prompt": prompt,
        "Model": model,
        "Workspace": "branch",
    }


def get_report_compiler_subagent_def() -> Dict[str, Any]:
    """Return dictionary matching define_subagent parameters for report-compiler-agent."""
    meta, prompt = load_agent_spec("report-compiler-agent.md")
    return {
        "name": meta.get("name", "report-compiler-agent"),
        "description": meta.get(
            "description",
            "Transforms research findings and section plans into polished APA 7.0 academic manuscripts and reports",
        ),
        "system_prompt": prompt,
        "enable_write_tools": parse_bool_meta(meta, "enable_write_tools", default=True),
        "enable_subagent_tools": parse_bool_meta(meta, "enable_subagent_tools", default=False),
        "enable_mcp_tools": parse_bool_meta(meta, "enable_mcp_tools", default=False),
    }


def get_report_compiler_subagent_invocation(prompt: str, model: str = "inherit") -> Dict[str, Any]:
    """Return invocation dictionary for invoke_subagent with isolated workspace."""
    meta, _ = load_agent_spec("report-compiler-agent.md")
    return {
        "TypeName": meta.get("name", "report-compiler-agent"),
        "Role": "APA 7.0 Report Compiler",
        "Prompt": prompt,
        "Model": model,
        "Workspace": "branch",
    }


def get_peer_reviewer_subagent_def() -> Dict[str, Any]:
    """Return dictionary matching define_subagent parameters for peer-reviewer-agent."""
    meta, prompt = load_agent_spec("peer-reviewer-agent.md")
    return {
        "name": meta.get("name", "peer-reviewer-agent"),
        "description": meta.get(
            "description",
            "Simulates rigorous double-blind peer review across five dimensions, flagging soundness and empirical gaps",
        ),
        "system_prompt": prompt,
        "enable_write_tools": parse_bool_meta(meta, "enable_write_tools", default=True),
        "enable_subagent_tools": parse_bool_meta(meta, "enable_subagent_tools", default=False),
        "enable_mcp_tools": parse_bool_meta(meta, "enable_mcp_tools", default=False),
    }


def get_peer_reviewer_subagent_invocation(prompt: str, model: str = "inherit") -> Dict[str, Any]:
    """Return invocation dictionary for invoke_subagent with isolated workspace."""
    meta, _ = load_agent_spec("peer-reviewer-agent.md")
    return {
        "TypeName": meta.get("name", "peer-reviewer-agent"),
        "Role": "Academic Peer Reviewer",
        "Prompt": prompt,
        "Model": model,
        "Workspace": "branch",
    }


def get_editorial_synthesizer_subagent_def() -> Dict[str, Any]:
    """Return dictionary matching define_subagent parameters for editorial-synthesizer-agent."""
    meta, prompt = load_agent_spec("editorial-synthesizer-agent.md")
    return {
        "name": meta.get("name", "editorial-synthesizer-agent"),
        "description": meta.get(
            "description",
            "Synthesizes multi-perspective reviewer reports into unified editorial decisions and revision roadmaps",
        ),
        "system_prompt": prompt,
        "enable_write_tools": parse_bool_meta(meta, "enable_write_tools", default=True),
        "enable_subagent_tools": parse_bool_meta(meta, "enable_subagent_tools", default=False),
        "enable_mcp_tools": parse_bool_meta(meta, "enable_mcp_tools", default=False),
    }


def get_editorial_synthesizer_subagent_invocation(prompt: str, model: str = "inherit") -> Dict[str, Any]:
    """Return invocation dictionary for invoke_subagent with isolated workspace."""
    meta, _ = load_agent_spec("editorial-synthesizer-agent.md")
    return {
        "TypeName": meta.get("name", "editorial-synthesizer-agent"),
        "Role": "Editorial Decision Synthesizer",
        "Prompt": prompt,
        "Model": model,
        "Workspace": "branch",
    }


def get_revision_coach_subagent_def() -> Dict[str, Any]:
    """Return dictionary matching define_subagent parameters for revision-coach-agent."""
    meta, prompt = load_agent_spec("revision-coach-agent.md")
    return {
        "name": meta.get("name", "revision-coach-agent"),
        "description": meta.get(
            "description",
            "Parses reviewer comments, plans revision strategies, and audits rebuttal response drafts",
        ),
        "system_prompt": prompt,
        "enable_write_tools": parse_bool_meta(meta, "enable_write_tools", default=True),
        "enable_subagent_tools": parse_bool_meta(meta, "enable_subagent_tools", default=False),
        "enable_mcp_tools": parse_bool_meta(meta, "enable_mcp_tools", default=False),
    }


def get_revision_coach_subagent_invocation(prompt: str, model: str = "inherit") -> Dict[str, Any]:
    """Return invocation dictionary for invoke_subagent with isolated workspace."""
    meta, _ = load_agent_spec("revision-coach-agent.md")
    return {
        "TypeName": meta.get("name", "revision-coach-agent"),
        "Role": "Rebuttal and Revision Coach",
        "Prompt": prompt,
        "Model": model,
        "Workspace": "branch",
    }


