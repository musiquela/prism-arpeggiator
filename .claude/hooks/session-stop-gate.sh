#!/bin/bash
# Session stop gate: blocks session end if work items incomplete or uncommitted.
# Hook: Stop | Exit 2 = BLOCK (stderr shown to Claude) | Exit 0 = allow
#
# Checks:
#   1. Uncommitted changes on disk (feature branches only)
#   2. Incomplete items in active work file
#   3. Work file "Next Steps" section exists (session continuity)

INPUT=$(cat)

# Safety: prevent infinite loop — if already triggered once, let it go
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
if [[ "$STOP_ACTIVE" == "true" ]]; then
  exit 0
fi

WARNINGS=""
BLOCKS=""
BRANCH=$(git branch --show-current 2>/dev/null)

# --- Check 1: Uncommitted changes on feature branches ---
# On main, you may have experimental uncommitted files — don't block.
# Feature branches should be clean before ending a session.
if [[ -n "$BRANCH" && "$BRANCH" != "main" ]]; then
  MODIFIED=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
  STAGED=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  TOTAL=$((MODIFIED + STAGED))
  if [[ "$TOTAL" -gt 0 ]]; then
    BLOCKS="${BLOCKS}UNCOMMITTED: ${TOTAL} modified/staged file(s) on branch '${BRANCH}'. Commit before ending session.\n"
  fi
fi

# --- Check 2: Incomplete work items in active work file ---
WORK_DIR="${CLAUDE_PROJECT_DIR:-.}/.work/active"

WORK_FILE=""
if [[ -n "$BRANCH" && "$BRANCH" != "main" ]]; then
  BRANCH_SLUG=$(echo "$BRANCH" | sed 's|^[^/]*/||')
  WORK_FILE=$(find "$WORK_DIR" -name "*${BRANCH_SLUG}*" -type f 2>/dev/null | head -1)
fi

# On main: skip work file check — no single work file owns the session
if [[ -n "$WORK_FILE" && -f "$WORK_FILE" ]]; then
  INCOMPLETE=$(grep -c '^\- \[ \]' "$WORK_FILE" 2>/dev/null | tr -d '[:space:]')
  INCOMPLETE=${INCOMPLETE:-0}
  COMPLETE=$(grep -c '^\- \[x\]' "$WORK_FILE" 2>/dev/null | tr -d '[:space:]')
  COMPLETE=${COMPLETE:-0}

  if [[ "$INCOMPLETE" -gt 0 ]]; then
    WARNINGS="${WARNINGS}WORK_ITEMS: ${INCOMPLETE} incomplete / ${COMPLETE} complete in $(basename "$WORK_FILE"). Update work file status before ending.\n"
  fi

  # --- Check 3: Next Steps section exists ---
  HAS_NEXT=$(grep -c '## Next Steps' "$WORK_FILE" 2>/dev/null | tr -d '[:space:]')
  HAS_NEXT=${HAS_NEXT:-0}
  if [[ "$HAS_NEXT" -eq 0 ]]; then
    WARNINGS="${WARNINGS}NO_NEXT_STEPS: Work file $(basename "$WORK_FILE") has no '## Next Steps' section. Add for session continuity.\n"
  fi
fi

# --- Decision ---
if [[ -n "$BLOCKS" ]]; then
  echo -e "SESSION STOP BLOCKED:\n${BLOCKS}${WARNINGS}" >&2
  exit 2
fi

if [[ -n "$WARNINGS" ]]; then
  echo -e "SESSION STOP WARNINGS (non-blocking):\n${WARNINGS}" >&2
  exit 0
fi

exit 0
