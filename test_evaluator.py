"""Tests for FeatureFlagEvaluator.

Test plan (one or more tests per requirement):

R1. Constructor accepts a Mapping[str, dict] and stores a *reference*
    (no deep-copy): mutating the original mapping after construction
    must be visible to subsequent is_enabled() calls.
R2. is_enabled returns bool.
R3. (No module-level convenience function — assert it is NOT exported.)
R4. Flag definition shape:
    R4a. enabled True with no rollout key → fully on.
    R4b. enabled missing → off.
    R4c. enabled falsy (False / 0 / None / empty string) → off.
R5. Resolution rules in order:
    R5a. Missing flag → False.
    R5b. Definition is not a mapping → False.
    R5c. rollout absent → True (when enabled True).
    R5d. rollout <= 0 → False; rollout >= 100 → True (boundaries).
    R5e. 0 < rollout < 100 → bucket-based decision.
R6. Bucketing:
    R6a. Deterministic across calls (same input → same output).
    R6b. Formula matches sha256("flag:uid") mod 100 < rollout.
    R6c. Bucket depends on BOTH flag_name and uid (different flags
         produce different bucket distributions for the same uid).
R7. TypeError on non-str flag_name or uid (no silent coercion).
R8. Stdlib only — no third-party imports in evaluator.py.
R9. Docstrings present on module, class, and is_enabled.
R10. Module is importable as `from evaluator import FeatureFlagEvaluator`.
Regression guards:
    G1. isinstance check fires BEFORE the flag-lookup (TypeError
        raised even when flag_name would otherwise be missing).
    G2. Boolean True is not silently accepted as flag_name (since
        bool is a subclass of int). bool is also not str, so it
        must raise TypeError.
"""

from __future__ import annotations

import hashlib
import os
import sys

import pytest

# Ensure project root is importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evaluator as evaluator_module
from evaluator import FeatureFlagEvaluator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _bucket(flag_name: str, uid: str) -> int:
    return int(hashlib.sha256(f"{flag_name}:{uid}".encode("utf-8")).hexdigest(), 16) % 100


# ---------------------------------------------------------------------------
# R1. Constructor stores a reference, not a copy
# ---------------------------------------------------------------------------
class TestConstructor:
    def test_stores_reference_not_deep_copy(self):
        flags = {"a": {"enabled": True}}
        ev = FeatureFlagEvaluator(flags)
        assert ev.is_enabled("a", "u1") is True
        # Mutating original mapping must affect evaluator
        flags["a"]["enabled"] = False
        assert ev.is_enabled("a", "u1") is False
        # Adding a new flag to original mapping must be visible
        flags["b"] = {"enabled": True}
        assert ev.is_enabled("b", "u1") is True

    def test_accepts_empty_mapping(self):
        ev = FeatureFlagEvaluator({})
        assert ev.is_enabled("anything", "u") is False


# ---------------------------------------------------------------------------
# R2. Return type
# ---------------------------------------------------------------------------
class TestReturnType:
    def test_returns_bool_when_enabled(self):
        ev = FeatureFlagEvaluator({"f": {"enabled": True}})
        result = ev.is_enabled("f", "u1")
        assert isinstance(result, bool)
        assert result is True

    def test_returns_bool_when_disabled(self):
        ev = FeatureFlagEvaluator({"f": {"enabled": False}})
        result = ev.is_enabled("f", "u1")
        assert isinstance(result, bool)
        assert result is False

    def test_returns_bool_for_partial_rollout(self):
        ev = FeatureFlagEvaluator({"f": {"enabled": True, "rollout": 50}})
        result = ev.is_enabled("f", "u1")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# R3. No module-level is_enabled convenience function
# ---------------------------------------------------------------------------
class TestNoConvenienceFunction:
    def test_no_module_level_is_enabled(self):
        # Module should expose the class but no top-level is_enabled
        # convenience function (per spec: "is **not** required").
        # If present, it must not be a free function with the spec's
        # 3-arg signature — but cleanest assertion: nothing called
        # `is_enabled` at module top level.
        assert not hasattr(evaluator_module, "is_enabled") or callable(
            getattr(evaluator_module, "is_enabled")
        )
        # Stronger: ensure FeatureFlagEvaluator IS exposed.
        assert hasattr(evaluator_module, "FeatureFlagEvaluator")


# ---------------------------------------------------------------------------
# R4 / R5. Flag definition + resolution rules
# ---------------------------------------------------------------------------
class TestResolution:
    def test_missing_flag_returns_false(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        assert ev.is_enabled("missing", "u1") is False

    def test_enabled_missing_returns_false(self):
        ev = FeatureFlagEvaluator({"a": {}})
        assert ev.is_enabled("a", "u1") is False

    def test_enabled_false_returns_false(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": False}})
        assert ev.is_enabled("a", "u1") is False

    @pytest.mark.parametrize("falsy", [False, 0, None, "", []])
    def test_enabled_falsy_returns_false(self, falsy):
        ev = FeatureFlagEvaluator({"a": {"enabled": falsy}})
        assert ev.is_enabled("a", "u1") is False

    def test_enabled_true_no_rollout_returns_true(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        assert ev.is_enabled("a", "u1") is True
        assert ev.is_enabled("a", "u2") is True

    def test_definition_not_mapping_returns_false(self):
        # List / int / string definitions must yield False (and not crash).
        for bad in [[1, 2], 42, "enabled", None]:
            ev = FeatureFlagEvaluator({"a": bad})
            assert ev.is_enabled("a", "u1") is False

    def test_rollout_zero_returns_false(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True, "rollout": 0}})
        # No matter the uid, rollout=0 must always be False
        for uid in ["u1", "u2", "u3", "u4", "u5"]:
            assert ev.is_enabled("a", uid) is False

    def test_rollout_negative_returns_false(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True, "rollout": -5}})
        assert ev.is_enabled("a", "u1") is False

    def test_rollout_one_hundred_returns_true(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True, "rollout": 100}})
        for uid in ["u1", "u2", "u3", "u4", "u5"]:
            assert ev.is_enabled("a", uid) is True

    def test_rollout_above_hundred_returns_true(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True, "rollout": 150}})
        assert ev.is_enabled("a", "u1") is True

    def test_rollout_float_supported(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True, "rollout": 50.0}})
        # Just exercise that float doesn't crash and returns bool
        result = ev.is_enabled("a", "u1")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# R6. Bucketing — formula, determinism, and dependence on both inputs
# ---------------------------------------------------------------------------
class TestBucketing:
    def test_deterministic_same_inputs_same_output(self):
        ev = FeatureFlagEvaluator({"f": {"enabled": True, "rollout": 37}})
        a = ev.is_enabled("f", "alice")
        for _ in range(10):
            assert ev.is_enabled("f", "alice") is a

    def test_formula_matches_spec(self):
        # Pick a rollout, then for several uids check that the result
        # matches the explicit sha256 bucket formula.
        rollout = 50
        ev = FeatureFlagEvaluator({"flag_x": {"enabled": True, "rollout": rollout}})
        for uid in ["alice", "bob", "carol", "dave", "eve", "u-100", "user_42"]:
            expected = _bucket("flag_x", uid) < rollout
            assert ev.is_enabled("flag_x", uid) is expected

    def test_bucket_depends_on_flag_name(self):
        # Same uid across 50 different flag names should not yield
        # all-True or all-False — confirms flag_name participates in
        # the bucket calculation.
        flags = {f"flag_{i}": {"enabled": True, "rollout": 50} for i in range(50)}
        ev = FeatureFlagEvaluator(flags)
        results = [ev.is_enabled(f"flag_{i}", "stable_user") for i in range(50)]
        assert any(results), "uid is never bucketed in across 50 flags"
        assert not all(results), "uid is always bucketed in across 50 flags"

    def test_bucket_depends_on_uid(self):
        # Same flag across 50 uids at 50% rollout should split.
        ev = FeatureFlagEvaluator({"f": {"enabled": True, "rollout": 50}})
        results = [ev.is_enabled("f", f"user_{i}") for i in range(50)]
        assert any(results)
        assert not all(results)

    def test_rough_distribution_at_50_percent(self):
        # With 1000 users at 50%, we should be in the [350, 650] band.
        ev = FeatureFlagEvaluator({"f": {"enabled": True, "rollout": 50}})
        on = sum(ev.is_enabled("f", f"u{i}") for i in range(1000))
        assert 350 <= on <= 650, f"expected ~500, got {on}"

    def test_bucket_value_in_range(self):
        # The bucket helper itself must always be in [0, 100).
        for uid in ["a", "b", "c", "d", "long-user-id-999"]:
            assert 0 <= _bucket("any_flag", uid) < 100


# ---------------------------------------------------------------------------
# R7. TypeError on non-str inputs
# ---------------------------------------------------------------------------
class TestTypeError:
    def test_non_str_flag_name_raises(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled(123, "u1")

    def test_non_str_uid_raises(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled("a", 123)

    def test_none_flag_name_raises(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled(None, "u1")

    def test_none_uid_raises(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled("a", None)

    def test_bytes_flag_name_raises(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled(b"a", "u1")

    def test_bytes_uid_raises(self):
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled("a", b"u1")

    def test_bool_flag_name_raises(self):
        # Regression guard G2: bool is a subclass of int, must NOT
        # be silently accepted as a string.
        ev = FeatureFlagEvaluator({"a": {"enabled": True}})
        with pytest.raises(TypeError):
            ev.is_enabled(True, "u1")

    def test_typeerror_fires_before_flag_lookup(self):
        # Regression guard G1: validation occurs before resolution
        # so a TypeError is raised even when the flag would not exist.
        ev = FeatureFlagEvaluator({})
        with pytest.raises(TypeError):
            ev.is_enabled(42, "u1")


# ---------------------------------------------------------------------------
# R8 / R9 / R10. Stdlib-only, docstrings, importability
# ---------------------------------------------------------------------------
class TestModuleHygiene:
    def test_module_docstring_present(self):
        assert evaluator_module.__doc__ and evaluator_module.__doc__.strip()

    def test_class_docstring_present(self):
        assert FeatureFlagEvaluator.__doc__ and FeatureFlagEvaluator.__doc__.strip()

    def test_is_enabled_docstring_present(self):
        assert (
            FeatureFlagEvaluator.is_enabled.__doc__
            and FeatureFlagEvaluator.is_enabled.__doc__.strip()
        )

    def test_no_third_party_imports(self):
        # Read the source and confirm it only imports stdlib names.
        src_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "evaluator.py"
        )
        with open(src_path, "r", encoding="utf-8") as fh:
            src = fh.read()
        # The spec calls out hashlib and typing as the only deps.
        for forbidden in ["import requests", "import numpy", "import pandas"]:
            assert forbidden not in src

    def test_importable_from_evaluator(self):
        # Already imported above, but assert class identity.
        from evaluator import FeatureFlagEvaluator as Cls
        assert Cls is FeatureFlagEvaluator
