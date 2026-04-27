"""Runtime feature flag evaluator with deterministic per-user rollout bucketing via SHA-256 hashing."""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping


class FeatureFlagEvaluator:
    """Evaluate feature flags against user identifiers.

    Accepts a mapping of flag name → flag definition dicts via constructor
    injection and exposes a single ``is_enabled`` method that resolves whether
    a given flag is active for a specific user.

    Flag definition keys (all optional unless noted):
        enabled (bool):  Master switch. Flag is off when absent or falsy.
        rollout (int | float, 0–100):  Percentage of users bucketed in.
            Defaults to 100 (fully on) when ``enabled`` is true and key is
            absent.

    Bucketing is deterministic: ``sha256(f\"{flag_name}:{uid}\")`` mod 100,
    ensuring the same uid is not uniformly in/out across different flags.
    """

    def __init__(self, flags: Mapping[str, dict]) -> None:
        self._flags = flags

    def is_enabled(self, flag_name: str, uid: str) -> bool:
        """Return whether *flag_name* is enabled for user *uid*.

        Resolution order:
        1. Unknown flag → ``False``.
        2. Definition is not a mapping or ``enabled`` is missing/falsy → ``False``.
        3. ``rollout`` absent → ``True`` (fully on).
        4. ``rollout <= 0`` → ``False``; ``rollout >= 100`` → ``True``.
        5. Deterministic SHA-256 bucket check: ``bucket < rollout``.

        Raises:
            TypeError: If *flag_name* or *uid* is not a ``str``.
        """
        if not isinstance(flag_name, str):
            raise TypeError(
                f"flag_name must be str, got {type(flag_name).__name__}"
            )
        if not isinstance(uid, str):
            raise TypeError(f"uid must be str, got {type(uid).__name__}")

        # Step (a): unknown flag
        if flag_name not in self._flags:
            return False

        definition = self._flags[flag_name]

        # Step (b): definition must be a mapping with a truthy `enabled`
        if not isinstance(definition, Mapping):
            return False
        if not definition.get("enabled"):
            return False

        # Step (c): no rollout key → fully on
        if "rollout" not in definition:
            return True

        rollout = definition["rollout"]

        # Step (d): boundary checks
        if rollout <= 0:
            return False
        if rollout >= 100:
            return True

        # Step (e): deterministic bucket
        digest = sha256(f"{flag_name}:{uid}".encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % 100
        return bucket < rollout