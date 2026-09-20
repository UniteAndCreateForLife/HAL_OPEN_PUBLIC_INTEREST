# Architecture

## Design goal

Provide small, portable controls that make AI infrastructure inspectable and
locally governable without requiring the HAL SUPREME product or its private
runtime.

## Components

### LocalRoutePolicy

Accepts a list of non-secret route descriptions. A route is accepted only when
both conditions hold:

- its declared data residency is `local`; and
- its endpoint is loopback HTTP (`127.0.0.1`, `localhost`, or `::1`).

No provider is contacted. No credentials are read. If no route meets the
conditions, the result is a denial rather than an inferred fallback.

### AuditLedger

Appends JSONL records containing an event type, payload, timestamp, previous
hash, and event hash. The hash chain supports basic tamper evidence and makes
the provenance record portable. It is not a database, signing service,
authorization system, or proof of external truth.

## Authority boundary

This repository has no authority over HAL SUPREME's EventStore, WorkGraph,
provider registry, renderer, public posting, or live operations. Any future
adapter must be one-way and explicit. A projection or receipt must never be
treated as a replacement authority.

## Non-goals

- autonomous public posting;
- credential storage or OAuth;
- model training or model weights;
- voice, face, avatar, or private identity data;
- commercial media production;
- a second HAL orchestrator;
- a claim of sentience, consciousness, or general autonomy.
