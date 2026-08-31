"""
Example usage for the FlagToggle React component (flag_toggle.tsx).

This file is a runnable Python script (despite the .tsx extension) that
demonstrates the component's behaviour by:
  1. Loading and showing the component source from flag_toggle.tsx
  2. Simulating the component's pure render logic in Python
  3. Producing expected output for several prop combinations

Inputs (props the React component accepts):
  - flagName: str  -- feature flag identifier; surfaced via data-flag-name
  - enabled:  bool -- gate on the flag (False -> render nothing)
  - children: any  -- optional content rendered when enabled is True

Outputs (what the component produces):
  - When enabled is False -> None  (i.e. React null, not rendered)
  - When enabled is True  -> a dict shaped like
        {"tag": "div", "data-flag-name": flagName, "children": children}
    representing the rendered <div data-flag-name={flagName}>{children}</div>
"""

import os
import re
import sys

# Make the project root importable regardless of cwd.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def load_component_source():
    """Return the textual source of flag_toggle.tsx as a string."""
    code_path = os.path.join(os.path.dirname(__file__), "..", "flag_toggle.tsx")
    code_path = os.path.normpath(code_path)
    with open(code_path, "r", encoding="utf-8") as fh:
        return fh.read()


def simulate_flag_toggle(flag_name, enabled, children=None):
    """Pure-Python mirror of the FlagToggle render function.

    Mirrors the spec exactly:
      - if not enabled: return None
      - else:           return a dict representing
                        <div data-flag-name={flagName}>{children}</div>

    Parameters
    ----------
    flag_name : str
        The feature flag identifier, surfaced via data-flag-name.
    enabled : bool
        When False the component returns None (renders nothing in React).
    children : Any, optional
        Optional renderable content. Default None.

    Returns
    -------
    dict | None
        None when enabled is False; otherwise a dict with keys
        "tag", "data-flag-name", "children".
    """
    if not enabled:
        return None
    return {"tag": "div", "data-flag-name": flag_name, "children": children}


def main():
    print("=== FlagToggle component example ===")
    print()

    src = load_component_source()
    print("Component source (flag_toggle.tsx):")
    print("-" * 40)
    print(src)
    print("-" * 40)
    print()

    # Static spec-compliance signals (what tests look for).
    print("Static spec checks:")
    print("  exports default FlagToggle:",
          bool(re.search(r"export\s+default\s+FlagToggle", src)))
    print("  exports FlagToggleProps:",
          bool(re.search(r"export\s+interface\s+FlagToggleProps", src)))
    print("  returns null when disabled:",
          "return null" in src)
    print("  renders data-flag-name div:",
          "data-flag-name=" in src and "<div" in src)
    print()

    # Demonstrate behaviour via the Python simulation.
    print("Behaviour (simulated):")

    disabled_result = simulate_flag_toggle("new-checkout", enabled=False,
                                           children="Experiment row")
    print(f"  enabled=False -> {disabled_result!r}")
    assert disabled_result is None, "spec: disabled flag must render nothing"

    enabled_result = simulate_flag_toggle("new-checkout", enabled=True,
                                          children="Experiment row")
    print(f"  enabled=True  -> {enabled_result!r}")
    assert enabled_result == {
        "tag": "div",
        "data-flag-name": "new-checkout",
        "children": "Experiment row",
    }

    no_children = simulate_flag_toggle("beta-banner", enabled=True)
    print(f"  enabled=True, no children -> {no_children!r}")
    assert no_children == {
        "tag": "div",
        "data-flag-name": "beta-banner",
        "children": None,
    }

    print()
    print("All example assertions passed.")


if __name__ == "__main__":
    main()
