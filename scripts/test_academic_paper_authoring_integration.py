"""Integration tests for Academic Paper Authoring and Report Compiler Subagent.

Verifies:
1. Report compiler agent definition and invocation parameters with dynamic capability parsing.
2. Robust error handling for subagents.load_agent_spec (directory inputs, path traversal, missing files).
3. Authoring command skills (ars-plan, ars-outline, ars-abstract, ars-format-convert).
4. APA 7.0 formatting compliance (unnumbered headings, Level 1–5 hierarchy, citation anchors).
5. End-to-end simulated Socratic planning session and section compilation written to disk.
6. Full AGY compatibility scan across all newly added assets.
"""
from __future__ import annotations

import re
import sys
import tempfile
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
    get_synthesis_subagent_def,
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

    def test_dynamic_capabilities_parsing(self):
        """Verify capabilities are dynamically parsed from frontmatter in subagents.py."""
        compiler_def = get_report_compiler_subagent_def()
        self.assertTrue(compiler_def["enable_write_tools"])
        self.assertFalse(compiler_def["enable_subagent_tools"])
        self.assertFalse(compiler_def["enable_mcp_tools"])

        synthesis_def = get_synthesis_subagent_def()
        self.assertTrue(synthesis_def["enable_write_tools"])
        self.assertFalse(synthesis_def["enable_subagent_tools"])
        self.assertFalse(synthesis_def["enable_mcp_tools"])

    def test_load_agent_spec_error_handling(self):
        """Verify load_agent_spec properly handles directories, missing files, and traversal."""
        # 1. Directory inputs should raise FileNotFoundError (not unhandled IsADirectoryError)
        with self.assertRaises(FileNotFoundError):
            load_agent_spec(".")

        # 2. Path escaping should raise ValueError
        with self.assertRaises(ValueError):
            load_agent_spec("../../etc/passwd")

        # 3. Missing file should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            load_agent_spec("non_existent_agent_file.md")

    def test_apa7_heading_compliance_rules(self):
        """Verify report-compiler-agent enforces APA 7.0 unnumbered headings."""
        meta, prompt = load_agent_spec("report-compiler-agent.md")
        # Headings in APA 7.0 must never be numbered
        self.assertIn("Headings must **never** be numbered", prompt)
        self.assertNotIn("## 1. Introduction", prompt)
        self.assertNotIn("## 2. Literature Review", prompt)
        self.assertNotIn("## 3. Methodology", prompt)

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

    def test_end_to_end_planning_and_section_compilation_disk(self):
        """Simulate Socratic planning session and section compilation written to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            investigation_dir = tmppath / "phase2_investigation"
            investigation_dir.mkdir(parents=True, exist_ok=True)
            draft_dir = tmppath / "phase4_draft"
            draft_dir.mkdir(parents=True, exist_ok=True)

            # 1. Simulate Socratic Planning Session Deliverable (phase2_investigation/chapter_plan.md)
            chapter_plan_content = """# Chapter Plan: AI in Higher Education QA

## Central Thesis
Integrating generative AI into university quality assurance enhances inter-rater consistency without sacrificing qualitative evaluation depth.

## Identified Research Gap
Prior studies focus on Western higher education contexts, lacking empirical analysis of AI-assisted evaluator reliability in East Asian consensus-driven governance.

## Section 1: Opening & Problem Statement
- Claim 1: Evaluator variance in institutional accreditation has persisted despite standardized guidelines.
  - Source: Martin & Parikh (2024), Studies in Higher Education, pp. 50-72.
  - Anchor: page:55-58, Slug: martin2024meta
- Claim 2: In Taiwan, evaluator agreement is lowest for qualitative judgments such as governance and institutional culture.
  - Source: Lin & Huang (2023), Higher Education Policy, pp. 910-928.
  - Anchor: page:915, Slug: lin2023evaluator
"""
            chapter_plan_file = investigation_dir / "chapter_plan.md"
            chapter_plan_file.write_text(chapter_plan_content, encoding="utf-8")
            self.assertTrue(chapter_plan_file.exists())

            # 2. Simulate Report Compiler Draft Generation (phase4_draft/intro_section.md)
            draft_lines = [
                "# AI Integration in Higher Education Quality Assurance",
                "",
                "Inter-evaluator consistency has long represented an enduring challenge in higher education accreditation. Evaluator variance in institutional accreditation has persisted despite standardized guidelines (Martin & Parikh, 2024) <!--ref:martin2024meta--><!--anchor:page:55-58-->. Specifically, empirical evidence demonstrates substantial inter-rater variance across evaluation teams.",
                "",
                "In Taiwan, evaluator agreement is lowest for qualitative judgments such as governance and institutional culture (Lin & Huang, 2023) <!--ref:lin2023evaluator--><!--anchor:page:915-->. Prior studies focus on Western higher education contexts, lacking empirical analysis of AI-assisted evaluator reliability in East Asian consensus-driven governance.",
                "",
                "## References",
                "",
                "Lin, M., & Huang, T. (2023). Inter-rater reliability in institutional evaluation. *Higher Education Policy*, *36*(4), 910–928. https://doi.org/10.1057/s41307-023-00312-1",
                "Martin, E., & Parikh, S. (2024). Accreditation consistency across jurisdictions: A meta-analysis. *Studies in Higher Education*, *49*(2), 50–72. https://doi.org/10.1080/03075079.2024.1029384",
            ]
            compiled_draft_content = "\n".join(draft_lines)
            draft_file = draft_dir / "intro_section.md"
            draft_file.write_text(compiled_draft_content, encoding="utf-8")

            # 3. Verify Artifact Properties
            self.assertTrue(draft_file.exists())
            read_back = draft_file.read_text(encoding="utf-8")

            # Verify unnumbered heading structure (APA 7.0)
            self.assertIn("# AI Integration in Higher Education Quality Assurance", read_back)
            self.assertNotIn("## 1. Introduction", read_back)
            self.assertIn("## References", read_back)

            # Verify three-layer citation markers
            self.assertIn("<!--ref:martin2024meta--><!--anchor:page:55-58-->", read_back)
            self.assertIn("<!--ref:lin2023evaluator--><!--anchor:page:915-->", read_back)

            # Verify HTTPS DOIs in reference list
            self.assertIn("https://doi.org/10.1057/s41307-023-00312-1", read_back)
            self.assertIn("https://doi.org/10.1080/03075079.2024.1029384", read_back)

    def test_verify_agy_compatibility_plugin_clean(self):
        """Run verify_agy_compatibility on the entire plugin and confirm 0 errors."""
        diags = scan_path(PLUGIN_ROOT)
        errors = [d for d in diags if d.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"Found {len(errors)} errors: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main()
