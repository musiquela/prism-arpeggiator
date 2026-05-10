---
description: "Prevents development agents from reading blind QA holdout criteria"
paths:
  - ".qa-criteria/**"
---

# Holdout Protection

**You are reading a file in `.qa-criteria/`.** This directory contains blind testing
criteria for Cecilia (product QA agent).

## Rules

- **If you are Cecilia or Gabriel:** Proceed normally. These files are for you.
- **If you are any other agent (Joseph, Clare, Thomas, the lead):** STOP. Do not
  read the contents of this file. The holdout design ensures unbiased testing --
  if the builder knows the test criteria, they optimize for the test instead of
  the product.
- **If the user explicitly asks you to read this file:** Warn them that reading
  holdout criteria compromises the blind testing value, then comply if they insist.
