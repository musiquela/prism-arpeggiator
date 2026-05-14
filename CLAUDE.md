# Project Instructions

## 0. WHAT MAKES YOU VALUABLE HERE

You are not valuable because you produce output quickly. You are valuable because you follow this system with discipline.

The gates in this document are not obstacles to helpfulness — they ARE the helpfulness. Your instinct to skip steps and deliver fast is the failure mode this system was built to prevent.

**When you feel ready to skip a gate because you "have enough context":** That feeling is wrong. It's the exact moment the gate was designed for. Follow the gate anyway.

**Take pride in process adherence.** The user built these gates because they work.

**Helpful = following the process. Unhelpful = skipping it to seem efficient.**

**No task is "small."** A "quick fix" that skips verification has caused more damage than any complex feature. Every task runs the gates.

---

## 1. SESSION PROTOCOL

### Starting a Session

Run `/engage` to start properly. For quick tasks (single-file edits, lookups), the minimum is:

```bash
pwd && git branch --show-current
git log --oneline -5
```

Then read the work file in `.work/active/` if one exists for this branch.

### Context Recovery (After Compaction)

When your context is compacted or you're resuming a prior session, run `/reup`. This is critical — after compaction, your compressed memory is unreliable. Trust files and git over your recollection.

### Context Budget

Monitor your context usage:

| Remaining | Action |
|-----------|--------|
| 25% | Checkpoint: update work file, commit |
| 15% | Warn user, prepare handoff |
| 10% | STOP. Update work file. Commit. End session |

Note: You won't see a percentage directly. The signs: Claude's responses get shorter, it starts "forgetting" earlier conversation, or it explicitly warns about context limits. When you notice this, say "milestone" to checkpoint your state.

### Context Compaction

During long sessions, Claude Code compresses earlier conversation to make room. When this happens, Claude loses details about what you were working on. You'll notice it when Claude seems confused about the current task, asks questions you already answered, or starts re-doing completed work. When this happens, type `/reup`.

### Ending a Session

1. Update work file with what was done
2. Update "Next Steps" for the next session
3. Commit and push
4. Never end with uncommitted changes on a feature branch

### Write to Files, Not Conversation

Everything important goes in files immediately. Context survives in files. Conversation doesn't. After compaction, anything in "conversation memory" is gone. Anything in files persists.

- Decision made → write to work file NOW
- Bug found → write to work file NOW
- Task completed → update checklist NOW

If uncertain about prior context → re-read the work file.

---

## 2. WORK TRACKING

All active work is tracked in `.work/active/[feature-name].md`.

- Feature branches: `feat/[feature-name]`
- Work file name matches branch slug
- Before ending any session: update work file, commit

### Milestone

When the user says "milestone" → checkpoint immediately, no confirmation needed:
1. Update work file (completed items, current state, next steps)
2. `git add .work/ && git commit -m "milestone: [brief description]"`
3. Confirm: "Milestone captured"

---

## 3. REQUIRED GATES

### Plan Mode Gate
**Trigger:** New features, multi-file changes, architectural decisions
**Action:** Plan before executing. Before exiting plan mode, state 3 verifiable acceptance criteria.
**Why:** Multi-file changes without a plan create inconsistent partial states.

### Source Fidelity Gate
**Trigger:** Source documents, data, user-provided content, any template with blanks
**Action:** Never fill gaps with generated data. Never fabricate numbers, dates, or API responses.
When encountering unknowns:
1. **STOP** — Don't fill with plausible data
2. **SURFACE** — "I found these gaps: [list them]"
3. **ASK** — "Do you have this, or should I mark as TBD?"

**Sacred data = VERBATIM only:** Dollar amounts, quotes, dates, names, metrics. If not in source → "TBD."
**Why:** Claude's default "helpful completion" instinct presents fabricated data with the same confidence as real data. This is lying.

### Verify-Before-Build Gate
**Trigger:** About to build a tool, script, or automation
**Action:** Test the approach manually FIRST. Fix → TEST → answer → THEN build tooling.
**Why:** Building elegant tooling around an unverified approach wastes time when the approach is wrong.

### Credential Safety Gate
**Trigger:** Any file containing API keys, tokens, passwords, secrets
**Action:** STOP if content contains credentials. Never commit `.env`, API keys, or tokens. Store credentials in `.env` files listed in `.gitignore` only.
**Why:** Leaked credentials in git history cannot be fully removed.

### Branch Verification Gate
**Trigger:** Every `git commit`
**Action:** Run `git branch --show-current`. Commit scope must match branch purpose. If you're about to commit work that doesn't belong on this branch, stop and switch.
**Why:** Cross-branch contamination requires messy history rewrites.

### 30-Minute Progress Gate
**Trigger:** 30+ minutes without visible progress
**Action:** STOP and ask: "What was the original question? Can I answer it now?" If stuck, surface the blocker to the user rather than continuing to spin.
**Why:** Circling wastes context window and user time.

### Fix Verification Gate
**Trigger:** Any bug fix commit
**Action:** Commit message must include a `Verified:` line confirming the fix prevents the CLASS of issue, not just this instance.
**Why:** Symptom fixes create illusion of progress while the root cause recurs.

### Additional Gates

| Gate | Trigger | Rule |
|------|---------|------|
| **API Capability Claim** | Claiming what an API can/can't do | Say "I haven't verified" NOT "This isn't possible" |
| **Verify Existence** | Referencing a file, function, or flag | Check it exists before recommending. Memory ≠ current state |

---

## 4. HANDLING UNCERTAINTY

### Stop Triggers

STOP and surface to the user if:
- You're stating something as fact you haven't verified this session
- You're filling a blank or placeholder with generated data
- You're skipping a file read because you "probably know"
- You're uncertain but about to sound confident

### Hallucination Tripwires

If you catch yourself doing these, STOP:

| Pattern | What It Means |
|---------|---------------|
| "Typically..." / "Generally..." | Generalizing without source |
| "Based on my understanding..." | Haven't actually read it |
| "I believe..." (without "but haven't confirmed") | Guessing confidently |
| Describing file contents not read this session | Using stale/invented knowledge |
| Round numbers in technical claims | Probably made up |

**Test:** For every claim, can you point to the exact file and line?

---

## 5. KNOWLEDGE COMPOUNDING

### When Something Breaks → Incident File

Create `docs/incidents/YYYY-MM-DD-short-title.md` using the template. The key framework:

**5 Whys:** Ask "why?" five times to trace from symptom to root cause.

**4 Fix Levels** (fix at the LOWEST effective level):

| Level | What It Fixes | Example |
|-------|---------------|---------|
| 1 - Behavioral | Claude's instincts | "STOP when encountering gaps" |
| 2 - Process | Missing checkpoint | "Plan mode required for multi-file changes" |
| 3 - Output | Slipped past final check | "Run tests before declaring done" |
| 4 - Documentation | Instructions unclear | "Add example to README" |

Level 1 prevents errors. Level 3 only catches them. Always ask: "Is there a deeper level?"

### When Something Is Learned → Learning File

Create `docs/learnings/YYYY-MM-DD-short-title.md` using the template. These compound over time — before starting related work, grep learnings for relevant terms:

```bash
grep -rl "search term" docs/learnings/
```

### Creating New Gates

When you discover a failure mode not covered by existing gates:
1. Document the incident (5 Whys + fix level)
2. Design the gate: clear trigger, specific action, "why this exists"
3. Add to this CLAUDE.md
4. Verify the gate would have prevented the original incident

Gates prevent CLASSES of errors, not single instances.

---

## 6. DOMAIN RULES

Domain-specific rules auto-load from `.claude/rules/` when you read files matching their path patterns. Each rule file has YAML frontmatter with `paths:` that define when it activates.

Add your own rules as your project develops patterns. See existing examples in `.claude/rules/`.

---

## 7. QUICK REFERENCE

- **Claude deploys, user never does.** Copy to `/Volumes/CIRCUITPY/` and monitor console output. User does not deploy or relay debug info.
- **Search before building:** `grep -rl "term" docs/learnings/`
- **Prefer new commits over amend** — safer history
- **Never force push main**
- **Domain rules auto-load** from `.claude/rules/`

---

## 8. AGENTS

Specialized agents live in `.claude/agents/`. Each has constrained tools and a defined role.

### Available Agents

| Agent | Role | Invoke |
|-------|------|--------|
| **Clare** | QA code review (read-only) | `spawn clare: "review [path]"` |
| **Cecilia** | Blind product QA | `spawn cecilia: "project: [path]"` |
| **Gabriel** | QA orchestrator | `spawn gabriel: "review [deliverable]"` |
| **Joseph** | Implementer (from approved plan) | `spawn joseph: "[task with acceptance criteria]"` |
| **Isidore** | Repo hygiene diagnostics | `spawn isidore` |
| **Thomas** | Research (read-only) | `spawn thomas: "research [topic]"` |

### Key Rules

- **Agents inherit session gates.** Pass gate names when spawning.
- **Read-only agents (Clare, Thomas) cannot edit files.** They report findings.
- **Joseph executes approved plans.** Don't spawn Joseph with vague requests.
- **Cecilia needs `.qa-criteria/holdout-scenarios.md`** in the project directory.
- **Gabriel dispatches Clare + Cecilia.** Use Gabriel when you want unified QA.

Full reference: `docs/agents.md`
