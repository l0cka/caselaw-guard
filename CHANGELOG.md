# Changelog

All notable changes to CaseLaw Guard will be documented in this file.

## Unreleased

## 0.3.0 — 2026-08-02

- Added a pinned AusLaw citation benchmark, approved full-index baseline and
  fail-closed coverage gate for future Australian index releases.
- Migrated the optional MCP integration to Python SDK v2 while preserving the
  `verify_case_law_text` tool and public verification report.
- Added `caselaw-guard au-index fetch VERSION --output PATH` for explicit,
  checksum-verified, size-bounded and atomic Australian index installation.
- Documented the 0.3.0 install, update, rollback, provenance and coverage
  limits without adding automatic index updates or legal analysis.

## 0.2.0 — 2026-08-01

- Consolidated OpenBench's Australian citation lookup, index builder and data
  provenance into CaseLaw Guard.
- Added parenthesised, bare-year, lower-case, pinpoint and alphanumeric-court
  Australian neutral citation handling.
- Added the canonical typed Australian index format, legacy flat-index loading
  and an explicit migration command.
- Added Australian index metadata, statistics and citation lookup routes to the
  CaseLaw Guard API.
- Preserved `caselaw-guard au-index build`, `--au-index` and
  `CASELAW_GUARD_AU_INDEX` without adding an `openbench` package dependency.

## 0.1.2

- Simplified README install and quickstart guidance.

## 0.1.1

- Fixed empty input verification so it returns a passing empty report instead of raising from citation extraction.
- Updated release documentation now that the package is published on PyPI.
- Added manual PyPI Trusted Publishing workflow automation.
- Added a manual v0.1 release checklist and expanded wheel smoke validation.
- Added optional Australian index verification metrics to the AusLaw benchmark harness.
- Improved Australian neutral citation extraction coverage for NSW tribunal and court codes surfaced by the AusLaw benchmark.
- Added a manual AusLaw Citation Benchmark extraction eval harness.
- Added Codex and Claude Code setup examples for the local MCP server.
- Added package build validation for future PyPI releases.
- Documented the intended PyPI Trusted Publishing path.

## 0.1.0

- Added fail-closed citation existence verification for plain text and Markdown.
- Added CLI, REST API, and local stdio MCP server entrypoints.
- Added CourtListener verification for U.S. citations.
- Added Australian neutral citation verification from a compact local index.
- Added an Australian index builder for Open Australian Legal Corpus JSONL exports.
- Added opt-in CourtListener lookup caching.
- Added CI, Dependabot, CODEOWNERS, security policy, and branch protection.
