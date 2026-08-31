"""Tests for the fail-closed feature flag evaluator.

Test plan (one-to-one with spec requirements):

  R1. is_enabled returns True only when flag_name is a key in _FLAGS with a
      truthy value; otherwise False.
        - test_is_enabled_known_true_returns_true
        - test_is_enabled_known_false_returns_false
        - test_is_enabled_truthy_non_bool_returns_true (after _set_flags coercion)
        - test_is_enabled_returns_bool_type
  R2. Unknown flag names return False (never raise KeyError).
        - test_is_enabled_unknown_flag_returns_false
        - test_is_enabled_unknown_flag_does_not_raise
  R3. Non-string flag_name (None, int, list, ...) returns False without raising.
        - test_is_enabled_none_flag_name_returns_false
        - test_is_enabled_int_flag_name_returns_false
        - test_is_enabled_non_string_does_not_raise (parametrized)
  R4. uid is accepted but MUST NOT influence the result.
        - test_uid_does_not_influence_result
        - test_uid_can_be_any_type_without_raising
  R5. The function never raises for any input combination (fail-closed).
        - test_is_enabled_never_raises (parametrized over weird inputs)
  R6. _set_flags replaces _FLAGS atomically (clear + update) and coerces to bool.
        - test_set_flags_replaces_state (no merge)
        - test_set_flags_coerces_truthy_to_true
        - test_set_flags_coerces_falsy_to_false
        - test_set_flags_empty_clears_state
        - test_set_flags_returns_none
  R7. _FLAGS is a module-level dict, initially empty (single source of state).
        - test_flags_is_module_level_dict
        - test_flags_initially_empty (verified after a fresh import / clear)
  R8. No I/O, std-lib only (no external imports beyond stdlib).
        - test_module_has_no_external_imports
  R9. Docstring on is_enabled describing fail-closed contract & uid future use.
        - test_is_enabled_has_docstring
        - test_is_enabled_docstring_mentions_uid_future
  R10. Type-annotated public API.
        - test_is_enabled_is_type_annotated
        - test_set_flags_is_type_annotated

Branch coverage:
  - is_enabled: isinstance(flag_name, str) True branch
                isinstance(flag_name, str) False branch
                _FLAGS.get default -> False (unknown key)
                _FLAGS.get returns truthy / falsy
"""

import importlib
import inspect
import re
from pathlib import Path

import pytest

import evaluator
from evaluator import _FLAGS, _set_flags, is_enabled


@pytest.fixture(autouse=True)
def _reset_flags():
    """Ensure each test starts and ends with an empty flag store."""
    _set_flags({})
    yield
    _set_flags({})


# ---------------------------------------------------------------------------
# R1 — is_enabled True only when key present and truthy
# ---------------------------------------------------------------------------

def test_is_enabled_known_true_returns_true():
    _set_flags({"feature_x": True})
    assert is_enabled("feature_x", "uid-1") is True


def test_is_enabled_known_false_returns_false():
    _set_flags({"feature_x": False})
    assert is_enabled("feature_x", "uid-1") is False


def test_is_enabled_returns_bool_type():
    _set_flags({"feature_x": True})
    result = is_enabled("feature_x", "uid-1")
    assert isinstance(result, bool)


def test_is_enabled_truthy_non_bool_returns_true():
    # _set_flags coerces non-bool truthy values to True, so is_enabled True.
    _set_flags({"feature_x": 1})  # type: ignore[dict-item]
    assert is_enabled("feature_x", "uid-1") is True


# ---------------------------------------------------------------------------
# R2 — Unknown flag names return False, never raise KeyError
# ---------------------------------------------------------------------------

def test_is_enabled_unknown_flag_returns_false():
    assert is_enabled("does_not_exist", "uid-1") is False


def test_is_enabled_unknown_flag_does_not_raise():
    # Make sure no KeyError leaks even if flag store was emptied.
    _set_flags({})
    try:
        result = is_enabled("missing", "uid")
    except KeyError:
        pytest.fail("is_enabled raised KeyError for unknown flag")
    assert result is False


# ---------------------------------------------------------------------------
# R3 — Non-string flag_name returns False
# ---------------------------------------------------------------------------

def test_is_enabled_none_flag_name_returns_false():
    assert is_enabled(None, "uid-1") is False  # type: ignore[arg-type]


def test_is_enabled_int_flag_name_returns_false():
    assert is_enabled(42, "uid-1") is False  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_name",
    [None, 0, 1, 3.14, [], (), {}, set(), object(), b"bytes"],
)
def test_is_enabled_non_string_does_not_raise(bad_name):
    # All must return False, no exception.
    assert is_enabled(bad_name, "uid") is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# R4 — uid does not influence the result
# ---------------------------------------------------------------------------

def test_uid_does_not_influence_result():
    _set_flags({"feature_x": True})
    uids = ["", "alice", "bob", "user-9999", "x" * 1000]
    results = [is_enabled("feature_x", u) for u in uids]
    assert all(r is True for r in results)
    assert len(set(results)) == 1


def test_uid_can_be_any_type_without_raising():
    _set_flags({"feature_x": True})
    # The signature says str, but spec R5 says never raises — exercise tolerance.
    for weird_uid in [None, 0, 3.14, [], (), {"a": 1}, object()]:
        # Should not raise; result is True because the flag is on
        # and uid must not influence the result.
        assert is_enabled("feature_x", weird_uid) is True  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# R5 — Never raises for any input combination
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "flag_name, uid",
    [
        (None, None),
        (None, ""),
        ("", None),
        ("", ""),
        (123, 456),
        ([], {}),
        (object(), object()),
        ("a" * 10_000, "u"),
    ],
)
def test_is_enabled_never_raises(flag_name, uid):
    try:
        result = is_enabled(flag_name, uid)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"is_enabled raised {type(exc).__name__}: {exc}")
    assert result is False  # store empty -> always False here


# ---------------------------------------------------------------------------
# R6 — _set_flags replaces atomically and coerces to bool
# ---------------------------------------------------------------------------

def test_set_flags_replaces_state():
    _set_flags({"a": True, "b": True})
    _set_flags({"c": True})
    # Old keys gone:
    assert is_enabled("a", "u") is False
    assert is_enabled("b", "u") is False
    # New key present:
    assert is_enabled("c", "u") is True


def test_set_flags_coerces_truthy_to_true():
    _set_flags({"x": 1, "y": "yes", "z": [0]})  # type: ignore[dict-item]
    # The stored values must be canonical True after coercion.
    assert evaluator._FLAGS["x"] is True
    assert evaluator._FLAGS["y"] is True
    assert evaluator._FLAGS["z"] is True


def test_set_flags_coerces_falsy_to_false():
    _set_flags({"x": 0, "y": "", "z": []})  # type: ignore[dict-item]
    assert evaluator._FLAGS["x"] is False
    assert evaluator._FLAGS["y"] is False
    assert evaluator._FLAGS["z"] is False


def test_set_flags_empty_clears_state():
    _set_flags({"a": True, "b": True})
    _set_flags({})
    assert dict(evaluator._FLAGS) == {}


def test_set_flags_returns_none():
    assert _set_flags({"a": True}) is None


def test_set_flags_uses_same_module_dict_object():
    # "Replaces contents" — the same underlying dict object stays.
    original_id = id(evaluator._FLAGS)
    _set_flags({"a": True})
    assert id(evaluator._FLAGS) == original_id


# ---------------------------------------------------------------------------
# R7 — _FLAGS module-level dict, initially empty
# ---------------------------------------------------------------------------

def test_flags_is_module_level_dict():
    assert hasattr(evaluator, "_FLAGS")
    assert isinstance(evaluator._FLAGS, dict)


def test_flags_initially_empty_on_fresh_import():
    # Reload the module in isolation and verify the *initial* state is empty.
    fresh = importlib.reload(importlib.import_module("evaluator"))
    try:
        assert fresh._FLAGS == {}
    finally:
        # Restore the autouse fixture's empty state for safety.
        fresh._set_flags({})


# ---------------------------------------------------------------------------
# R8 — No I/O / std-lib only
# ---------------------------------------------------------------------------

def test_module_has_no_external_imports():
    src = Path(evaluator.__file__).read_text()
    # Reject any "import" / "from X import" line that references a non-stdlib
    # third-party package.  Stdlib-only modules pass; we're strict and require
    # no imports at all because the spec says "standard library only" and the
    # module doesn't need anything.
    import_lines = [
        line.strip()
        for line in src.splitlines()
        if re.match(r"^\s*(import|from)\s+\w", line)
    ]
    # All imports (if any) must be from stdlib.  In practice this module
    # should have zero imports.
    assert import_lines == [], f"Unexpected imports: {import_lines}"


# ---------------------------------------------------------------------------
# R9 — Docstring on is_enabled
# ---------------------------------------------------------------------------

def test_is_enabled_has_docstring():
    assert is_enabled.__doc__ is not None
    assert is_enabled.__doc__.strip() != ""


def test_is_enabled_docstring_mentions_uid_future():
    doc = (is_enabled.__doc__ or "").lower()
    # Should describe fail-closed contract AND uid being reserved/future.
    assert "uid" in doc
    # At least one of these phrases describing forward-compat:
    assert any(word in doc for word in ("future", "reserved", "forward"))


# ---------------------------------------------------------------------------
# R10 — Type-annotated public API
# ---------------------------------------------------------------------------

def test_is_enabled_is_type_annotated():
    sig = inspect.signature(is_enabled)
    params = sig.parameters
    assert params["flag_name"].annotation is str
    assert params["uid"].annotation is str
    assert sig.return_annotation is bool


def test_set_flags_is_type_annotated():
    sig = inspect.signature(_set_flags)
    # Return annotation must be None.
    assert sig.return_annotation is None or sig.return_annotation is type(None)
    # The "flags" parameter must have *some* annotation (dict[str, bool] or alias).
    assert sig.parameters["flags"].annotation is not inspect.Parameter.empty


# ---------------------------------------------------------------------------
# Branch coverage — explicit both-branches of `isinstance` check
# ---------------------------------------------------------------------------

def test_branch_isinstance_str_true():
    _set_flags({"on": True})
    assert is_enabled("on", "u") is True   # hits str-branch + truthy get


def test_branch_isinstance_str_false():
    _set_flags({"on": True})
    assert is_enabled(123, "u") is False  # type: ignore[arg-type]
    # hits non-str branch
