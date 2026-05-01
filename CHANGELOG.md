# Changelog

All notable changes to CaseLaw Guard will be documented in this file.

## Unreleased

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
