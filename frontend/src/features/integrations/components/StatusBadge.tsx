import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { presentStatus, type Tone } from "../lib/presentation";

const TONE_CLASS: Record<Tone, string> = {
  positive: "bg-success/10 text-success border-success/25",
  warning: "bg-warning/10 text-amber-700 dark:text-amber-300 border-warning/30",
  negative: "bg-destructive/10 text-destructive border-destructive/25",
  neutral: "bg-muted text-foreground/80 border-border",
  // Dashed and muted: "we cannot see it" must not look like "it is down".
  unknown: "bg-muted/60 text-muted-foreground border-dashed border-muted-foreground/40",
};

/**
 * A status pill. The label is always text (never colour alone), and the raw
 * backend value is kept in `data-status` for tests and support.
 */
export const StatusBadge = ({
  status,
  title,
  className,
}: {
  status: string | null | undefined;
  title?: string | null;
  className?: string;
}) => {
  const { label, tone } = presentStatus(status);
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold",
        TONE_CLASS[tone],
        className,
      )}
      data-status={status ?? "unknown"}
      data-tone={tone}
      title={title ?? undefined}
    >
      {label}
    </span>
  );
};

/**
 * One status inside a status panel: a label, its badge and (optionally) one
 * short plain-language explanation. Several of these sit side by side in a
 * grid; the dimensions are never folded into one verdict.
 */
export const StatusItem = ({
  label,
  status,
  explanation,
  children,
}: {
  label: string;
  status: string | null | undefined;
  explanation?: string | null;
  children?: ReactNode;
}) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <div className="min-w-0 rounded-xl border border-border/60 bg-background/40 px-3.5 py-3" data-status-item={label}>
      <p className="text-xs leading-4" style={{ color: textMuted }}>
        {label}
      </p>
      <div className="mt-1.5">
        <StatusBadge status={status} />
      </div>
      {explanation ? (
        <p className="mt-1.5 text-xs leading-5" style={{ color: textMuted }}>
          {explanation}
        </p>
      ) : null}
      {children}
    </div>
  );
};
