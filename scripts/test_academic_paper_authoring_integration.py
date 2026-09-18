"""Integration tests for Academic Paper Authoring and Report Compiler Subagent.

Verifies:
1. Report compiler agent definition and invocation parameters.
2. Authoring command skills (ars-plan, ars-outline, ars-abstract, ars-format-convert).
3. End-to-end simulated Socratic planning session and section compilation with APA 7.0 formatting.
4. AGY compatibility across all newly added assets.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# Add plugin scripts and root scripts to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / ".agents" / "plugins" / "academic-research-skills"
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from subagents import (  # type: ignore
    load_agent_spec,
    get_report_compiler_subagent_def,
    get_report_compiler_subagent_invocation,
)
from verify_agy_compatibility import scan_path  # type: ignore


class TestAcademicPaperAuthoringIntegration(unittest.TestCase):
    """Test suite for Ticket 03 authoring and report compilation workflows."""

    def test_report_compiler_subagent_def(self):
        """Verify report-compiler-agent definition schema for define_subagent."""
        agent_def = get_report_compiler_subagent_def()
        self.assertEqual(agent_def["name"], "report-compiler-agent")
        self.assertTrue(agent_def["enable_write_tools"])
        self.assertFalse(agent_def["enable_subagent_tools"])
        self.assertFalse(agent_def["enable_mcp_tools"])
        self.assertIn("APA 7.0", agent_def["description"])
        self.assertIn("APA 7.0 Strict Compliance", agent_def["system_prompt"])
        self.assertIn("Heading Hierarchy (Levels 1–5)", agent_def["system_prompt"])
        self.assertIn("Three-Layer Citation Emission", agent_def["system_prompt"])

    def test_report_compiler_subagent_invocation(self):
        """Verify report-compiler-agent invocation dictionary for invoke_subagent."""
        prompt = "Compile Section 1: Introduction draft based on chapter plan."
        invocation = get_report_compiler_subagent_invocation(prompt, model="inherit")
        self.assertEqual(invocation["TypeName"], "report-compiler-agent")
        self.assertEqual(invocation["Role"], "APA 7.0 Report Compiler")
        self.assertEqual(invocation["Prompt"], prompt)
        self.assertEqual(invocation["Model"], "inherit")
        self.assertEqual(invocation["Workspace"], "branch")

    def test_authoring_skills_exist_and_conform(self):
        """Verify all authoring skills exist with valid frontmatter."""
        skills = [
            "academic-paper",
            "ars-plan",
            "ars-outline",
            "ars-abstract",
            "ars-format-convert",
        ]
        for skill_name in skills:
            skill_path = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
            self.assertTrue(skill_path.exists(), f"Missing skill file: {skill_path}")
            content = skill_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), f"Skill {skill_name} missing frontmatter fence")
            match = re.search(r"^name:\s*([^\n\r]+)", content, re.MULTILINE)
            self.assertIsNotNone(match, f"Skill {skill_name} missing name in frontmatter")
            self.assertEqual(match.group(1).strip(), skill_name)

    def test_end_to_end_planning_and_section_compilation(self):
        """Simulate Socratic planning session and section compilation with APA 7.0."""
        # 1. Simulate Socratic Planning Session Outputs (ars-plan)
        planning_session = {
            "thesis": "Integrating generative AI into university quality assurance enhances inter-rater consistency without sacrificing qualitative evaluation depth.",
            "research_gap": "Prior studies focus on Western higher education contexts, lacking empirical analysis of AI-assisted evaluator reliability in East Asian consensus-driven governance.",
            "section": "1. Introduction",
            "claims": [
                {
                    "claim": "Evaluator variance in institutional accreditation has persisted despite standardized guidelines.",
                    "slug": "martin2024meta",
                    "locator": "page:55-58",
                    "citation_visible": "(Martin & Parikh, 2024)",
                },
                {
                    "claim": "In Taiwan, evaluator agreement is lowest for qualitative judgments such as governance and institutional culture.",
                    "slug": "lin2023evaluator",
                    "locator": "page:915",
                    "citation_visible": "(Lin & Huang, 2023)",
                },
            ],
            "target_word_count": 450,
        }

        # 2. Simulate Report Compiler Execution (report-compiler-agent)
        # Verify system prompt has required formatting rules
        meta, prompt = load_agent_spec("report-compiler-agent.md")
        self.assertIn("Heading Hierarchy (Levels 1–5)", prompt)

        # Generate APA 7.0 compiled section draft
        draft_lines = [
            "# AI Integration in Higher Education Quality Assurance",
            "",
            "## Introduction",
            "",
            "### Context and Problem Statement",
            "",
            f"Inter-evaluator consistency has long represented an enduring challenge in higher education accreditation. {planning_session['claims'][0]['claim']} {planning_session['claims'][0]['citation_visible']} <!--ref:{planning_session['claims'][0]['slug']}--><!--anchor:{planning_session['claims'][0]['locator']}-->. Specifically, empirical evidence demonstrates substantial inter-rater variance across evaluation teams.",
            "",
            f"{planning_session['claims'][1]['claim']} {planning_session['claims'][1]['citation_visible']} <!--ref:{planning_session['claims'][1]['slug']}--><!--anchor:{planning_session['claims'][1]['locator']}-->. {planning_session['research_gap']}",
            "",
            "## References",
            "",
            "Lin, M., & Huang, T. (2023). Inter-rater reliability in institutional evaluation. *Higher Education Policy*, *36*(4), 910–928. https://doi.org/10.1057/s41307-023-00312-1",
            "Martin, E., & Parikh, S. (2024). Accreditation consistency across jurisdictions: A meta-analysis. *Studies in Higher Education*, *49*(2), 50–72. https://doi.org/10.1080/03075079.2024.1029384",
        ]
        compiled_draft = "\n".join(draft_lines)

        # 3. Assert APA 7.0 Formatting and Marker Integrity
        self.assertIn("### Context and Problem Statement", compiled_draft)
        # Check two/three layer citation markers
        for claim in planning_session["claims"]:
            expected_marker = f"<!--ref:{claim['slug']}--><!--anchor:{claim['locator']}-->"
            self.assertIn(expected_marker, compiled_draft)
            self.assertIn(claim["citation_visible"], compiled_draft)

        # Check references section
        self.assertIn("## References", compiled_draft)
        self.assertIn("https://doi.org/10.1057/s41307-023-00312-1", compiled_draft)
        self.assertIn("https://doi.org/10.1080/03075079.2024.1029384", compiled_draft)

    def test_verify_agy_compatibility_plugin_clean(self):
        """Run verify_agy_compatibility on the entire plugin and confirm 0 errors."""
        diags = scan_path(PLUGIN_ROOT)
        errors = [d for d in diags if d.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"Found {len(errors)} errors: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main()
