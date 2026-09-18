# Product Guidelines

## Core Principles
1. **Human-First Integrity:** The AI is an augmenting copilot, never an autonomous surrogate. Critical decisions—hypothesis formulation, research question definitions, and final review determinations—must remain under human control.
2. **Fail-Closed Verification:** Verification gates must block progression on unverified or hallucinated claims. If a citation cannot be anchored or a claim lacks empirical support, it must be flagged with explicit severity (e.g., HIGH-WARN) rather than silently smoothed over.
3. **Reproducibility & Traceability:** All pipeline transformations, citation lookups, and simulated review rounds must produce structured, auditable artifacts (e.g., Material Passports, R&R matrices).

## Prose & Tone
- **Scholarly & Objective:** Formal academic English or native academic equivalents without hyperbolic marketing language or speculative jargon.
- **Anti-Synthetic Phrasing:** Actively avoid repetitive LLM marker phrases (e.g., "delve", "testament", "tapestry", "in conclusion it is important to remember"). Use active, precise verbs.
- **Epistemic Modesty:** Clearly delineate between established literature, speculative hypotheses, and preliminary empirical findings. Avoid unjustified certainty.

## Agent & Interaction Design
- **Socratic Engagement:** Prefer guided, iterative questioning when establishing requirements, paper outlines, or track definitions over one-shot speculative generation.
- **Read-Only Peer Reviews:** Reviewer agents must operate under read-only constraints to prevent bias leakage or unvetted self-modifications during evaluation cycles.
- **Transparent Boundaries:** Always declare limitations, assumptions, and tool dependencies explicitly in generated artifacts and stage outputs.
