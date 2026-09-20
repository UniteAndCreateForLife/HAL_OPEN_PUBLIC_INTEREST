# HAL SUPREME inventory and public/private classification

Snapshot date: 2026-09-20. This is a bounded inventory, not a claim that every
file in the large dirty checkout has been individually reviewed.

## Repository facts

| Fact | Evidence | Result |
| --- | --- | --- |
| Public GitHub repository exists | GitHub API read of `UniteAndCreateForLife/HAL_SUPREME` | public, default branch `main` |
| GitHub license metadata | GitHub API `license` endpoint | no license metadata detected |
| Local checkout remote | `git remote -v` | no configured remote |
| Local branch | `git branch --show-current` | `main` |
| Tracked files | `git ls-files` | 212 |
| Dirty entries | `git status --short` | 2,526 |
| Test files | `tests/test_*.py` top-level inventory | 525 |
| Root license | `Test-Path LICENSE` | absent |
| Root architecture file | `Test-Path ARCHITECTURE.md` | absent |

## Candidate modules

| Local path | Proposed classification | Why | Required review |
| --- | --- | --- | --- |
| `hal_providers/mesh.py` | candidate, not copied | provider-routing concepts may be reusable; implementation needs secret/network audit | API, license, dependency, and data-flow review |
| `hal_providers/types.py` | candidate, not copied | public contracts may be separable | inspect imports and private fields |
| `hal_cognition/event_store.py` | private / reference only | canonical HAL authority and historical data boundaries | do not copy database or private records |
| `hal_security/secret_broker.py` | private / reference only | credential boundary and implementation details | design a clean public interface instead |
| `scripts/hal_repo_intelligence.py` | candidate, not copied | inventory/reproducibility concept | inspect filesystem reach and output redaction |
| `tests/` | private / evidence source | broad tests may depend on private runtime, data, or credentials | extract only self-contained fixtures |
| `simulation/` | private / excluded | Godot embodiment, avatar, media, and live-show concerns | do not migrate into public-interest repo |
| `data/` | private / excluded | derived runtime state, receipts, and possible personal/live evidence | do not copy; redact examples |
| `scripts/hal_youtube_*` | private / excluded | public posting, credentials, browser automation, and external side effects | no migration |
| `hal_voice/`, `hal_vertical_life/` | private / excluded | voice, avatar, embodiment, and show systems | no migration |

## Current migration decision

No HAL SUPREME source file is copied into this draft. The minimal public slice
is independently implemented and deliberately narrower than the private
system. This avoids accidental leakage and avoids implying that a private
module is release-ready merely because it exists.
