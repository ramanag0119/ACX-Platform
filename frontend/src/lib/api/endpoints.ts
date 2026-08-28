/**
 * Typed wrappers over the delivered Phase 2.1 - 2.9 endpoints.
 *
 * This file is the frontend's complete view of the backend surface: if a call
 * is not here, the backend does not offer it. Notably absent, because the
 * schema has no such concept and Phases 2.8/2.9 refused to invent one:
 *
 *   /bookings      -- there is no booking table; reservations are `stays`
 *   /guests        -- guests are `app_user` rows, reached via stays/occupancy
 *   /telemetry     -- readings are `device_param` + `device_stat`
 *   /departments   -- no endpoint; department names ride along on users
 *   /room-allocations (top level) -- only nested under a stay
 *
 * Everything is GET except the login POST. Phase 2.10 adds no write paths.
 */

import { apiClient, type QueryParams } from "./client";
import type {
  ActivityRead,
  AlertRead,
  AlertTypeRead,
  AmenityConditionRead,
  AmenityStatusRead,
  BuildingRead,
  CurrentUser,
  DailyDataPointRead,
  DeviceCurrentStatRead,
  DeviceHealthRead,
  DeviceParamRead,
  DeviceRead,
  DeviceStatRead,
  DeviceTypeRead,
  EnergyStatRead,
  EnergySummaryRead,
  FacilityRead,
  FirmwareRead,
  FloorRead,
  IncidentRead,
  InvoiceRead,
  ModuleRead,
  NotificationRead,
  NotificationTemplateRead,
  OccupancyDetail,
  OccupancyRead,
  OtherDeviceReadingRead,
  Page,
  PermissionRead,
  PropertyRead,
  RoleRead,
  RolePermissionRead,
  RoomAllocationRead,
  RoomRead,
  ServiceCategoryRead,
  ServiceItemRead,
  ServiceRequestRead,
  ServiceStatusRead,
  ServiceTypeRead,
  StayOccupantRead,
  StayRead,
  TokenResponse,
  UserPermissionRead,
  UserRead,
  ValueAlertRead,
} from "./types";

// --- Authentication (Phase 2.4) --------------------------------------------

export const login = (username: string, password: string) =>
  apiClient.post<TokenResponse>(
    "/auth/login",
    { username, password },
    { skipAuthRedirect: true },
  );

export const fetchCurrentUser = () => apiClient.get<CurrentUser>("/auth/me");

// --- Facility & property (Phase 2.2) ---------------------------------------

export const listFacilities = (params?: QueryParams) =>
  apiClient.get<Page<FacilityRead>>("/facilities", params);
export const listProperties = (params?: QueryParams) =>
  apiClient.get<Page<PropertyRead>>("/properties", params);
export const listBuildings = (params?: QueryParams) =>
  apiClient.get<Page<BuildingRead>>("/buildings", params);
export const listFloors = (params?: QueryParams) =>
  apiClient.get<Page<FloorRead>>("/floors", params);
export const listRooms = (params?: QueryParams) =>
  apiClient.get<Page<RoomRead>>("/rooms", params);
export const getRoom = (roomId: string) => apiClient.get<RoomRead>(`/rooms/${roomId}`);

// --- Users, roles, permissions (Phase 2.3) ---------------------------------

export const listUsers = (params?: QueryParams) =>
  apiClient.get<Page<UserRead>>("/users", params);
export const getUser = (userId: string) => apiClient.get<UserRead>(`/users/${userId}`);
export const listUserPermissions = (userId: string, params?: QueryParams) =>
  apiClient.get<UserPermissionRead[]>(`/users/${userId}/permissions`, params);
export const listRoles = (params?: QueryParams) =>
  apiClient.get<Page<RoleRead>>("/roles", params);
export const listRolePermissions = (roleId: string) =>
  apiClient.get<RolePermissionRead[]>(`/roles/${roleId}/permissions`);
export const listModules = (params?: QueryParams) =>
  apiClient.get<Page<ModuleRead>>("/modules", params);
export const listPermissions = (params?: QueryParams) =>
  apiClient.get<Page<PermissionRead>>("/permissions", params);

// --- Services (Phase 2.5) --------------------------------------------------

export const listServiceTypes = (params?: QueryParams) =>
  apiClient.get<Page<ServiceTypeRead>>("/service-types", params);
export const listServiceStatuses = (params?: QueryParams) =>
  apiClient.get<Page<ServiceStatusRead>>("/service-statuses", params);
export const listServiceCategories = (params?: QueryParams) =>
  apiClient.get<Page<ServiceCategoryRead>>("/service-categories", params);
export const listServiceItems = (params?: QueryParams) =>
  apiClient.get<Page<ServiceItemRead>>("/service-items", params);
export const listServiceRequests = (params?: QueryParams) =>
  apiClient.get<Page<ServiceRequestRead>>("/service-requests", params);

// --- Devices & firmware (Phase 2.6) ----------------------------------------

export const listDeviceTypes = (params?: QueryParams) =>
  apiClient.get<Page<DeviceTypeRead>>("/device-types", params);
export const listDevices = (params?: QueryParams) =>
  apiClient.get<Page<DeviceRead>>("/devices", params);
export const getDevice = (deviceId: string) => apiClient.get<DeviceRead>(`/devices/${deviceId}`);
export const getDeviceHealth = (deviceId: string, params?: QueryParams) =>
  apiClient.get<DeviceHealthRead>(`/devices/${deviceId}/health`, params);
export const listFirmware = (params?: QueryParams) =>
  apiClient.get<Page<FirmwareRead>>("/firmware", params);

// --- Alerts & notifications (Phase 2.7) ------------------------------------

export const listAlertTypes = (params?: QueryParams) =>
  apiClient.get<Page<AlertTypeRead>>("/alert-types", params);
export const listAlerts = (params?: QueryParams) =>
  apiClient.get<Page<AlertRead>>("/alerts", params);
export const listIncidents = (params?: QueryParams) =>
  apiClient.get<Page<IncidentRead>>("/incidents", params);
export const listValueAlerts = (params?: QueryParams) =>
  apiClient.get<Page<ValueAlertRead>>("/value-alerts", params);
export const listNotifications = (params?: QueryParams) =>
  apiClient.get<Page<NotificationRead>>("/notifications", params);
export const listNotificationTemplates = (params?: QueryParams) =>
  apiClient.get<Page<NotificationTemplateRead>>("/notification-templates", params);
export const listActivities = (params?: QueryParams) =>
  apiClient.get<Page<ActivityRead>>("/activities", params);

// --- Occupancy & stays (Phase 2.8) -----------------------------------------

export const listOccupancy = (params?: QueryParams) =>
  apiClient.get<Page<OccupancyRead>>("/occupancy", params);
export const getOccupancy = (amenityId: string) =>
  apiClient.get<OccupancyDetail>(`/occupancy/${amenityId}`);
export const listAmenityStatuses = (params?: QueryParams) =>
  apiClient.get<Page<AmenityStatusRead>>("/amenity-statuses", params);
export const listAmenityConditions = (params?: QueryParams) =>
  apiClient.get<Page<AmenityConditionRead>>("/amenity-conditions", params);
export const listStays = (params?: QueryParams) =>
  apiClient.get<Page<StayRead>>("/stays", params);
export const getStay = (stayId: string) => apiClient.get<StayRead>(`/stays/${stayId}`);
export const listStayOccupants = (stayId: string) =>
  apiClient.get<StayOccupantRead[]>(`/stays/${stayId}/occupants`);
export const listStayRoomAllocations = (stayId: string) =>
  apiClient.get<RoomAllocationRead[]>(`/stays/${stayId}/room-allocations`);
export const listInvoices = (params?: QueryParams) =>
  apiClient.get<Page<InvoiceRead>>("/invoices", params);

// --- Telemetry & energy (Phase 2.9) ----------------------------------------

export const listDeviceParams = (params?: QueryParams) =>
  apiClient.get<Page<DeviceParamRead>>("/device-params", params);
export const listDeviceStats = (params?: QueryParams) =>
  apiClient.get<Page<DeviceStatRead>>("/device-stats", params);
export const listDeviceCurrentStats = (params?: QueryParams) =>
  apiClient.get<Page<DeviceCurrentStatRead>>("/device-current-stats", params);
export const listOtherDeviceReadings = (params?: QueryParams) =>
  apiClient.get<Page<OtherDeviceReadingRead>>("/other-device-readings", params);
export const listEnergyStats = (params?: QueryParams) =>
  apiClient.get<Page<EnergyStatRead>>("/energy-stats", params);
export const getEnergySummary = (params?: QueryParams) =>
  apiClient.get<EnergySummaryRead>("/energy-stats/summary", params);
export const listDailyDataPoints = (params?: QueryParams) =>
  apiClient.get<Page<DailyDataPointRead>>("/daily-data-points", params);
