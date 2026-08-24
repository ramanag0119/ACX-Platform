/**
 * React Query hooks over the API client.
 *
 * The QueryClientProvider already existed in App.tsx but had no consumers;
 * these hooks are its first real use. Retry is disabled for 401/403/404/422
 * because those are answers, not transient failures.
 */

import { useQueries, useQuery, type UseQueryOptions } from "@tanstack/react-query";

import { ApiError, type QueryParams } from "./client";
import * as api from "./endpoints";
import * as writeApi from "./writes";
import { MAX_PAGE_SIZE, type Page } from "./types";

function retry(failureCount: number, error: unknown) {
  if (error instanceof ApiError && error.status > 0 && error.status < 500) return false;
  return failureCount < 2;
}

type Options<T> = Omit<UseQueryOptions<T, ApiError>, "queryKey" | "queryFn">;

/** Every list hook is built from this, so paging behaves identically. */
function useApiQuery<T>(
  key: unknown[],
  fetcher: (signal: AbortSignal) => Promise<T>,
  options?: Options<T>,
) {
  return useQuery<T, ApiError>({
    queryKey: key,
    queryFn: ({ signal }) => fetcher(signal),
    retry,
    staleTime: 30_000,
    ...options,
  });
}

/** Clamps to the backend's limit so a stray page size can never 422. */
export function pageParams(page: number, pageSize: number, filters?: QueryParams): QueryParams {
  return { page, page_size: Math.min(pageSize, MAX_PAGE_SIZE), ...filters };
}

export const emptyPage = <T>(): Page<T> => ({ items: [], page: 1, page_size: 0, total: 0 });

// --- KPI counts ------------------------------------------------------------

/**
 * The list endpoints a KPI count may be taken from, and the module each one is
 * gated on by the backend. A count that is not in this table cannot be shown,
 * because there is no endpoint whose `total` answers it.
 */
interface CountSourceEntry {
  /** Any list endpoint; only the envelope's `total` is read, never the rows. */
  list: (params?: QueryParams) => Promise<Page<unknown>>;
  /** The module the backend gates this endpoint on. */
  module: string;
}

export const COUNT_SOURCES = {
  devices: { list: api.listDevices, module: "caleido_network" },
  alerts: { list: api.listAlerts, module: "caleido_network" },
  incidents: { list: api.listIncidents, module: "caleido_network" },
  "value-alerts": { list: api.listValueAlerts, module: "caleido_network" },
  occupancy: { list: api.listOccupancy, module: "occupancy" },
  stays: { list: api.listStays, module: "bookings" },
  "service-requests": { list: api.listServiceRequests, module: "service_tracking" },
  activities: { list: api.listActivities, module: "dashboard" },
  notifications: { list: api.listNotifications, module: "dashboard" },
  rooms: { list: api.listRooms, module: "facility_management" },
} satisfies Record<string, CountSourceEntry>;

export type CountSource = keyof typeof COUNT_SOURCES;

/** Each entry's `list` widens to the shared signature; only `total` is used. */
const countFetcher = (source: CountSource, filters?: QueryParams) =>
  (COUNT_SOURCES[source].list as CountSourceEntry["list"])({
    page: 1,
    page_size: 1,
    ...filters,
  });

/**
 * One KPI number, straight from a list endpoint's `total`.
 *
 * `page_size: 1` is deliberate: the count comes from the backend's COUNT(*)
 * over the same filtered query the table would run, so it is exact regardless
 * of how many rows exist. Nothing is counted in the browser, and no row beyond
 * the one the envelope requires is transferred.
 */
export function useCount(source: CountSource, filters?: QueryParams, enabled = true) {
  const query = useApiQuery(
    ["count", source, filters],
    () => countFetcher(source, filters),
    { enabled },
  );
  return {
    ...query,
    total: query.data?.total ?? null,
    module: COUNT_SOURCES[source].module,
  };
}

/**
 * A variable number of KPI counts over one resource -- one per filter.
 *
 * Needed where the set of buckets comes from a lookup table (the four
 * `amenity_status` rows, say) and so is not known at compile time. Each bucket
 * is still its own exact backend COUNT(*); the alternative -- fetching a page
 * of rows and tallying them here -- silently undercounts as soon as the
 * resource has more rows than one page holds.
 */
export function useCounts(
  source: CountSource,
  filterSets: QueryParams[],
  enabled = true,
) {
  const results = useQueries({
    queries: filterSets.map((filters) => ({
      queryKey: ["count", source, filters],
      queryFn: () => countFetcher(source, filters),
      enabled,
      retry,
      staleTime: 30_000,
    })),
  });
  return {
    totals: results.map((result) => result.data?.total ?? null),
    isLoading: results.some((result) => result.isLoading),
    error: (results.find((result) => result.error)?.error as ApiError | undefined) ?? null,
  };
}

// --- Auth ------------------------------------------------------------------

export const useCurrentUser = (enabled: boolean) =>
  useApiQuery(["auth", "me"], () => api.fetchCurrentUser(), {
    enabled,
    staleTime: 5 * 60_000,
    retry: false,
  });

// --- Facility --------------------------------------------------------------

export const useFacilities = (params?: QueryParams) =>
  useApiQuery(["facilities", params], () => api.listFacilities(params));
export const useProperties = (params?: QueryParams) =>
  useApiQuery(["properties", params], () => api.listProperties(params));
export const useBuildings = (params?: QueryParams) =>
  useApiQuery(["buildings", params], () => api.listBuildings(params));
export const useFloors = (params?: QueryParams) =>
  useApiQuery(["floors", params], () => api.listFloors(params));
export const useRooms = (params?: QueryParams) =>
  useApiQuery(["rooms", params], () => api.listRooms(params));

// --- Users, roles, permissions ---------------------------------------------

export const useUsers = (params?: QueryParams) =>
  useApiQuery(["users", params], () => api.listUsers(params));
export const useRoles = (params?: QueryParams) =>
  useApiQuery(["roles", params], () => api.listRoles(params));
export const useRolePermissions = (roleId: string | null) =>
  useApiQuery(["roles", roleId, "permissions"], () => api.listRolePermissions(roleId!), {
    enabled: Boolean(roleId),
  });
export const useModules = (params?: QueryParams) =>
  useApiQuery(["modules", params], () => api.listModules(params));

// --- Services --------------------------------------------------------------

export const useServiceTypes = (params?: QueryParams) =>
  useApiQuery(["service-types", params], () => api.listServiceTypes(params));
export const useServiceStatuses = (params?: QueryParams) =>
  useApiQuery(["service-statuses", params], () => api.listServiceStatuses(params));
export const useServiceCategories = (params?: QueryParams) =>
  useApiQuery(["service-categories", params], () => api.listServiceCategories(params));
export const useServiceItems = (params?: QueryParams) =>
  useApiQuery(["service-items", params], () => api.listServiceItems(params));
export const useServiceRequests = (params?: QueryParams) =>
  useApiQuery(["service-requests", params], () => api.listServiceRequests(params));

// --- Devices ---------------------------------------------------------------

export const useDeviceTypes = (params?: QueryParams) =>
  useApiQuery(["device-types", params], () => api.listDeviceTypes(params));
export const useDevices = (params?: QueryParams) =>
  useApiQuery(["devices", params], () => api.listDevices(params));
export const useDeviceHealth = (deviceId: string | null) =>
  useApiQuery(["devices", deviceId, "health"], () => api.getDeviceHealth(deviceId!), {
    enabled: Boolean(deviceId),
  });
export const useFirmware = (params?: QueryParams) =>
  useApiQuery(["firmware", params], () => api.listFirmware(params));

// --- Alerts & notifications ------------------------------------------------

export const useAlerts = (params?: QueryParams) =>
  useApiQuery(["alerts", params], () => api.listAlerts(params));
export const useAlertTypes = (params?: QueryParams) =>
  useApiQuery(["alert-types", params], () => api.listAlertTypes(params));
export const useIncidents = (params?: QueryParams) =>
  useApiQuery(["incidents", params], () => api.listIncidents(params));
export const useValueAlerts = (params?: QueryParams) =>
  useApiQuery(["value-alerts", params], () => api.listValueAlerts(params));
export const useNotifications = (params?: QueryParams) =>
  useApiQuery(["notifications", params], () => api.listNotifications(params));
export const useNotificationTemplates = (params?: QueryParams) =>
  useApiQuery(["notification-templates", params], () => api.listNotificationTemplates(params));
export const useActivities = (params?: QueryParams) =>
  useApiQuery(["activities", params], () => api.listActivities(params));

// --- Occupancy & stays -----------------------------------------------------

export const useOccupancy = (params?: QueryParams) =>
  useApiQuery(["occupancy", params], () => api.listOccupancy(params));
export const useOccupancyDetail = (amenityId: string | null) =>
  useApiQuery(["occupancy", amenityId], () => api.getOccupancy(amenityId!), {
    enabled: Boolean(amenityId),
  });
export const useAmenityStatuses = (params?: QueryParams) =>
  useApiQuery(["amenity-statuses", params], () => api.listAmenityStatuses(params));
export const useAmenityConditions = (params?: QueryParams) =>
  useApiQuery(["amenity-conditions", params], () => api.listAmenityConditions(params));
export const useStays = (params?: QueryParams) =>
  useApiQuery(["stays", params], () => api.listStays(params));
export const useStayRoomAllocations = (stayId: string | null) =>
  useApiQuery(
    ["stays", stayId, "room-allocations"],
    () => api.listStayRoomAllocations(stayId!),
    { enabled: Boolean(stayId) },
  );
export const useStayOccupants = (stayId: string | null) =>
  useApiQuery(["stays", stayId, "occupants"], () => api.listStayOccupants(stayId!), {
    enabled: Boolean(stayId),
  });
export const useInvoices = (params?: QueryParams) =>
  useApiQuery(["invoices", params], () => api.listInvoices(params));

// --- Telemetry & energy ----------------------------------------------------

export const useDeviceParams = (params?: QueryParams) =>
  useApiQuery(["device-params", params], () => api.listDeviceParams(params));
export const useDeviceStats = (params?: QueryParams) =>
  useApiQuery(["device-stats", params], () => api.listDeviceStats(params));
export const useDeviceCurrentStats = (params?: QueryParams) =>
  useApiQuery(["device-current-stats", params], () => api.listDeviceCurrentStats(params));
export const useOtherDeviceReadings = (params?: QueryParams) =>
  useApiQuery(["other-device-readings", params], () => api.listOtherDeviceReadings(params));
export const useEnergyStats = (params?: QueryParams) =>
  useApiQuery(["energy-stats", params], () => api.listEnergyStats(params));
export const useEnergySummary = (params?: QueryParams) =>
  useApiQuery(["energy-summary", params], () => api.getEnergySummary(params));
export const useDailyDataPoints = (params?: QueryParams) =>
  useApiQuery(["daily-data-points", params], () => api.listDailyDataPoints(params));

// ---------------------------------------------------------------------------
// Phase 3.0 reads: tables that gained an endpoint alongside their writes
// ---------------------------------------------------------------------------

export const useDepartments = (params?: QueryParams) =>
  useApiQuery(["departments", params], () => writeApi.listDepartments(params as never));
export const useJobFunctions = (params?: QueryParams) =>
  useApiQuery(["job-functions", params], () => writeApi.listJobFunctions(params as never));
export const useAmenityTypes = (params?: QueryParams) =>
  useApiQuery(["amenity-types", params], () => writeApi.listAmenityTypes(params as never));
export const usePackages = (params?: QueryParams) =>
  useApiQuery(["packages", params], () => writeApi.listPackages(params as never));
export const useFeatures = (params?: QueryParams) =>
  useApiQuery(["features", params], () => writeApi.listFeatures(params as never));
export const useOffers = (params?: QueryParams) =>
  useApiQuery(["offers", params], () => writeApi.listOffers(params as never));
export const useEvents = (params?: QueryParams) =>
  useApiQuery(["events", params], () => writeApi.listEvents(params as never));
export const useHolidays = (params?: QueryParams) =>
  useApiQuery(["holidays", params], () => writeApi.listHolidays(params as never));
export const useOccasionTypes = () =>
  useApiQuery(["holidays", "types"], () => writeApi.listOccasionTypes());
export const useLimitConfigs = (params?: QueryParams) =>
  useApiQuery(["limit-configs", params], () => writeApi.listLimitConfigs(params as never));

/** Services Planning. One endpoint per tab, filtered by `request_type`. */
export const useMaintenanceRequests = (params?: QueryParams) =>
  useApiQuery(["maintenance-requests", params], () =>
    writeApi.listMaintenanceRequests(params),
  );

/** Job Order Management. Each row arrives with its rooms and devices attached. */
export const useJobOrders = (params?: QueryParams) =>
  useApiQuery(["job-orders", params], () => writeApi.listJobOrders(params));
export const useJobOrder = (id: string | undefined) =>
  useApiQuery(["job-orders", id], () => writeApi.getJobOrder(id as string), {
    enabled: Boolean(id),
  });
