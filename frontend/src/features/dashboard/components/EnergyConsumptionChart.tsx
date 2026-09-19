import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { DataState } from "@/core/components/DataState";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { useEnergySummary } from "@/lib/api/hooks";
import { toEnergyPoints, type EnergyGrouping } from "../data/energyConsumption";

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
 * Bucket-to-point conversion lives in `../data/energyConsumption` so the axis
 * wording, the rounding and the divide-by-zero guard are defined once. This
 * component had its own inline copy, which rendered the raw ISO timestamp
 * (`2026-09-16T00:00:00+05:30`) as the x-axis tick for every day bucket --
 * the default Week view -- and ignored the `bucket_label` the API supplies.
 *
 * THE SELECTED PERIOD IS APPLIED BY THE BACKEND. `date_from` / `date_to` go to
 * the API and the filter runs in SQL, so nothing here re-slices or re-sums:
 * every bucket that arrives already belongs to the chosen window.
 *
 * THE UNIT IS NOT WRITTEN HERE. It comes from the API's `energy_unit`, which
 * the backend reads from `device_param` for the `active_energy` parameter.
 * `energy_stat` still stores no unit of its own, so the label describes the
 * parameter, not the row -- and it is null whenever the registry cannot resolve
 * one, in which case no suffix is shown rather than a guessed one. Nothing here
 * is converted, costed or carbon-weighted.
 */

/**
 * The ranges the picker offers.
 *
 * `daysBack` is how far the range reaches, in whole days from today's local
 * midnight, and lives here beside the grouping it belongs to rather than as a
 * chain of ternaries at the call site, so adding a range is a single entry.
 *
 * Rolling windows, matching the convention every other date filter in this app
 * already uses (Alerts and Recent Activity both count back 0 / 6 / 29 days), so
 * "Week" means the last seven days INCLUDING today rather than a calendar week
 * starting Monday. Keeping one definition across the dashboard is what stops
 * two widgets disagreeing about what "this week" covers.
 *
 * This replaced a `bucketLimit` that trimmed the most recent N buckets in the
 * browser. Trimming client-side could only ever hide extra rows after they were
 * fetched; the window now bounds the query itself, so there is nothing to trim.
 */
const RANGES = {
  Today: { groupBy: "hour", daysBack: 0 },
  Week: { groupBy: "day", daysBack: 6 },
  Month: { groupBy: "day", daysBack: 29 },
} satisfies Record<string, { groupBy: EnergyGrouping; daysBack: number }>;

type RangeKey = keyof typeof RANGES;

const RANGE_KEYS = Object.keys(RANGES) as RangeKey[];

/** Named per period: an empty Today must not read as "there is no energy data
 *  at all", and it must never fall back to another period's figures. */
const EMPTY_TITLES: Record<RangeKey, string> = {
  Today: "No energy data available for today",
  Week: "No energy data available for this week",
  Month: "No energy data available for this month",
};

const TOTAL_COLOR = "hsl(35,90%,50%)";
const AVERAGE_COLOR = "hsl(145,70%,45%)";

export const EnergyConsumptionChart = () => {
  const tokens = useSurfaceTokens();
  const [range, setRange] = useState<RangeKey>("Week");
  const { groupBy, daysBack } = RANGES[range];

  /**
   * The selected period, resolved to an absolute instant pair the API filters
   * on. Local midnight is used for the lower bound so the window matches the
   * viewer's day, and `toISOString()` hands the backend an offset-aware UTC
   * value -- `energy_stat.hour` counts from a UTC epoch, so the conversion has
   * to carry a zone or the boundary drifts by the local offset.
   *
   * Recomputed whenever the range changes, which changes the query key and
   * makes React Query refetch instead of reusing the previous period's rows.
   */
  const { date_from, date_to } = useMemo(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    start.setDate(start.getDate() - daysBack);

    const end = new Date();
    end.setHours(23, 59, 59, 999);

    return { date_from: start.toISOString(), date_to: end.toISOString() };
  }, [daysBack]);

  const query = useEnergySummary({ group_by: groupBy, date_from, date_to });

  const data = useMemo(
    () => toEnergyPoints(query.data?.buckets ?? [], groupBy),
    [query.data, groupBy],
  );

  /**
   * The unit for `energy_consumed`, as the backend resolved it from
   * `device_param` (`param_name = 'active_energy'`). Null is a real outcome --
   * the registry may hold no unit, or device types may disagree -- so every use
   * below degrades to no suffix rather than inventing a label.
   */
  const energyUnit = query.data?.energy_unit ?? null;
  const unitSuffix = energyUnit ? ` (${energyUnit})` : "";

  return (
    /* h-full: the card fills its grid cell and the plot takes whatever height
       the header and legend do not, so no dead space collects at the bottom. */
    <div
      className="rounded-[16px] p-4 h-full min-w-0 flex flex-col transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: tokens.cardBg, border: tokens.cardBorder, boxShadow: tokens.cardShadow }}
    >
      <div className="flex items-center justify-between mb-4 shrink-0 gap-3">
        <h3 className="font-medium" style={{ color: tokens.titleColor }}>Average Energy Consumption</h3>
        <div className="flex items-center gap-2">
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors"
            style={{ background: tokens.controlBg, color: tokens.titleColor, border: tokens.controlBorder }}
            value={range}
            onChange={(event) => setRange(event.target.value as RangeKey)}
            aria-label="Energy summary range"
          >
            {/* Driven off RANGES so the options cannot fall out of step with
                the groupings they select. */}
            {RANGE_KEYS.map((key) => (
              <option key={key} value={key}>{key}</option>
            ))}
          </select>
          <button
            type="button"
            className="transition-colors"
            style={{ color: tokens.textMuted }}
            onClick={() => query.refetch()}
            title="Refresh"
            aria-label="Refresh energy summary"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* The unit rides on the legend rather than a caption of its own. The
          caption used to state that no unit was recorded; the API now resolves
          one from `device_param`, and when it cannot the suffix is simply
          absent. */}
      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-1 mb-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: TOTAL_COLOR }} />
          <span className="text-xs truncate" style={{ color: tokens.textMuted }}>
            Total energy (all rooms){unitSuffix}
          </span>
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: AVERAGE_COLOR }} />
          <span className="text-xs truncate" style={{ color: tokens.textMuted }}>
            Average per reading{unitSuffix}
          </span>
        </div>
      </div>

      {/* 180px is the floor, not the height: flex-1 grows the plot into the
          rest of the card and ResponsiveContainer re-measures to match. */}
      <div className="flex-1 min-h-[180px] min-w-0">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={data.length === 0}
          emptyTitle={EMPTY_TITLES[range]}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke={tokens.gridStroke} vertical={false} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: tokens.textMuted, fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: tokens.textMuted, fontSize: 11 }} />
              <Tooltip
                // Same API-resolved unit as the legend; no suffix when the
                // registry could not resolve one.
                formatter={(value: number) => `${value}${unitSuffix}`}
                contentStyle={{
                  background: tokens.tooltipBg,
                  border: tokens.tooltipBorder,
                  borderRadius: "8px",
                  color: tokens.titleColor,
                  boxShadow: tokens.cardShadow,
                }}
                /* The spelled-out bucket, so a "Mon" tick reads as
                   "Monday, Sep 16" in the tooltip. */
                labelFormatter={(_label, payload) =>
                  payload?.[0]?.payload?.fullName ?? _label
                }
              />
              <Bar dataKey="totalEnergy" name="Total energy" fill={TOTAL_COLOR} radius={[2, 2, 0, 0]} />
              <Bar dataKey="avgPerReading" name="Average per reading" fill={AVERAGE_COLOR} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </DataState>
      </div>
    </div>
  );
};
