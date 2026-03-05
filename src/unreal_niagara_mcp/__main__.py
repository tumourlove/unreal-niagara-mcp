"""Entry point for `python -m unreal_niagara_mcp` and `uvx unreal-niagara-mcp`."""

from __future__ import annotations

import argparse

from unreal_niagara_mcp import __version__


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="unreal-niagara-mcp",
        description="Niagara particle system intelligence for Unreal Engine AI development.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()
    _run_server()


def _run_server() -> None:
    from unreal_niagara_mcp.server import main
    main()


if __name__ == "__main__":
    cli()
