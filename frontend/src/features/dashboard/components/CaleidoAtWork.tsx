import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useOperationalKpis } from "@/lib/api/hooks";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import type { CaleidoRange, OperationalKPIRead } from "@/lib/api/types";

/**
 * The four operational KPIs: Smart Rooms Online, Service Request Status,
 * Rooms For Check-Out, Pending Bookings.
 *
 * WHAT CHANGED AND WHY. This card used to read `daily_dual_data_point`, a
 * table of pre-computed daily snapshots. Nothing has written to it since
 * 2026-08-17, so with the Today filter the window held no rows and the card
 * rendered "No daily KPI data points recorded". The business data was fine;
 * the snapshot was stale. It now reads GET /dashboard/caleido-at-work, which
 * computes the same four indicators from the live records.
 *
 * NOTHING IS CALCULATED HERE. The backend returns `percentage`, `numerator`,
 * `denominator`, `count` and `detail` already resolved. This file chooses a
 * colour and draws an arc; it never divides, defaults or substitutes.
 *
 * THREE DISTINCT STATES, deliberately not collapsed:
 *   unavailable  -- `available === false`: the figure cannot be known (no
 *                   device-to-room mapping, OSS unreachable). Shows "-" and
 *                   the backend's reason. NEVER 0 %.
 *   no ratio     -- available, but `percentage === null` because the
 *                   denominator is 0 (nothing raised in this period). Shows
 *                   the real count with "-" for the ring.
 *   a value      -- draws the arc.
 */

const RANGES: { key: CaleidoRange; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
];

/** Ring colour per KPI. Presentation only -- it encodes nothing about data. */
const COLORS: Record<string, string> = {
  smart_rooms_online: "hsl(265,70%,58%)",
  service_request_status: "hsl(145,70%,45%)",
  rooms_for_checkout: "hsl(28,85%,55%)",
  pending_bookings: "hsl(205,75%,52%)",
};

interface RingProps {
  kpi: OperationalKPIRead;
  isDark: boolean;
}

const Ring = ({ kpi, isDark }: RingProps) => {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#8A86A8";
  const color = COLORS[kpi.key] ?? "hsl(145,70%,45%)";

  const hasRatio = kpi.available && kpi.percentage !== null;
  const pct = hasRatio ? Math.min(Math.max(kpi.percentage as number, 0), 100) : 0;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  /* Headline: the percentage when there is one; otherwise the real count
     (a true zero is worth showing); otherwise "-" for unknown. */
  const headline = hasRatio
    ? `${kpi.percentage}%`
    : kpi.available && kpi.count !== null
      ? String(kpi.count)
      : "-";

  const sub = kpi.available ? kpi.detail : (kpi.unavailable_reason ?? "Unavailable");

  return (
    <div className="flex items-center gap-3 min-w-0">
      <div className="relative w-12 h-12 shrink-0">
        <svg className="w-12 h-12 -rotate-90" viewBox="0 0 44 44">
          <circle
            cx="22" cy="22" r={radius} fill="none"
            stroke={isDark ? "rgba(255,255,255,0.08)" : "rgba(124,92,255,0.1)"}
            strokeWidth="3"
          />
          {hasRatio && (
            <circle
              cx="22" cy="22" r={radius} fill="none" stroke={color} strokeWidth="3"
              strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          )}
        </svg>
        {/* A dimmed dot marks "no arc to draw", so an unavailable ring is
            visibly different from a genuine 0 % rather than just empty. */}
        {!hasRatio && (
          <span
            className="absolute inset-0 flex items-center justify-center text-[10px]"
            style={{ color: mutedColor }}
            aria-hidden
          >
            ●
          </span>
        )}
      </div>
      <div className="min-w-0">
        <p
          style={{ color: kpi.available ? titleColor : mutedColor }}
          className="font-medium text-lg truncate"
        >
          {headline}
        </p>
        <p
          style={{ color: mutedColor }}
          className="text-xs uppercase tracking-wide truncate"
          title={kpi.label}
        >
          {kpi.label}
        </p>
        {sub && (
          <p style={{ color: mutedColor }} className="text-[10px] truncate" title={sub}>
            {sub}
          </p>
        )}
      </div>
    </div>
  );
};

export const CaleidoAtWork = () => {
  const { isDark } = useTheme();
  const [range, setRange] = useState<CaleidoRange>("today");

  /* `range` is part of the query key, so switching period refetches instead
     of showing the previous window's numbers. */
  const query = useOperationalKpis({ range });

  const {
    cardBg,
    cardBorder,
    cardShadow,
    titleColor,
    textMuted: mutedColor,
    controlBg: selectBg,
    controlBorder: selectBorder,
  } = useSurfaceTokens();

  const kpis = query.data?.kpis ?? [];

  return (
    <div
      className="rounded-lg p-4 h-full min-w-0 flex flex-col transition-all duration-250 ease hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: cardShadow }}
    >
      <div className="flex items-center justify-between mb-4 shrink-0 gap-3">
        <h3 style={{ color: titleColor }} className="font-medium">
          Caleido At work
        </h3>
        <div className="flex items-center gap-2">
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors duration-200"
            style={{ backgroundColor: selectBg, color: titleColor, border: selectBorder }}
            value={range}
            onChange={(event) => setRange(event.target.value as CaleidoRange)}
            aria-label="KPI period"
          >
            {RANGES.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            style={{ color: mutedColor }}
            className="hover:opacity-100 opacity-70 transition-opacity disabled:opacity-40"
            onClick={() => query.refetch()}
            disabled={query.isFetching}
            title="Refresh"
            aria-label="Refresh KPIs"
          >
            <RefreshCw className={`h-4 w-4 ${query.isFetching ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 min-w-0 flex flex-col">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={kpis.length === 0}
          emptyTitle="No operational KPIs available"
        >
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {kpis.map((kpi) => (
              <Ring key={kpi.key} kpi={kpi} isDark={isDark} />
            ))}
          </div>
          {/* The window the backend actually applied. `live` KPIs are not
              scoped by it, which is why each ring carries its own detail
              line rather than this being presented as one global period. */}
          {query.data && (
            <p style={{ color: mutedColor }} className="text-[10px] mt-3 shrink-0">
              Period {query.data.period_from} to {query.data.period_to} · live
              indicators show current state
            </p>
          )}
        </DataState>
      </div>
    </div>
  );
};
