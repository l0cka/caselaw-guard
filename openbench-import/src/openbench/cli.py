"""openbench CLI: build indexes, inspect stats, run the API."""

import json
from pathlib import Path

import typer
import uvicorn

from openbench.api import create_app
from openbench.index_builder import build_index
from openbench.index_store import IndexStore

app = typer.Typer(no_args_is_help=True, add_completion=False)
index_app = typer.Typer(no_args_is_help=True, help="Build and inspect openbench indexes.")
app.add_typer(index_app, name="index")


@index_app.command("build")
def index_build(
    corpus: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    output: Path = typer.Option(Path("index.json"), "--output", "-o"),
    index_version: str | None = typer.Option(None, "--index-version"),
) -> None:
    """Build an index from a JSONL corpus file."""
    data = build_index(corpus, index_version=index_version)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    typer.echo(f"wrote {output} ({data['record_count']} records)")


@index_app.command("stats")
def index_stats(
    index: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
) -> None:
    """Print stats for an index file."""
    store = IndexStore.load(index)
    typer.echo(json.dumps(store.stats().model_dump(mode="json"), indent=2))


@app.command("serve")
def serve(
    index: Path = typer.Option(..., "--index", exists=True, dir_okay=False, readable=True),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run the openbench API server."""
    application = create_app(index_path=index)
    uvicorn.run(application, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    app()
