import React from "react";

/**
 * Props for the FlagToggle component.
 *
 * @property flagName  - The identifier of the feature flag (used as `data-flag`).
 * @property enabled   - Whether the experiment row should be rendered.
 * @property children  - The content to display inside the experiment row.
 */
export interface FlagToggleProps {
  flagName: string;
  enabled: boolean;
  children: React.ReactNode;
}

/**
 * A pure, presentational gate component.
 *
 * When `enabled` is `true` it renders its children inside a container
 * `<div>` styled as an experiment row. When `false` it renders nothing.
 *
 * The container `<div>` carries:
 *   - className `experiment-row`        (stable styling hook)
 *   - data-testid `flag-toggle`         (test selector)
 *   - data-flag={flagName}              (downstream targeting)
 *
 * The parent is responsible for resolving the flag value — this component
 * performs no data fetching, no flag resolution, no side effects, no
 * hooks, and no internal state.
 *
 * Note: this file is `.ts` (not `.tsx`), so React.createElement is used
 * directly instead of JSX literal syntax. The runtime output is identical
 * to the equivalent JSX form
 *   <div className="experiment-row" data-testid="flag-toggle"
 *        data-flag={flagName}>{children}</div>
 */
export function FlagToggle({
  flagName,
  enabled,
  children,
}: FlagToggleProps): React.ReactElement | null {
  if (!enabled) {
    return null;
  }

  return React.createElement(
    "div",
    {
      className: "experiment-row",
      "data-testid": "flag-toggle",
      "data-flag": flagName,
    },
    children,
  );
}

export default FlagToggle;
