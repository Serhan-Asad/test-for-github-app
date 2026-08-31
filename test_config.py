"""Tests for config.load_config.

Test plan (one-to-one with the spec requirements):

1. Requirement 1 — public function exists with correct signature returning dict.
   - test_load_config_is_callable_and_returns_dict_for_mapping

2. Requirement 2 — uses yaml.safe_load, NOT yaml.load.
   - test_uses_safe_load_not_load

3. Requirement 3 — accepts str and pathlib.Path; opens with UTF-8 text mode.
   - test_accepts_str_path
   - test_accepts_pathlib_path
   - test_opens_file_with_utf8_encoding

4. Requirement 4 — None / list / scalar root normalizes to {}.
   - test_empty_file_returns_empty_dict
   - test_list_root_returns_empty_dict
   - test_scalar_string_root_returns_empty_dict
   - test_scalar_int_root_returns_empty_dict
   - test_scalar_bool_root_returns_empty_dict

5. Requirement 5 — mapping root returned unchanged.
   - test_mapping_root_returned_unchanged
   - test_nested_mapping_preserved

6. Requirement 6 — graceful errors return {} and log a WARNING via getLogger(__name__).
   - test_file_not_found_returns_empty_and_logs_warning
   - test_permission_error_returns_empty_and_logs_warning
   - test_oserror_returns_empty_and_logs_warning
   - test_yaml_error_returns_empty_and_logs_warning
   - test_warning_logger_uses_module_name

7. Requirement 7 — unrelated exceptions (e.g. TypeError from wrong-typed path) propagate.
   - test_typeerror_from_bad_path_propagates

8. Requirement 8 — module is importable with no side effects.
   - test_module_is_importable_no_side_effects

9. Requirement 9 — module-level and function-level docstrings present.
   - test_module_has_docstring
   - test_function_has_docstring

10. Requirement 10 — type hints on public function.
    - test_function_has_type_hints

11. Public API exposes only load_config.
    - test_all_exposes_only_load_config
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pathlib
import sys
import os

import pytest
import yaml

# Make the project root importable when pytest is run from anywhere.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import config as config_module  # noqa: E402
from config import load_config  # noqa: E402


# ---------------------------------------------------------------------------
# Requirement 1 — signature & return type
# ---------------------------------------------------------------------------

def test_load_config_is_callable_and_returns_dict_for_mapping(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "f.yaml"
    p.write_text("key: value\n", encoding="utf-8")
    result = load_config(p)
    assert isinstance(result, dict)
    assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# Requirement 2 — uses yaml.safe_load
# ---------------------------------------------------------------------------

def test_uses_safe_load_not_load(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The module must call yaml.safe_load (not yaml.load directly).

    We can't patch yaml.load because safe_load internally calls it with SafeLoader,
    so we instead verify safe_load is the entry point used by config.load_config
    AND inspect the source to confirm yaml.load is never directly invoked.
    """
    p = tmp_path / "f.yaml"
    p.write_text("a: 1\n", encoding="utf-8")

    calls = {"safe_load": 0}
    real_safe_load = yaml.safe_load

    def fake_safe_load(stream):
        calls["safe_load"] += 1
        return real_safe_load(stream)

    monkeypatch.setattr(config_module.yaml, "safe_load", fake_safe_load)

    result = load_config(p)
    assert result == {"a": 1}
    assert calls["safe_load"] == 1

    # Confirm yaml.load is NOT used directly in the module source.
    src = inspect.getsource(config_module)
    assert "yaml.safe_load" in src
    # Strip comments/strings is overkill; just check there's no bare yaml.load( call.
    import re
    assert re.search(r"\byaml\.load\s*\(", src) is None, (
        "config module must not call yaml.load directly; use yaml.safe_load"
    )


# ---------------------------------------------------------------------------
# Requirement 3 — accepts str/Path, opens with UTF-8
# ---------------------------------------------------------------------------

def test_accepts_str_path(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "f.yaml"
    p.write_text("k: v\n", encoding="utf-8")
    result = load_config(str(p))
    assert result == {"k": "v"}


def test_accepts_pathlib_path(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "f.yaml"
    p.write_text("k: v\n", encoding="utf-8")
    result = load_config(p)
    assert result == {"k": "v"}


def test_opens_file_with_utf8_encoding(tmp_path: pathlib.Path) -> None:
    """Non-ASCII content must round-trip via the UTF-8 text-mode open."""
    p = tmp_path / "f.yaml"
    # Write bytes explicitly as UTF-8 to verify the loader decodes them as UTF-8.
    p.write_bytes("greeting: héllo — 世界\n".encode("utf-8"))
    result = load_config(p)
    assert result == {"greeting": "héllo — 世界"}


# ---------------------------------------------------------------------------
# Requirement 4 — None / non-mapping → {}
# ---------------------------------------------------------------------------

def test_empty_file_returns_empty_dict(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    assert load_config(p) == {}


def test_list_root_returns_empty_dict(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    assert load_config(p) == {}


def test_scalar_string_root_returns_empty_dict(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "scalar.yaml"
    p.write_text("just-a-string\n", encoding="utf-8")
    assert load_config(p) == {}


def test_scalar_int_root_returns_empty_dict(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "scalar.yaml"
    p.write_text("42\n", encoding="utf-8")
    assert load_config(p) == {}


def test_scalar_bool_root_returns_empty_dict(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "scalar.yaml"
    p.write_text("true\n", encoding="utf-8")
    assert load_config(p) == {}


# ---------------------------------------------------------------------------
# Requirement 5 — mapping returned unchanged
# ---------------------------------------------------------------------------

def test_mapping_root_returned_unchanged(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "m.yaml"
    p.write_text(
        "flag_a:\n"
        "  enabled: true\n"
        "  rollout: 0.25\n"
        "flag_b:\n"
        "  enabled: false\n",
        encoding="utf-8",
    )
    result = load_config(p)
    assert result == {
        "flag_a": {"enabled": True, "rollout": 0.25},
        "flag_b": {"enabled": False},
    }


def test_nested_mapping_preserved(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "m.yaml"
    p.write_text(
        "a:\n"
        "  b:\n"
        "    c: 1\n"
        "    d:\n"
        "      - x\n"
        "      - y\n",
        encoding="utf-8",
    )
    result = load_config(p)
    assert result == {"a": {"b": {"c": 1, "d": ["x", "y"]}}}


# ---------------------------------------------------------------------------
# Requirement 6 — graceful errors → {} and log WARNING
# ---------------------------------------------------------------------------

def test_file_not_found_returns_empty_and_logs_warning(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "nope.yaml"
    with caplog.at_level(logging.WARNING, logger="config"):
        result = load_config(missing)
    assert result == {}
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings, "expected a WARNING to be logged"
    assert str(missing) in warnings[0].getMessage()


def test_permission_error_returns_empty_and_logs_warning(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    p = tmp_path / "f.yaml"
    p.write_text("a: 1\n", encoding="utf-8")

    real_open = open

    def fake_open(file, *args, **kwargs):
        if str(file) == str(p):
            raise PermissionError("denied")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(config_module, "open", fake_open, raising=False)

    with caplog.at_level(logging.WARNING, logger="config"):
        result = load_config(p)
    assert result == {}
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(str(p) in m for m in msgs)


def test_oserror_returns_empty_and_logs_warning(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    p = tmp_path / "f.yaml"
    p.write_text("a: 1\n", encoding="utf-8")

    def fake_open(file, *args, **kwargs):
        raise OSError("disk on fire")

    monkeypatch.setattr(config_module, "open", fake_open, raising=False)

    with caplog.at_level(logging.WARNING, logger="config"):
        result = load_config(p)
    assert result == {}
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(str(p) in m for m in msgs)
    assert any("disk on fire" in m for m in msgs)


def test_yaml_error_returns_empty_and_logs_warning(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    p = tmp_path / "bad.yaml"
    # Unterminated flow sequence — guaranteed YAMLError.
    p.write_text("key: [unterminated\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="config"):
        result = load_config(p)
    assert result == {}
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(str(p) in m for m in msgs)


def test_warning_logger_uses_module_name(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Spec: log via logging.getLogger(__name__) — i.e. logger named 'config'."""
    missing = tmp_path / "absent.yaml"
    with caplog.at_level(logging.WARNING):
        load_config(missing)
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "expected a WARNING record"
    assert any(r.name == "config" for r in warning_records), (
        f"expected a warning from logger 'config', got: {[r.name for r in warning_records]}"
    )


# ---------------------------------------------------------------------------
# Requirement 7 — unrelated exceptions propagate
# ---------------------------------------------------------------------------

def test_typeerror_from_bad_path_propagates() -> None:
    """A wrong-typed path (e.g. an int) should raise — load_config must not swallow it."""
    with pytest.raises(TypeError):
        # open() raises TypeError when given a non-path-like object that is not int fd-ish.
        # An object() reliably triggers TypeError.
        load_config(object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Requirement 8 — importable with no side effects
# ---------------------------------------------------------------------------

def test_module_is_importable_no_side_effects() -> None:
    # Re-importing must not raise. We can't truly assert "no side effects" but we can
    # confirm the module has no top-level mutable state we can detect.
    mod = importlib.reload(config_module)
    assert hasattr(mod, "load_config")
    # No top-level mutable container intended for runtime state.
    public = [n for n in vars(mod) if not n.startswith("_")]
    # Allow imports + load_config; reject obvious mutable global state.
    for name in public:
        val = getattr(mod, name)
        if name == "load_config":
            continue
        # Modules and the yaml import are fine. Reject lists/dicts/sets at module level
        # other than __all__.
        if name == "__all__":
            continue
        assert not isinstance(val, (list, dict, set)) or name == "__all__", (
            f"unexpected mutable global: {name}={val!r}"
        )


# ---------------------------------------------------------------------------
# Requirement 9 — docstrings present
# ---------------------------------------------------------------------------

def test_module_has_docstring() -> None:
    assert config_module.__doc__ is not None
    assert len(config_module.__doc__.strip()) > 0


def test_function_has_docstring() -> None:
    assert load_config.__doc__ is not None
    assert len(load_config.__doc__.strip()) > 0


# ---------------------------------------------------------------------------
# Requirement 10 — type hints on public function
# ---------------------------------------------------------------------------

def test_function_has_type_hints() -> None:
    sig = inspect.signature(load_config)
    path_param = sig.parameters["path"]
    assert path_param.annotation is not inspect.Parameter.empty, "path must have a type hint"
    assert sig.return_annotation is not inspect.Signature.empty, "return type must be annotated"
    # Return annotation should be `dict` (or equivalent).
    assert sig.return_annotation in (dict, "dict")


# ---------------------------------------------------------------------------
# __all__ exposes only load_config
# ---------------------------------------------------------------------------

def test_all_exposes_only_load_config() -> None:
    assert getattr(config_module, "__all__", None) == ["load_config"]
