# Security

## Current guarantees of the minimal slice

- no network requests;
- no credential reads;
- no subprocess execution;
- no model loading;
- explicit loopback/local route requirement;
- JSONL audit records are hash-linked for basic tamper evidence.

## Threats to address before a hosted release

- malicious or misleading route metadata;
- path traversal and unsafe audit paths;
- concurrent writers and partial records;
- replay or truncation of audit logs;
- secret leakage through payloads or logs;
- dependency and supply-chain compromise;
- confused-deputy adapters that turn projections into authority.

## Release requirements

Run tests, static checks, dependency review, secret scanning, malformed-input
tests, and an independent security review. Do not describe the hash chain as
cryptographic signing or as proof that an external action occurred.
