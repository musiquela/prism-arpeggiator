---
description: "Test verification before claiming tests pass"
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "__tests__/**"
  - "tests/**"
  - "test/**"
---

# Testing Verification Gate

**Trigger:** Any work involving tests or test-adjacent code.

**Before claiming tests pass:**
1. Actually RUN the tests — do not claim passing from reading test files
2. If a test fails, investigate — do not comment it out or mark as skipped without user approval
3. New features require new tests. Bug fixes require regression tests.

**When tests fail unexpectedly:**
- Read the failure message carefully
- Check if the failure is in your changes or pre-existing
- Surface pre-existing failures to the user rather than fixing silently
