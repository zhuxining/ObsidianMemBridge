"""Command line entrypoint for MemBridge."""

import argparse

from .core import create_bridge


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="membridge", description="MemBridge CLI")
    parser.add_argument("--source", required=True, help="Source identifier to bridge")
    parser.add_argument("--target", default="memory", help="Target identifier")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    bridge = create_bridge(args.source, args.target)
    print(bridge.describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
