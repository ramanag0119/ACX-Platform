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
 * NO UNIT IS SHOWN: `energy_stat` stores none and the API returns
 * `energy_unit: null`. These values must not be labelled kWh. Nothing here is
 * converted, costed or carbon-weighted.
 */

/**
 * The ranges the picker offers. `bucketLimit` is how many of the most recent
 * buckets the range plots -- 24 hours, 7 days, 30 days -- and lives here beside
 * the grouping it belongs to rather than as a chain of ternaries at the call
 * site, so adding a range is a single entry.
 */
const RANGES = {
  Today: { groupBy: "hour", bucketLimit: 24 },
  Week: { groupBy: "day", bucketLimit: 7 },
  Month: { groupBy: "day", bucketLimit: 30 },
} satisfies Record<string, { groupBy: EnergyGrouping; bucketLimit: number }>;

type RangeKey = keyof typeof RANGES;

const RANGE_KEYS = Object.keys(RANGES) as RangeKey[];

const TOTAL_COLOR = "hsl(35,90%,50%)";
const AVERAGE_COLOR = "hsl(145,70%,45%)";

export const EnergyConsumptionChart = () => {
  const tokens = useSurfaceTokens();
  const [range, setRange] = useState<RangeKey>("Week");
  const { groupBy, bucketLimit } = RANGES[range];

  const query = useEnergySummary({ group_by: groupBy });

  const data = useMemo(() => {
    const buckets = query.data?.buckets ?? [];
    return toEnergyPoints(buckets.slice(-bucketLimit), groupBy);
  }, [query.data, groupBy, bucketLimit]);

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

      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-1 mb-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: TOTAL_COLOR }} />
          <span className="text-xs truncate" style={{ color: tokens.textMuted }}>Total energy (all rooms)</span>
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: AVERAGE_COLOR }} />
          <span className="text-xs truncate" style={{ color: tokens.textMuted }}>Average per reading</span>
        </div>
      </div>
      <p className="text-center text-[10px] mb-2 shrink-0" style={{ color: tokens.textMuted }}>
        Stored values, no unit recorded in the database
      </p>

      {/* 180px is the floor, not the height: flex-1 grows the plot into the
          rest of the card and ResponsiveContainer re-measures to match. */}
      <div className="flex-1 min-h-[180px] min-w-0">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={data.length === 0}
          emptyTitle="No energy statistics recorded"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke={tokens.gridStroke} vertical={false} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: tokens.textMuted, fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: tokens.textMuted, fontSize: 11 }} />
              <Tooltip
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
