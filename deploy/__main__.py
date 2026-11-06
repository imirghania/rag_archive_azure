"""uv run python -m deploy [--from N] [--to M] [--only N] [--menu] [--teardown] [--dry-run] [--yes]"""
from __future__ import annotations

import argparse
import importlib
import os
import sys

from . import STEPS, select
from .lib import Ctx, DeployError, make_ctx, say


def run_steps(ctx: Ctx, numbers: list[int]) -> None:
    for n in numbers:
        say(f"=== {n:02d} {STEPS[n]}")
        ctx.step = STEPS[n]
        importlib.import_module(f"deploy.{STEPS[n]}").run(ctx)


def menu(ctx: Ctx) -> None:
    """Pick a step to run again, or everything up to 90. Every step is idempotent."""
    while True:
        say(f"\nResource group {ctx.n.rg} in {ctx.n.loc}" + ("   [DRY RUN]" if ctx.az.dry_run else ""))
        for n, name in STEPS.items():
            say(f"  {n:>2}  {name}" + ("   (teardown: use --teardown)" if n == 99 else ""))
        say("   a  all steps up to 90        q  quit")
        choice = input("Select: ").strip().lower()
        if choice == "q":
            return
        numbers = select() if choice == "a" else [int(choice)] if choice.isdigit() and int(choice) in STEPS and int(choice) != 99 else []
        if not numbers:
            say("Invalid choice.")
            continue
        try:
            run_steps(ctx, numbers)
        except DeployError as e:
            say(f"[error] {e}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m deploy", description=__doc__)
    ap.add_argument("--from", dest="from_", type=int, default=0, help="first step number (default 0)")
    ap.add_argument("--to", type=int, default=90, help="last step number (default 90)")
    ap.add_argument("--only", type=int, help="run one step")
    ap.add_argument("--menu", action="store_true", help="choose the steps interactively")
    ap.add_argument("--teardown", action="store_true", help="step 99: delete everything (asks for the resource group name)")
    ap.add_argument("--dry-run", action="store_true", default=os.environ.get("DRY_RUN") == "1", help="run no az command (also DRY_RUN=1)")
    ap.add_argument("--yes", action="store_true", help="do not ask for the teardown confirmation")
    args = ap.parse_args(argv)
    if args.only == 99 and not args.teardown:
        ap.error("step 99 deletes everything: use --teardown")
    try:
        ctx = make_ctx(dry_run=args.dry_run, yes=args.yes)
        if args.menu:
            menu(ctx)
        else:
            run_steps(ctx, select(args.from_, args.to, args.only, args.teardown))
    except DeployError as e:
        say(f"[error] {e}")
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
