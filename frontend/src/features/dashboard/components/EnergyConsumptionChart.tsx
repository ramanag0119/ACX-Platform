import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useEnergySummary } from "@/lib/api/hooks";

/**
 * Real `energy_stat` values via GET /energy-stats/summary.
 *
 * The backend performs SUM and COUNT only. Two series are plotted:
 *   - "Total energy (all rooms)"  = the stored SUM for the bucket
 *   - "Average per reading"       = that SUM / the stored COUNT
 *
 * The second is a frontend presentation division of two real aggregates. The
 * original mock legends ("Average energy (all rooms)" / "per room") were
 * renamed to describe exactly what is plotted rather than imply a per-room
 * figure the API does not provide.
 *
 * THE UNIT IS NOT WRITTEN HERE. It comes from the API's `energy_unit`, which
 * the backend reads from `device_param` for the `active_energy` parameter.
 * `energy_stat` still stores no unit of its own, so this label describes the
 * parameter, not the row -- and it is null whenever the registry cannot resolve
 * one, in which case no suffix is shown rather than a guessed one. Nothing here
 * is converted, costed or carbon-weighted.
 *
 * The selected period is sent to the API and applied in SQL; this component
 * does not re-slice or re-sum what comes back.
 */

const GROUPINGS: Record<string, "hour" | "day"> = {
  Today: "hour",
  Week: "day",
  Month: "day",
};

/**
 * How far back each range reaches, in whole days from today's local midnight.
 *
 * Rolling windows, matching the convention every other date filter in this app
 * already uses (Alerts and Recent Activity both count back 0 / 6 / 29 days),
 * so "Week" means the last seven days INCLUDING today rather than a calendar
 * week starting Monday. Keeping one definition across the dashboard is what
 * stops two widgets disagreeing about what "this week" covers.
 */
const RANGE_DAYS_BACK: Record<keyof typeof GROUPINGS, number> = {
  Today: 0,
  Week: 6,
  Month: 29,
};

const EMPTY_TITLES: Record<keyof typeof GROUPINGS, string> = {
  Today: "No energy data available for today",
  Week: "No energy data available for this week",
  Month: "No energy data available for this month",
};

export const EnergyConsumptionChart = () => {
  const { isDark } = useTheme();
  const [range, setRange] = useState<keyof typeof GROUPINGS>("Week");
  const groupBy = GROUPINGS[range];

  /**
   * The selected period, resolved to an absolute instant pair the API filters
   * on. Local midnight is used for the lower bound so the window matches the
   * viewer's day, and `toISOString()` hands the backend an offset-aware UTC
   * value -- `energy_stat.hour` counts from a UTC epoch, so the conversion has
   * to carry a zone or the boundary drifts by the local offset.
   *
   * Recomputed whenever `range` changes, which changes the query key and makes
   * React Query refetch instead of reusing the previous period's rows.
   */
  const { date_from, date_to } = useMemo(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    start.setDate(start.getDate() - RANGE_DAYS_BACK[range]);

    const end = new Date();
    end.setHours(23, 59, 59, 999);

    return { date_from: start.toISOString(), date_to: end.toISOString() };
  }, [range]);

  // The period is applied BY THE BACKEND. Nothing below re-slices or re-sums:
  // every bucket returned belongs to the selected window, so the two series
  // and the bucket count describe that window and nothing wider.
  const query = useEnergySummary({ group_by: groupBy, date_from, date_to });

  const data = useMemo(
    () =>
      (query.data?.buckets ?? []).map((bucket) => ({
        name:
          groupBy === "hour"
            ? new Date(bucket.bucket).toLocaleTimeString([], { hour: "2-digit" })
            : bucket.bucket,
        totalEnergy: Number(bucket.total_energy_consumed.toFixed(3)),
        avgPerReading:
          bucket.reading_count > 0
            ? Number((bucket.total_energy_consumed / bucket.reading_count).toFixed(3))
            : 0,
      })),
    [query.data, groupBy],
  );

  /**
   * The unit for `energy_consumed`, as the backend resolved it from
   * `device_param` (`param_name = 'active_energy'`). Null is a real outcome --
   * the registry may hold no unit, or device types may disagree -- so every
   * use below degrades to no suffix rather than inventing a label.
   */
  const energyUnit = query.data?.energy_unit ?? null;
  const unitSuffix = energyUnit ? ` (${energyUnit})` : "";

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const selectBg = isDark ? "#252a3e" : "#FFFFFF";
  const selectBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";
  const tooltipBg = isDark ? "#1e2233" : "#FFFFFF";
  const tooltipBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";
  const gridStroke = isDark ? "rgba(255,255,255,0.06)" : "rgba(124,92,255,0.1)";

  return (
    /* h-full: the card fills its grid cell and the plot takes whatever height
       the header and legend do not, so no dead space collects at the bottom. */
    <div
      className="rounded-[16px] p-4 h-full min-w-0 flex flex-col transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4 shrink-0 gap-3">
        <h3 className="font-medium" style={{ color: titleColor }}>Average Energy Consumption</h3>
        <div className="flex items-center gap-2">
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors"
            style={{ background: selectBg, color: titleColor, border: selectBorder }}
            value={range}
            onChange={(event) => setRange(event.target.value as keyof typeof GROUPINGS)}
          >
            <option>Today</option>
            <option>Week</option>
            <option>Month</option>
          </select>
          <button
            className="transition-colors"
            style={{ color: mutedColor }}
            onClick={() => query.refetch()}
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-1 mb-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-3 h-3 bg-[hsl(35,90%,50%)] rounded-sm shrink-0" />
          <span className="text-xs truncate" style={{ color: mutedColor }}>
            Total energy (all rooms){unitSuffix}
          </span>
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-3 h-3 bg-[hsl(145,70%,45%)] rounded-sm shrink-0" />
          <span className="text-xs truncate" style={{ color: mutedColor }}>
            Average per reading{unitSuffix}
          </span>
        </div>
      </div>
      {/* The caption line was removed on request. The unit still reaches the
          user through the legend and the tooltip, both of which read it from
          the API (`device_param`) rather than writing it here. */}

      {/* 180px is the floor, not the height: flex-1 grows the plot into the
          rest of the card and ResponsiveContainer re-measures to match. */}
      <div className="flex-1 min-h-[180px] min-w-0">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={data.length === 0}
          // Named per period: an empty Today must not read as "there is no
          // energy data at all", and it must never fall back to showing
          // another period's figures.
          emptyTitle={EMPTY_TITLES[range]}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: mutedColor, fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: mutedColor, fontSize: 11 }} />
              <Tooltip
                // Same API-resolved unit as the legend; no suffix when the
                // registry could not resolve one.
                formatter={(value: number) => `${value}${unitSuffix}`}
                contentStyle={{
                  background: tooltipBg,
                  border: tooltipBorder,
                  borderRadius: "8px",
                  color: titleColor,
                  boxShadow: "0 8px 24px rgba(17,12,46,0.12)"
                }}
              />
              <Bar dataKey="totalEnergy" name="Total energy" fill="hsl(35,90%,50%)" radius={[2, 2, 0, 0]} />
              <Bar dataKey="avgPerReading" name="Average per reading" fill="hsl(145,70%,45%)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </DataState>
      </div>
    </div>
  );
};
