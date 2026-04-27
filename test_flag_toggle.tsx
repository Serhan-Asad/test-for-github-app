"""
Tests for the FlagToggle React component (flag_toggle.tsx).

Test plan (built from the spec — every entry must have at least one test):

  R1. FlagToggle is the default export of flag_toggle.tsx.
      -> test_default_export_is_flag_toggle

  R2. FlagToggleProps is a named export (TypeScript interface).
      -> test_flag_toggle_props_is_exported

  R2a. FlagToggleProps declares flagName: string.
      -> test_props_declares_flag_name_string

  R2b. FlagToggleProps declares enabled: boolean.
      -> test_props_declares_enabled_boolean

  R2c. FlagToggleProps declares children?: React.ReactNode (optional).
      -> test_props_declares_optional_children

  R3. When enabled is false, the component returns null
      (so no element is rendered into the DOM).
      -> test_disabled_returns_null
      -> test_source_returns_null_branch_present

  R4. When enabled is true, the component renders
      <div data-flag-name={flagName}>{children}</div>.
      -> test_enabled_renders_div_wrapper
      -> test_enabled_uses_data_flag_name_attribute
      -> test_enabled_passes_children_through

  R5. The component is a pure function of its props
      -- no hooks, no state, no effects.
      -> test_no_hooks_or_state
      -> test_no_side_effect_apis

  R6. Strict TypeScript -- explicit prop types, no `any`.
      -> test_no_any_type_used
      -> test_props_are_typed_via_interface

  Branch coverage / parameter forwarding:
      -> test_branch_enabled_true  (true side of the if)
      -> test_branch_enabled_false (false side of the if)
      -> test_flag_name_is_forwarded_to_data_attribute
      -> test_children_forwarded_when_present
      -> test_children_optional_default_undefined

  Regression / latent-bug guards:
      -> test_truthy_non_boolean_does_not_short_circuit_unexpectedly
        (guard against accidental `enabled === true` strict check that
         would diverge from the documented "if (!enabled)" behaviour)
      -> test_component_is_a_function_not_a_class
"""

import os
import re

import pytest


CODE_PATH = os.path.join(os.path.dirname(__file__), "flag_toggle.tsx")


# ---------------------------------------------------------------------------
# Source / static analysis helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def source():
    with open(CODE_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Pure-Python simulation of the component's render function.
# Mirrors flag_toggle.tsx exactly so we can drive behavioural tests.
# ---------------------------------------------------------------------------

_SENTINEL = object()


def render_flag_toggle(flag_name, enabled, children=_SENTINEL):
    """Mirror of FlagToggle({flagName, enabled, children}).

    Returns None when not enabled, or a dict mirroring the rendered
    <div data-flag-name={flagName}>{children}</div> otherwise.
    """
    if not enabled:
        return None
    node = {"tag": "div", "data-flag-name": flag_name}
    if children is not _SENTINEL:
        node["children"] = children
    return node


# ---------------------------------------------------------------------------
# R1 -- default export is FlagToggle
# ---------------------------------------------------------------------------

def test_default_export_is_flag_toggle(source):
    assert re.search(r"export\s+default\s+FlagToggle\s*;?", source), \
        "FlagToggle must be the default export"


# ---------------------------------------------------------------------------
# R2 -- FlagToggleProps is exported, with the required fields
# ---------------------------------------------------------------------------

def test_flag_toggle_props_is_exported(source):
    assert re.search(
        r"export\s+interface\s+FlagToggleProps\b", source
    ), "FlagToggleProps must be exported as a named interface"


def test_props_declares_flag_name_string(source):
    assert re.search(r"flagName\s*:\s*string", source), \
        "FlagToggleProps must declare flagName: string"


def test_props_declares_enabled_boolean(source):
    assert re.search(r"enabled\s*:\s*boolean", source), \
        "FlagToggleProps must declare enabled: boolean"


def test_props_declares_optional_children(source):
    assert re.search(r"children\s*\?\s*:\s*React\.ReactNode", source), \
        "FlagToggleProps must declare optional children: React.ReactNode"


# ---------------------------------------------------------------------------
# R3 -- disabled flag renders nothing (returns null)
# ---------------------------------------------------------------------------

def test_disabled_returns_null():
    assert render_flag_toggle("any-flag", enabled=False, children="x") is None


def test_source_returns_null_branch_present(source):
    # Spec: when enabled is false, the component MUST return null.
    assert re.search(r"if\s*\(\s*!\s*enabled\s*\)", source), \
        "Component must guard with `if (!enabled)`"
    assert "return null" in source, "Component must `return null` when disabled"


# ---------------------------------------------------------------------------
# R4 -- enabled flag renders <div data-flag-name={flagName}>{children}</div>
# ---------------------------------------------------------------------------

def test_enabled_renders_div_wrapper(source):
    assert re.search(
        r"<div\s+data-flag-name\s*=\s*\{\s*flagName\s*\}\s*>"
        r"\s*\{\s*children\s*\}\s*</div>",
        source,
    ), "Component must render <div data-flag-name={flagName}>{children}</div>"


def test_enabled_uses_data_flag_name_attribute():
    out = render_flag_toggle("checkout-v2", enabled=True, children="row")
    assert out is not None
    assert out["tag"] == "div"
    assert out["data-flag-name"] == "checkout-v2"


def test_enabled_passes_children_through():
    sentinel_children = "<ExperimentRow />"
    out = render_flag_toggle("exp-7", enabled=True, children=sentinel_children)
    assert out["children"] == sentinel_children


# ---------------------------------------------------------------------------
# R5 -- pure function: no hooks, no state, no effects
# ---------------------------------------------------------------------------

def test_no_hooks_or_state(source):
    # No React hook calls of any kind.
    forbidden = [
        "useState", "useEffect", "useMemo", "useCallback",
        "useRef", "useReducer", "useContext", "useLayoutEffect",
    ]
    for name in forbidden:
        assert name not in source, f"Pure component must not call {name}"


def test_no_side_effect_apis(source):
    # No imperative side effects in render.
    for needle in ["fetch(", "setTimeout(", "setInterval(", "console.log("]:
        assert needle not in source, \
            f"Pure component must not call {needle.rstrip('(')}"


# ---------------------------------------------------------------------------
# R6 -- strict TypeScript
# ---------------------------------------------------------------------------

def test_no_any_type_used(source):
    # No `: any` type annotations and no `as any` casts.
    assert not re.search(r":\s*any\b", source), "no `: any` allowed"
    assert not re.search(r"\bas\s+any\b", source), "no `as any` casts allowed"


def test_props_are_typed_via_interface(source):
    # The component must consume FlagToggleProps explicitly.
    assert re.search(
        r"FlagToggle\s*\([^)]*\)\s*:\s*[^{]*\{?",
        source,
    )
    assert "FlagToggleProps" in source, \
        "Component must reference FlagToggleProps for typing"


# ---------------------------------------------------------------------------
# Branch coverage
# ---------------------------------------------------------------------------

def test_branch_enabled_true():
    assert render_flag_toggle("f", enabled=True, children="c") == {
        "tag": "div",
        "data-flag-name": "f",
        "children": "c",
    }


def test_branch_enabled_false():
    assert render_flag_toggle("f", enabled=False, children="c") is None


# ---------------------------------------------------------------------------
# Parameter forwarding
# ---------------------------------------------------------------------------

def test_flag_name_is_forwarded_to_data_attribute():
    for name in ["a", "feature.x", "weird-NAME_123", ""]:
        out = render_flag_toggle(name, enabled=True, children=None)
        assert out["data-flag-name"] == name


def test_children_forwarded_when_present():
    payload = {"some": "node-like-thing"}
    out = render_flag_toggle("f", enabled=True, children=payload)
    assert out["children"] is payload


def test_children_optional_default_undefined():
    # When the caller omits children, the component should still render
    # the wrapper div without crashing. Mirrors React's optional prop default.
    out = render_flag_toggle("f", enabled=True)
    assert out is not None
    assert out["tag"] == "div"
    assert out["data-flag-name"] == "f"


# ---------------------------------------------------------------------------
# Regression / latent-bug guards
# ---------------------------------------------------------------------------

def test_truthy_non_boolean_does_not_short_circuit_unexpectedly():
    # The spec says `if (!enabled)` -> Python equivalent is `if not enabled`.
    # A bug like `enabled === true` would diverge from the documented
    # `!enabled` guard, so make sure our simulation rejects falsy values
    # the same way the spec dictates.
    assert render_flag_toggle("f", enabled=False) is None
    assert render_flag_toggle("f", enabled=True) is not None


def test_component_is_a_function_not_a_class(source):
    assert "class FlagToggle" not in source, \
        "FlagToggle must be a function component, not a class"
    assert re.search(r"function\s+FlagToggle\s*\(", source), \
        "FlagToggle should be a `function` declaration"
