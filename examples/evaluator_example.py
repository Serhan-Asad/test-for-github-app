"""Example usage of the fail-closed feature flag evaluator.

This script demonstrates:
  * Populating the in-memory flag store via ``_set_flags``.
  * Querying flags with ``is_enabled``.
  * Fail-closed behavior on unknown flags / malformed input.
  * That ``uid`` does not influence the result in this revision.

Inputs / outputs
----------------
``is_enabled(flag_name: str, uid: str) -> bool``
    Returns ``True`` iff *flag_name* is a known, truthy entry in
    ``_FLAGS``; otherwise ``False``.  Never raises.

``_set_flags(flags: dict[str, bool]) -> None``
    Atomically replaces the flag store; values are coerced to bool.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluator import _FLAGS, _set_flags, is_enabled


def main() -> None:
    # 1. Seed the in-memory flag store.
    _set_flags({
        "new_checkout": True,
        "dark_mode": False,
        "beta_search": 1,        # truthy non-bool — coerced to True
        "legacy_banner": "",     # falsy non-bool — coerced to False
    })
    print("Seeded flags:", dict(_FLAGS))
    print()

    # 2. Query a known-enabled flag.
    print("is_enabled('new_checkout', 'user-123') ->",
          is_enabled("new_checkout", "user-123"))

    # 3. Query a known-disabled flag.
    print("is_enabled('dark_mode', 'user-123')    ->",
          is_enabled("dark_mode", "user-123"))

    # 4. Coerced truthy/falsy values.
    print("is_enabled('beta_search', 'user-123')  ->",
          is_enabled("beta_search", "user-123"))
    print("is_enabled('legacy_banner', 'user-123')->",
          is_enabled("legacy_banner", "user-123"))
    print()

    # 5. Unknown flag — fail-closed (False, never raises).
    print("is_enabled('does_not_exist', 'user-123') ->",
          is_enabled("does_not_exist", "user-123"))

    # 6. Malformed flag_name — fail-closed.
    print("is_enabled(None, 'user-123')  ->", is_enabled(None, "user-123"))
    print("is_enabled(42, 'user-123')    ->", is_enabled(42, "user-123"))
    print()

    # 7. uid does NOT influence the result in this version.
    a = is_enabled("new_checkout", "alice")
    b = is_enabled("new_checkout", "bob")
    print(f"uid-independence: alice={a}, bob={b}, equal={a == b}")
    print()

    # 8. _set_flags replaces (does not merge) state.
    _set_flags({"only_flag": True})
    print("After replacement, _FLAGS:", dict(_FLAGS))
    print("is_enabled('new_checkout', '') ->",
          is_enabled("new_checkout", ""))  # gone -> False


if __name__ == "__main__":
    main()
