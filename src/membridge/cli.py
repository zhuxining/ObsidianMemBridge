"""CLI entrypoint — Typer app for MemBridge."""

import json
from pathlib import Path

from pydantic import BaseModel
import typer

from membridge.core import MemoryService
from membridge.models import (
    MemBridgeError,
    MemoryDocument,
    MemoryFilter,
    MemoryFrontmatter,
)
from membridge.settings import Settings

cli = typer.Typer(help="MemBridge — Obsidian memory management CLI", add_completion=False)


def _service(vault_root: str | None = None) -> MemoryService:
    settings = Settings()
    if vault_root:
        settings.vault_root = Path(vault_root)
    svc = MemoryService(settings)
    if settings.vault_root:
        svc.init_vault()
    return svc


def _exit_ok(data: object, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(_jsonable(data), ensure_ascii=False, indent=2))
    else:
        _print_human(data)


def _jsonable(data: object) -> object:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_jsonable(item) for item in data]
    return data


def _print_human(data: object) -> None:
    if isinstance(data, MemoryDocument):
        _print_doc(data)
    elif isinstance(data, list) and data:
        docs = [item for item in data if isinstance(item, MemoryDocument)]
        if len(docs) != len(data):
            typer.echo(data)
            return
        for doc in docs:
            _print_doc(doc)
            print("---")
    elif isinstance(data, dict):
        for k, v in data.items():
            typer.echo(f"  {k}: {v}")
    else:
        typer.echo(data)


def _print_doc(doc: MemoryDocument) -> None:
    typer.echo(f"Path:        {doc.path}")
    typer.echo(f"Title:       {doc.title}")
    typer.echo(f"Status:      {doc.frontmatter.status}")
    typer.echo(f"Type:        {doc.frontmatter.type}")
    typer.echo(f"Source:      {doc.frontmatter.source}")
    if doc.frontmatter.project:
        typer.echo(f"Project:     {doc.frontmatter.project}")
    if doc.frontmatter.scope:
        typer.echo(f"Scope:       {doc.frontmatter.scope}")
    if doc.frontmatter.tags:
        typer.echo(f"Tags:        {', '.join(doc.frontmatter.tags)}")
    typer.echo(f"Created:     {doc.frontmatter.created_at}")
    if doc.frontmatter.updated_at:
        typer.echo(f"Updated:     {doc.frontmatter.updated_at}")
    typer.echo(f"Summary:     {doc.summary}")


# -- init ---------------------------------------------------------------------


@cli.command()
def init(
    vault_root: str = typer.Argument(..., help="Path to Obsidian vault root"),
    memories_dir: str = typer.Option("memories", help="Memories subdirectory name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Initialize MemBridge against an Obsidian vault."""
    settings = Settings(vault_root=Path(vault_root), memories_dir=memories_dir)
    svc = MemoryService(settings)
    try:
        info = svc.init_vault()
        _exit_ok({"vault_root": str(info.root), "memories_dir": info.memories_dir}, json_output)
    except MemBridgeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


# -- read ---------------------------------------------------------------------


@cli.command()
def read(
    path: str | None = typer.Argument(None, help="Vault-relative path to a specific memory"),
    status: str | None = typer.Option(None, help="Filter by status"),
    type: str | None = typer.Option(None, help="Filter by type"),
    scope: str | None = typer.Option(None, help="Filter by scope"),
    project: str | None = typer.Option(None, help="Filter by project"),
    source: str | None = typer.Option(None, help="Filter by source"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Filter by tag (repeatable)"),
    vault_root: str | None = typer.Option(None, help="Vault root path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read or query memories."""
    svc = _service(vault_root)
    svc._require_vault()

    try:
        if path:
            doc = svc.read_memory(path)
            _exit_ok(doc, json_output)
        else:
            filters = MemoryFilter(
                status=status,
                type=type,
                scope=scope,
                project=project,
                source=source,
                tags=tag or [],
            )
            docs = svc.query_memories(filters)
            if not docs:
                typer.echo("No memories found.")
            _exit_ok(docs, json_output)
    except MemBridgeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


# -- write --------------------------------------------------------------------


@cli.command()
def write(
    title: str = typer.Option(..., help="Memory title"),
    content: str = typer.Option(..., help="Memory body content"),
    type: str = typer.Option(..., help="Memory type"),
    source: str = typer.Option(..., help="Source identifier"),
    status: str = typer.Option("active", help="Memory status"),
    scope: str | None = typer.Option(None, help="Scope"),
    project: str | None = typer.Option(None, help="Project"),
    tags: list[str] | None = typer.Option(None, "--tag", help="Tags (repeatable)"),
    path: str | None = typer.Option(None, help="Vault-relative output path"),
    vault_root: str | None = typer.Option(None, help="Vault root path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Write a new memory."""
    svc = _service(vault_root)
    svc._require_vault()

    frontmatter = MemoryFrontmatter(
        status=status,
        type=type,
        source=source,
        scope=scope,
        project=project,
        tags=tags or [],
    )

    try:
        doc = svc.write_memory(title, content, frontmatter, path)
        _exit_ok(doc, json_output)
    except MemBridgeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


# -- update -------------------------------------------------------------------


@cli.command()
def update(
    path: str = typer.Argument(..., help="Vault-relative path to the memory"),
    content: str | None = typer.Option(None, help="New body content"),
    content_file: Path | None = typer.Option(None, help="Read content from file"),
    set: list[str] | None = typer.Option(
        None, "--set", help="Frontmatter patch as key=value (repeatable)"
    ),
    vault_root: str | None = typer.Option(None, help="Vault root path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Update an existing memory."""
    svc = _service(vault_root)
    svc._require_vault()

    if content_file:
        content = content_file.read_text(encoding="utf-8")

    patch: dict[str, str] = {}
    if set:
        for item in set:
            if "=" not in item:
                typer.echo(f"Invalid --set format (expected key=value): {item}", err=True)
                raise typer.Exit(1)
            k, v = item.split("=", 1)
            patch[k.strip()] = v.strip()

    try:
        doc = svc.update_memory(path, content, patch or None)
        _exit_ok(doc, json_output)
    except MemBridgeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    cli()
