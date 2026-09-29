# ragentledger prototype

This directory is a bounded proof-of-concept for an R Consortium ISC proposal.
It is **not** presented as a released CRAN package or production security tool.

## Problem being tested

R now has strong tools for package/environment reproducibility (`renv`),
pipeline state (`targets`), and model/tool calling (`ellmer`). This prototype
tests a complementary layer: a portable, R-native receipt for AI model and tool
events that can be inspected independently of the provider.

The initial schema records:

- event type and UTC timestamp;
- workflow/run identifier;
- model and/or tool identifiers;
- event-specific payload;
- previous record hash; and
- current SHA-256 record hash.

`ragent_verify()` checks the chain and reports the first invalid record.

## Explicit limits

The chain is tamper-evident, not digitally signed. It does not prove external
truth, prevent a malicious process from replacing an entire ledger, preserve
secrets safely by itself, or recreate provider-side state. Payload redaction and
privacy rules are part of the proposed grant work.

## Proposed next steps

1. formalize a versioned schema and redaction policy;
2. add wrappers/hooks for common R AI workflows, beginning with `ellmer`;
3. add optional `targets` integration so receipts can be emitted alongside
   pipeline metadata;
4. add replay/export helpers and failure/uncertainty fields;
5. build tests, documentation, vignettes, and examples with no required hosted
   service.

The wider public-interest repository already contains a tested Python
implementation of fail-closed local routing and a hash-linked audit ledger.
This R prototype is an independent R-facing experiment rather than a claim that
the Python implementation is directly reusable as an R package.
