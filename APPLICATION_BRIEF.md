# HAL Campus Evidence Desk — Global Smart Campus 2026

## Problem
Campus staff and students often need fast answers and routing across fragmented policies, facilities procedures, accessibility processes, academic rules, and privacy requirements. Generic assistants can answer without proving which policy controls, can guess when evidence is missing, and can over-automate sensitive cases.

## Target customer
Higher-education institutions that need a privacy-conscious, auditable assistant for campus operations, student support, academic-policy navigation, and internal service routing.

## Market need
The competition asks for practical, inclusive, secure, scalable campus technology. This MVP focuses on a concrete operational gap: turning questions and incidents into evidence-backed answers or human-reviewed actions without making unsupported decisions.

## MVP description
HAL Campus Evidence Desk is a bounded local prototype that ranks approved campus policy sources, returns citations, produces deterministic audit IDs, routes operational requests, and fails closed when evidence is absent or the request is sensitive.

The current runnable MVP demonstrates facilities routing, academic-policy evidence, sensitive-case human review, and refusal to invent an unknown parking policy.

## Demonstration
Run `python campus_mvp.py --demo`. The demo uses synthetic campus policy text and contains no student records or production institutional data.

Run `python -m unittest -v` for the deterministic regression suite.

## Current stage
Functional local MVP / pre-pilot competition prototype. No institutional deployment, customer adoption, paid revenue, clinical use, or production student-data use is claimed.

## Users, pilots, revenue, validation
No verified production users, pilots, or revenue are claimed. Current validation is deterministic software testing against synthetic policy/request fixtures. This section should be updated only from real receipts or documented pilots.

## Business model
Potential institutional licensing or support model for deployable campus workflows, with an open/public-interest core where appropriate. Commercial terms are not committed by this competition package.

## Pricing approach
Not fixed. A future pilot would first measure deployment/support cost and institutional value before proposing pricing. No price is represented as approved or offered.

## Technology architecture
Campus request -> evidence retrieval -> policy-ranked response -> action proposal -> human-approval gate -> append-only audit receipt. The competition MVP is dependency-light Python and can later connect to HAL SUPREME's WorkGraph/EventStore/Supervisor/ProviderMesh architecture rather than creating a second authority stack.

## Data privacy
Default to synthetic or institution-approved policy data, minimize personal data, avoid logging raw student identifiers, and keep sensitive cases out of autonomous resolution.

## Security
Fail closed on absent evidence, keep action suggestions separate from authorization, preserve deterministic audit identifiers, and require human review for sensitive categories. Production authentication, authorization, retention, and institutional security review remain deployment work.

## Responsible AI
The system is a support and workflow tool, not a decision authority. It cites controlling evidence, escalates ambiguity, routes sensitive matters to trained humans, and does not make diagnostic, disciplinary, immigration, or other high-stakes determinations.

## Scale-up plan
1. Replace synthetic fixtures with institution-approved policy corpora.
2. Add role-based authentication and institution-specific authorization.
3. Connect ticketing/LMS/SIS adapters through explicit permissions.
4. Add measured retrieval quality, task-completion, latency, and escalation metrics.
5. Pilot one bounded campus workflow before expanding across departments.

## Founder / core team
HAL SUPREME / UniteAndCreateForLife is currently represented here as an early-stage founder-led technology project. Final identity, turnover, startup representation, travel, tax, and other eligibility attestations remain human-only form steps and are not asserted by this artifact.

## Differentiation
This is deliberately not another free-form campus chatbot. The differentiator is provenance-first routing: every autonomous answer needs policy evidence, operational actions remain proposals until approved, sensitive requests fail closed, and the same audit contract can later plug into HAL's durable task/history/supervisor architecture.

## Competition evidence status
Organizer email confirms the HAL project is eligible for the startup track and that solo founders can participate. The official challenge page lists an October 5, 2026 submission deadline and INR 50,000 startup winner prize. No application submission, finalist status, award, procurement, funding, or payment is claimed.

## Submission requirement cross-check
- Live or recorded demonstration: current local deterministic CLI demo; recorded presentation not yet produced.
- Users/pilots/revenue/validation where available: no verified users, pilots, or revenue; software validation only.
- Responsible-AI considerations: evidence citation, fail-closed ambiguity handling, sensitive-case escalation, and human authorization.
- Founder/core-team profile: founder-led HAL SUPREME / UniteAndCreateForLife project; final personal/startup attestations remain human-only.
