# Data sources

## Primary source

**Open Australian Legal Corpus** by Isaacus.

- Dataset: <https://huggingface.co/datasets/isaacus/open-australian-legal-corpus>
- Licence: CC-BY-4.0 — <https://creativecommons.org/licenses/by/4.0/>
- Update cadence: irregular. openbench treats each build as a snapshot and surfaces freshness via `/v1/au/index/metadata` (`generated_at`, `dataset_version`).

### Modifications by openbench

- Filtered to records where `type == "decision"`.
- Extracted neutral citation, case name, court, jurisdiction, date, and source URL — discarded full judgment text.
- Normalised neutral citations to canonical `[YYYY] COURT N` form.
- Deduplicated records sharing `(normalized_citation, case_name, date)`.

### Required attribution

Any redistribution of an openbench index must include:

> Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction, normalisation, deduplication).

This attribution is automatically embedded in every API response's `provenance.attribution` field and in `/v1/au/index/metadata`.

## Disclaimers

- openbench is not affiliated with any court, government, or the Isaacus team.
- openbench does not provide legal advice. Use authorised sources for substantive matters.
- A `not_found` response only proves the citation is not present in the configured index.
