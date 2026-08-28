import { useMemo } from "react";
import { Info, RefreshCw } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useAmenityStatuses, useCount, useCounts } from "@/lib/api/hooks";
import type { QueryParams } from "@/lib/api/client";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Room counts by the real `amenity_status` row, from GET /occupancy.
 *
 * The slices are the FOUR statuses the lookup table actually holds --
 * Available, Occupied, Unavailable, Allotted -- read from GET
 * /amenity-statuses so the chart can never drift from the table. The mock's
 * two-slice Occupied/Vacant split would have folded two of them away.
 *
 * Each slice is a separate backend COUNT(*) (`?status=<id>&page_size=1`), not
 * a tally of one fetched page: a page holds at most 100 rows, and counting
 * client-side would quietly undercount a property with more rooms than that.
 *
 * THE CENTRE FIGURE IS A DIFFERENT SOURCE OF TRUTH, deliberately. Phase 2.8
 * defines in-house occupancy as a stay with `actual_checkin_time IS NOT NULL
 * AND actual_checkout_time IS NULL`, which is what `is_occupied=true` asks the
 * backend. `amenity.status` is a flag on the room and nothing in the schema
 * keeps the two in step -- in the current data 4 rooms are flagged Occupied
 * while 2 have a guest in house. Both are shown; neither is silently
 * substituted for the other.
 */

const STATUS_COLORS: Record<string, string> = {
  Occupied: "hsl(145,70%,45%)",
  Available: "hsl(199,89%,48%)",
  Allotted: "hsl(38,92%,50%)",
  Unavailable: "hsl(0,70%,50%)",
};
const FALLBACK_COLOR = "hsl(220,9%,60%)";

export const OccupancyStatisticsChart = () => {
  const { isDark } = useTheme();

  const statusesQuery = useAmenityStatuses({ page: 1, page_size: MAX_PAGE_SIZE });
  // Memoised so the identity is stable between renders: a bare `?? []` hands a
  // new array to the useMemo/useCounts dependencies on every pass.
  const statuses = useMemo(() => statusesQuery.data?.items ?? [], [statusesQuery.data]);

  const filterSets = useMemo<QueryParams[]>(
    () => statuses.map((status) => ({ status: status.id })),
    [statuses],
  );
  const perStatus = useCounts("occupancy", filterSets, statuses.length > 0);

  const roomTotal = useCount("occupancy");
  const inHouse = useCount("occupancy", { is_occupied: true });

  const data = useMemo(
    () =>
      statuses
        .map((status, index) => ({
          name: status.amenity_status_name,
          value: perStatus.totals[index] ?? 0,
          color: STATUS_COLORS[status.amenity_status_name] ?? FALLBACK_COLOR,
        }))
        .filter((slice) => slice.value > 0),
    [statuses, perStatus.totals],
  );

  const total = roomTotal.total;
  const inHouseCount = inHouse.total;
  const inHousePercent =
    total && inHouseCount !== null ? Math.round((inHouseCount / total) * 100) : null;

  // The amenity flag's own Occupied count, for the disagreement note.
  const flaggedOccupied = useMemo(() => {
    const index = statuses.findIndex((s) => s.amenity_status_name === "Occupied");
    return index >= 0 ? perStatus.totals[index] : null;
  }, [statuses, perStatus.totals]);

  const isLoading = statusesQuery.isLoading || perStatus.isLoading || roomTotal.isLoading;
  const error = statusesQuery.error ?? perStatus.error ?? roomTotal.error;

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const tooltipBg = isDark ? "#1e2233" : "#FFFFFF";

  return (
    <div
      className="rounded-[16px] p-4 transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium" style={{ color: titleColor }}>Occupancy Statistics</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: mutedColor }}>
            {total ?? "-"} rooms
          </span>
          <button
            className="transition-colors"
            style={{ color: mutedColor }}
            onClick={() => {
              void roomTotal.refetch();
              void inHouse.refetch();
              void statusesQuery.refetch();
            }}
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <DataState
        isLoading={isLoading}
        error={error}
        isEmpty={data.length === 0}
        emptyTitle="No rooms found"
      >
        <div className="flex items-center justify-between">
          <div className="relative w-[160px] h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                  startAngle={90}
                  endAngle={-270}
                >
                  {data.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: tooltipBg,
                    border: "1px solid rgba(124,92,255,0.12)",
                    borderRadius: "8px",
                    color: titleColor,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-[hsl(145,70%,45%)] text-lg font-bold">
                {inHousePercent === null ? "-" : `${inHousePercent}%`}
              </span>
              <span className="text-[10px]" style={{ color: mutedColor }}>in house</span>
            </div>
          </div>

          <div className="space-y-2">
            {data.map((entry) => (
              <div key={entry.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm" style={{ background: entry.color }} />
                <span className="text-sm" style={{ color: mutedColor }}>
                  {entry.name} ({entry.value})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* The two sources of truth, stated rather than reconciled. */}
        {inHouseCount !== null && flaggedOccupied !== null && (
          <p
            className="mt-3 flex items-start gap-1.5 text-[10px] leading-snug"
            style={{ color: mutedColor }}
          >
            <Info className="mt-px h-3 w-3 shrink-0" />
            <span>
              Slices are the room's <span className="font-mono">amenity.status</span> flag.
              The centre figure is the stay graph: {inHouseCount} guest
              {inHouseCount === 1 ? "" : "s"} in house
              {flaggedOccupied !== inHouseCount && `, against ${flaggedOccupied} flagged Occupied`}.
            </span>
          </p>
        )}
      </DataState>
    </div>
  );
};
