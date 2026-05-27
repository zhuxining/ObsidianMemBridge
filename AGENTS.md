# AGENTS.md

This file provides guidance to Code Agents (claude.ai/code、codex、pi、opencode) when working with code in this repository.

## Project Overview

`obsidianmembridge` is an Obsidian-based shared memory layer for agents, providing governed context retrieval, memory proposals, episodic summaries, and project state across Claude, OpenClaw, Pi, Codex, and other AI tools.

- Python 3.14, managed with **uv**
- Src layout: source in `src/obsidianmembridge/` (built as wheel package via `uv_build`)
- Entry point: `src/obsidianmembridge/cli.py` → `cli()` (registered as `meb` command via `project.scripts`)

## Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run meb

# Lint & format (auto-fix enabled)
uv run ruff check --fix

# Type check
uv run ty check --fix

# Run all tests
uv run pytest

# Run tests excluding external service calls
uv run pytest -m "not integration"

# Run a single test file
uv run pytest tests/path/to/test_file.py
```
