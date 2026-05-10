---
description: "Safety gates for production deployments"
paths:
  - "deploy/**"
  - ".github/workflows/**"
  - "infrastructure/**"
  - "Dockerfile"
  - "docker-compose*.yml"
---

# Deployment Safety Gate

**Trigger:** Any file change that affects production deployment.

**Before deploying to production:**
1. Run the full test suite — do not skip failing tests
2. Verify the build succeeds locally
3. After deployment, verify the deployment works (hit an endpoint, check the UI, confirm the app starts)
4. Never declare "deployed" based on a CI/CD pipeline passing — verify the actual running application

**If deployment fails:**
- Do not retry blindly — read the error
- Check if the failure is in your code or the deployment infrastructure
- Roll back if the production app is broken, then debug
