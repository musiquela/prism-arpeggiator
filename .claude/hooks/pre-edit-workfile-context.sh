#!/bin/bash
# Pre-tool context injection: surfaces active work file before Write/Edit.
# Ensures Claude knows what it's supposed to be doing before every edit.
# Hook: PreToolUse | Matcher: Write|Edit|MultiEdit
# Exit 0 = allow (with additionalContext injected)

INPUT=$(cat)

# Check for jq — required for JSON parsing
if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found. Install with 'brew install jq' for work file context injection." >&2
  exit 0
fi

TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)

# Only inject context for file-modifying tools
case "$TOOL" in
  Write|Edit|MultiEdit) ;;
  *) exit 0 ;;
esac

# Determine active work file from git branch
BRANCH=$(git branch --show-current 2>/dev/null)
WORK_DIR="${CLAUDE_PROJECT_DIR:-.}/.work/active"

# Strategy: match branch name to work file, fallback to most recent
WORK_FILE=""
if [[ -n "$BRANCH" && "$BRANCH" != "main" ]]; then
  # Branch "feat/add-auth" → look for *add-auth* work file
  BRANCH_SLUG=$(echo "$BRANCH" | sed 's|^[^/]*/||')
  WORK_FILE=$(find "$WORK_DIR" -name "*${BRANCH_SLUG}*" -type f 2>/dev/null | head -1)
fi

# Fallback: most recently modified work file
if [[ -z "$WORK_FILE" ]]; then
  WORK_FILE=$(find "$WORK_DIR" -name "*.md" -type f 2>/dev/null -exec stat -f '%m %N' {} + 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
fi

# No work file found — allow silently
[[ -z "$WORK_FILE" || ! -f "$WORK_FILE" ]] && exit 0

# Extract "Next Steps" or "Status" section (keep context concise)
# Look for ## Next Steps, ## Status, ## Current, or last ## section
CONTEXT=""

# Try extracting Next Steps section first
CONTEXT=$(awk '/^##[[:space:]]+(Next Steps|Status|Current|TODO)/{found=1; next} found && /^##[[:space:]]/{exit} found{print}' "$WORK_FILE" 2>/dev/null | head -20)

# Fallback: last 10 lines of the file (usually contains recent state)
if [[ -z "$CONTEXT" ]]; then
  CONTEXT=$(tail -10 "$WORK_FILE" 2>/dev/null)
fi

[[ -z "$CONTEXT" ]] && exit 0

# Inject as additionalContext — Claude sees this before executing the tool
BASENAME=$(basename "$WORK_FILE")
jq -n --arg ctx "Active work file ($BASENAME): $CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    additionalContext: $ctx
  }
}'

exit 0
