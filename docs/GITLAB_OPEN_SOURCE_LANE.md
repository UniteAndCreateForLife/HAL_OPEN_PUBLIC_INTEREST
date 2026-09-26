# GitLab for Open Source lane

Status: prepared, not applied. Nothing here has been submitted.

## What the program offers

GitLab for Open Source grants a qualifying group GitLab Ultimate and 50,000
compute minutes per month. Membership renews every year; start the renewal at
least one month before it expires. The program page does not ask for a payment
method. Stop if any activation step asks for one.

Source: https://about.gitlab.com/solutions/open-source/join/ (checked 2026-09-25).

## Eligibility, in GitLab's words, and where this repository stands

| Requirement | Evidence in this repository |
|---|---|
| "Every project in your namespace must be published under an OSI-approved open source license" | `LICENSE` is Apache-2.0 |
| "Both your GitLab.com group or self-managed instance and your source code must be publicly visible and publicly available" | Public on GitHub; the GitLab group must be public too |
| The organization cannot "seek to make a profit by selling services, by charging for enhancements or add-ons, or by other means" | `SCOPE.md` excludes commercial media, monetization and HAL SUPREME product code; `README.md` and `GOVERNANCE.md` keep the commercial system separate |
| Only Free-tier groups you own; personal namespaces must be converted to a group | Create a new group used only for this repository |

The owner decides the eligibility attestation. Points to review first (from
`docs/DECISION_2026-09-20_LOCAL_ONLY.md`): scope, license, related-party
compensation (`CONFLICTS.md`), fiscal-host requirements (`BUDGET.md`), and the
fact that the same maintainer runs the commercial HAL SUPREME. HAL SUPREME
itself must never be placed in this group.

## Steps

Owner only (account and attestation steps):

1. Create a GitLab.com account, or sign in to an existing one.
2. Create a public top-level group used only for HAL Open Public Interest.
3. Apply through the GitLab for Open Source form and accept the program terms.

Either the owner or an agent with the owner's go-ahead:

4. Import this repository from GitHub into the group, public visibility. Before
   the first push, turn off CI/CD for the project (Settings > General >
   Visibility, project features, permissions > CI/CD), so no pipeline asks for
   card verification before the program is active.
5. After the coupon is active, turn CI/CD back on. `.gitlab-ci.yml` runs the
   Linux x64 and Linux Arm64 jobs automatically. Run the Windows and macOS jobs
   once by hand; make them automatic only after a green run.

## Zero-spend rules

- Standard hosted runners only: `saas-linux-small-amd64`,
  `saas-linux-small-arm64`, `saas-windows-medium-amd64`, and after approval
  `saas-macos-medium-m1`. Never larger, GPU or self-hosted runners.
- Never buy compute minutes. Never add a card for runner verification.
- No secrets or credential variables in CI/CD settings. No model or provider
  calls from CI.
