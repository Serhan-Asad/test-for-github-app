"""Example usage of feature_flags_config.

This script demonstrates the public API of ``feature_flags_config``:
    * ``load_flags(path)`` -> dict[str, FlagDefinition]
    * ``FlagDefinition`` (frozen dataclass: name, enabled, rollout)
    * ``ConfigError`` (raised on any non-OSError validation failure)

Inputs:
    * ``path`` (str): filesystem path to a YAML file with the structure::

          flags:
            <flag_name>:
              enabled: <bool>          # required
              rollout: <number 0..100> # optional, percent

Outputs:
    * dict mapping flag name -> FlagDefinition. ``rollout`` is in percent
      (0.0 to 100.0) and is ``None`` when not specified.

The script writes temporary YAML files into a temp directory, exercises the
loader against each, and prints the results.
"""

from __future__ import annotations

import os
import sys
import tempfile

# Make the module importable no matter the cwd.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from feature_flags_config import ConfigError, FlagDefinition, load_flags


VALID_YAML = """\
flags:
  new_checkout:
    enabled: true
    rollout: 25
  beta_search:
    enabled: false
  fully_rolled_out:
    enabled: true
    rollout: 100
"""

EMPTY_FLAGS_YAML = "flags:\n"

INVALID_ENABLED_YAML = """\
flags:
  bad_flag:
    enabled: "yes"
"""

OUT_OF_RANGE_YAML = """\
flags:
  too_high:
    enabled: true
    rollout: 150
"""

UNKNOWN_KEY_YAML = """\
flags:
  weird:
    enabled: true
    description: "not allowed"
"""


def _write(tmpdir: str, name: str, body: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        # --- happy path -----------------------------------------------------
        good_path = _write(tmpdir, "flags.yaml", VALID_YAML)
        flags = load_flags(good_path)

        print("Loaded", len(flags), "flag(s) from valid config:")
        for name, definition in flags.items():
            assert isinstance(definition, FlagDefinition)
            print(
                "  -",
                name,
                "enabled=" + str(definition.enabled),
                "rollout=" + str(definition.rollout),
            )
        print()

        # FlagDefinition is frozen / immutable.
        sample = flags["new_checkout"]
        try:
            sample.enabled = False  # type: ignore[misc]
        except Exception as exc:
            print("FlagDefinition is immutable:", type(exc).__name__)
        print()

        # --- empty flags mapping is valid ----------------------------------
        empty_path = _write(tmpdir, "empty.yaml", EMPTY_FLAGS_YAML)
        empty = load_flags(empty_path)
        print("Empty 'flags:' mapping returned:", empty)
        print()

        # --- error: missing file -------------------------------------------
        try:
            load_flags(os.path.join(tmpdir, "does_not_exist.yaml"))
        except ConfigError as exc:
            print("Missing file -> ConfigError:", exc)
        print()

        # --- error: enabled is not a bool ----------------------------------
        bad_enabled = _write(tmpdir, "bad_enabled.yaml", INVALID_ENABLED_YAML)
        try:
            load_flags(bad_enabled)
        except ConfigError as exc:
            print("Bad 'enabled' -> ConfigError:", exc)
        print()

        # --- error: rollout out of range -----------------------------------
        bad_rollout = _write(tmpdir, "bad_rollout.yaml", OUT_OF_RANGE_YAML)
        try:
            load_flags(bad_rollout)
        except ConfigError as exc:
            print("Out-of-range rollout -> ConfigError:", exc)
        print()

        # --- error: unknown key in flag body -------------------------------
        bad_key = _write(tmpdir, "bad_key.yaml", UNKNOWN_KEY_YAML)
        try:
            load_flags(bad_key)
        except ConfigError as exc:
            print("Unknown key -> ConfigError:", exc)


if __name__ == "__main__":
    main()
