"""Run and optionally preserve the deterministic assistant golden set."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from fleetpulse_project.assistant_eval import evaluate_cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("evaluations/assistant_golden.json"))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = asyncio.run(evaluate_cases(args.dataset))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
