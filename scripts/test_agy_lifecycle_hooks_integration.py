"""Integration test suite for AGY Lifecycle Hooks & Write-Scope Guard (Ticket #05 / Issue #9).

Verifies:
1. Lifecycle hook configuration (hooks.json) conforms to AGY named hook groups and tool matchers.
2. ars_write_scope_guard_agy.py evaluates AGY protojson tool calls against write-scope rules:
   - In-scope writes permitted (allow)
   - Out-of-scope writes blocked (deny)
   - Shell commands blocked for Bucket A agents (deny)
   - Shell commands allowed for unconstrained actors (allow)
   - Infrastructure tampering blocked for all actors (deny)
   - Path traversal blocked for Bucket A agents (deny)
3. End-to-end launcher script (run_guard_agy.sh) pipes stdin/stdout and gracefully degrades.
4. Full verify_agy_compatibility scan passes cleanly.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add plugin scripts and root scripts to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / ".agents" / "plugins" / "academic-research-skills"
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ars_write_scope_guard_agy import (  # type: ignore
    evaluate_agy_decision,
    load_scope_manifest,
)
from verify_agy_compatibility import check_hooks_json, scan_path  # type: ignore


class TestAgyLifecycleHooksIntegration(unittest.TestCase):
    """Test suite for Ticket 05 lifecycle hooks and write-scope guard."""

    @classmethod
    def setUpClass(cls):
        cls.hooks_json_path = PLUGIN_ROOT / "hooks.json"
        cls.launcher_path = PLUGIN_ROOT / "hooks" / "run_guard_agy.sh"
        cls.manifest = load_scope_manifest()

    def test_hooks_json_schema_validity(self):
        """Verify hooks.json conforms to AGY specification with named hook groups."""
        self.assertTrue(self.hooks_json_path.exists(), "hooks.json missing from plugin root")
        content = self.hooks_json_path.read_text(encoding="utf-8")
        diags = check_hooks_json(self.hooks_json_path, content)
        errors = [d for d in diags if d.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"hooks.json schema errors: {errors}")

        data = json.loads(content)
        self.assertIn("write-scope-guard", data)
        self.assertIn("PreToolUse", data["write-scope-guard"])
        pre_tool_use = data["write-scope-guard"]["PreToolUse"]
        self.assertEqual(len(pre_tool_use), 1)
        self.assertIn("matcher", pre_tool_use[0])
        self.assertIn("write_to_file|replace_file_content|run_command", pre_tool_use[0]["matcher"])

    def test_launcher_script_executable(self):
        """Verify run_guard_agy.sh exists and has execute permissions."""
        self.assertTrue(self.launcher_path.exists(), "run_guard_agy.sh missing from hooks dir")
        self.assertTrue(os.access(self.launcher_path, os.X_OK), "run_guard_agy.sh is not executable")

    def test_permitted_in_scope_writes(self):
        """Verify permitted write actions pass with decision 'allow'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_root = tmpdir
            # synthesis_agent is allowed in phase3_*/**
            payload = {
                "toolCall": {
                    "name": "write_to_file",
                    "args": {
                        "TargetFile": os.path.join(ws_root, "phase3_analysis", "synthesis.md"),
                        "CodeContent": "# Evidence Synthesis\n..."
                    }
                },
                "agent_type": "synthesis_agent",
                "workspacePaths": [ws_root],
            }
            decision = evaluate_agy_decision(payload, self.manifest, ws_root, str(PLUGIN_ROOT))
            self.assertEqual(decision["decision"], "allow")

            # replace_file_content in phase6 for peer_reviewer_agent
            payload2 = {
                "toolCall": {
                    "name": "replace_file_content",
                    "args": {
                        "TargetFile": os.path.join(ws_root, "phase6_review", "review_card.md"),
                        "TargetContent": "Old",
                        "ReplacementContent": "New"
                    }
                },
                "agent_type": "peer_reviewer_agent",
                "workspacePaths": [ws_root],
            }
            decision2 = evaluate_agy_decision(payload2, self.manifest, ws_root, str(PLUGIN_ROOT))
            self.assertEqual(decision2["decision"], "allow")

    def test_out_of_scope_writes_denied(self):
        """Verify out-of-scope writes by Bucket A agents are denied with informative reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_root = tmpdir
            # synthesis_agent attempting to write to phase1_planning (outside phase3_*/**)
            payload = {
                "toolCall": {
                    "name": "write_to_file",
                    "args": {
                        "TargetFile": os.path.join(ws_root, "phase1_planning", "scope.md"),
                        "CodeContent": "Unauthorized edit"
                    }
                },
                "agent_type": "synthesis_agent",
                "workspacePaths": [ws_root],
            }
            decision = evaluate_agy_decision(payload, self.manifest, ws_root, str(PLUGIN_ROOT))
            self.assertEqual(decision["decision"], "deny")
            self.assertIn("outside declared allowed_write_globs", decision["reason"])

    def test_shell_command_gating(self):
        """Verify shell command (run_command) is denied for Bucket A agents but allowed for others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_root = tmpdir
            # Bucket A agent calling run_command -> DENIED
            payload_subagent = {
                "toolCall": {
                    "name": "run_command",
                    "args": {
                        "CommandLine": "ls -la",
                        "Cwd": ws_root
                    }
                },
                "agent_type": "synthesis_agent",
                "workspacePaths": [ws_root],
            }
            decision_sub = evaluate_agy_decision(payload_subagent, self.manifest, ws_root, str(PLUGIN_ROOT))
            self.assertEqual(decision_sub["decision"], "deny")
            self.assertIn("may not execute shell commands directly", decision_sub["reason"])

            # Unconstrained main session calling run_command -> ALLOWED
            payload_main = {
                "toolCall": {
                    "name": "run_command",
                    "args": {
                        "CommandLine": "pytest",
                        "Cwd": ws_root
                    }
                },
                "workspacePaths": [ws_root],
            }
            decision_main = evaluate_agy_decision(payload_main, self.manifest, ws_root, str(PLUGIN_ROOT))
            self.assertEqual(decision_main["decision"], "allow")

    def test_infrastructure_self_protection(self):
        """Verify tampering with enforcement infrastructure is blocked even for main session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_root = tmpdir
            infra_targets = [
                str(PLUGIN_ROOT / "hooks.json"),
                str(PLUGIN_ROOT / "hooks" / "run_guard_agy.sh"),
                str(PLUGIN_ROOT / "plugin.json"),
                str(PLUGIN_ROOT / "scripts" / "ars_write_scope_guard_agy.py"),
                str(PLUGIN_ROOT / "agents" / "peer-reviewer-agent.md"),
            ]
            for target in infra_targets:
                payload = {
                    "toolCall": {
                        "name": "write_to_file",
                        "args": {
                            "TargetFile": target,
                            "CodeContent": "corrupted"
                        }
                    },
                    "workspacePaths": [ws_root],
                }
                decision = evaluate_agy_decision(payload, self.manifest, ws_root, str(PLUGIN_ROOT))
                self.assertEqual(decision["decision"], "deny", f"Target {target} was not protected!")
                self.assertIn("enforcement infrastructure", decision["reason"])

    def test_path_traversal_denied(self):
        """Verify path traversal outside workspace is blocked for Bucket A agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_root = tmpdir
            payload = {
                "toolCall": {
                    "name": "write_to_file",
                    "args": {
                        "TargetFile": os.path.join(ws_root, "..", "escaped_file.txt"),
                        "CodeContent": "escape"
                    }
                },
                "agent_type": "bibliography_agent",
                "workspacePaths": [ws_root],
            }
            decision = evaluate_agy_decision(payload, self.manifest, ws_root, str(PLUGIN_ROOT))
            self.assertEqual(decision["decision"], "deny")
            self.assertIn("path traversal violation", decision["reason"])

    def test_end_to_end_launcher_subprocess(self):
        """Verify run_guard_agy.sh runs as a subprocess, parsing stdin and emitting valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_root = tmpdir
            # 1. Allowed write payload
            allow_payload = {
                "toolCall": {
                    "name": "write_to_file",
                    "args": {
                        "TargetFile": os.path.join(ws_root, "phase3_analysis", "report.md"),
                        "CodeContent": "Safe content"
                    }
                },
                "agent_type": "synthesis_agent",
                "workspacePaths": [ws_root],
            }
            proc = subprocess.run(
                [str(self.launcher_path)],
                input=json.dumps(allow_payload),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            out_data = json.loads(proc.stdout)
            self.assertEqual(out_data.get("decision"), "allow")

            # 2. Denied write payload
            deny_payload = {
                "toolCall": {
                    "name": "write_to_file",
                    "args": {
                        "TargetFile": os.path.join(ws_root, "phase1_planning", "hack.md"),
                        "CodeContent": "Breach"
                    }
                },
                "agent_type": "synthesis_agent",
                "workspacePaths": [ws_root],
            }
            proc_deny = subprocess.run(
                [str(self.launcher_path)],
                input=json.dumps(deny_payload),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc_deny.returncode, 0)
            out_deny = json.loads(proc_deny.stdout)
            self.assertEqual(out_deny.get("decision"), "deny")
            self.assertIn("outside declared allowed_write_globs", out_deny.get("reason", ""))

            # 3. Graceful degradation on empty / malformed input
            proc_empty = subprocess.run(
                [str(self.launcher_path)],
                input="not-valid-json",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc_empty.returncode, 0)
            out_empty = json.loads(proc_empty.stdout)
            self.assertEqual(out_empty.get("decision"), "allow")

    def test_verify_agy_compatibility_clean(self):
        """Run verify_agy_compatibility across the plugin and confirm 0 errors."""
        diags = scan_path(PLUGIN_ROOT)
        errors = [d for d in diags if d.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"Found {len(errors)} errors: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main()
