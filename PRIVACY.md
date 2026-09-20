# Privacy

The public-interest repository must not contain driver's-license images,
mailing addresses, API keys, browser profiles, OAuth tokens, private voice or
avatar assets, or other sensitive personal information.

Identity documents and mailing information must be provided only through a
secure intake channel designated by the fiscal host. They must not be sent in
ordinary email or committed to this repository.

The reference code records route metadata and audit payloads supplied by its
caller. Callers are responsible for excluding secrets and personal data from
payloads. Future releases need automated secret scanning, fixture redaction,
retention rules, and a documented data-subject deletion procedure.
