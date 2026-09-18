"""Unit tests for verify_agy_compatibility.py."""
from __future__ import annotations

import json
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_helpers import run_script

SCRIPT = Path(__file__).resolve().parent / "verify_agy_compatibility.py"


class TestVerifyAgyCompatibility(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run_script(SCRIPT, *args, cwd=self.root)

    def test_valid_agy_skill_passes(self) -> None:
        skill_dir = self.root / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: my-skill
                description: Provides automated verification and testing workflows for Antigravity CLI.
                ---

                # My Skill

                Run the tool:
                ```bash
                python3 run.py --check
                ```
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        self.assertIn("All AGY compatibility checks passed", res.stdout)

    def test_frontmatter_invalid_kebab_name_fails(self) -> None:
        skill_dir = self.root / "skills" / "Bad_Skill_Name"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: Bad_Skill_Name
                description: Provides automated verification and testing workflows for Antigravity CLI.
                ---
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("must be lowercase kebab-case", res.stdout)

    def test_frontmatter_forbidden_claude_fields_fail(self) -> None:
        skill_dir = self.root / "skills" / "claude-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: claude-skill
                description: This skill performs tasks in Antigravity CLI.
                disable-model-invocation: true
                model: sonnet
                ---
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Forbidden Claude-specific frontmatter field", res.stdout)

    def test_deprecated_claude_tool_references_fail(self) -> None:
        skill_dir = self.root / "skills" / "leaky-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: leaky-skill
                description: Performs deep research on academic papers using Antigravity tools.
                ---

                Call Bash(command="ls -la") or use ${CLAUDE_PLUGIN_ROOT}/scripts/run.sh.
                Also remember to /compact context when tired.
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Forbidden Claude tool reference", res.stdout)
        self.assertIn("Deprecated Claude environment variable", res.stdout)
        self.assertIn("Deprecated Claude session command", res.stdout)

    def test_forbidden_claude_tools_broad_coverage(self) -> None:
        skill_dir = self.root / "skills" / "broad-tool-test"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: broad-tool-test
                description: Testing detection of various Claude tools across formats.
                ---

                Use StrReplace or FileEdit or MultiEdit to modify files.
                Call create_file or ReadDir or Grep or Glob.
                Also /clear before starting.
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Forbidden Claude tool reference", res.stdout)
        self.assertIn("Deprecated Claude session command", res.stdout)

    def test_multiline_bash_block_fails_user_rule(self) -> None:
        skill_dir = self.root / "skills" / "multiline-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: multiline-skill
                description: A skill that unfortunately provides multi-line shell snippets.
                ---

                Execute these steps:
                ```bash
                cd /tmp
                echo "hello"
                ls -la
                ```
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Multi-line shell command block detected", res.stdout)

    def test_zsh_multiline_block_fails(self) -> None:
        skill_dir = self.root / "skills" / "zsh-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: zsh-skill
                description: A skill using zsh code block with multiple lines.
                ---

                Execute these steps:
                ```zsh
                echo "one"
                echo "two"
                ```
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Multi-line shell command block detected", res.stdout)

    def test_frontmatter_inline_comments_allowed(self) -> None:
        skill_dir = self.root / "skills" / "commented-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: commented-skill # primary skill identifier
                description: >- # folded description starts here
                  A valid description that exceeds minimum length without issues.
                ---

                # Commented Skill
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    def test_claude_model_full_identifier_fails(self) -> None:
        skill_dir = self.root / "skills" / "full-model-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: full-model-skill
                description: A skill specifying a full Claude model identifier.
                model: claude-3-5-sonnet-20241022
                ---
                """
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(skill_dir))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Forbidden Claude-specific model", res.stdout)

    def test_valid_agy_hooks_json_passes(self) -> None:
        hooks_file = self.root / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "ars-guard": {
                        "PreToolUse": [
                          {
                            "matcher": "run_command|write_to_file",
                            "hooks": [
                              {
                                "type": "command",
                                "command": "./scripts/guard.sh"
                              }
                            ]
                          }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(hooks_file))
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    def test_claude_hooks_json_fails(self) -> None:
        hooks_file = self.root / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                          {
                            "matcher": "Bash|Write",
                            "hooks": [{"type": "command", "command": "run.sh"}]
                          }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(hooks_file))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Claude-format 'hooks' wrapper detected", res.stdout)

    def test_hooks_misspelled_event_fails(self) -> None:
        hooks_file = self.root / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "my-hook": {
                        "preToolUse": [
                            {"matcher": "run_command", "hooks": [{"type": "command", "command": "run.sh"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(hooks_file))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Invalid hook event 'preToolUse'", res.stdout)

    def test_migration_ledger_validation(self) -> None:
        src = self.root / "deep-research"
        src.mkdir(parents=True)
        (src / "SKILL.md").write_text("test", encoding="utf-8")

        ledger_file = self.root / "migration_ledger.json"
        ledger_file.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "last_updated": "2026-09-18T15:00:00Z",
                    "summary": {
                        "total": 1,
                        "pending": 0,
                        "in_progress": 1,
                        "adapted": 0,
                        "validated": 0
                    },
                    "assets": [
                        {
                            "id": "deep-research",
                            "category": "skill",
                            "source_path": "deep-research/SKILL.md",
                            "target_path": "skills/deep-research/SKILL.md",
                            "status": "IN_PROGRESS",
                            "ticket": "02",
                            "notes": "Testing ledger"
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(ledger_file))
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    def test_migration_ledger_desynchronized_summary_fails(self) -> None:
        ledger_file = self.root / "migration_ledger.json"
        ledger_file.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "last_updated": "2026-09-18T15:00:00Z",
                    "summary": {
                        "total": 999,
                        "pending": 0,
                        "in_progress": 0,
                        "adapted": 0,
                        "validated": 0
                    },
                    "assets": []
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(ledger_file))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Summary 'total' (999) does not match actual assets count (0)", res.stdout)

    def test_plugin_json_validation(self) -> None:
        plugin_file = self.root / "plugin.json"
        plugin_file.write_text(
            json.dumps(
                {
                    "name": "my-plugin",
                    "version": "1.0.0",
                    "description": "A comprehensive plugin for Antigravity development."
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(plugin_file))
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    def test_invalid_plugin_json_fails(self) -> None:
        plugin_file = self.root / "plugin.json"
        plugin_file.write_text(
            json.dumps(
                {
                    "name": "Bad_Plugin_Name",
                    "version": "1.0.0"
                }
            ),
            encoding="utf-8",
        )

        res = self._run("--path", str(plugin_file))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("plugin.json missing required 'description' field", res.stdout)


if __name__ == "__main__":
    unittest.main()
