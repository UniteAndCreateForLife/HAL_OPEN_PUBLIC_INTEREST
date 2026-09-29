# Vercel Open Source Program Readiness

**Prepared:** 2026-09-29  
**Purpose:** track public requirements and evidence for a future Vercel Open Source Program application.  
**Status:** applications are currently closed; this document is preparation only.

## Current public program criteria

The current Vercel Open Source Program page says projects should:

1. be open source and actively developed/maintained;
2. be hosted on Vercel or intend to host on Vercel;
3. show measurable impact or growth potential;
4. follow a Code of Conduct that defines community standards;
5. use program credits exclusively for open-source work and the project itself.

Official program page: https://vercel.com/open-source-program

## Repository readiness matrix

| Criterion | Current state | Evidence / next action |
| --- | --- | --- |
| Open source | Ready | Apache-2.0 `LICENSE`; public repository |
| Active development | Evidence exists | Dated release-readiness records, tests, public work; continue publishing bounded changes |
| Hosted/intended on Vercel | Preparation required | Build one public, synthetic-data-only Vercel demonstration rather than moving private HAL state |
| Measurable impact/growth potential | Needs stronger public metrics | Track forks/stars/contributors/downloads/demo use only from verifiable sources |
| Code of Conduct | Added in this readiness branch | `CODE_OF_CONDUCT.md` |
| Credits restricted to OSS work | Policy can be stated | Any future Vercel credits for this application must be isolated to this public project and its public demo |

## Appropriate Vercel-hosted proof

The Vercel-hosted component should remain deliberately small and public-safe:

- a read-only browser/API demonstration of the repository's local-route and provenance concepts;
- synthetic inputs only;
- no production HAL credentials, private endpoints, identity data, voice/avatar state, commercial media assets, or private work orders;
- no claim that hosting a demonstration changes the repository's local-first policy primitives;
- no external model call required for the first deployment.

A later optional AI demonstration can use Vercel AI Gateway only if it remains clearly separated from the local-only routing example and does not weaken the fail-closed contract.

## Evidence to collect before applying

- public deployment URL;
- exact deployment source commit;
- deterministic test output tied to that commit;
- screenshot/video of the public synthetic demo;
- repository activity metrics captured with date/source;
- issue/contributor/community activity if present;
- explicit statement that credits are used only for this open-source project;
- current `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE`;
- short explanation of independent public benefit.

## Application positioning

HAL Open Local AI is not a mirror of the private HAL SUPREME product. It is a small public-interest repository for inspectable local/private AI infrastructure primitives. The application should emphasize reproducibility, data-locality controls, provenance, evidence-bound development, and the fact that the public project is useful independently of HAL's commercial/private systems.

## Do not claim

Until direct evidence exists, do not claim:

- acceptance into the Vercel Open Source Program;
- that the project is currently hosted on Vercel;
- user, contributor, traffic, or adoption numbers;
- that Vercel has reviewed or endorsed the architecture;
- that the broader HAL SUPREME system is open source or covered by this application.