from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from caselaw_guard.adapters import build_adapters
from caselaw_guard.australia.index_builder import migrate_index, write_index
from caselaw_guard.australia.index_store import IndexStore
from caselaw_guard.verifier import verify_text

app = typer.Typer(help="Verify case-law citation existence and fail closed on unresolved authorities.")
au_index_app = typer.Typer(help="Build and inspect Australian citation indexes.")


@app.callback()
def main() -> None:
    """Case-law citation verification tools."""


@app.command()
def verify(
    path: Annotated[str, typer.Argument(help="Path to a .txt/.md file, or '-' for stdin.")],
    courtlistener_token: Annotated[
        str | None,
        typer.Option(
            "--courtlistener-token",
            help="CourtListener API token. Defaults to CASELAW_GUARD_COURTLISTENER_TOKEN.",
        ),
    ] = None,
    no_courtlistener: Annotated[
        bool,
        typer.Option("--no-courtlistener", help="Disable the CourtListener adapter."),
    ] = False,
    au_index: Annotated[
        Path | None,
        typer.Option("--au-index", help="Path to an Open Australian Legal Corpus metadata index JSON file."),
    ] = None,
    cache: Annotated[
        Path | None,
        typer.Option("--cache", help="Opt-in persistent CourtListener cache path."),
    ] = None,
    cache_ttl_days: Annotated[
        int | None,
        typer.Option("--cache-ttl-days", help="Number of days before cached CourtListener lookups expire."),
    ] = None,
) -> None:
    text = _read_input(path)
    adapters = build_adapters(
        courtlistener_token=courtlistener_token,
        no_courtlistener=no_courtlistener,
        au_index=au_index,
        cache_path=cache,
        cache_ttl_days=cache_ttl_days,
    )
    report = verify_text(text, adapters=adapters)
    typer.echo(json.dumps(report.model_dump(by_alias=True), indent=2, default=str))
    raise typer.Exit(code=0 if report.pass_ else 1)


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()

    file_path = Path(path)
    if file_path.suffix.lower() not in {".txt", ".md"}:
        raise typer.BadParameter("Only .txt, .md, and stdin inputs are supported in v0.")
    return file_path.read_text(encoding="utf-8")


@au_index_app.command("build")
def build_au_index(
    corpus_jsonl: Annotated[Path, typer.Argument(help="Path to an Open Australian Legal Corpus corpus.jsonl file.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Path for the compact CaseLaw Guard index JSON.")],
    index_version: Annotated[
        str | None,
        typer.Option("--index-version", help="Version recorded in index metadata."),
    ] = None,
    dataset_revision: Annotated[
        str | None,
        typer.Option("--dataset-revision", help="Upstream dataset revision, or omit to record 'unknown'."),
    ] = None,
) -> None:
    index = write_index(
        corpus_jsonl,
        output,
        index_version=index_version,
        dataset_revision=dataset_revision,
    )
    typer.echo(json.dumps(index.model_dump(mode="json", exclude={"entries"}), indent=2))


@au_index_app.command("stats")
def stats_au_index(
    index: Annotated[Path, typer.Argument(help="Path to a canonical or legacy Australian index JSON file.")],
) -> None:
    stats = IndexStore.load(index).stats()
    typer.echo(json.dumps(stats.model_dump(mode="json"), indent=2))


@au_index_app.command("migrate")
def migrate_au_index(
    input_path: Annotated[Path, typer.Argument(help="Path to a canonical or legacy Australian index JSON file.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Path for the canonical migrated index JSON.")],
) -> None:
    index = migrate_index(input_path, output)
    typer.echo(json.dumps(index.model_dump(mode="json", exclude={"entries"}), indent=2))


app.add_typer(au_index_app, name="au-index")


if __name__ == "__main__":
    app()
