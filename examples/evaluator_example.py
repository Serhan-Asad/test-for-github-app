"""Example usage of the FeatureFlagEvaluator module.

Demonstrates:
  * Construction with a mapping of flag definitions.
  * Evaluating fully-enabled, fully-disabled, and partial-rollout flags.
  * Determinism: the same (flag_name, uid) always returns the same result.
  * Boundary handling for rollout values 0 and 100.
  * Defensive TypeError on non-string inputs.

Run:
    python examples/evaluator_example.py
"""

import os
import sys

# Make the project root importable regardless of CWD.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluator import FeatureFlagEvaluator


def main() -> None:
    # --- Flag definitions -------------------------------------------------
    # Each value is a dict. `enabled` is the master switch; `rollout`
    # (0-100) is the percentage of users for whom the flag is on when
    # enabled. `rollout` is optional (defaults to 100).
    flags = {
        "new_dashboard": {"enabled": True},               # 100% on
        "beta_search": {"enabled": True, "rollout": 50},  # 50% rollout
        "always_off": {"enabled": False},                  # master off
        "zero_rollout": {"enabled": True, "rollout": 0},   # explicit 0%
        "full_rollout": {"enabled": True, "rollout": 100}, # explicit 100%
    }

    evaluator = FeatureFlagEvaluator(flags)

    # --- Fully enabled flag ----------------------------------------------
    print("new_dashboard for alice:", evaluator.is_enabled("new_dashboard", "alice"))
    print("new_dashboard for bob:  ", evaluator.is_enabled("new_dashboard", "bob"))
    print()

    # --- Fully disabled flag ---------------------------------------------
    print("always_off for alice:   ", evaluator.is_enabled("always_off", "alice"))
    print("zero_rollout for alice: ", evaluator.is_enabled("zero_rollout", "alice"))
    print()

    # --- Unknown flag returns False --------------------------------------
    print("unknown_flag for alice: ", evaluator.is_enabled("unknown_flag", "alice"))
    print()

    # --- Partial rollout: deterministic per (flag, uid) ------------------
    sample_uids = ["alice", "bob", "carol", "dave", "eve", "frank", "grace", "henry"]
    print("beta_search 50% rollout sample:")
    in_count = 0
    for uid in sample_uids:
        on = evaluator.is_enabled("beta_search", uid)
        in_count += int(on)
        print(f"  {uid:<6} -> {on}")
    print(f"  ({in_count}/{len(sample_uids)} bucketed in)")
    print()

    # --- Determinism check -----------------------------------------------
    first = evaluator.is_enabled("beta_search", "alice")
    second = evaluator.is_enabled("beta_search", "alice")
    print("determinism (same call twice):", first, "==", second, "->", first == second)
    print()

    # --- Full rollout boundary -------------------------------------------
    print("full_rollout for alice: ", evaluator.is_enabled("full_rollout", "alice"))
    print()

    # --- Defensive TypeError on non-string inputs ------------------------
    try:
        evaluator.is_enabled(123, "alice")  # type: ignore[arg-type]
    except TypeError as exc:
        print("TypeError on non-string flag_name:", exc)

    try:
        evaluator.is_enabled("new_dashboard", 42)  # type: ignore[arg-type]
    except TypeError as exc:
        print("TypeError on non-string uid:      ", exc)


if __name__ == "__main__":
    main()
