# Dependency and license inventory

Snapshot date: 2026-09-20.

| Layer | Dependency | Version constraint | License / status | Evidence |
| --- | --- | --- | --- | --- |
| Runtime | Python standard library | Python >= 3.11 | Python license terms apply | `src/hal_public_interest/audit.py` imports only stdlib modules |
| Tests | pytest | environment-provided | test-only; version and license must be recorded in release CI | `pyproject.toml` test configuration and validation command |
| Build | setuptools | >= 68 | build-only; version and license must be recorded in release CI | `pyproject.toml` build-system |

No model weights, media, fonts, browser profiles, credentials, or external
source packages are included in this draft. This inventory is a first-pass
manifest, not a substitute for a lockfile, SBOM, or legal license review.

Before publication, generate a fresh environment report containing exact
versions and license metadata, then attach it to the release receipt.
