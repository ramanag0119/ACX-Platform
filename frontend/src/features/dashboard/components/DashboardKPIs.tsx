import { Loader2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  BedDouble,
  ClipboardList,
  Gauge,
  LifeBuoy,
  UserCheck,
  Zap,
} from "lucide-react";

import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";
import { scrollPanelIntoView } from "@/hooks/use-scroll-to-top";
import { ALERTS_PANEL_ID } from "./AlertsPanel";
import { ACTIVITY_PANEL_ID } from "./RecentActivityPanel";
import { useTheme } from "@/core/contexts/ThemeContext";
import { useAuth } from "@/core/contexts/AuthContext";
import { ApiError, describeApiError } from "@/lib/api/client";
import { useAmenityStatuses, useCount, useEnergySummary } from "@/lib/api/hooks";
import {
  MAX_PAGE_SIZE,
  ROOM_STATUS,
  VALUE_ALERT_ACTIVE,
} from "@/lib/api/types";

/**
 * The dashboard KPI row. Every figure is a backend `total` -- the COUNT(*) the
 * list endpoint runs for the same filter its table would use -- fetched with
 * `page_size: 1`. Nothing is counted in the browser, summed across pages, or
 * carried over from a mock.
 *
 * Each tile owns its own query, so a widget that 403s or 500s shows that state
 * in its own box and leaves the rest of the row intact (Step 11).
 *
 * KPIs the schema does NOT support, and which are therefore absent rather than
 * approximated:
 *
 *   - "Unresolved / Open incidents". `incident_status` is Unread | Read |
 *     Assigned | Resolved; there is no Open state. GET /incidents filters
 *     `status` by a single incident_status.id and there is no lookup endpoint
 *     to resolve "Resolved" to its id, so a NOT-Resolved count cannot be asked
 *     for. The tile shows the real total and the real unassigned count instead.
 *   - Trends ("+12% vs last week"). No endpoint returns a prior-period figure,
 *     and no table stores one.
 *   - Energy cost, carbon or kWh. `energy_stat` stores no unit and the summary
 *     performs SUM and COUNT only.
 */

interface TileProps {
  label: string;
  icon: LucideIcon;
  accent: string;
  /** null while unknown; the backend total once it arrives. */
  value: number | string | null;
  detail?: string;
  isLoading: boolean;
  error: ApiError | null;
  /**
   * The screen that lists what this figure counts, when one exists.
   *
   * Deliberately optional. Where the detail lives on this page instead of a
   * route, use `panelId` -- Device alerts and Activities both do.
   *
   * TWO tiles still have nowhere to go, verified against every page's data
   * hooks and all nine report definitions:
   *
   *   Incidents            no page reads `useIncidents`, and no report covers
   *                        `device_incident`. The Alert Report only mentions
   *                        incidents in prose ("the lifecycle lives on the
   *                        incident").
   *   Active value alerts  `useValueAlerts` is read only by useMeterHierarchy,
   *                        which feeds Power/Energy View -- both RETIRED, their
   *                        routes redirect to /occupancy. Limit Config Alert is
   *                        NOT it: that screen reads device_params, devices and
   *                        limit_configs, i.e. where thresholds are DEFINED,
   *                        not where breaches are listed.
   *
   * Those stay plain, non-interactive cards. A link to a screen that does not
   * show the data is worse than no link -- it looks answered and is not.
   *
   * Energy consumed has a real destination (`/reports/energy`) but is left
   * unmapped on purpose, by request.
   */
  to?: string;
  /**
   * Id of a panel on THIS page that already lists what the tile counts, for a
   * figure whose detail is on the dashboard itself rather than on a route.
   * Mutually exclusive with `to`; `to` wins if both are somehow given.
   */
  panelId?: string;
}

const Tile = ({
  label,
  icon: Icon,
  accent,
  value,
  detail,
  isLoading,
  error,
  to,
  panelId,
}: TileProps) => {
  const { isDark } = useTheme();
  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark
    ? "1px solid rgba(255,255,255,0.07)"
    : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const detailText = !isLoading && !error ? detail : undefined;

  /*
    Every slot below reserves its height, so a tile is the same size whatever
    its text says -- the label wraps to two lines on some tiles and one on
    others, the value slot swaps a spinner for error text for a 2xl number as
    the query resolves, and not every tile passes a detail line. Without the
    reserved heights each of those changed the height of the whole grid row.

    h-full fills the grid cell, min-w-0 stops a long value widening the track
    (and the page with it), min-h holds the floor on mobile where there is no
    taller sibling to stretch against.
  */
  const interactive = Boolean(to || panelId);
  const shellClass = cn(
    "rounded-[16px] p-4 h-full min-w-0 min-h-[136px] flex flex-col transition-all duration-250 hover:-translate-y-0.5",
    // Only a tile that actually goes somewhere advertises itself as clickable.
    interactive &&
      "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
  );
  const shellStyle = {
    background: cardBg,
    border: cardBorder,
    boxShadow: "0 8px 24px rgba(17,12,46,0.12)",
  };

  const body = (
    <>
      <div className="flex items-start justify-between gap-3 shrink-0">
        {/* Two lines always reserved; longer text wraps then clamps, so it
            neither overflows nor grows the card. */}
        <p
          className="min-w-0 min-h-[2rem] text-xs uppercase tracking-wide leading-4 line-clamp-2"
          style={{ color: mutedColor }}
          title={label}
        >
          {label}
        </p>
        <div
          className="h-9 w-9 shrink-0 rounded-xl flex items-center justify-center"
          style={{ background: `${accent}1f`, color: accent }}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>

      {/* One 32px slot shared by all three states, so the number, the spinner
          and the error message all sit at the same height. */}
      <div className="mt-0.5 flex min-h-[2rem] min-w-0 items-center">
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" style={{ color: mutedColor }} />
        ) : error ? (
          <p className="truncate text-xs" style={{ color: mutedColor }} title={describeApiError(error)}>
            {error.isForbidden
              ? "No access"
              : error.isUnauthorized
                ? "Session expired"
                : "Unavailable"}
          </p>
        ) : (
          <p className="truncate text-2xl font-semibold leading-8" style={{ color: titleColor }}>
            {value ?? "-"}
          </p>
        )}
      </div>

      {/* Always rendered, even when empty: the reserved slot keeps the subtitle
          row aligned across cards, and mt-auto pins it to the bottom when the
          cell is stretched taller than this card needs. */}
      <p
        className="mt-auto min-h-[1rem] truncate pt-1 text-[11px] leading-4"
        style={{ color: mutedColor }}
        title={detailText}
      >
        {detailText}
      </p>
    </>
  );

  /*
    A real <Link>, not a div with an onClick: it keeps middle-click and
    "open in new tab" working, is reachable and activatable from the keyboard
    for free, and is announced as a link. `aria-label` carries the figure as
    well as the label, because the visible text alone ("Incidents") does not
    say where the link goes.
  */
  /* Same-page target: a <button>, not a link. The detail is a panel further
     down THIS page, so there is no URL to navigate to -- a link would have to
     invent one. `type="button"` keeps it out of any enclosing form. */
  if (!to && panelId) {
    return (
      <button
        type="button"
        onClick={() => scrollPanelIntoView(panelId)}
        className={cn(shellClass, "text-left")}
        style={shellStyle}
        aria-label={
          value === null ? `${label}, show panel` : `${label}: ${value}, show panel`
        }
      >
        {body}
      </button>
    );
  }

  if (!to) {
    return (
      <div className={shellClass} style={shellStyle}>
        {body}
      </div>
    );
  }

  return (
    <Link
      to={to}
      className={shellClass}
      style={shellStyle}
      aria-label={value === null ? `${label}, open list` : `${label}: ${value}, open list`}
    >
      {body}
    </Link>
  );
};

const BLUE = "#38bdf8";
const GREEN = "#22c55e";
const AMBER = "#f59e0b";
const RED = "#ef4444";
const VIOLET = "#7c5cff";

/** Device alerts carry a SEVERITY (warning | critical) and no status. */
const AlertTiles = ({ enabled }: { enabled: boolean }) => {
  const all = useCount("alerts", undefined, enabled);
  const critical = useCount("alerts", { alert_severity: "critical" }, enabled);
  const warning = useCount("alerts", { alert_severity: "warning" }, enabled);
  // `value_alert.status` has no lookup table in the schema; the 0 = Active
  // convention is named in lib/api/types rather than written inline.
  const activeValue = useCount("value-alerts", { status: VALUE_ALERT_ACTIVE }, enabled);
  const incidents = useCount("incidents", undefined, enabled);
  const unassigned = useCount("incidents", { unassigned: true }, enabled);

  return (
    <>
      <Tile
        label="Device alerts"
        // The Alerts panel below on THIS page is the device-alert list: its
        // "Caleido" source is GET /alerts, the same rows this tile counts, and
        // it is the panel's default source. So the tile reveals that panel
        // rather than routing away to the Alert Report.
        panelId={ALERTS_PANEL_ID}
        icon={AlertTriangle}
        accent={critical.total ? RED : AMBER}
        value={all.total}
        detail={
          critical.total !== null && warning.total !== null
            ? `${critical.total} critical · ${warning.total} warning`
            : undefined
        }
        isLoading={all.isLoading}
        error={all.error}
      />
      <Tile
        label="Active value alerts"
        icon={Gauge}
        accent={activeValue.total ? RED : GREEN}
        value={activeValue.total}
        detail="threshold breaches not yet resolved"
        isLoading={activeValue.isLoading}
        error={activeValue.error}
      />
      <Tile
        label="Incidents"
        icon={LifeBuoy}
        accent={VIOLET}
        value={incidents.total}
        detail={unassigned.total !== null ? `${unassigned.total} unassigned` : undefined}
        isLoading={incidents.isLoading}
        error={incidents.error}
      />
    </>
  );
};

/**
 * In-house occupancy, by the Phase 2.8 definition: a stay with
 * `actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL`, which is
 * what `is_occupied=true` asks the backend for. The amenity's own `status`
 * flag is reported beside it, never in place of it -- the two are separate
 * sources of truth and the seeded data has them disagreeing.
 */
const OccupancyTile = ({ enabled }: { enabled: boolean }) => {
  const rooms = useCount("occupancy", undefined, enabled);
  const inHouse = useCount("occupancy", { is_occupied: true }, enabled);

  // The "Occupied" id is READ FROM `amenity_status`, not assumed to be 1. The
  // ids are seeded values, so a re-seed or reorder would have silently counted
  // the wrong status here. /amenity-statuses is gated on the same `occupancy`
  // module as this tile, so it needs no extra grant.
  // `enabled` is passed as an option too: conditional params alone would still
  // fire the request, which is the 403 the tile's own gate exists to avoid.
  const statusesQuery = useAmenityStatuses(
    enabled ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    { enabled },
  );
  const occupiedStatusId = statusesQuery.data?.items.find(
    (status) => status.amenity_status_name === ROOM_STATUS.OCCUPIED,
  )?.id;
  const flaggedOccupied = useCount(
    "occupancy",
    occupiedStatusId === undefined ? undefined : { status: occupiedStatusId },
    enabled && occupiedStatusId !== undefined,
  );

  const detail =
    rooms.total !== null
      ? `of ${rooms.total} rooms` +
        (flaggedOccupied.total !== null
          ? ` · amenity flag says ${flaggedOccupied.total} Occupied`
          : "")
      : undefined;

  return (
    <Tile
      label="Rooms in house"
      to="/occupancy"
      icon={BedDouble}
      accent={GREEN}
      value={inHouse.total}
      detail={detail}
      isLoading={inHouse.isLoading}
      error={inHouse.error}
    />
  );
};

const StayTile = ({ enabled }: { enabled: boolean }) => {
  const all = useCount("stays", undefined, enabled);
  const inHouse = useCount("stays", { is_in_house: true }, enabled);
  return (
    <Tile
      label="Stays in house"
      to="/bookings"
      icon={UserCheck}
      accent={BLUE}
      value={inHouse.total}
      detail={all.total !== null ? `of ${all.total} stays on record` : undefined}
      isLoading={inHouse.isLoading}
      error={inHouse.error}
    />
  );
};

const ServiceTile = ({ enabled }: { enabled: boolean }) => {
  const all = useCount("service-requests", undefined, enabled);
  const unassigned = useCount("service-requests", { unassigned: true }, enabled);
  return (
    <Tile
      label="Service requests"
      to="/services/tracking"
      icon={ClipboardList}
      accent={VIOLET}
      value={all.total}
      detail={unassigned.total !== null ? `${unassigned.total} unassigned` : undefined}
      isLoading={all.isLoading}
      error={all.error}
    />
  );
};

/**
 * The stored SUM over `energy_stat`, with NO unit: the table has no unit
 * column and the API returns `energy_unit: null`. It is not kWh, not costed
 * and not carbon-weighted.
 */
const EnergyTile = ({ enabled }: { enabled: boolean }) => {
  const query = useEnergySummary(enabled ? { group_by: "day" } : undefined);
  const summary = query.data;
  return (
    <Tile
      label="Energy consumed (no unit)"
      icon={Zap}
      accent={AMBER}
      value={summary ? Number(summary.total_energy_consumed.toFixed(3)) : null}
      detail={summary ? `${summary.reading_count} readings, all time` : undefined}
      isLoading={query.isLoading}
      error={query.error}
    />
  );
};

const ActivityTile = ({ enabled }: { enabled: boolean }) => {
  const all = useCount("activities", undefined, enabled);
  return (
    <Tile
      label="Activities"
      // Recent Activity below on THIS page is the activity list (GET
      // /activities) -- the same rows this tile counts. There is no activity
      // log route, so the tile reveals that panel.
      panelId={ACTIVITY_PANEL_ID}
      icon={Activity}
      accent={BLUE}
      value={all.total}
      detail="operational events recorded"
      isLoading={all.isLoading}
      error={all.error}
    />
  );
};

/**
 * Tiles are rendered only where the backend's own permission projection says
 * the module is readable. This is UX, not enforcement: the API re-checks every
 * request and answers 403 regardless of what is on screen.
 */
export const DashboardKPIs = () => {
  const { canRead } = useAuth();
  const network = canRead("caleido_network");

  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
      {network && <AlertTiles enabled={network} />}
      {canRead("occupancy") && <OccupancyTile enabled />}
      {canRead("bookings") && <StayTile enabled />}
      {canRead("service_tracking") && <ServiceTile enabled />}
      {canRead("reports") && <EnergyTile enabled />}
      {canRead("dashboard") && <ActivityTile enabled />}
    </div>
  );
};
