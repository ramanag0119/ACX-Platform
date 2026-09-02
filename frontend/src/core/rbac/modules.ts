/**
 * Route -> backend module map.
 *
 * The names below are the exact `role_module.module_name` values the backend
 * discovered (18 rows) and gates each router on with `require_permission`.
 * Frontend RBAC is UX only: hiding nav and guarding routes. The backend's
 * 401/403 remains the security boundary, and no role name appears anywhere
 * in this file or its consumers.
 *
 * Two screens have no module of their own and are documented, not invented:
 *
 *   /config/limit-alert  Limit Config Alert reads `value-alerts`, which the
 *                        backend gates on `caleido_network`.
 *   /power-view          Both read device telemetry, also `caleido_network`.
 *   /energy-view         (see the frontend/backend gap list in the report)
 *   /room-view           Reads rooms + occupancy -> `occupancy`.
 */

/** Every module the backend recognises. */
export const HMS_MODULES = [
  "dashboard",
  "occupancy",
  "bookings",
  "service_tracking",
  "service_planning",
  "facility_management",
  "user_roles",
  "service_setup",
  "employees",
  "job_order",
  "offers",
  "events",
  "caleido_network",
  "firmware_management",
  "reports",
  "tickets",
  "holidays",
  "default_key",
] as const;

export type HmsModule = (typeof HMS_MODULES)[number];

/**
 * The module that guards each route, chosen to match the module the backend
 * actually enforces on the endpoints that route calls.
 */
export const ROUTE_MODULE: Record<string, HmsModule> = {
  "/dashboard": "dashboard",
  "/occupancy": "occupancy",
  "/bookings": "bookings",
  "/services/tracking": "service_tracking",
  "/services/planning": "service_planning",
  "/config/facility": "facility_management",
  "/config/user-roles": "user_roles",
  "/config/services-setup": "service_setup",
  "/config/employees": "employees",
  "/config/job-order": "job_order",
  "/config/limit-alert": "caleido_network",
  "/offers": "offers",
  "/holidays": "holidays",
  "/events": "events",
  "/devices/caleido-network": "caleido_network",
  "/devices/firmware-management": "firmware_management",
  "/reports": "reports",
  "/tickets": "tickets",
  "/power-view": "caleido_network",
  "/energy-view": "reports",
  "/room-view": "occupancy",
  "/key-settings": "default_key",
};

/** Longest-prefix lookup, so `/reports/occupancy` resolves to `reports`. */
export function moduleForPath(pathname: string): HmsModule | undefined {
  const direct = ROUTE_MODULE[pathname];
  if (direct) return direct;
  const match = Object.keys(ROUTE_MODULE)
    .filter((route) => pathname === route || pathname.startsWith(`${route}/`))
    .sort((a, b) => b.length - a.length)[0];
  return match ? ROUTE_MODULE[match] : undefined;
}
