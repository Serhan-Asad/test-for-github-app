"""Example usage of the feature-flag config loader.

This script demonstrates the public API of ``config.load_config``:
- Loading a valid YAML mapping (returns a dict).
- Loading an empty YAML file (returns ``{}``).
- Loading a YAML file whose root is a list/scalar (returns ``{}``).
- Loading a missing file (returns ``{}`` and logs a warning).
- Loading malformed YAML (returns ``{}`` and logs a warning).
- Passing both ``str`` and ``pathlib.Path`` inputs.

Inputs:
    path (str | pathlib.Path): filesystem path to a YAML file.

Outputs:
    dict: parsed root mapping, or ``{}`` on empty/invalid/unreadable input.
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys
import tempfile

# Make the project root importable regardless of working directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import load_config  # noqa: E402


def main() -> int:
    # Show the WARNING logs that load_config emits on graceful failures.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)

        # 1) Valid YAML mapping --------------------------------------------
        valid_path = tmpdir / "flags.yaml"
        valid_path.write_text(
            "new_checkout:\n"
            "  enabled: true\n"
            "  rollout: 0.5\n"
            "dark_mode:\n"
            "  enabled: false\n",
            encoding="utf-8",
        )
        flags = load_config(valid_path)
        print("valid YAML (Path) ->", flags)
        print("  type:", type(flags).__name__)
        print("  new_checkout.enabled:", flags["new_checkout"]["enabled"])
        print()

        # str path also works.
        flags_str = load_config(str(valid_path))
        print("valid YAML (str)  ->", flags_str)
        print()

        # 2) Empty file ----------------------------------------------------
        empty_path = tmpdir / "empty.yaml"
        empty_path.write_text("", encoding="utf-8")
        print("empty file        ->", load_config(empty_path))
        print()

        # 3) Non-mapping root (list) --------------------------------------
        list_path = tmpdir / "list.yaml"
        list_path.write_text("- one\n- two\n", encoding="utf-8")
        print("list root         ->", load_config(list_path))
        print()

        # 4) Non-mapping root (scalar) ------------------------------------
        scalar_path = tmpdir / "scalar.yaml"
        scalar_path.write_text("just-a-string\n", encoding="utf-8")
        print("scalar root       ->", load_config(scalar_path))
        print()

        # 5) Missing file --------------------------------------------------
        print("missing file      ->", load_config(tmpdir / "does_not_exist.yaml"))
        print()

        # 6) Malformed YAML ------------------------------------------------
        bad_path = tmpdir / "bad.yaml"
        bad_path.write_text("key: [unterminated\n", encoding="utf-8")
        print("malformed YAML    ->", load_config(bad_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
