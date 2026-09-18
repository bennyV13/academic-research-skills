"""Integration test for Deep Research & Synthesis Subagent Tracer (Ticket #02 / Issue #3)."""
from __future__ import annotations

import unittest
from pathlib import Path

import importlib.util
from scripts.verify_agy_compatibility import scan_path

_SUBAGENTS_PATH = Path(__file__).resolve().parent.parent / ".agents" / "plugins" / "academic-research-skills" / "scripts" / "subagents.py"
_spec = importlib.util.spec_from_file_location("subagents_module", _SUBAGENTS_PATH)
_subagents = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(_subagents)  # type: ignore
get_synthesis_subagent_def = _subagents.get_synthesis_subagent_def
get_synthesis_subagent_invocation = _subagents.get_synthesis_subagent_invocation


class TestDeepResearchSynthesisIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.plugin_dir = cls.repo_root / ".agents" / "plugins" / "academic-research-skills"

    def test_assets_exist(self) -> None:
        expected_paths = [
            self.plugin_dir / "skills" / "deep-research" / "SKILL.md",
            self.plugin_dir / "agents" / "synthesis-agent.md",
            self.plugin_dir / "skills" / "ars-lit-review" / "SKILL.md",
            self.plugin_dir / "skills" / "ars-cache-invalidate" / "SKILL.md",
            self.plugin_dir / "scripts" / "subagents.py",
        ]
        for p in expected_paths:
            self.assertTrue(p.exists(), f"Expected asset missing: {p}")

    def test_synthesis_subagent_definitions(self) -> None:
        subagent_def = get_synthesis_subagent_def()
        self.assertEqual(subagent_def["name"], "synthesis-agent")
        self.assertTrue(subagent_def["enable_write_tools"])
        self.assertFalse(subagent_def["enable_subagent_tools"])
        self.assertIn("Synthesis Agent", subagent_def["system_prompt"])

        invocation = get_synthesis_subagent_invocation("Synthesize findings on AI in education")
        self.assertEqual(invocation["TypeName"], "synthesis-agent")
        self.assertEqual(invocation["Role"], "Evidence Synthesis Specialist")
        self.assertEqual(invocation["Model"], "inherit")
        self.assertEqual(invocation["Workspace"], "inherit")

    def test_compatibility_clean(self) -> None:
        target_skills = [
            self.plugin_dir / "skills" / "deep-research",
            self.plugin_dir / "agents" / "synthesis-agent.md",
            self.plugin_dir / "skills" / "ars-lit-review",
            self.plugin_dir / "skills" / "ars-cache-invalidate",
        ]
        for target in target_skills:
            diags = scan_path(target)
            errors = [d for d in diags if d.severity == "ERROR"]
            self.assertEqual(len(errors), 0, f"Errors in {target}: {errors}")


if __name__ == "__main__":
    unittest.main()
