# Security policy

## Supported versions

Only the latest tagged release receives security fixes during v1.

## Reporting a vulnerability

Please do not open a public issue for security problems. Instead, email
security@openbench.invalid with:

- a description of the issue
- steps to reproduce
- the openbench version (`uv run openbench --version` once available, or commit SHA)

We will respond within 7 days. Once a fix is ready we will coordinate disclosure.

## Scope

In scope:
- The openbench API and CLI source code in this repository.
- Index file handling and parsing.

Out of scope:
- The upstream Open Australian Legal Corpus (report to Isaacus).
- Self-hosted deployments not maintained by this project.
- Issues that require an attacker with local file write access.
