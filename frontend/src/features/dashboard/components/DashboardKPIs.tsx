import { Loader2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  BedDouble,
  ClipboardList,
  Cpu,
  Gauge,
  LifeBuoy,
  UploadCloud,
  UserCheck,
  Zap,
} from "lucide-react";

import { useTheme } from "@/core/contexts/ThemeContext";
import { useAuth } from "@/core/contexts/AuthContext";
import { ApiError, describeApiError } from "@/lib/api/client";
import { useCount, useEnergySummary } from "@/lib/api/hooks";

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
}

const Tile = ({ label, icon: Icon, accent, value, detail, isLoading, error }: TileProps) => {
  const { isDark } = useTheme();
  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark
    ? "1px solid rgba(255,255,255,0.07)"
    : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";

  return (
    <div
      className="rounded-[16px] p-4 transition-all duration-250 hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide" style={{ color: mutedColor }}>
            {label}
          </p>

          {isLoading ? (
            <Loader2 className="mt-2 h-5 w-5 animate-spin" style={{ color: mutedColor }} />
          ) : error ? (
            <p className="mt-1 text-xs" style={{ color: mutedColor }} title={describeApiError(error)}>
              {error.isForbidden
                ? "No access"
                : error.isUnauthorized
                  ? "Session expired"
                  : "Unavailable"}
            </p>
          ) : (
            <p className="mt-0.5 text-2xl font-semibold" style={{ color: titleColor }}>
              {value ?? "-"}
            </p>
          )}

          {!isLoading && !error && detail && (
            <p className="mt-1 text-[11px] truncate" style={{ color: mutedColor }} title={detail}>
              {detail}
            </p>
          )}
        </div>
        <div
          className="h-9 w-9 shrink-0 rounded-xl flex items-center justify-center"
          style={{ background: `${accent}1f`, color: accent }}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
};

const BLUE = "#38bdf8";
const GREEN = "#22c55e";
const AMBER = "#f59e0b";
const RED = "#ef4444";
const VIOLET = "#7c5cff";

/** Devices, with the real `device_health_status` enum: Active | Inactive. */
const DeviceTiles = ({ enabled }: { enabled: boolean }) => {
  const all = useCount("devices", undefined, enabled);
  const active = useCount("devices", { health_status: "Active" }, enabled);
  const inactive = useCount("devices", { health_status: "Inactive" }, enabled);
  const outdated = useCount("devices", { firmware_outdated: true }, enabled);

  return (
    <>
      <Tile
        label="Devices"
        icon={Cpu}
        accent={BLUE}
        value={all.total}
        detail={
          active.total !== null && inactive.total !== null
            ? `${active.total} Active · ${inactive.total} Inactive`
            : undefined
        }
        isLoading={all.isLoading}
        error={all.error}
      />
      <Tile
        label="Firmware outdated"
        icon={UploadCloud}
        accent={outdated.total ? AMBER : GREEN}
        value={outdated.total}
        detail="current version differs from expected"
        isLoading={outdated.isLoading}
        error={outdated.error}
      />
    </>
  );
};

/** Device alerts carry a SEVERITY (warning | critical) and no status. */
const AlertTiles = ({ enabled }: { enabled: boolean }) => {
  const all = useCount("alerts", undefined, enabled);
  const critical = useCount("alerts", { alert_severity: "critical" }, enabled);
  const warning = useCount("alerts", { alert_severity: "warning" }, enabled);
  // value_alert.status is an integer: 0 = Active, 1 = Resolved.
  const activeValue = useCount("value-alerts", { status: 0 }, enabled);
  const incidents = useCount("incidents", undefined, enabled);
  const unassigned = useCount("incidents", { unassigned: true }, enabled);

  return (
    <>
      <Tile
        label="Device alerts"
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
  const flaggedOccupied = useCount("occupancy", { status: 1 }, enabled);

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
      {network && <DeviceTiles enabled={network} />}
      {network && <AlertTiles enabled={network} />}
      {canRead("occupancy") && <OccupancyTile enabled />}
      {canRead("bookings") && <StayTile enabled />}
      {canRead("service_tracking") && <ServiceTile enabled />}
      {canRead("reports") && <EnergyTile enabled />}
      {canRead("dashboard") && <ActivityTile enabled />}
    </div>
  );
};
