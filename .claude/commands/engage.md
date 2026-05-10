You are starting a work session. Complete every step before doing work.

**Proportionality:** For single-file edits or quick lookups, complete Steps 1 and 2 only. For multi-file changes, new features, or anything touching production: complete every step.

**Step 1 — Ground truth**
Run `pwd && git branch --show-current && git log --oneline -5 && git status -s | head -20`.
Report: what branch, any uncommitted work, recent commit history.

**Step 2 — Work file**
Check `.work/active/` for any file matching the current branch or work described. If one exists, read it and state what "Next Steps" says. If none exists and this is non-trivial work, you will create one after this checklist.

**Step 3 — Gate identification**
Open CLAUDE.md Section 3 (Required Gates). For the work described, list each gate that applies and what it requires before acting.

**Step 4 — Learnings search**
Search `docs/learnings/` for terms related to this work. Use at least 2 search terms. List relevant learnings and what each warns about. If none found, state "No relevant learnings found for: [terms]" and move on.

**Step 5 — State your plan**
State in your own words:
- What work is being done
- Which gates apply
- Your first concrete action
- This sentence: "If I feel ready to skip a gate because I have enough context, I will stop and re-read the gate before proceeding."

Then ask: "Ready to begin, or should I adjust?"
