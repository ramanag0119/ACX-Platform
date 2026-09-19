import { useMemo } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { cn } from "@/lib/utils";
import { DataState } from "@/core/components/DataState";
import { useAmenityStatuses, useCount, useCounts } from "@/lib/api/hooks";
import type { QueryParams } from "@/lib/api/client";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { roomStatusColor } from "../lib/roomStatus";

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
 * THE CENTRE FIGURE IS A DIFFERENT SOURCE OF TRUTH from the slices. Phase 2.8
 * defines in-house occupancy as a stay with `actual_checkin_time IS NOT NULL
 * AND actual_checkout_time IS NULL`, which is what `is_occupied=true` asks the
 * backend. `amenity.status` is a flag on the room and nothing in the schema
 * keeps the two in step, so the ring and the centre can disagree.
 *
 * A footnote used to spell that disagreement out on screen ("N guests in
 * house, against M flagged Occupied"). It was removed by request, so the
 * divergence is now recorded HERE and nowhere in the UI: a reader comparing
 * the centre percentage against the Occupied slice has no on-screen
 * explanation for why they differ.
 */

export const OccupancyStatisticsChart = () => {

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
          color: roomStatusColor(status.amenity_status_name),
        }))
        .filter((slice) => slice.value > 0),
    [statuses, perStatus.totals],
  );

  const total = roomTotal.total;
  const inHouseCount = inHouse.total;
  const inHousePercent =
    total && inHouseCount !== null ? Math.round((inHouseCount / total) * 100) : null;

  const isLoading = statusesQuery.isLoading || perStatus.isLoading || roomTotal.isLoading;
  const error = statusesQuery.error ?? perStatus.error ?? roomTotal.error;
  const isFetching = roomTotal.isFetching || inHouse.isFetching || statusesQuery.isFetching;

  /** Green = settled, amber = refetching, red = last attempt failed. */
  const dotColor = error ? "#ef4444" : isFetching ? "#f59e0b" : "#22c55e";
  const dotLabel = error ? "Data unavailable" : isFetching ? "Refreshing" : "Data up to date";
  const {
    cardBg,
    cardBorder,
    cardShadow,
    titleColor,
    textMuted: mutedColor,
    tooltipBg,
  } = useSurfaceTokens();

  return (
    /* h-full: this is the short panel beside the energy chart, so its cell
       stretched while the card kept its natural height. The card now fills the
       cell and the donut grows into the spare height. */
    <div
      className="rounded-[16px] p-4 h-full min-w-0 flex flex-col transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: cardShadow }}
    >
      <div className="flex items-center justify-between mb-3 shrink-0 gap-3">
        <h3 className="text-base font-semibold tracking-tight" style={{ color: titleColor }}>
          Occupancy Statistics
        </h3>
        <div className="flex items-center gap-2">
          {/* The chart counts rooms per `amenity_status` from GET /occupancy;
              the Occupancy screen lists those same rooms and filters by that
              same status, so this is the panel's detail view rather than a
              related-looking guess. */}
          <Link
            to="/occupancy"
            className="text-xs underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            style={{ color: mutedColor }}
          >
            {total ?? "-"} rooms
          </Link>
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
            <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
          </button>
          <span
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ background: dotColor }}
            title={dotLabel}
            aria-label={dotLabel}
            role="img"
          />
        </div>
      </div>

      {/* DataState renders a fragment, so this wrapper is what carries the
          growable height -- for the chart AND for the loading / empty / error
          shells that replace it. */}
      <div className="flex-1 min-h-0 min-w-0 flex flex-col">
        <DataState
          isLoading={isLoading}
          error={error}
          isEmpty={data.length === 0}
          emptyTitle="No rooms found"
        >
            {/* `justify-center`, NOT `justify-between`: between pushed the legend
                to the card's right edge and parked all the spare width in the
                middle, which is the gap that opened up between the ring and its
                labels. Centred, the two sit together as one block and the spare
                width falls outside the pair. */}
            <div className="flex flex-1 min-h-0 min-w-0 items-center justify-center gap-6">
            {/* `aspect-square h-full` sizes the donut from the card's spare
                height. Bounded both ways: a square sized off height takes its
                width from that height, so max-h caps it and max-w stops it
                crushing the legend or widening the card. */}
            {/* `[&_*:focus:not(:focus-visible)]:outline-none`: Recharts makes the
                chart surface and its sectors focusable, so CLICKING a slice gave
                it focus and the browser drew a focus rectangle round the chart.
                The slices carry no click action, so that outline told the user
                nothing.

                Scoped to mouse focus only -- `:focus-visible` is untouched, so a
                keyboard user tabbing through still gets a visible ring. */}
            <div className="relative aspect-square h-full min-h-[160px] max-h-[200px] max-w-[55%] shrink-0 [&_*:focus:not(:focus-visible)]:outline-none">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data}
                    cx="50%"
                    cy="50%"
                    /* Percentages, not px, so the ring scales with the box
                       instead of floating at a fixed 160px inside it. */
                    innerRadius="62%"
                    outerRadius="92%"
                    paddingAngle={2}
                    /* Rounded caps read as one continuous band instead of four
                       flat wedges butted against each other. */
                    cornerRadius={5}
                    stroke="none"
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
                <span
                  className="text-[28px] font-bold leading-none tracking-tight"
                  style={{ color: titleColor }}
                >
                  {inHousePercent === null ? "-" : `${inHousePercent}%`}
                </span>
                <span className="mt-1.5 text-[11px]" style={{ color: mutedColor }}>
                  in house
                </span>
              </div>
            </div>

            {/* min-w-0, never shrink-0 -- two non-shrinking children in one
                flex row is how a card ends up wider than its column.

                `max-w` is what closes the gap between a label and its count:
                an uncapped `flex-1` stretched each row to the full width of the
                card, so the right-aligned number ended up far from "Available".
                Capped, the number sits just past the longest label. */}
            <ul className="min-w-0 max-w-[200px] flex-1 space-y-2.5">
              {data.map((entry) => (
                <li key={entry.name} className="flex min-w-0 items-center gap-3">
                  {/* A capsule, not a 12px square: it carries the slice colour
                      at a size that reads next to the ring. */}
                  <span
                    className="h-3.5 w-7 shrink-0 rounded-full"
                    style={{ background: entry.color }}
                  />
                  <span
                    className="min-w-0 flex-1 truncate text-sm"
                    style={{ color: titleColor }}
                    title={entry.name}
                  >
                    {entry.name}
                  </span>
                  {/* tabular-nums keeps the counts in a straight right-hand
                      column instead of shifting with digit width. */}
                  <span
                    className="shrink-0 text-sm font-semibold tabular-nums"
                    style={{ color: titleColor }}
                  >
                    {entry.value}
                  </span>
                </li>
              ))}
            </ul>
          </div>

        </DataState>
      </div>
    </div>
  );
};
