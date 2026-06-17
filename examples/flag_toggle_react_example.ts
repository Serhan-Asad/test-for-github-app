/**
 * Example: Using the FlagToggle React component.
 *
 * This example demonstrates the public API of `FlagToggle` from
 * `flag_toggle_react.ts`. `FlagToggle` is a pure presentational React
 * function component that gates its children on a boolean `enabled` prop:
 *
 *   - When `enabled` is `true`, it renders `children` inside a single
 *     container `<div className="experiment-row" data-testid="flag-toggle"
 *     data-flag={flagName}>`.
 *   - When `enabled` is `false`, it renders nothing (returns `null`).
 *
 * Props:
 *   - flagName : string             — the feature-flag identifier; copied
 *                                     verbatim into the `data-flag` attribute
 *                                     so downstream code/tests can target it.
 *   - enabled  : boolean            — gate; `false` ⇒ render nothing.
 *   - children : React.ReactNode    — content shown inside the experiment
 *                                     row when `enabled` is `true`.
 *
 * Returns:
 *   React.ReactElement | null       — the wrapper `<div>` or `null`.
 *
 * The component performs no side effects, no data fetching, and uses no
 * hooks — the parent is responsible for resolving the flag.
 *
 * To execute this example in a real environment:
 *   $ npm install react react-dom @types/react
 *   $ npx ts-node examples/flag_toggle_react_example.ts
 */

import React from "react";
import { FlagToggle, FlagToggleProps } from "../flag_toggle_react";

// --- Demo 1: enabled=true renders children inside a wrapper <div> ---------
const enabledProps: FlagToggleProps = {
  flagName: "new-dashboard",
  enabled: true,
  children: React.createElement("span", null, "Experiment content"),
};
const enabledElement = React.createElement(FlagToggle, enabledProps);
console.log("[demo 1] enabled=true ->",
  enabledElement === null ? "null" : "<FlagToggle> element created");

// --- Demo 2: enabled=false renders nothing (component returns null) -------
const disabledProps: FlagToggleProps = {
  flagName: "new-dashboard",
  enabled: false,
  children: React.createElement("span", null, "Should not appear"),
};
// Direct invocation of the function component to observe its return value.
const disabledOutput = FlagToggle(disabledProps);
console.log("[demo 2] enabled=false direct return ->", disabledOutput);

// --- Demo 3: data-flag forwards the flagName prop ------------------------
const flagName = "checkout-v2";
const taggedOutput = FlagToggle({
  flagName,
  enabled: true,
  children: React.createElement("p", null, "Details"),
}) as React.ReactElement;
console.log("[demo 3] data-flag attribute ->",
  (taggedOutput.props as { ["data-flag"]: string })["data-flag"]);
console.log("[demo 3] className           ->",
  (taggedOutput.props as { className: string }).className);
console.log("[demo 3] data-testid         ->",
  (taggedOutput.props as { ["data-testid"]: string })["data-testid"]);

console.log("FlagToggle example complete.");
