Your context was just compacted. Your compressed memory is unreliable — you may believe you know the current state, but you do not. Trust files and git over your recollection.

Complete every step before your next action.

**Step 1 — Ground truth**
Run `git log --oneline -10` and `git status -s | head -20`. State exactly what has been committed and what is uncommitted. Do not describe what you "were working on" — describe what git shows.

**Step 2 — Work file**
Read the active work file in `.work/active/`. Compare its "Next Steps" against git history. Which steps are already committed? Which is actually next? If the work file is stale or conflicts with git state, say so explicitly.

**Step 3 — Re-derive gates**
Do NOT try to recall what gates you were following. Open CLAUDE.md Section 3 now. Based on the current branch and uncommitted files, identify which gates apply.

**Step 4 — State your position**
State in your own words:
- What work is in progress (based on git and work file, not memory)
- Which gates apply (from Step 3)
- Your next concrete action
- This sentence: "If I feel ready to skip a gate because I have enough context, I will stop and re-read the gate before proceeding."

**Conflict rule:** If the work file and git state conflict — state the conflict and ask. Do not resolve silently.

Then ask: "Proceeding — correct?"
