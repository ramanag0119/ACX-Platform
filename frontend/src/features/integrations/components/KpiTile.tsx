import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { useCardSurfaceStyle, useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { formatMetric, unavailableExplanation } from "../lib/presentation";

/** The dashboard KPI accents (features/dashboard/components/DashboardKPIs.tsx). */
export const ACCENT = {
  blue: "#38bdf8",
  green: "#22c55e",
  amber: "#f59e0b",
  red: "#ef4444",
  violet: "#7c5cff",
} as const;

/**
 * One figure, with the anatomy of the HMS dashboard KPI tile: uppercase
 * label, icon chip, 2xl value, one detail line, reserved slot heights.
 *
 * THE NULL RULE: `value === null` renders "Unavailable" / "Not currently
 * observable" plus a short explanation, never 0, and is marked
 * `data-unavailable` so tests can prove it.
 */
export const KpiTile = ({
  label,
  value,
  blockStatus,
  detail,
  icon: Icon,
  accent = ACCENT.violet,
  format,
  emptyText,
  emptyExplanation,
}: {
  label: string;
  value: number | null | undefined;
  blockStatus?: string | null;
  detail?: string;
  icon: LucideIcon;
  accent?: string;
  /** Formats a measured value (e.g. a percentage or duration). */
  format?: (value: number) => string;
  /** When the value is null for a reason other than unavailable data (e.g. no
   *  completed message in the window), the text and explanation to show. */
  emptyText?: string;
  emptyExplanation?: string;
}) => {
  const surface = useCardSurfaceStyle();
  const { titleColor, textMuted } = useSurfaceTokens();
  const unavailable = value === null || value === undefined;
  const footer = unavailable ? (emptyExplanation ?? unavailableExplanation(blockStatus)) : detail;
  const text = unavailable
    ? (emptyText ?? formatMetric(value, blockStatus))
    : format ? format(value as number) : formatMetric(value, blockStatus);

  return (
    <div className="flex h-full min-h-[136px] min-w-0 flex-col rounded-[16px] p-4" style={surface} data-kpi={label}>
      <div className="flex shrink-0 items-start justify-between gap-3">
        <p
          className="line-clamp-2 min-h-[2rem] min-w-0 text-xs uppercase leading-4 tracking-wide"
          style={{ color: textMuted }}
        >
          {label}
        </p>
        <div
          className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-xl sm:flex"
          style={{ background: `${accent}1f`, color: accent }}
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-0.5 flex min-h-[2rem] min-w-0 items-center">
        <p
          className={cn("min-w-0", unavailable ? "text-sm font-medium leading-5" : "truncate text-2xl font-semibold leading-8 tabular-nums")}
          style={{ color: unavailable ? textMuted : titleColor }}
          data-unavailable={unavailable ? "true" : undefined}
        >
          {text}
        </p>
      </div>
      <p className="mt-auto line-clamp-2 min-h-[1rem] pt-1 text-[11px] leading-4" style={{ color: textMuted }}>
        {footer}
      </p>
    </div>
  );
};
