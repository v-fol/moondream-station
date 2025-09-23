import typer
from typing import Optional
from rich import print as rprint

from .repl import REPLSession


DEFAULT_MANIFEST_URL = "https://m87-md-prod-assets.s3.us-west-2.amazonaws.com/station/mds2/production_manifest.json"


app = typer.Typer(
    name="moondream-station",
    help="🌙 Model hosting and management CLI",
    rich_markup_mode="rich",
    add_completion=False,
)


@app.command()
def interactive(
    manifest: Optional[str] = typer.Option(
        DEFAULT_MANIFEST_URL, "--manifest", "-m", help="Manifest URL or local path"
    )
):
    """Start interactive REPL mode (default)"""
    session = REPLSession(manifest_source=manifest)
    session.start()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    manifest: Optional[str] = typer.Option(
        DEFAULT_MANIFEST_URL, "--manifest", "-m", help="Manifest URL or local path"
    ),
):
    """🌙 Model hosting and management CLI"""
    if version:
        from . import __version__

        rprint(f"moondream-station version {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        session = REPLSession(manifest_source=manifest)
        session.start()


if __name__ == "__main__":
    app()
