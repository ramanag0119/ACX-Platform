import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { DataState } from "@/core/components/DataState";
import { useAmenityStatuses, useCount, useCounts } from "@/lib/api/hooks";
import type { QueryParams } from "@/lib/api/client";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { roomStatusColor } from "../lib/roomStatus";
import { OCCUPANCY_PATH, statusDetailPath } from "../lib/occupancyLinks";

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
 * The centre figure comes from the same counts as the slices. It used to show
 * a stay-based in-house figure (`is_occupied=true`) for Occupied, which could
 * disagree with the Occupied arc it sat inside; that request is gone, and the
 * centre now reads only what the ring draws.
 */

/**
 * The inactive treatment is OPACITY, not a fixed grey.
 *
 * The spec offered either a muted slate (#2D3748 / #374151) or a fade. This
 * card is themed -- `useSurfaceTokens` returns a LIGHT palette as well as the
 * dark one -- so a hardcoded slate would sit on a white card as a dark smudge
 * and read as a fifth, darker status rather than as "dimmed". Fading the real
 * accent colour dims correctly against either background and keeps each slice
 * recognisable as its own status while muted.
 *
 * Two values, because the ring and the legend need different depths: a faded
 * arc still has to read as a coloured band, while faded text only has to stay
 * legible.
 */
const INACTIVE_SLICE_OPACITY = 0.2;
const INACTIVE_LEGEND_OPACITY = 0.45;

export const OccupancyStatisticsChart = () => {
  const navigate = useNavigate();

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

  /**
   * Which status the pointer is on. `null` means "the pointer is nowhere near
   * this card", and that is the RESTING state -- not a status.
   *
   * It used to fall through to a default, so one slice was always singled out
   * and the other three sat permanently faded. The card opened looking as
   * though a filter had been applied that nobody had asked for. Dimming now
   * happens only while something is genuinely hovered or focused, and clearing
   * this restores every slice and legend row to full strength.
   *
   * The slice names come from the `amenity_status` lookup table, so nothing
   * here assumes a spelling that table owns.
   */
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null);

  /**
   * The hovered status, resolved against the data actually on screen.
   *
   * `data` drops any status with zero rooms, so a refetch can remove the slice
   * the pointer was on. Re-resolving here means the highlight disappears with
   * it rather than dimming everything against a status that is no longer drawn.
   */
  const hoveredName = useMemo(
    () =>
      hoveredCategory && data.some((slice) => slice.name === hoveredCategory)
        ? hoveredCategory
        : null,
    [hoveredCategory, data],
  );

  /** A slice fades only when a DIFFERENT one is being pointed at. */
  const isDimmed = (name: string) => hoveredName !== null && name !== hoveredName;

  /**
   * The centre readout: the whole ring at rest, the hovered slice otherwise.
   *
   * At rest it reads "100% / Total Rooms" -- the ring as a whole -- rather than
   * singling out one status. It used to default to Occupied, so the card
   * opened on a lone "7%" that looked like the headline figure for the whole
   * chart.
   *
   * Hovered, every slice uses the SAME formula, its own share `value / total`,
   * so the figure in the middle always matches the arc under the pointer.
   */
  const hoveredSlice = hoveredName ? data.find((slice) => slice.name === hoveredName) : undefined;
  const centreValue = hoveredSlice ? hoveredSlice.value : total;
  const centrePercent = total ? Math.round((centreValue / total) * 100) : null;
  const centreLabel = hoveredSlice ? hoveredSlice.name : "Total Rooms";

  const isLoading = statusesQuery.isLoading || perStatus.isLoading || roomTotal.isLoading;
  const error = statusesQuery.error ?? perStatus.error ?? roomTotal.error;
  const isFetching = roomTotal.isFetching || statusesQuery.isFetching;

  /** Green = settled, amber = refetching, red = last attempt failed. */
  const dotColor = error ? "#ef4444" : isFetching ? "#f59e0b" : "#22c55e";
  const dotLabel = error ? "Data unavailable" : isFetching ? "Refreshing" : "Data up to date";
  const {
    cardBg,
    cardBorder,
    cardShadow,
    titleColor,
    textMuted: mutedColor,
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
            to={OCCUPANCY_PATH}
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
            {/* onMouseLeave sits on the pair, not on the ring and the legend
                separately: moving the pointer from a slice to its legend row
                crosses the gap between them, and a reset on each child would
                flash every slice back to full strength on the way past. One
                handler here means the card returns to its resting state when
                the pointer actually leaves it. */}
            <div
              className="flex flex-1 min-h-0 min-w-0 items-center justify-center gap-6"
              onMouseLeave={() => setHoveredCategory(null)}
            >
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
            {/* The 0.3s transition is scoped to `fill-opacity` rather than
                `all`: a Recharts sector is an SVG <path>, and transitioning
                `all` would drag the arc geometry (`d`) into the animation
                alongside Recharts' own enter animation. Fading only the
                opacity keeps the ring geometry crisp. */}
            {/* No <Tooltip>. Hovering a slice now writes the centre readout, so
                a floating "Available : 19" restated what the middle of the ring
                was already saying -- and Recharts anchors a pie tooltip over the
                hole, so it said it ON TOP of the figure it was duplicating. The
                centre is the readout; the ring does not need a second one. */}
            <div className="relative aspect-square h-full min-h-[160px] max-h-[200px] max-w-[55%] shrink-0 [&_*:focus:not(:focus-visible)]:outline-none [&_.recharts-sector]:transition-[fill-opacity] [&_.recharts-sector]:duration-300 [&_.recharts-sector]:ease-out">
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
                    className="cursor-pointer"
                    onMouseEnter={(_, index) => setHoveredCategory(data[index]?.name ?? null)}
                    onClick={(_, index) => {
                      const name = data[index]?.name;
                      if (name) navigate(statusDetailPath(name));
                    }}
                  >
                    {data.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={entry.color}
                        fillOpacity={isDimmed(entry.name) ? INACTIVE_SLICE_OPACITY : 1}
                      />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span
                  className="text-[28px] font-bold leading-none tracking-tight"
                  style={{ color: titleColor }}
                >
                  {centrePercent === null ? "-" : `${centrePercent}%`}
                </span>
                {/* No `capitalize` here: `amenity_status` already stores
                    display-cased names ("Available", "Occupied"). */}
                <span className="mt-1.5 text-[11px]" style={{ color: mutedColor }}>
                  {centreLabel}
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
              {data.map((entry) => {
                const isHovered = entry.name === hoveredName;
                return (
                  <li key={entry.name} className="flex min-w-0">
                    {/* A real <Link>, not a button: clicking a status now opens
                        that status's rooms on /occupancy, so this is navigation
                        and should behave like it -- a real href the browser can
                        show, open in a new tab or middle-click. Keyboard users
                        reach it in tab order and get the same highlight through
                        onFocus, which onBlur clears so the card does not stay
                        dimmed after focus moves on. */}
                    <Link
                      to={statusDetailPath(entry.name)}
                      title={`Show ${entry.value} ${entry.name} rooms`}
                      onMouseEnter={() => setHoveredCategory(entry.name)}
                      onFocus={() => setHoveredCategory(entry.name)}
                      onBlur={() => setHoveredCategory(null)}
                      className="flex min-w-0 w-full items-center gap-3 rounded-sm text-left transition-opacity duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      style={{ opacity: isDimmed(entry.name) ? INACTIVE_LEGEND_OPACITY : 1 }}
                    >
                      {/* A capsule, not a 12px square: it carries the slice colour
                          at a size that reads next to the ring. */}
                      <span
                        className="h-3.5 w-7 shrink-0 rounded-full"
                        style={{ background: entry.color }}
                      />
                      <span
                        className={cn(
                          "min-w-0 flex-1 truncate text-sm",
                          isHovered ? "font-semibold" : "font-normal",
                        )}
                        style={{ color: titleColor }}
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
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>

        </DataState>
      </div>
    </div>
  );
};
