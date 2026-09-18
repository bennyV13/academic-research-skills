"""Antigravity CLI Subagent definitions for Academic Research Skills.

Provides declarative and programmatic configurations to define and invoke
specialized academic research subagents using Antigravity CLI APIs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


def load_agent_prompt(filename: str) -> str:
    agent_path = AGENTS_DIR / filename
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent definition '{filename}' not found at {agent_path}")
    content = agent_path.read_text(encoding="utf-8")
    # Return body after YAML frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


def get_synthesis_subagent_def() -> Dict[str, Any]:
    """Return dictionary matching define_subagent parameters for synthesis-agent."""
    return {
        "name": "synthesis-agent",
        "description": "Integrates findings across sources, resolves evidence conflicts, and maps knowledge gaps",
        "system_prompt": load_agent_prompt("synthesis-agent.md"),
        "enable_write_tools": True,
        "enable_subagent_tools": False,
        "enable_mcp_tools": False,
    }


def get_synthesis_subagent_invocation(prompt: str, model: str = "inherit") -> Dict[str, Any]:
    """Return invocation dictionary for invoke_subagent."""
    return {
        "TypeName": "synthesis-agent",
        "Role": "Evidence Synthesis Specialist",
        "Prompt": prompt,
        "Model": model,
        "Workspace": "inherit",
    }
