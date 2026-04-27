"""Fail-closed, in-memory feature flag evaluator."""

_FLAGS: dict[str, bool] = {}


def is_enabled(flag_name: str, uid: str) -> bool:
    """Return whether *flag_name* is enabled.

    Fail-closed contract
    --------------------
    * Returns ``True`` **only** when *flag_name* is a known key in the
      in-memory flag store **and** its value is truthy.
    * Returns ``False`` for unknown flags, ``None``/non-string flag names,
      or any other unexpected input — never raises.

    Parameters
    ----------
    flag_name:
        Name of the feature flag to evaluate.
    uid:
        User identifier.  Reserved for future per-user targeting; currently
        accepted but **does not** influence the result.
    """
    if not isinstance(flag_name, str):
        return False
    return bool(_FLAGS.get(flag_name, False))


def _set_flags(flags: dict[str, bool]) -> None:
    """Replace the in-memory flag state atomically (clear + update).

    Each value is coerced to ``bool`` so the store always contains
    canonical ``True``/``False`` entries.
    """
    _FLAGS.clear()
    _FLAGS.update({k: bool(v) for k, v in flags.items()})