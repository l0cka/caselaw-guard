# Data sources

## Open Australian Legal Corpus

CaseLaw Guard builds its Australian citation index from the
[Open Australian Legal Corpus](https://huggingface.co/datasets/isaacus/open-australian-legal-corpus)
by Isaacus.

- **Licence:** [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
- **Update cadence:** irregular
- **Dataset revision:** recorded in each index when available, otherwise
  `unknown`

### Changes made by CaseLaw Guard

CaseLaw Guard:

- keeps records where `type == "decision"`;
- extracts citation, case name, court, jurisdiction, date and source metadata;
- discards the full judgment text;
- normalises neutral citations to `[YYYY] COURT N`; and
- deduplicates records that share a citation, case name and date.

### Attribution

Each index redistribution must include:

> Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw
> Guard (metadata extraction, normalisation and deduplication).

CaseLaw Guard embeds the same statement in index metadata and Australian lookup
results.

## AusLaw Citation Benchmark

The reproducible coverage harness uses the `test` split of
[auslawbench/AusLaw-Citation-Benchmark](https://huggingface.co/datasets/auslawbench/AusLaw-Citation-Benchmark).

- **Licence:** [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
- **Rows:** 1,000
- **Revision:** `fabee289f2a5bbfb3c6476be55084abe426f6f18`
- **File:** `roc_test.json`
- **SHA-256:** `154d272792778df49c01814d9e864121fcca3828df5f23c6ace90e992effb005`

The harness downloads the file from that immutable revision, verifies the
digest before caching it, and records the dataset, split, revision, file,
digest and licence in each report. The benchmark measures citation extraction
and snapshot verification; it does not measure proposition support or whether
a case remains good law.

## Limits

The Australian index is a snapshot of its configured source. A `not_found`
result means only that the citation is absent from that snapshot. Verify
important matters against an authorised source.

CaseLaw Guard is not affiliated with Isaacus, a court or a government body. It
does not provide legal advice.
