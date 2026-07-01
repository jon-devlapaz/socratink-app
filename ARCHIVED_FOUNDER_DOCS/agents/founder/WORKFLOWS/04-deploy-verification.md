# Deploy Verification

## Trigger

Any request to verify that a just-pushed commit is actually live on production, confirm whether a deploy succeeded, or answer "is prod ready?" for a specific publication.

## Goal

Wait for the intended production deployment to finish, then run the browser smoke against the live site so the verdict is about the new code, not the previous deploy.

## Inputs To Inspect

- target SHA, if provided
- whether the target should default to `origin/main` or `HEAD`
- production base URL
- GitHub repo slug used by the deployment poller
- PR checks, main preflight, Vercel deployment status, and any unrelated red GitHub workflows that could confuse the release verdict
- wrapper exit code
- smoke test output when a failure occurs

## Risk Classification

- `safe`: determining the target SHA, polling deployment status, running production smoke, reporting the result
- `confirm`: sharing or promoting a deployment result as release-ready
- `hard-confirm`: none in v1; this workflow verifies state but does not mutate production

## Recommended Route

Use the wrapper instead of stitching the steps together manually:

1. resolve the intended SHA
2. run `bash scripts/verify-deploy.sh`, optionally with `<sha>` or `HEAD`
3. let the wrapper wait for the matching Vercel production deployment
4. let the wrapper run `scripts/qa-smoke.sh` against production only after deploy success
5. report the result in the standard verification format

Use direct `bash scripts/qa-smoke.sh live` only when the question is generic production health and not "did this specific deploy go live correctly?"

## Required Confirmation

- do not claim a deploy is live based only on `git push`
- do not substitute a local or pre-deploy smoke result for production verification
- do not conflate Vercel production deploy status with unrelated GitHub workflows; inspect red signals, label their scope, and state whether they are part of the production app path
- if the wrapper reports failure, timeout, or smoke regression, treat that as a blocker until explicitly reframed

## Verification

- target SHA is stated explicitly
- if the verification follows a PR merge, the merge SHA is stated separately from the pre-merge branch head
- Vercel result is one of `success`, `failure`, or `timeout`
- production smoke is run only after deploy success
- unrelated red workflows, such as GitHub Pages/Jekyll, are reported separately from the Vercel app verdict after inspection
- failure reports include either the offending pytest output or the Vercel inspect URL
- the final summary clearly distinguishes deploy status from smoke status

## Stop Rules

- stop if the wrapper cannot resolve or accept the intended SHA
- stop if the deploy times out and no one has checked whether Vercel is still building
- stop if the smoke fails; do not reframe it as "mostly live"
- stop if the environment lacks the required CLI/auth dependencies and the harness error is still untriaged

## Artifact Destination

- shared workflow truth: this file
- executable enforcement and polling logic: `scripts/verify-deploy.sh`
- runtime evidence: production smoke output and wrapper stdout
