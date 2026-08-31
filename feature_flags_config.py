"""YAML-based feature flag configuration loader.

Public symbols: ``load_flags``, ``FlagDefinition``, ``ConfigError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

__all__ = ["load_flags", "FlagDefinition", "ConfigError"]


class ConfigError(Exception):
    """Raised for any non-OSError failure during flag config loading/validation."""


@dataclass(frozen=True)
class FlagDefinition:
    """Immutable record describing a single feature flag."""

    name: str
    enabled: bool
    rollout: float | None = None


_ALLOWED_FLAG_KEYS = frozenset({"enabled", "rollout"})


def load_flags(path: str) -> dict[str, FlagDefinition]:
    """Load and validate feature flag definitions from a YAML file.

    Parameters
    ----------
    path:
        Filesystem path to a YAML file whose top-level structure is::

            flags:
              my_flag:
                enabled: true
                rollout: 50   # optional, 0–100

    Returns
    -------
    dict[str, FlagDefinition]
        Mapping of flag name → validated, immutable ``FlagDefinition``.

    Raises
    ------
    ConfigError
        On missing file, YAML parse error, or any schema / validation violation.
    """
    raw_text = _read_file(path)
    data = _parse_yaml(raw_text, path)

    # Empty file (safe_load returns None) → valid, zero flags.
    if data is None:
        return {}

    _validate_top_level(data, path)

    flags_mapping = data["flags"]

    # ``flags:`` with no value underneath → None in PyYAML → zero entries.
    if flags_mapping is None:
        return {}

    if not isinstance(flags_mapping, dict):
        raise ConfigError(
            f"{path}: 'flags' must be a mapping, got {type(flags_mapping).__name__}"
        )

    result: dict[str, FlagDefinition] = {}
    for flag_name, body in flags_mapping.items():
        result[flag_name] = _validate_flag(flag_name, body, path)

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_file(path: str) -> str:
    """Read the file at *path*, converting ``FileNotFoundError`` to ``ConfigError``."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found: {path}") from None


def _parse_yaml(text: str, path: str) -> Any:
    """Run ``yaml.safe_load``; wrap ``YAMLError`` in ``ConfigError``."""
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML file {path}: {exc}") from exc


def _validate_top_level(data: Any, path: str) -> None:
    """Ensure *data* is a mapping containing a ``flags`` key."""
    if not isinstance(data, dict):
        raise ConfigError(
            f"{path}: expected a top-level mapping, got {type(data).__name__}"
        )
    if "flags" not in data:
        raise ConfigError(f"{path}: top-level mapping must contain a 'flags' key")


def _validate_flag(flag_name: str, body: Any, path: str) -> FlagDefinition:
    """Validate a single flag body and return a ``FlagDefinition``."""
    if not isinstance(body, dict):
        raise ConfigError(
            f"Flag '{flag_name}': body must be a mapping, "
            f"got {type(body).__name__}"
        )

    # Reject unknown keys -----------------------------------------------
    unknown = set(body.keys()) - _ALLOWED_FLAG_KEYS
    if unknown:
        raise ConfigError(
            f"Flag '{flag_name}': unknown keys {sorted(unknown)}"
        )

    # --- enabled (required, strict bool) --------------------------------
    if "enabled" not in body:
        raise ConfigError(f"Flag '{flag_name}': missing required key 'enabled'")

    enabled = body["enabled"]
    if not isinstance(enabled, bool):
        raise ConfigError(
            f"Flag '{flag_name}': 'enabled' must be a bool, "
            f"got {type(enabled).__name__} ({enabled!r})"
        )

    # --- rollout (optional, numeric in [0, 100]) ------------------------
    rollout: float | None = None
    if "rollout" in body:
        raw_rollout = body["rollout"]
        # Accept int/float but NOT bool (bool is a subclass of int in Python).
        if isinstance(raw_rollout, bool) or not isinstance(raw_rollout, (int, float)):
            raise ConfigError(
                f"Flag '{flag_name}': 'rollout' must be a number, "
                f"got {type(raw_rollout).__name__} ({raw_rollout!r})"
            )
        rollout = float(raw_rollout)
        if not (0.0 <= rollout <= 100.0):
            raise ConfigError(
                f"Flag '{flag_name}': 'rollout' must be in [0, 100], got {rollout}"
            )

    return FlagDefinition(name=flag_name, enabled=enabled, rollout=rollout)