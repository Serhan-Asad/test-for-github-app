"""Tests for feature_flags_config.

Test plan (mapped to spec requirements):

  1. Public API surface
     - load_flags returns dict[str, FlagDefinition]
     - module exports load_flags, FlagDefinition, ConfigError
  2. FlagDefinition dataclass
     - has fields name, enabled, rollout (default None)
     - is frozen (immutable)
  3. ConfigError
     - subclass of Exception (not OSError)
  4. Top-level shape validation
     - non-mapping top level -> ConfigError
     - missing 'flags' key -> ConfigError
     - 'flags' value not a mapping (e.g., list) -> ConfigError
  5. YAML parsing
     - uses yaml.safe_load
     - yaml.YAMLError wrapped into ConfigError mentioning path + underlying msg
  6. Missing file
     - FileNotFoundError wrapped into ConfigError; raw FileNotFoundError must
       not escape; message names the missing path
  7. Per-flag validation (each error raises ConfigError naming the flag)
     - returned name equals YAML key
     - 'enabled' required
     - 'enabled' must be Python bool (reject ints / strings like "true")
     - 'rollout' if present must be a number in [0, 100] inclusive
     - 'rollout' rejects bool, strings, lists, etc.
     - 'rollout' absent -> None
     - unknown keys rejected
     - boundary values 0 and 100 accepted; -0.1 and 100.1 rejected
  8. Empty cases
     - completely empty file -> {}
     - 'flags:' mapping with no entries (None) -> {}
     - 'flags:' explicit empty mapping {} -> {}
  9. Idempotency / no global state
     - calling load_flags repeatedly returns equal results
     - calling on the same file twice is safe
 10. Return type / shape
     - keys are strings, values are FlagDefinition instances
     - rollout values are floats (or None)

Each test is designed to fail if the corresponding spec requirement is
violated.
"""

from __future__ import annotations

import dataclasses
import os
import sys

import pytest

# Allow running from any cwd by adding the project root to sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feature_flags_config import ConfigError, FlagDefinition, load_flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path, body: str, name: str = "flags.yaml") -> str:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# 1. Public API surface
# ---------------------------------------------------------------------------


def test_module_exports_public_symbols():
    import feature_flags_config as mod

    assert hasattr(mod, "load_flags")
    assert hasattr(mod, "FlagDefinition")
    assert hasattr(mod, "ConfigError")


def test_load_flags_returns_dict(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n")
    result = load_flags(path)
    assert isinstance(result, dict)
    assert list(result.keys()) == ["a"]
    assert isinstance(result["a"], FlagDefinition)


# ---------------------------------------------------------------------------
# 2. FlagDefinition dataclass
# ---------------------------------------------------------------------------


def test_flag_definition_is_dataclass_with_expected_fields():
    assert dataclasses.is_dataclass(FlagDefinition)
    field_names = {f.name for f in dataclasses.fields(FlagDefinition)}
    assert field_names == {"name", "enabled", "rollout"}


def test_flag_definition_default_rollout_is_none():
    d = FlagDefinition(name="x", enabled=True)
    assert d.rollout is None


def test_flag_definition_is_frozen():
    d = FlagDefinition(name="x", enabled=True, rollout=10.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.enabled = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. ConfigError
# ---------------------------------------------------------------------------


def test_config_error_is_exception_subclass():
    assert issubclass(ConfigError, Exception)
    # Must NOT be an OSError so callers can distinguish I/O errors.
    assert not issubclass(ConfigError, OSError)


# ---------------------------------------------------------------------------
# 4. Top-level shape validation
# ---------------------------------------------------------------------------


def test_top_level_must_be_mapping(tmp_path):
    path = _write(tmp_path, "- a\n- b\n")  # YAML list
    with pytest.raises(ConfigError):
        load_flags(path)


def test_top_level_must_contain_flags_key(tmp_path):
    path = _write(tmp_path, "other: 1\n")
    with pytest.raises(ConfigError):
        load_flags(path)


def test_flags_value_must_be_mapping(tmp_path):
    path = _write(tmp_path, "flags:\n  - one\n  - two\n")
    with pytest.raises(ConfigError):
        load_flags(path)


# ---------------------------------------------------------------------------
# 5. YAML parsing errors
# ---------------------------------------------------------------------------


def test_yaml_parse_error_wrapped_in_config_error(tmp_path):
    # malformed YAML
    path = _write(tmp_path, "flags: : :\n  - [unbalanced\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    msg = str(exc_info.value)
    assert path in msg  # mentions offending file path


def test_yaml_parse_error_uses_safe_load(monkeypatch, tmp_path):
    """Confirms parsing routes through yaml.safe_load (not yaml.load)."""
    import feature_flags_config as mod

    called = {}

    def fake_safe_load(text):
        called["yes"] = True
        return {"flags": {"a": {"enabled": True}}}

    monkeypatch.setattr(mod.yaml, "safe_load", fake_safe_load)
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n")
    result = load_flags(path)
    assert called.get("yes") is True
    assert "a" in result


# ---------------------------------------------------------------------------
# 6. Missing file
# ---------------------------------------------------------------------------


def test_missing_file_raises_config_error(tmp_path):
    missing = str(tmp_path / "nope.yaml")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(missing)
    assert missing in str(exc_info.value)


def test_missing_file_does_not_leak_filenotfounderror(tmp_path):
    missing = str(tmp_path / "nope.yaml")
    try:
        load_flags(missing)
    except ConfigError:
        pass
    except FileNotFoundError:
        pytest.fail("Raw FileNotFoundError must not escape load_flags")


# ---------------------------------------------------------------------------
# 7. Per-flag validation
# ---------------------------------------------------------------------------


def test_returned_name_equals_yaml_key(tmp_path):
    path = _write(
        tmp_path,
        "flags:\n  alpha:\n    enabled: true\n  beta:\n    enabled: false\n",
    )
    result = load_flags(path)
    assert result["alpha"].name == "alpha"
    assert result["beta"].name == "beta"


def test_enabled_required(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    rollout: 50\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_enabled_must_be_bool_reject_int(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: 1\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_enabled_must_be_bool_reject_string(tmp_path):
    path = _write(tmp_path, 'flags:\n  a:\n    enabled: "true"\n')
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_enabled_true_accepted(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n")
    result = load_flags(path)
    assert result["a"].enabled is True


def test_enabled_false_accepted(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: false\n")
    result = load_flags(path)
    assert result["a"].enabled is False


def test_rollout_absent_is_none(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n")
    result = load_flags(path)
    assert result["a"].rollout is None


def test_rollout_integer_accepted(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: 50\n")
    result = load_flags(path)
    assert result["a"].rollout == 50.0


def test_rollout_float_accepted(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: 12.5\n")
    result = load_flags(path)
    assert result["a"].rollout == 12.5


def test_rollout_lower_boundary_accepted(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: 0\n")
    assert load_flags(path)["a"].rollout == 0.0


def test_rollout_upper_boundary_accepted(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: 100\n")
    assert load_flags(path)["a"].rollout == 100.0


def test_rollout_below_zero_rejected(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: -0.1\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_rollout_above_hundred_rejected(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: 100.1\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_rollout_string_rejected(tmp_path):
    path = _write(tmp_path, 'flags:\n  a:\n    enabled: true\n    rollout: "50"\n')
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_rollout_bool_rejected(tmp_path):
    path = _write(tmp_path, "flags:\n  a:\n    enabled: true\n    rollout: true\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_unknown_key_rejected(tmp_path):
    path = _write(
        tmp_path,
        "flags:\n  a:\n    enabled: true\n    description: hi\n",
    )
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


def test_flag_body_must_be_mapping(tmp_path):
    path = _write(tmp_path, "flags:\n  a: true\n")
    with pytest.raises(ConfigError) as exc_info:
        load_flags(path)
    assert "a" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 8. Empty cases
# ---------------------------------------------------------------------------


def test_empty_file_returns_empty_dict(tmp_path):
    path = _write(tmp_path, "")
    assert load_flags(path) == {}


def test_flags_key_with_null_value_returns_empty_dict(tmp_path):
    path = _write(tmp_path, "flags:\n")
    assert load_flags(path) == {}


def test_flags_key_with_explicit_empty_mapping_returns_empty_dict(tmp_path):
    path = _write(tmp_path, "flags: {}\n")
    assert load_flags(path) == {}


# ---------------------------------------------------------------------------
# 9. Idempotency / safe to call repeatedly
# ---------------------------------------------------------------------------


def test_repeated_calls_return_equal_results(tmp_path):
    path = _write(
        tmp_path,
        "flags:\n  a:\n    enabled: true\n    rollout: 25\n",
    )
    first = load_flags(path)
    second = load_flags(path)
    assert first == second
    # Distinct dict objects -> no cached/global state is being shared mutably.
    assert first is not second


# ---------------------------------------------------------------------------
# 10. Return type / shape
# ---------------------------------------------------------------------------


def test_return_value_keys_are_strings_and_values_are_flag_definitions(tmp_path):
    path = _write(
        tmp_path,
        "flags:\n  a:\n    enabled: true\n  b:\n    enabled: false\n    rollout: 10\n",
    )
    result = load_flags(path)
    assert all(isinstance(k, str) for k in result.keys())
    assert all(isinstance(v, FlagDefinition) for v in result.values())
    assert result["b"].rollout == 10.0
    assert isinstance(result["b"].rollout, float)
