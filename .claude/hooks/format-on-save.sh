#!/bin/bash
# Auto-formats code after edits (Biome > Prettier > skip)
# Receives JSON from stdin with tool_input.file_path
# Hook runs on PostToolUse for Edit|Write|MultiEdit

# Read stdin (JSON input from Claude Code)
INPUT=$(cat)

# Extract file path from JSON
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE_PATH" ]] && exit 0
[[ ! -f "$FILE_PATH" ]] && exit 0

# Only format these extensions
EXT="${FILE_PATH##*.}"
case "$EXT" in
  ts|tsx|js|jsx|json|css|md|html)
    ;;
  *)
    exit 0
    ;;
esac

# Detect npx location (Homebrew, nvm, or system)
NPX=$(command -v npx 2>/dev/null || echo "/opt/homebrew/bin/npx")

# Walk up directory tree to find formatter config
SEARCH_DIR="$(dirname "$FILE_PATH")"
while [[ "$SEARCH_DIR" != "/" ]]; do
  if [[ -f "$SEARCH_DIR/biome.json" || -f "$SEARCH_DIR/biome.jsonc" ]]; then
    "$NPX" @biomejs/biome format --write "$FILE_PATH" 2>/dev/null
    exit 0
  elif [[ -f "$SEARCH_DIR/.prettierrc" || -f "$SEARCH_DIR/prettier.config.js" || -f "$SEARCH_DIR/.prettierrc.json" || -f "$SEARCH_DIR/.prettierrc.yaml" ]]; then
    "$NPX" prettier --write "$FILE_PATH" 2>/dev/null
    exit 0
  fi
  SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

# No formatter config found - exit silently
exit 0
