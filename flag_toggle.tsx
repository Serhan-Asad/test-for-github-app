// frontend/components/FlagToggle.tsx

import React from "react";

export interface FlagToggleProps {
  /** The feature flag identifier, surfaced as a `data-flag-name` attribute. */
  flagName: string;
  /** When `false` the component renders nothing; when `true` it renders children. */
  enabled: boolean;
  /** Optional content to render when the flag is on. */
  children?: React.ReactNode;
}

function FlagToggle({ flagName, enabled, children }: FlagToggleProps): React.ReactElement | null {
  if (!enabled) {
    return null;
  }

  return <div data-flag-name={flagName}>{children}</div>;
}

export default FlagToggle;