import React from "react";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { cn } from "@/lib/utils";

export interface DonutHoleMetricRow {
  label: string;
  value: React.ReactNode;
}

export interface DonutHoleSliceInfo {
  name: string;
  color?: string;
  count?: number | string;
  percent?: number | string;
  extraRows?: DonutHoleMetricRow[];
}

export interface DonutHoleTooltipProps {
  /** If present, the chart is in hover state displaying this segment's details. */
  hoveredSlice?: DonutHoleSliceInfo | null;
  /** Resting state total value (e.g. total count "2" or percentage "100%"). */
  totalValue?: React.ReactNode;
  /** Resting state subtitle/label (e.g. "Room Service" or "Total Requests"). */
  totalLabel?: React.ReactNode;
  /** Custom CSS classes for the outer overlay container. */
  className?: string;
  /** Optional custom title for resting state tooltip. */
  restingTitle?: string;
}

/**
 * Reusable center-hole presentation for HMS donut charts.
 *
 * Implements a clean, centered, theme-aware tooltip overlay positioned
 * within the donut hole.
 * - In resting state: displays headline metric and category label.
 * - On hover: smoothly transitions to a compact, perfectly centered card
 *   displaying segment name, color indicator, share percentage, and count.
 * - Matches the visual hierarchy and styling of the Occupancy Statistics reference.
 * - Pointer events are disabled to ensure smooth chart segment hover tracking.
 */
export const DonutHoleTooltip: React.FC<DonutHoleTooltipProps> = ({
  hoveredSlice,
  totalValue,
  totalLabel,
  className,
  restingTitle,
}) => {
  const tokens = useSurfaceTokens();

  return (
    <div
      className={cn(
        "absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center select-none z-10",
        className
      )}
    >
      {hoveredSlice ? (
        <div
          className="rounded-xl px-3.5 py-2 text-xs transition-all duration-200 animate-fade-in shadow-md min-w-[120px] max-w-[145px]"
          style={{
            background: tokens.tooltipBg,
            border: tokens.tooltipBorder,
            boxShadow: tokens.cardShadow,
          }}
        >
          {/* Segment Name with Color Indicator */}
          <div className="flex items-center justify-center gap-1.5 font-medium mb-1">
            {hoveredSlice.color && (
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ background: hoveredSlice.color }}
              />
            )}
            <span
              className="truncate font-semibold text-xs"
              style={{ color: tokens.titleColor }}
              title={hoveredSlice.name}
            >
              {hoveredSlice.name}
            </span>
          </div>

          {/* Share Percentage */}
          {hoveredSlice.percent !== undefined && (
            <div
              className="flex items-center justify-between gap-3 font-normal text-[11px]"
              style={{ color: tokens.textMuted }}
            >
              <span>Share:</span>
              <span
                className="font-semibold tabular-nums"
                style={{ color: tokens.titleColor }}
              >
                {hoveredSlice.percent}%
              </span>
            </div>
          )}

          {/* Count */}
          {hoveredSlice.count !== undefined && (
            <div
              className="flex items-center justify-between gap-3 font-normal text-[11px] mt-0.5"
              style={{ color: tokens.textMuted }}
            >
              <span>Count:</span>
              <span
                className="font-semibold tabular-nums"
                style={{ color: tokens.titleColor }}
              >
                {hoveredSlice.count}
              </span>
            </div>
          )}

          {/* Optional extra rows */}
          {hoveredSlice.extraRows?.map((row, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between gap-3 font-normal text-[11px] mt-0.5"
              style={{ color: tokens.textMuted }}
            >
              <span>{row.label}:</span>
              <span
                className="font-semibold tabular-nums"
                style={{ color: tokens.titleColor }}
              >
                {row.value}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center animate-fade-in">
          {totalValue !== undefined && (
            <span
              className="text-3xl font-bold tracking-tight"
              style={{ color: tokens.titleColor }}
            >
              {totalValue}
            </span>
          )}
          {totalLabel !== undefined && (
            <span
              className="text-xs font-medium mt-0.5 max-w-[105px] leading-tight line-clamp-2"
              style={{ color: tokens.textMuted }}
              title={restingTitle ?? (typeof totalLabel === "string" ? totalLabel : undefined)}
            >
              {totalLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Custom Recharts Tooltip renderer for donut charts.
 * Can be passed directly to `<Tooltip content={<DonutHoleTooltipContent />} />`.
 * Positions cleanly within the donut hole with no offset or collision.
 */
export interface RechartsDonutTooltipProps {
  active?: boolean;
  payload?: Array<{
    name?: string;
    value?: number;
    payload?: DonutHoleSliceInfo;
  }>;
}

export const DonutHoleTooltipContent: React.FC<RechartsDonutTooltipProps> = ({
  active,
  payload,
}) => {
  const tokens = useSurfaceTokens();

  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div
      className="transform -translate-x-1/2 -translate-y-1/2 rounded-xl px-3.5 py-2 text-xs transition-all duration-200 animate-fade-in shadow-md min-w-[120px] max-w-[145px] pointer-events-none select-none"
      style={{
        background: tokens.tooltipBg,
        border: tokens.tooltipBorder,
        boxShadow: tokens.cardShadow,
      }}
    >
      <div className="flex items-center justify-center gap-1.5 font-medium mb-1">
        {data.color && (
          <span
            className="h-2 w-2 rounded-full shrink-0"
            style={{ background: data.color }}
          />
        )}
        <span
          className="truncate font-semibold text-xs"
          style={{ color: tokens.titleColor }}
          title={data.name}
        >
          {data.name}
        </span>
      </div>

      {data.percent !== undefined && (
        <div
          className="flex items-center justify-between gap-3 font-normal text-[11px]"
          style={{ color: tokens.textMuted }}
        >
          <span>Share:</span>
          <span
            className="font-semibold tabular-nums"
            style={{ color: tokens.titleColor }}
          >
            {data.percent}%
          </span>
        </div>
      )}

      {data.count !== undefined && (
        <div
          className="flex items-center justify-between gap-3 font-normal text-[11px] mt-0.5"
          style={{ color: tokens.textMuted }}
        >
          <span>Count:</span>
          <span
            className="font-semibold tabular-nums"
            style={{ color: tokens.titleColor }}
          >
            {data.count}
          </span>
        </div>
      )}
    </div>
  );
};
