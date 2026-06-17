/**
 * Test plan for FlagToggle (derived from prompt spec):
 *
 *  Spec requirements →  test mapping
 *  ----------------------------------
 *  R1. Named export `FlagToggle` (also default export) typed as
 *      { flagName: string; enabled: boolean; children: React.ReactNode }.
 *        → tests "named export exists", "default export equals named export",
 *          "props are forwarded by name".
 *
 *  R2. When `enabled` is `false`, render nothing (return `null`).
 *        → test "returns null when enabled is false".
 *
 *  R3. When `enabled` is `true`, render `children` wrapped in a single
 *      container `<div>` (the experiment row).
 *        → tests "returns a div element when enabled is true",
 *                "wraps children in the div",
 *                "wraps multiple children",
 *                "container is a single element (not a fragment / array)".
 *
 *  R4. Container `<div>` has data-testid="flag-toggle" and
 *      data-flag={flagName}.
 *        → tests "data-testid attribute equals 'flag-toggle'",
 *                "data-flag attribute equals flagName prop",
 *                "data-flag forwards different flagName values".
 *
 *  R5. Container `<div>` has className `experiment-row`.
 *        → test "className attribute equals 'experiment-row'".
 *
 *  R6. Component is a pure function with no hooks / state / side effects.
 *        → tests "calling repeatedly with same props yields equivalent
 *          output", "same input ⇒ deterministic output (purity)".
 *
 *  R7. Imports only from `react` (no other runtime deps).
 *        → static check via reading the source file in
 *          "code file imports only from react".
 *
 *  Branch coverage:
 *    - if (!enabled) → tested by R2
 *    - else (render div) → tested by R3, R4, R5
 *
 *  Regression guards:
 *    - data-testid must be exactly "flag-toggle" (not e.g. "FlagToggle").
 *    - className must be exactly "experiment-row".
 *    - When enabled=false the return must be `null` (not `undefined`,
 *      not an empty fragment, not an empty div).
 */

import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as React from "react";

import FlagToggleDefault, {
  FlagToggle,
  FlagToggleProps,
} from "./flag_toggle_react";

// ------------------------------------------------------------------ helpers
function elementProps(el: unknown): Record<string, unknown> {
  // React 18 ReactElement: { type, props, key, ... }
  return (el as { props: Record<string, unknown> }).props;
}

function elementType(el: unknown): unknown {
  return (el as { type: unknown }).type;
}

const childA = React.createElement("span", { key: "a" }, "Experiment content");
const childB = React.createElement("p", { key: "b" }, "Details");

// ------------------------------------------------------------------ R1: exports
test("named export FlagToggle exists and is a function", () => {
  assert.equal(typeof FlagToggle, "function");
});

test("default export equals named export", () => {
  assert.equal(FlagToggleDefault, FlagToggle);
});

// ------------------------------------------------------------------ R2: enabled=false
test("returns null when enabled is false", () => {
  const out = FlagToggle({
    flagName: "new-dashboard",
    enabled: false,
    children: childA,
  });
  assert.equal(out, null);
});

test("returns null when enabled is false, regardless of children content", () => {
  const out = FlagToggle({
    flagName: "x",
    enabled: false,
    children: React.createElement("div", null, "anything"),
  });
  // Must be exactly `null`, not just falsy.
  assert.strictEqual(out, null);
});

// ------------------------------------------------------------------ R3: wraps children in <div>
test("returns a div element when enabled is true", () => {
  const out = FlagToggle({
    flagName: "new-dashboard",
    enabled: true,
    children: childA,
  });
  assert.notEqual(out, null);
  assert.equal(elementType(out), "div");
});

test("wraps a single child inside the container div", () => {
  const out = FlagToggle({
    flagName: "f",
    enabled: true,
    children: childA,
  }) as React.ReactElement;
  assert.equal(elementProps(out).children, childA);
});

test("wraps multiple children inside the container div", () => {
  const kids = [childA, childB];
  const out = FlagToggle({
    flagName: "f",
    enabled: true,
    children: kids,
  }) as React.ReactElement;
  assert.deepEqual(elementProps(out).children, kids);
});

test("returns a single element (not a fragment or array)", () => {
  const out = FlagToggle({
    flagName: "f",
    enabled: true,
    children: childA,
  });
  assert.equal(Array.isArray(out), false);
  // React.Fragment has Symbol(react.fragment) as its type. We require a div.
  assert.equal(elementType(out), "div");
});

// ------------------------------------------------------------------ R4: data-testid + data-flag
test("data-testid attribute equals 'flag-toggle'", () => {
  const out = FlagToggle({
    flagName: "any",
    enabled: true,
    children: childA,
  }) as React.ReactElement;
  assert.equal(elementProps(out)["data-testid"], "flag-toggle");
});

test("data-flag attribute equals flagName prop", () => {
  const out = FlagToggle({
    flagName: "checkout-v2",
    enabled: true,
    children: childB,
  }) as React.ReactElement;
  assert.equal(elementProps(out)["data-flag"], "checkout-v2");
});

test("data-flag forwards different flagName values verbatim", () => {
  for (const name of ["a", "b-c", "very_long_flag_name_42"]) {
    const out = FlagToggle({
      flagName: name,
      enabled: true,
      children: childA,
    }) as React.ReactElement;
    assert.equal(elementProps(out)["data-flag"], name);
  }
});

// ------------------------------------------------------------------ R5: className
test("className attribute equals 'experiment-row'", () => {
  const out = FlagToggle({
    flagName: "f",
    enabled: true,
    children: childA,
  }) as React.ReactElement;
  assert.equal(elementProps(out).className, "experiment-row");
});

// ------------------------------------------------------------------ R6: purity
test("same input yields equivalent output (purity / determinism)", () => {
  const props: FlagToggleProps = {
    flagName: "pure",
    enabled: true,
    children: childA,
  };
  const a = FlagToggle(props) as React.ReactElement;
  const b = FlagToggle(props) as React.ReactElement;
  assert.equal(elementType(a), elementType(b));
  assert.deepEqual(elementProps(a), elementProps(b));
});

test("two disabled invocations both return null (no internal state)", () => {
  const a = FlagToggle({ flagName: "x", enabled: false, children: childA });
  const b = FlagToggle({ flagName: "x", enabled: false, children: childB });
  assert.equal(a, null);
  assert.equal(b, null);
});

// ------------------------------------------------------------------ R7: imports
test("code file imports only from react", () => {
  const src = fs.readFileSync(
    path.join(__dirname, "flag_toggle_react.ts"),
    "utf8",
  );
  const importLines = src
    .split("\n")
    .filter((line) => /^\s*import\s/.test(line));
  assert.notEqual(importLines.length, 0, "expected at least one import");
  for (const line of importLines) {
    const match = line.match(/from\s+['"]([^'"]+)['"]/);
    assert.notEqual(match, null, `import without a from: ${line}`);
    assert.equal(
      match![1],
      "react",
      `non-react import detected: ${line.trim()}`,
    );
  }
});

// ------------------------------------------------------------- branch combos
test("toggle: enabled=true ⇒ div, enabled=false ⇒ null (both branches)", () => {
  const onP: FlagToggleProps = {
    flagName: "toggle-test",
    enabled: true,
    children: childA,
  };
  const offP: FlagToggleProps = {
    flagName: "toggle-test",
    enabled: false,
    children: childA,
  };
  const onOut = FlagToggle(onP);
  const offOut = FlagToggle(offP);
  assert.equal(elementType(onOut), "div");
  assert.equal(offOut, null);
});
