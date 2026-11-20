import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { formatMetric, unavailableExplanation } from "../lib/presentation";

/** A label/value pair inside a panel's definition list. */
export const DetailRow = ({ label, children, className }: { label: string; children: ReactNode; className?: string }) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <div className={cn("flex items-start justify-between gap-4 py-2 text-sm", className)}>
      <dt className="shrink-0" style={{ color: textMuted }}>
        {label}
      </dt>
      <dd className="min-w-0 text-right text-foreground">{children}</dd>
    </div>
  );
};

/**
 * A count in a definition list, honouring the null rule: an unmeasured value
 * reads "Unavailable" / "Not currently observable" (with a plain-language
 * tooltip), never 0.
 */
export const CountValue = ({
  value,
  blockStatus,
}: {
  value: number | null | undefined;
  blockStatus?: string | null;
}) => {
  const { textMuted } = useSurfaceTokens();
  const unavailable = value === null || value === undefined;
  return (
    <span
      className={unavailable ? "text-xs" : "font-semibold tabular-nums"}
      style={unavailable ? { color: textMuted } : undefined}
      title={unavailable ? unavailableExplanation(blockStatus) : undefined}
      data-unavailable={unavailable ? "true" : undefined}
    >
      {formatMetric(value, blockStatus)}
    </span>
  );
};
