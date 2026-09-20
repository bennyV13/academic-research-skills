"""Unit tests for ARS Deterministic Report Path Allocator.

Tests slugification, sequential numbering, dated directory creation,
CLI arguments, and Antigravity PreToolUse hook integration.
"""
import datetime
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.allocate_report_path import (
    allocate_report_path,
    evaluate_report_tool_call,
    format_sequence_prefix,
    get_next_sequence_number,
    slugify,
)


class TestSlugify(unittest.TestCase):
    def test_basic_slug(self):
        self.assertEqual(slugify("Literature Review"), "literature_review")

    def test_special_characters_and_punctuation(self):
        title = "Quantum & Classical AI: A 2026 Survey (Meta-Analysis)!"
        self.assertEqual(
            slugify(title),
            "quantum_classical_ai_a_2026_survey_meta_analysis",
        )

    def test_extension_removal(self):
        self.assertEqual(slugify("draft_paper.md"), "draft_paper")

    def test_empty_and_whitespace(self):
        self.assertEqual(slugify(""), "report")
        self.assertEqual(slugify("   "), "report")
        self.assertEqual(slugify("---___---"), "report")

    def test_max_length_truncation(self):
        long_title = "a" * 100
        slug = slugify(long_title, max_length=50)
        self.assertEqual(len(slug), 50)


class TestSequenceNumbering(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dir_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_dir_returns_one(self):
        self.assertEqual(get_next_sequence_number(self.dir_path), 1)

    def test_nonexistent_dir_returns_one(self):
        non_existent = self.dir_path / "does_not_exist"
        self.assertEqual(get_next_sequence_number(non_existent), 1)

    def test_sequential_increment(self):
        (self.dir_path / "01_intro.md").touch()
        (self.dir_path / "02_lit_review.md").touch()
        self.assertEqual(get_next_sequence_number(self.dir_path), 3)

    def test_handles_gaps_cleanly(self):
        (self.dir_path / "01_intro.md").touch()
        (self.dir_path / "05_discussion.md").touch()
        self.assertEqual(get_next_sequence_number(self.dir_path), 6)

    def test_ignores_non_numbered_files(self):
        (self.dir_path / "README.md").touch()
        (self.dir_path / "notes.txt").touch()
        (self.dir_path / ".DS_Store").touch()
        self.assertEqual(get_next_sequence_number(self.dir_path), 1)

        (self.dir_path / "01_first.md").touch()
        self.assertEqual(get_next_sequence_number(self.dir_path), 2)

    def test_formatting_prefixes(self):
        self.assertEqual(format_sequence_prefix(1), "01")
        self.assertEqual(format_sequence_prefix(9), "09")
        self.assertEqual(format_sequence_prefix(10), "10")
        self.assertEqual(format_sequence_prefix(99), "99")
        self.assertEqual(format_sequence_prefix(100), "100")


class TestAllocateReportPath(unittest.TestCase):
    def setUp(self):
        self.temp_workspace = tempfile.mkdtemp()
        self.ws = Path(self.temp_workspace).resolve()

    def tearDown(self):
        shutil.rmtree(self.temp_workspace, ignore_errors=True)

    def test_allocates_canonical_path(self):
        today = datetime.date.today().isoformat()
        res = allocate_report_path("Lit Review", workspace_root=self.ws)
        expected = self.ws / "reports" / "ars" / today / "01_lit_review.md"
        self.assertEqual(res, expected)
        self.assertTrue(res.parent.is_dir())

    def test_increments_when_file_exists(self):
        today = datetime.date.today().isoformat()
        res1 = allocate_report_path("Paper One", workspace_root=self.ws)
        res1.touch()
        res2 = allocate_report_path("Paper Two", workspace_root=self.ws)
        expected2 = self.ws / "reports" / "ars" / today / "02_paper_two.md"
        self.assertEqual(res2, expected2)

    def test_date_override(self):
        target_date = "2026-10-15"
        res = allocate_report_path("Milestone", workspace_root=self.ws, date_str=target_date)
        expected = self.ws / "reports" / "ars" / target_date / "01_milestone.md"
        self.assertEqual(res, expected)

    def test_custom_extension(self):
        res = allocate_report_path("Analysis", workspace_root=self.ws, ext="tex")
        self.assertTrue(res.name.endswith(".tex"))


class TestEvaluateReportToolCallHook(unittest.TestCase):
    def setUp(self):
        self.temp_workspace = tempfile.mkdtemp()
        self.ws = Path(self.temp_workspace).resolve()

    def tearDown(self):
        shutil.rmtree(self.temp_workspace, ignore_errors=True)

    def test_ignores_non_write_tools(self):
        payload = {
            "toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}},
            "workspacePaths": [str(self.ws)],
        }
        dec = evaluate_report_tool_call(payload, workspace_root=self.ws)
        self.assertEqual(dec, {"decision": "allow"})

    def test_ignores_regular_project_files(self):
        payload = {
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": "src/module.py"}},
            "workspacePaths": [str(self.ws)],
        }
        dec = evaluate_report_tool_call(payload, workspace_root=self.ws)
        self.assertEqual(dec, {"decision": "allow"})

    def test_ignores_adaptation_reports(self):
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": "reports/agy-adaptation/issue10.md"},
            },
            "workspacePaths": [str(self.ws)],
        }
        dec = evaluate_report_tool_call(payload, workspace_root=self.ws)
        self.assertEqual(dec, {"decision": "allow"})

    def test_redirects_unformatted_ars_report(self):
        today = datetime.date.today().isoformat()
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": "reports/ars/synthesis_summary.md"},
            },
            "workspacePaths": [str(self.ws)],
        }
        dec = evaluate_report_tool_call(payload, workspace_root=self.ws)
        self.assertEqual(dec["decision"], "allow")
        self.assertIn("overwrite", dec)
        overwritten = dec["overwrite"]["TargetFile"]
        expected = str(self.ws / "reports" / "ars" / today / "01_synthesis_summary.md")
        self.assertEqual(overwritten, expected)

    def test_leaves_canonical_path_untouched(self):
        today = datetime.date.today().isoformat()
        canonical = f"reports/ars/{today}/01_synthesis_summary.md"
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": str(self.ws / canonical)},
            },
            "workspacePaths": [str(self.ws)],
        }
        dec = evaluate_report_tool_call(payload, workspace_root=self.ws)
        self.assertEqual(dec, {"decision": "allow"})
        self.assertNotIn("overwrite", dec)

    def test_redirects_report_compiler_agent_files(self):
        today = datetime.date.today().isoformat()
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": "final_manuscript.md"},
            },
            "agent_type": "report-compiler-agent",
            "workspacePaths": [str(self.ws)],
        }
        dec = evaluate_report_tool_call(payload, workspace_root=self.ws)
        self.assertEqual(dec["decision"], "allow")
        self.assertIn("overwrite", dec)
        overwritten = dec["overwrite"]["TargetFile"]
        expected = str(self.ws / "reports" / "ars" / today / "01_final_manuscript.md")
        self.assertEqual(overwritten, expected)


if __name__ == "__main__":
    unittest.main()
