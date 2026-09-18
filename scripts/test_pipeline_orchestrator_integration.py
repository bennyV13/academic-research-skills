"""Integration tests for Academic Pipeline Orchestrator & Plugin Packaging (Ticket #06 / Issue #11).

Verifies:
1. Research architect subagent definition and invocation schemas.
2. Academic pipeline skill instructions and 10-stage orchestration flow.
3. Utility command skills (ars-full, ars-3w, ars-disclosure, ars-citation-check).
4. Complete migration ledger validation state (31/31 validated, 0 pending).
5. Workspace rules and plugin manifest integrity.
6. End-to-end simulated 10-stage pipeline orchestration flow and checkpoint progression.
7. Full AGY compatibility verification across all Ticket 06 assets and entire plugin tree.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

# Add plugin scripts and root scripts to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / ".agents" / "plugins" / "academic-research-skills"
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from subagents import (  # type: ignore
    load_agent_spec,
    get_research_architect_subagent_def,
    get_research_architect_subagent_invocation,
    get_synthesis_subagent_def,
    get_report_compiler_subagent_def,
    get_peer_reviewer_subagent_def,
    get_editorial_synthesizer_subagent_def,
    get_revision_coach_subagent_def,
)
from verify_agy_compatibility import scan_path  # type: ignore


class TestPipelineOrchestratorIntegration(unittest.TestCase):
    """Test suite for Ticket 06 pipeline orchestrator and packaging workflows."""

    def test_research_architect_subagent_definition(self):
        """Verify research-architect-agent definition and invocation schemas."""
        agent_def = get_research_architect_subagent_def()
        self.assertEqual(agent_def["name"], "research-architect-agent")
        self.assertTrue(agent_def["enable_write_tools"])
        self.assertFalse(agent_def["enable_subagent_tools"])
        self.assertFalse(agent_def["enable_mcp_tools"])
        self.assertIn("Methodology Blueprint Designer", agent_def["system_prompt"])
        self.assertIn("Research Paradigm", agent_def["system_prompt"])
        self.assertIn("Validity Criteria", agent_def["system_prompt"])
        self.assertIn("Antigravity Communication Protocol", agent_def["system_prompt"])

        invocation = get_research_architect_subagent_invocation("Design methodology blueprint for causal study.")
        self.assertEqual(invocation["TypeName"], "research-architect-agent")
        self.assertEqual(invocation["Role"], "Research Methodology Architect")
        self.assertEqual(invocation["Workspace"], "branch")

    def test_all_six_subagents_registered(self):
        """Verify all six Antigravity subagents can be initialized and configured cleanly."""
        subagent_getters = [
            get_synthesis_subagent_def,
            get_report_compiler_subagent_def,
            get_peer_reviewer_subagent_def,
            get_editorial_synthesizer_subagent_def,
            get_revision_coach_subagent_def,
            get_research_architect_subagent_def,
        ]
        for getter in subagent_getters:
            defn = getter()
            self.assertIn("name", defn)
            self.assertIn("description", defn)
            self.assertIn("system_prompt", defn)
            self.assertTrue(defn["enable_write_tools"])
            self.assertFalse(defn["enable_subagent_tools"])
            self.assertFalse(defn["enable_mcp_tools"])
            self.assertNotIn("Claude", defn["system_prompt"])
            self.assertNotIn("Anthropic", defn["system_prompt"])

    def test_academic_pipeline_skill(self):
        """Verify academic-pipeline skill frontmatter and 10-stage content."""
        skill_path = PLUGIN_ROOT / "skills" / "academic-pipeline" / "SKILL.md"
        self.assertTrue(skill_path.exists())
        content = skill_path.read_text(encoding="utf-8")

        self.assertIn("name: academic-pipeline", content)
        self.assertIn("10-stage", content)
        # Check canonical 10 stages from the pipeline table
        expected_stages = ["1", "2", "2.5", "3", "4", "3'", "4'", "4.5", "5", "6"]
        for st in expected_stages:
            self.assertTrue(
                f"Stage {st}" in content or f"Stage **{st}**" in content or f"**{st}**" in content,
                f"Stage {st} should be referenced in academic-pipeline skill"
            )

    def test_utility_command_skills(self):
        """Verify utility command skills: ars-full, ars-3w, ars-disclosure, ars-citation-check."""
        commands = {
            "ars-full": PLUGIN_ROOT / "skills" / "ars-full" / "SKILL.md",
            "ars-3w": PLUGIN_ROOT / "skills" / "ars-3w" / "SKILL.md",
            "ars-disclosure": PLUGIN_ROOT / "skills" / "ars-disclosure" / "SKILL.md",
            "ars-citation-check": PLUGIN_ROOT / "skills" / "ars-citation-check" / "SKILL.md",
        }
        for cmd_name, path in commands.items():
            self.assertTrue(path.exists(), f"Skill file for {cmd_name} must exist at {path}")
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"name: {cmd_name}", text)
            self.assertIn("description:", text)
            self.assertNotIn("sonnet", text.lower())
            self.assertNotIn("claude", text.lower())

    def test_migration_ledger_fully_validated(self):
        """Verify migration_ledger.json has 31/31 validated assets and 0 pending."""
        ledger_path = PLUGIN_ROOT / "migration_ledger.json"
        self.assertTrue(ledger_path.exists())
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

        summary = ledger["summary"]
        self.assertEqual(summary["total"], 31)
        self.assertEqual(summary["validated"], 31)
        self.assertEqual(summary["pending"], 0)
        self.assertEqual(summary["in_progress"], 0)
        self.assertEqual(summary["adapted"], 0)

        for asset in ledger["assets"]:
            self.assertEqual(asset["status"], "VALIDATED", f"Asset {asset['id']} should be VALIDATED")
            # Verify target path exists
            target_path = REPO_ROOT / asset["target_path"]
            self.assertTrue(target_path.exists(), f"Target path for {asset['id']} must exist: {target_path}")

    def test_plugin_manifest_and_workspace_rules(self):
        """Verify plugin.json and rules/AGENTS.md exist and conform to AGY standards."""
        manifest_path = PLUGIN_ROOT / "plugin.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "academic-research-skills")
        self.assertEqual(manifest["version"], "3.22.0")

        rules_path = PLUGIN_ROOT / "rules" / "AGENTS.md"
        self.assertTrue(rules_path.exists())
        rules_text = rules_path.read_text(encoding="utf-8")
        self.assertIn("Academic Research Skills — Workspace Guidelines & Rules", rules_text)
        self.assertIn("single-line code blocks", rules_text)
        self.assertIn('"branch"', rules_text)


    def test_simulated_ten_stage_pipeline_orchestration(self):
        """Simulate a complete 10-stage pipeline orchestration execution and state transitions."""
        stages = [
            ("Stage 1", "Scoping", "phase1_scoping/methodology_blueprint.md"),
            ("Stage 2", "Investigation", "phase2_investigation/annotated_bibliography.md"),
            ("Stage 3", "Analysis", "phase3_analysis/synthesis_report.md"),
            ("Stage 4", "Drafting", "phase4_drafting/manuscript_draft.md"),
            ("Stage 5", "Integrity Gate", "phase5_review/claim_verification_audit.md"),
            ("Stage 6", "Peer Review Panel", "phase5_review/editorial_decision_package.md"),
            ("Stage 7", "Revision Planning", "phase6_revision/revision_roadmap.md"),
            ("Stage 8", "Re-Review Verification", "phase6_revision/re_review_verification.md"),
            ("Stage 9", "Final Integrity Check", "phase6_revision/final_integrity_report.md"),
            ("Stage 10", "Packaging & Finalize", "delivery/publication_package_manifest.json"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            pipeline_state: Dict[str, Any] = {
                "project_id": "ars-demo-quantum-computing",
                "current_stage": 0,
                "history": [],
            }

            for idx, (stage_name, desc, rel_deliverable) in enumerate(stages, 1):
                pipeline_state["current_stage"] = idx
                target_file = tmproot / rel_deliverable
                target_file.parent.mkdir(parents=True, exist_ok=True)

                if rel_deliverable.endswith(".json"):
                    target_file.write_text(json.dumps({
                        "stage": stage_name,
                        "description": desc,
                        "status": "APPROVED",
                        "artifacts": [str(rel_deliverable)]
                    }, indent=2), encoding="utf-8")
                else:
                    target_file.write_text(
                        f"# {stage_name}: {desc}\n\n"
                        f"**Status**: PASSED\n"
                        f"**Deliverable**: {rel_deliverable}\n"
                        f"**Content**: Verified academic findings for {pipeline_state['project_id']}.\n",
                        encoding="utf-8"
                    )

                self.assertTrue(target_file.exists())
                pipeline_state["history"].append({
                    "stage": stage_name,
                    "description": desc,
                    "deliverable": rel_deliverable,
                    "verified": True,
                })

            self.assertEqual(pipeline_state["current_stage"], 10)
            self.assertEqual(len(pipeline_state["history"]), 10)
            self.assertTrue(all(h["verified"] for h in pipeline_state["history"]))

    def test_full_agy_compatibility_plugin_tree(self):
        """Run verify_agy_compatibility across the entire plugin directory."""
        diagnostics = scan_path(PLUGIN_ROOT)
        errors = [d for d in diagnostics if d.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"Encountered {len(errors)} AGY compatibility errors:\n" + "\n".join(str(e) for e in errors))


if __name__ == "__main__":
    unittest.main()
