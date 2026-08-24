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
 * NO UNIT IS SHOWN: `energy_stat` stores none and the API returns
 * `energy_unit: null`. These values must not be labelled kWh. Nothing here is
 * converted, costed or carbon-weighted.
 */

const GROUPINGS: Record<string, "hour" | "day"> = {
  Today: "hour",
  Week: "day",
  Month: "day",
};

export const EnergyConsumptionChart = () => {
  const { isDark } = useTheme();
  const [range, setRange] = useState<keyof typeof GROUPINGS>("Week");
  const groupBy = GROUPINGS[range];

  const query = useEnergySummary({ group_by: groupBy });

  const data = useMemo(() => {
    const buckets = query.data?.buckets ?? [];
    const recent = buckets.slice(-(range === "Month" ? 30 : range === "Week" ? 7 : 24));
    return recent.map((bucket) => ({
      name:
        groupBy === "hour"
          ? new Date(bucket.bucket).toLocaleTimeString([], { hour: "2-digit" })
          : bucket.bucket,
      totalEnergy: Number(bucket.total_energy_consumed.toFixed(3)),
      avgPerReading:
        bucket.reading_count > 0
          ? Number((bucket.total_energy_consumed / bucket.reading_count).toFixed(3))
          : 0,
    }));
  }, [query.data, groupBy, range]);

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
    <div
      className="rounded-[16px] p-4 transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
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

      <div className="flex items-center justify-center gap-6 mb-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-[hsl(35,90%,50%)] rounded-sm" />
          <span className="text-xs" style={{ color: mutedColor }}>Total energy (all rooms)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-[hsl(145,70%,45%)] rounded-sm" />
          <span className="text-xs" style={{ color: mutedColor }}>Average per reading</span>
        </div>
      </div>
      <p className="text-center text-[10px] mb-2" style={{ color: mutedColor }}>
        Stored values, no unit recorded in the database
      </p>

      <div className="h-[180px]">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={data.length === 0}
          emptyTitle="No energy statistics recorded"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: mutedColor, fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: mutedColor, fontSize: 11 }} />
              <Tooltip
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
