"""Deployment of the DocAI resources to Azure, one module per numbered step.

    uv run python -m deploy --dry-run            # print the plan, run nothing
    uv run python -m deploy [--from N] [--to M] [--only N] [--menu] [--teardown]
"""
STEPS = {
    0: "s00_preflight", 10: "s10_core", 20: "s20_data", 30: "s30_ai", 40: "s40_rbac", 41: "s41_entra",
    42: "s42_assign_users", 50: "s50_apps", 60: "s60_bootstrap", 90: "s90_write_env", 99: "s99_teardown",
}


def select(from_: int = 0, to: int = 90, only: int | None = None, teardown: bool = False) -> list[int]:
    """Step numbers to run, in order. Teardown (99) is never part of a range: it runs alone, and only with `teardown`."""
    if teardown:
        return [99]
    if only is not None:
        return [only] if only in STEPS and only != 99 else []
    return [n for n in STEPS if from_ <= n <= to and n != 99]
