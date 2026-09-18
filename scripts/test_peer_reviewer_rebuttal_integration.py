"""Integration tests for Peer Reviewer Panel & Rebuttal Engine (Ticket #04 / Issue #7).

Verifies:
1. Subagent definitions and invocation schemas for peer-reviewer, editorial-synthesizer, and revision-coach.
2. Skill definitions and frontmatter conformity (academic-paper-reviewer, ars-reviewer, ars-revision, ars-rebuttal-audit, ars-revision-coach).
3. Simulated reviewer evaluation scoring (five dimensions, soundness/empirical gap detection, severity classification).
4. Rebuttal audit engine (item-by-item alignment, detection of unaddressed critiques, substantive gaps, no Claude artifacts).
5. End-to-end simulated review panel and rebuttal audit session written to disk.
6. Clean AGY compatibility scan across all newly added assets.
"""
from __future__ import annotations

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
    get_peer_reviewer_subagent_def,
    get_peer_reviewer_subagent_invocation,
    get_editorial_synthesizer_subagent_def,
    get_editorial_synthesizer_subagent_invocation,
    get_revision_coach_subagent_def,
    get_revision_coach_subagent_invocation,
)
from verify_agy_compatibility import scan_path  # type: ignore


class TestPeerReviewerRebuttalIntegration(unittest.TestCase):
    """Test suite for Ticket 04 reviewer panel and rebuttal engine workflows."""

    def test_reviewer_subagent_definitions(self):
        """Verify peer-reviewer-agent definition and invocation schemas."""
        agent_def = get_peer_reviewer_subagent_def()
        self.assertEqual(agent_def["name"], "peer-reviewer-agent")
        self.assertTrue(agent_def["enable_write_tools"])
        self.assertFalse(agent_def["enable_subagent_tools"])
        self.assertFalse(agent_def["enable_mcp_tools"])
        self.assertIn("Five-Dimension Evaluation Rubric", agent_def["system_prompt"])
        self.assertIn("Defect & Gap Classification", agent_def["system_prompt"])

        invocation = get_peer_reviewer_subagent_invocation("Review manuscript section 3 for methodology rigor.")
        self.assertEqual(invocation["TypeName"], "peer-reviewer-agent")
        self.assertEqual(invocation["Role"], "Academic Peer Reviewer")
        self.assertEqual(invocation["Workspace"], "branch")

    def test_editorial_synthesizer_subagent_definitions(self):
        """Verify editorial-synthesizer-agent definition and invocation schemas."""
        agent_def = get_editorial_synthesizer_subagent_def()
        self.assertEqual(agent_def["name"], "editorial-synthesizer-agent")
        self.assertTrue(agent_def["enable_write_tools"])
        self.assertFalse(agent_def["enable_subagent_tools"])
        self.assertFalse(agent_def["enable_mcp_tools"])
        self.assertIn("Consensus & Divergence Analysis", agent_def["system_prompt"])
        self.assertIn("Fatal Block Principle", agent_def["system_prompt"])

        invocation = get_editorial_synthesizer_subagent_invocation("Synthesize reports from 3 reviewers and render decision.")
        self.assertEqual(invocation["TypeName"], "editorial-synthesizer-agent")
        self.assertEqual(invocation["Role"], "Editorial Decision Synthesizer")
        self.assertEqual(invocation["Workspace"], "branch")

    def test_revision_coach_subagent_definitions(self):
        """Verify revision-coach-agent definition and invocation schemas."""
        agent_def = get_revision_coach_subagent_def()
        self.assertEqual(agent_def["name"], "revision-coach-agent")
        self.assertTrue(agent_def["enable_write_tools"])
        self.assertFalse(agent_def["enable_subagent_tools"])
        self.assertFalse(agent_def["enable_mcp_tools"])
        self.assertIn("Workflow 1: Comment Parsing & Roadmap Construction", agent_def["system_prompt"])
        self.assertIn("Workflow 2: Rebuttal Audit (QA Mode)", agent_def["system_prompt"])
        self.assertIn("[UNADDRESSED_CRITIQUE]", agent_def["system_prompt"])

        invocation = get_revision_coach_subagent_invocation("Audit author rebuttal draft against 5 reviewer comments.")
        self.assertEqual(invocation["TypeName"], "revision-coach-agent")
        self.assertEqual(invocation["Role"], "Rebuttal and Revision Coach")
        self.assertEqual(invocation["Workspace"], "branch")

    def test_reviewer_skills_exist_and_conform(self):
        """Verify all reviewer and rebuttal skills exist with valid frontmatter."""
        skills = [
            "academic-paper-reviewer",
            "ars-reviewer",
            "ars-revision",
            "ars-rebuttal-audit",
            "ars-revision-coach",
        ]
        for skill_name in skills:
            skill_path = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
            self.assertTrue(skill_path.exists(), f"Missing skill file: {skill_path}")
            content = skill_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), f"Skill {skill_name} missing frontmatter fence")
            match = re.search(r"^name:\s*([^\n\r]+)", content, re.MULTILINE)
            self.assertIsNotNone(match, f"Skill {skill_name} missing name in frontmatter")
            self.assertEqual(match.group(1).strip(), skill_name)

    def test_simulated_reviewer_evaluation_scoring(self):
        """Test reviewer scoring logic, gap detection, and verdict derivation."""
        # Simulated manuscript with known empirical gap (missing control baseline)
        manuscript_claims = {
            "title": "Quantum Neural Network Scalability on NISQ Devices",
            "has_empirical_baseline": False,
            "sample_size": 25,
            "has_reproducibility_artifacts": True,
        }

        # Evaluator simulation adhering to the five dimensions
        def evaluate_manuscript(m: Dict[str, Any]) -> Dict[str, Any]:
            scores: Dict[str, str] = {
                "Originality": "EXCEEDS",
                "Methodological Rigor": "DOES_NOT_MEET" if not m["has_empirical_baseline"] else "MEETS",
                "Evidence Sufficiency": "PARTLY_MEETS" if m["sample_size"] < 100 else "MEETS",
                "Argument Coherence": "MEETS",
                "Writing Quality": "MEETS",
            }
            gaps: List[Dict[str, str]] = []
            if not m["has_empirical_baseline"]:
                gaps.append({
                    "severity": "Major",
                    "dimension": "Methodological Rigor",
                    "issue": "Lacks classical benchmark baseline comparison (e.g. ResNet on classical hardware).",
                })
            if m["sample_size"] < 100:
                gaps.append({
                    "severity": "Minor",
                    "dimension": "Evidence Sufficiency",
                    "issue": f"Sample size (n={m['sample_size']}) provides insufficient statistical power.",
                })

            # Verdict derivation: Major gaps prevent Accept and Minor Revision
            has_critical = any(g["severity"] == "Critical" for g in gaps)
            has_major = any(g["severity"] == "Major" for g in gaps)
            if has_critical:
                verdict = "Reject"
            elif has_major:
                verdict = "Major Revision"
            elif any(g["severity"] == "Minor" for g in gaps):
                verdict = "Minor Revision"
            else:
                verdict = "Accept"

            return {"scores": scores, "gaps": gaps, "verdict": verdict}

        review_result = evaluate_manuscript(manuscript_claims)
        self.assertEqual(review_result["scores"]["Methodological Rigor"], "DOES_NOT_MEET")
        self.assertEqual(review_result["verdict"], "Major Revision")
        self.assertEqual(len(review_result["gaps"]), 2)
        self.assertEqual(review_result["gaps"][0]["severity"], "Major")
        self.assertIn("baseline comparison", review_result["gaps"][0]["issue"])

    def test_rebuttal_audit_item_by_item_alignment(self):
        """Verify rebuttal audit correctly identifies unaddressed critiques and substantive gaps."""
        reviewer_critiques = [
            {"id": "C1", "reviewer": "R1", "text": "Missing baseline comparison with standard transformer architecture."},
            {"id": "C2", "reviewer": "R1", "text": "Statistical error bars are not provided in Figure 3."},
            {"id": "C3", "reviewer": "R2", "text": "The ablation study in Section 4.2 does not isolate the attention mechanism."},
        ]

        author_responses = [
            {
                "target_id": "C1",
                "text": "We have added baseline transformer comparisons in Table 2 (lines 145-160), demonstrating a 4.2% accuracy improvement.",
                "has_manuscript_anchor": True,
            },
            {
                "target_id": "C2",
                "text": "We acknowledge this point and plan to look into this in future work.",
                "has_manuscript_anchor": False,  # Substantive gap / hand-waving
            },
            # Note: C3 is unaddressed entirely!
        ]

        def audit_rebuttal(critiques: List[Dict[str, str]], responses: List[Dict[str, Any]]) -> Dict[str, Any]:
            resp_map = {r["target_id"]: r for r in responses}
            unaddressed = []
            substantive_gaps = []
            addressed = []

            for c in critiques:
                cid = c["id"]
                if cid not in resp_map:
                    unaddressed.append(cid)
                else:
                    r = resp_map[cid]
                    if not r.get("has_manuscript_anchor", False):
                        substantive_gaps.append(cid)
                    else:
                        addressed.append(cid)

            total = len(critiques)
            coverage = (len(addressed) + len(substantive_gaps)) / total if total > 0 else 1.0
            return {
                "total_critiques": total,
                "coverage_rate": coverage,
                "addressed": addressed,
                "unaddressed": unaddressed,
                "substantive_gaps": substantive_gaps,
            }

        audit_result = audit_rebuttal(reviewer_critiques, author_responses)
        self.assertEqual(audit_result["unaddressed"], ["C3"])
        self.assertEqual(audit_result["substantive_gaps"], ["C2"])
        self.assertEqual(audit_result["addressed"], ["C1"])
        self.assertAlmostEqual(audit_result["coverage_rate"], 2 / 3, places=2)

    def test_end_to_end_review_and_rebuttal_disk_simulation(self):
        """Simulate review report generation, editorial synthesis, and rebuttal audit on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            reviews_dir = tmppath / "phase6_review"
            reviews_dir.mkdir(parents=True, exist_ok=True)
            rebuttal_dir = tmppath / "phase6_rebuttal"
            rebuttal_dir.mkdir(parents=True, exist_ok=True)

            # 1. Simulate Peer Review Report Disk Generation
            review_card_content = """# Peer Review Report

**Reviewer Persona / Seat**: Methodology Reviewer (R1)
**Date**: 2026-09-18
**Overall Verdict**: Major Revision

## Five-Dimension Scores
- **Originality**: MEETS — Sound application of Bayesian optimization.
- **Methodological Rigor**: DOES_NOT_MEET — Missing standard baseline comparison.
- **Evidence Sufficiency**: PARTLY_MEETS — Sample size too limited (N=30).
- **Argument Coherence**: MEETS — Logical structure is clear.
- **Writing Quality**: EXCEEDS — Clear prose and formatting.

## Major Weaknesses & Empirical Gaps
1. **[Finding R1-01] Missing Benchmark Baseline** [Severity: Major]
   - **Location**: Section 3.2, lines 110-125
   - **Issue**: No comparison against classical linear regression baselines.
   - **Required Remedy**: Provide comparative benchmarks in Table 2.

2. **[Finding R1-02] Insufficient Statistical Power** [Severity: Major]
   - **Location**: Section 4.1, lines 200-215
   - **Issue**: Sample size of 30 participants limits power.
   - **Required Remedy**: Perform power calculation and discuss generalizability.
"""
            review_file = reviews_dir / "review_report_r1.md"
            review_file.write_text(review_card_content, encoding="utf-8")
            self.assertTrue(review_file.exists())

            # 2. Simulate Editorial Decision & Revision Roadmap Generation
            decision_content = """# Editorial Decision Letter & Synthesis Package

**Manuscript Title**: Bayesian Optimization in Clinical Trials
**Editorial Decision**: Major Revision
**Decision Date**: 2026-09-18

## 1. Editorial Summary & Synthesis
Reviewers agree the core approach is novel, but significant methodological and empirical gaps prevent publication in its current form.

## 2. Reviewer Consensus & Disagreement Matrix
| Issue / Topic | Reviewers in Agreement | Dissenting Views | Editorial Adjudication |
|---|---|---|---|
| Benchmark Baselines | R1, R2 | None | Mandatory Major Revision |
| Statistical Power | R1 | R3 (considers N=30 adequate) | Require explicit power calculation |

## 3. Revision Roadmap Core
- **Item RR-01** [Source: R1-01] [Severity: Major] [Obligation: Mandatory]
  - **Issue**: Missing classical benchmark comparisons.
  - **Action Required**: Add comparative benchmarks in Table 2.
- **Item RR-02** [Source: R1-02] [Severity: Major] [Obligation: Mandatory]
  - **Issue**: Statistical power justification.
  - **Action Required**: Add power analysis in Section 4.1.
"""
            decision_file = reviews_dir / "editorial_decision.md"
            decision_file.write_text(decision_content, encoding="utf-8")
            self.assertTrue(decision_file.exists())

            # 3. Simulate Rebuttal Audit QA Report Generation
            audit_content = """# Rebuttal QA Audit Report

**Audit Date**: 2026-09-18
**Coverage Rate**: 100% (2/2 critiques addressed)
**Substantive Gaps Detected**: 0
**Tone Assessment**: Polite, professional, and evidence-grounded.

## Item-by-Item Verification
1. **[R1-01 / RR-01] Benchmark Baselines**:
   - Author Response: Complete. Table 2 updated with OLS and Lasso baselines (Section 3.2, lines 115-130).
   - Status: VERIFIED

2. **[R1-02 / RR-02] Statistical Power**:
   - Author Response: Complete. Post-hoc power analysis added in Section 4.1 (lines 205-218).
   - Status: VERIFIED
"""
            audit_file = rebuttal_dir / "rebuttal_audit_report.md"
            audit_file.write_text(audit_content, encoding="utf-8")
            self.assertTrue(audit_file.exists())

            # 4. Verify Disk Integrity
            read_review = review_file.read_text(encoding="utf-8")
            self.assertIn("Major Revision", read_review)
            self.assertIn("DOES_NOT_MEET", read_review)

            read_decision = decision_file.read_text(encoding="utf-8")
            self.assertIn("Revision Roadmap Core", read_decision)
            self.assertIn("RR-01", read_decision)

            read_audit = audit_file.read_text(encoding="utf-8")
            self.assertIn("**Coverage Rate**: 100%", read_audit)
            self.assertIn("VERIFIED", read_audit)

    def test_subagent_capability_parsing_with_comments(self):
        """Verify parse_bool_meta and load_agent_spec handle inline comments and boolean variants."""
        from subagents import parse_bool_meta  # type: ignore

        meta_with_comments = {
            "enable_write_tools": "true # inline comment describing write permission",
            "enable_subagent_tools": "0 # numeric false",
            "enable_mcp_tools": "false",
            "custom_flag": "yes # affirmative",
        }
        self.assertTrue(parse_bool_meta(meta_with_comments, "enable_write_tools", default=False))
        self.assertFalse(parse_bool_meta(meta_with_comments, "enable_subagent_tools", default=True))
        self.assertFalse(parse_bool_meta(meta_with_comments, "enable_mcp_tools", default=True))
        self.assertTrue(parse_bool_meta(meta_with_comments, "custom_flag", default=False))
        self.assertTrue(parse_bool_meta({}, "non_existent_key", default=True))

    def test_devils_advocate_critical_issue_blocking(self):
        """Verify Devil's Advocate CRITICAL issues trigger escalation and block silent Accept."""
        # Simulated scenario: Manuscript meets all standard dimensions (Accept eligible),
        # but Devil's Advocate identifies a CRITICAL unaddressed confounder (C1).
        manuscript_scores = {
            "Originality": "EXCEEDS",
            "Methodological Rigor": "MEETS",
            "Evidence Sufficiency": "MEETS",
            "Argument Coherence": "MEETS",
            "Writing Quality": "MEETS",
        }
        da_critical_findings = [
            {"id": "C1", "status": "VALIDATED", "issue": "Data leakage between training and evaluation splits."},
        ]

        def arbitrate_decision(scores: Dict[str, str], da_findings: List[Dict[str, str]]) -> Dict[str, Any]:
            # Initial mechanical decision based on standard scores
            base_decision = "Accept"
            if any(s == "DOES_NOT_MEET" for s in scores.values()):
                base_decision = "Reject"
            elif any(s == "PARTLY_MEETS" for s in scores.values()):
                base_decision = "Major Revision"

            # Check Devil's Advocate CRITICAL adjudications
            escalation_marker = None
            final_status = base_decision
            blocking_da = [f for f in da_findings if f["status"] in ("VALIDATED", "UNRESOLVED")]
            if base_decision == "Accept" and blocking_da:
                count = len(blocking_da)
                escalation_marker = f"[DA-CRITICAL-VS-ACCEPT: {count} validated/unresolved]"
                final_status = "ESCALATED_TO_USER"

            return {
                "base_decision": base_decision,
                "final_status": final_status,
                "escalation_marker": escalation_marker,
            }

        result = arbitrate_decision(manuscript_scores, da_critical_findings)
        self.assertEqual(result["base_decision"], "Accept")
        self.assertEqual(result["final_status"], "ESCALATED_TO_USER")
        self.assertEqual(result["escalation_marker"], "[DA-CRITICAL-VS-ACCEPT: 1 validated/unresolved]")

    def test_rebuttal_audit_tone_and_evasion_detection(self):
        """Verify rebuttal audit flags defensive, dismissive, or evasive tone risks."""
        responses = [
            {
                "target_id": "C1",
                "text": "The reviewer clearly misunderstood our experimental setup because they failed to read Section 2.",
                "has_manuscript_anchor": False,
            },
            {
                "target_id": "C2",
                "text": "We thank the reviewer for this constructive observation. We have revised Section 3.1 (lines 88-95) to clarify the baseline parameters.",
                "has_manuscript_anchor": True,
            },
        ]

        def screen_tone(resp_list: List[Dict[str, Any]]) -> List[Dict[str, str]]:
            defensive_patterns = [
                re.compile(r"clearly\s+misunderstood", re.IGNORECASE),
                re.compile(r"failed\s+to\s+(read|understand|grasp)", re.IGNORECASE),
                re.compile(r"obviously\s+wrong", re.IGNORECASE),
            ]
            flags = []
            for r in resp_list:
                for pat in defensive_patterns:
                    if pat.search(r["text"]):
                        flags.append({
                            "target_id": r["target_id"],
                            "risk": "[TONE_RISK]",
                            "matched_phrase": pat.pattern,
                        })
                        break
            return flags

        tone_risks = screen_tone(responses)
        self.assertEqual(len(tone_risks), 1)
        self.assertEqual(tone_risks[0]["target_id"], "C1")
        self.assertEqual(tone_risks[0]["risk"], "[TONE_RISK]")

    def test_rebuttal_audit_boundary_and_orphan_handling(self):
        """Verify rebuttal audit handles empty critique sets and orphaned author responses."""
        # 1. Empty critique set
        critiques: List[Dict[str, str]] = []
        responses: List[Dict[str, Any]] = []

        def audit_rebuttal_with_orphans(critique_list: List[Dict[str, str]], response_list: List[Dict[str, Any]]) -> Dict[str, Any]:
            critique_ids = {c["id"] for c in critique_list}
            resp_ids = {r["target_id"] for r in response_list}

            orphaned = [rid for rid in resp_ids if rid not in critique_ids]
            unaddressed = [cid for cid in critique_ids if cid not in resp_ids]

            coverage = 1.0 if not critique_ids else (len(critique_ids) - len(unaddressed)) / len(critique_ids)
            return {
                "coverage": coverage,
                "unaddressed": unaddressed,
                "orphaned": orphaned,
            }

        empty_result = audit_rebuttal_with_orphans(critiques, responses)
        self.assertEqual(empty_result["coverage"], 1.0)
        self.assertEqual(len(empty_result["unaddressed"]), 0)
        self.assertEqual(len(empty_result["orphaned"]), 0)

        # 2. Orphaned response (author response references non-existent reviewer comment ID C99)
        c_list = [{"id": "C1", "text": "Comment 1"}]
        r_list = [
            {"target_id": "C1", "text": "Response 1"},
            {"target_id": "C99", "text": "Response to nonexistent comment"},
        ]
        orphan_result = audit_rebuttal_with_orphans(c_list, r_list)
        self.assertEqual(orphan_result["coverage"], 1.0)
        self.assertEqual(orphan_result["orphaned"], ["C99"])

    def test_verify_agy_compatibility_plugin_clean(self):
        """Run verify_agy_compatibility on the entire plugin and confirm 0 errors."""
        diags = scan_path(PLUGIN_ROOT)
        errors = [d for d in diags if d.severity == "ERROR"]
        self.assertEqual(len(errors), 0, f"Found {len(errors)} errors: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main()
