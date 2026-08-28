/**
 * Typed write calls against the Phase 3.0 endpoints.
 *
 * Every function here corresponds to one real backend route. Request shapes
 * mirror the FastAPI Pydantic bodies exactly -- a field that does not exist in
 * the schema cannot be sent from here, because it is not in the type.
 *
 * Nothing in this file writes to localStorage or keeps its own copy of state:
 * PostgreSQL is the source of truth, and every mutation is followed by a
 * refetch (see `mutations.ts`).
 */

import { apiClient, type QueryParams } from "./client";
import type {
  DeviceRead,
  FirmwareRead,
  IncidentRead,
  OccupancyDetail,
  Page,
  RoleRead,
  RolePermissionRead,
  RoomAllocationRead,
  RoomRead,
  ServiceCategoryRead,
  ServiceItemRead,
  ServiceRequestRead,
  StayOccupantRead,
  StayRead,
  UserRead,
  UserRef,
} from "./types";

// ---------------------------------------------------------------------------
// Shared shapes
// ---------------------------------------------------------------------------

export interface PermissionEntry {
  module_id: number;
  read_access: boolean;
  write_access: boolean;
}

/** `department` and `job_function`, which gained endpoints in Phase 3.0. */
export interface DepartmentRead {
  id: string;
  department_name: string;
  facility_id: string;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export interface JobFunctionRead {
  id: string;
  function_name: string;
  facility_id: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Users, roles, departments, job functions
// ---------------------------------------------------------------------------

export interface UserWrite {
  first_name: string;
  last_name?: string | null;
  phone_number: string;
  alternate_phone_number?: string | null;
  email?: string | null;
  user_name?: string | null;
  /** Hashed with bcrypt server-side; never stored or echoed by the API. */
  password?: string | null;
  user_uid?: string | null;
  emp_id?: string | null;
  gender?: "male" | "female" | "other" | null;
  dob?: string | null;
  date_of_joining?: string | null;
  supervisor?: string | null;
  address?: string | null;
  marital_status?: "married" | "unmarried" | "divorced" | "other" | null;
  department_id?: string | null;
  job_function_id?: string | null;
  /** 1 = staff, 0 = guest. There is no separate guest table. */
  is_staff?: number;
  is_child?: number;
  /** Rows in `user_role`; replaces the whole set on PATCH. */
  role_ids?: string[];
}

export const createUser = (body: UserWrite) => apiClient.post<UserRead>("/users", body);
export const updateUser = (id: string, body: Partial<UserWrite>) =>
  apiClient.patch<UserRead>(`/users/${id}`, body);
export const setUserPassword = (id: string, password: string) =>
  apiClient.post<void>(`/users/${id}/password`, { password });
export const deactivateUser = (id: string) =>
  apiClient.post<UserRead>(`/users/${id}/deactivate`, {});
export const reactivateUser = (id: string) =>
  apiClient.post<UserRead>(`/users/${id}/reactivate`, {});

export interface RoleWrite {
  name: string;
  description?: string | null;
  role_type?: "admin" | "system_user" | "manager" | "guest" | "staff";
  status?: number | null;
  permissions?: PermissionEntry[];
}

export const createRole = (body: RoleWrite) => apiClient.post<RoleRead>("/roles", body);
export const updateRole = (id: string, body: Partial<RoleWrite>) =>
  apiClient.patch<RoleRead>(`/roles/${id}`, body);
export const replaceRolePermissions = (id: string, permissions: PermissionEntry[]) =>
  apiClient.put<RolePermissionRead[]>(`/roles/${id}/permissions`, { permissions });

export const listDepartments = (params?: Record<string, string | number>) =>
  apiClient.get<Page<DepartmentRead>>("/departments", params);
export const createDepartment = (department_name: string) =>
  apiClient.post<DepartmentRead>("/departments", { department_name });
export const updateDepartment = (id: string, department_name: string) =>
  apiClient.patch<DepartmentRead>(`/departments/${id}`, { department_name });

export const listJobFunctions = (params?: Record<string, string | number>) =>
  apiClient.get<Page<JobFunctionRead>>("/job-functions", params);
export const createJobFunction = (function_name: string) =>
  apiClient.post<JobFunctionRead>("/job-functions", { function_name });
export const updateJobFunction = (id: string, function_name: string) =>
  apiClient.patch<JobFunctionRead>(`/job-functions/${id}`, { function_name });

// ---------------------------------------------------------------------------
// Service requests and catalogue
// ---------------------------------------------------------------------------

export interface ServiceRequestItemWrite {
  item_id?: string | null;
  category_id?: string | null;
  quantity?: number;
  /** Omit to copy the catalogue price -- the only price the schema stores. */
  price_per_unit?: string | null;
  assigned_to?: string | null;
}

export interface ServiceRequestWrite {
  service_type: number;
  category_id?: string | null;
  description?: string | null;
  amenity_id?: string | null;
  stay_id?: string | null;
  department_id?: string | null;
  assigned_to?: string | null;
  app_user_id?: string | null;
  expected_date?: string | null;
  status?: number | null;
  status_reason?: string | null;
  items?: ServiceRequestItemWrite[];
}

export const createServiceRequest = (body: ServiceRequestWrite) =>
  apiClient.post<ServiceRequestRead>("/service-requests", body);
export const updateServiceRequest = (
  id: string,
  body: Partial<Omit<ServiceRequestWrite, "service_type" | "items">>,
) => apiClient.patch<ServiceRequestRead>(`/service-requests/${id}`, body);
export const replaceServiceRequestItems = (id: string, items: ServiceRequestItemWrite[]) =>
  apiClient.put<ServiceRequestRead>(`/service-requests/${id}/items`, { items });
export const cancelServiceRequest = (id: string, reason?: string | null) =>
  apiClient.post<ServiceRequestRead>(`/service-requests/${id}/cancel`, { reason });

export interface ServiceCategoryWrite {
  category_name: string;
  service_type: number;
  description?: string | null;
  status?: number | null;
}

export const createServiceCategory = (body: ServiceCategoryWrite) =>
  apiClient.post<ServiceCategoryRead>("/service-categories", body);
export const updateServiceCategory = (id: string, body: Partial<ServiceCategoryWrite>) =>
  apiClient.patch<ServiceCategoryRead>(`/service-categories/${id}`, body);

export interface ServiceItemWrite {
  item_name: string;
  category_id: string;
  description?: string | null;
  price_per_unit?: string | null;
  amenity_id?: string | null;
  status?: number | null;
}

export const createServiceItem = (body: ServiceItemWrite) =>
  apiClient.post<ServiceItemRead>("/service-items", body);
export const updateServiceItem = (id: string, body: Partial<ServiceItemWrite>) =>
  apiClient.patch<ServiceItemRead>(`/service-items/${id}`, body);

// ---------------------------------------------------------------------------
// Stays: the reservation lifecycle
// ---------------------------------------------------------------------------

export interface StayWrite {
  booking_user_id: string;
  expected_checkin_time: string;
  expected_checkout_time: string;
  no_of_guests?: number;
  external_stay_ref_number?: string | null;
  gst?: string | null;
  comments?: string | null;
  /** Allocated in the same transaction; each room becomes Allotted. */
  room_ids?: string[];
  occupant_ids?: string[];
}

export type StayStatus =
  | "pending"
  | "active"
  | "checkout accepted"
  | "checkout pending"
  | "checkout rejected"
  | "checked out"
  | "cancelled";

export const createStay = (body: StayWrite) => apiClient.post<StayRead>("/stays", body);
export const updateStay = (id: string, body: Partial<StayWrite>) =>
  apiClient.patch<StayRead>(`/stays/${id}`, body);
export const checkInStay = (id: string, when?: string) =>
  apiClient.post<StayRead>(`/stays/${id}/check-in`, when ? { when } : {});
export const checkOutStay = (id: string, when?: string) =>
  apiClient.post<StayRead>(`/stays/${id}/check-out`, when ? { when } : {});
export const extendStay = (id: string, expected_checkout_time: string) =>
  apiClient.post<StayRead>(`/stays/${id}/extend`, { expected_checkout_time });
export const setStayStatus = (id: string, status: StayStatus) =>
  apiClient.post<StayRead>(`/stays/${id}/status`, { status });
export const setStayDocumentApproval = (id: string, approved: boolean) =>
  apiClient.post<StayRead>(`/stays/${id}/documents/approval`, {
    document_approval_status: approved ? "approved" : "pending",
  });
export const cancelStay = (id: string) => apiClient.post<StayRead>(`/stays/${id}/cancel`, {});

export const allocateRoom = (stayId: string, room_id: string, package_id?: string) =>
  apiClient.post<RoomAllocationRead[]>(`/stays/${stayId}/room-allocations`, {
    room_id,
    ...(package_id ? { package_id } : {}),
  });
/** Reallocation: the old room is released in the same transaction. */
export const reallocateRoom = (allocationId: string, room_id: string) =>
  apiClient.patch<RoomAllocationRead[]>(`/room-allocations/${allocationId}`, { room_id });
export const releaseAllocation = (allocationId: string) =>
  apiClient.del<void>(`/room-allocations/${allocationId}`);

export const addOccupant = (
  stayId: string,
  body: { guest_id: string; room_id?: string | null; is_key_required?: number | null },
) => apiClient.post<StayOccupantRead[]>(`/stays/${stayId}/occupants`, body);
export const removeOccupant = (occupantId: string) =>
  apiClient.del<void>(`/stay-occupants/${occupantId}`);

// ---------------------------------------------------------------------------
// Room state (the Occupancy screen's own controls)
// ---------------------------------------------------------------------------

export interface RoomStateWrite {
  /** `amenity_status`: 0 Available, 1 Occupied, 2 Unavailable, 3 Allotted. */
  status?: number;
  is_dnd?: number;
  power_save_mode?: number;
}

export const updateRoomState = (amenityId: string, body: RoomStateWrite) =>
  apiClient.patch<OccupancyDetail>(`/occupancy/${amenityId}`, body);
/** `amenity_condition` ids: 1 Dirty, 2 Low battery, 3 Under maintenance, 4 Sanitation. */
export const setRoomConditions = (amenityId: string, condition_ids: number[]) =>
  apiClient.put<RoomRead>(`/occupancy/${amenityId}/conditions`, { condition_ids });

// ---------------------------------------------------------------------------
// Devices, firmware, incidents, limit configs
// ---------------------------------------------------------------------------

export interface DeviceWrite {
  device_type: number;
  amenity_id: string;
  device_name?: string | null;
  device_uid?: string | null;
  appliance_name?: string | null;
  manufacturer_name?: string | null;
  model?: string | null;
  part_number?: string | null;
  mfg_date?: string | null;
  installed_on?: string | null;
  parent_device_id?: string | null;
  /** NOTE: `authentication_code` is absent by design -- it is a credential. */
}

export const createDevice = (body: DeviceWrite) => apiClient.post<DeviceRead>("/devices", body);
export const updateDevice = (
  id: string,
  body: Partial<Omit<DeviceWrite, "device_type">> & { expected_firmware_version?: string | null },
) => apiClient.patch<DeviceRead>(`/devices/${id}`, body);
export const commissionDevice = (id: string) =>
  apiClient.post<DeviceRead>(`/devices/${id}/commission`, {});
export const decommissionDevice = (id: string, reason?: string | null) =>
  apiClient.post<DeviceRead>(`/devices/${id}/decommission`, { reason });
export const deviceUnderMaintenance = (id: string) =>
  apiClient.post<DeviceRead>(`/devices/${id}/maintenance`, {});

export interface FirmwareWrite {
  device_type_id: number;
  firmware_version: string;
  firmware_filename: string;
  firmware_url: string;
  crc: string;
  release_notes?: string | null;
  release_date?: string | null;
  status?: "active" | "decommissioned";
}

export const createFirmware = (body: FirmwareWrite) =>
  apiClient.post<FirmwareRead>("/firmware", body);
export const updateFirmware = (id: string, body: Partial<FirmwareWrite>) =>
  apiClient.patch<FirmwareRead>(`/firmware/${id}`, body);
/** Sets `device.expected_firmware_version` (a firmware id) on each device. */
export const assignFirmware = (id: string, device_ids: string[]) =>
  apiClient.post<DeviceRead[]>(`/firmware/${id}/assign`, { device_ids });

export interface IncidentWrite {
  /** `incident_status`: 1 Unread, 2 Read, 3 Assigned, 4 Resolved. */
  current_incident_status?: number;
  assigned_to?: string | null;
  subject?: string | null;
  description?: string | null;
}

export const updateIncident = (id: string, body: IncidentWrite) =>
  apiClient.patch<IncidentRead>(`/incidents/${id}`, body);

export interface LimitConfigRead {
  id: string;
  parameter: string;
  device_name: string;
  device_id: string | null;
  limit_check: boolean;
  is_percentage_value: boolean;
  nominal: string | null;
  limit_low_percentage: string | null;
  limit_high_percentage: string | null;
  limit_low_value: string | null;
  limit_high_value: string | null;
  remarks: string;
  facility_id: string;
  created_on: string;
  updated_on: string;
}

export interface LimitConfigWrite {
  parameter: string;
  device_name: string;
  device_id?: string | null;
  limit_check?: boolean;
  is_percentage_value?: boolean;
  nominal?: string | null;
  limit_low_percentage?: string | null;
  limit_high_percentage?: string | null;
  limit_low_value?: string | null;
  limit_high_value?: string | null;
  remarks?: string;
}

export const listLimitConfigs = (params?: Record<string, string | number>) =>
  apiClient.get<Page<LimitConfigRead>>("/limit-configs", params);
export const createLimitConfig = (body: LimitConfigWrite) =>
  apiClient.post<LimitConfigRead>("/limit-configs", body);
export const updateLimitConfig = (id: string, body: Partial<LimitConfigWrite>) =>
  apiClient.patch<LimitConfigRead>(`/limit-configs/${id}`, body);

// ---------------------------------------------------------------------------
// Facility, rooms and the room catalogue
// ---------------------------------------------------------------------------

export interface FacilityWrite {
  name?: string;
  city?: string | null;
  state?: string | null;
  pin_code?: string | null;
  email?: string | null;
  additional_email?: string | null;
  google_map_link?: string | null;
  guest_rooms?: number | null;
  default_key_user?: string | null;
}

export const updateFacility = (id: string, body: FacilityWrite) =>
  apiClient.patch(`/facilities/${id}`, body);

export interface RoomWrite {
  name: string;
  amenity_type_id: string;
  package_id: string;
  property_chain_id?: string | null;
  parent_amenity_id?: string | null;
}

export const createRoom = (body: RoomWrite) => apiClient.post<RoomRead>("/rooms", body);
export const updateRoom = (id: string, body: Partial<RoomWrite>) =>
  apiClient.patch<RoomRead>(`/rooms/${id}`, body);

export interface AmenityTypeRead {
  id: string;
  name: string;
  amenity_category: "room" | "restaurant" | "others";
  facility_id: string | null;
  status: number;
  created_on: string;
  updated_on: string;
}

export const listAmenityTypes = (params?: Record<string, string | number>) =>
  apiClient.get<Page<AmenityTypeRead>>("/amenity-types", params);
export const createAmenityType = (body: {
  name: string;
  amenity_category: "room" | "restaurant" | "others";
}) => apiClient.post<AmenityTypeRead>("/amenity-types", body);
/**
 * `status` is how this API deletes. There is no DELETE route for the catalogue
 * tables -- rows are referenced by amenities, packages and requests -- so
 * retiring one is PATCH status=0, exactly as /holidays and /firmware work.
 * Omitting `status` from these signatures is what previously made the delete
 * buttons on the catalogue screens impossible to wire.
 */
export const updateAmenityType = (
  id: string,
  body: {
    name?: string;
    amenity_category?: "room" | "restaurant" | "others";
    status?: number | null;
  },
) => apiClient.patch<AmenityTypeRead>(`/amenity-types/${id}`, body);

export interface PackageRead {
  id: string;
  name: string;
  description: string | null;
  amenity_type: string;
  amenity_type_name: string | null;
  is_sub_package: boolean;
  facility_id: string | null;
  status: number;
  feature_names: string[];
  room_count: number;
  created_on: string;
  updated_on: string;
}

export const listPackages = (params?: Record<string, string | number | boolean>) =>
  apiClient.get<Page<PackageRead>>("/packages", params as Record<string, string | number>);
export const createPackage = (body: {
  name: string;
  amenity_type: string;
  description?: string | null;
  is_sub_package?: boolean;
  feature_ids?: string[];
}) => apiClient.post<PackageRead>("/packages", body);
export const updatePackage = (
  id: string,
  body: {
    name?: string;
    amenity_type?: string;
    description?: string | null;
    feature_ids?: string[];
    /** 0 retires the package. See updateAmenityType. */
    status?: number | null;
  },
) => apiClient.patch<PackageRead>(`/packages/${id}`, body);
/**
 * Soft delete: `status = 0`. Nothing is physically removed -- `amenity.package_id`
 * is NOT NULL and references the row, so this is how the catalogue deletes (see
 * updateAmenityType). The package then leaves GET /packages, and the API answers
 * 409 if rooms are still assigned to it.
 */
export const removePackage = (id: string) => updatePackage(id, { status: 0 });

export interface FeatureRead {
  id: string;
  feature_name: string;
  is_smart_feature: number | null;
  device_type: number | null;
  facility_id: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export const listFeatures = (params?: Record<string, string | number>) =>
  apiClient.get<Page<FeatureRead>>("/features", params);
export const createFeature = (feature_name: string) =>
  apiClient.post<FeatureRead>("/features", { feature_name });
export const updateFeature = (id: string, feature_name: string) =>
  apiClient.patch<FeatureRead>(`/features/${id}`, { feature_name });
/** 0 retires the room amenity. See updateAmenityType. */
export const setFeatureStatus = (id: string, status: number) =>
  apiClient.patch<FeatureRead>(`/features/${id}`, { status });

// ---------------------------------------------------------------------------
// Offers, events, holidays
// ---------------------------------------------------------------------------

export interface OfferRead {
  id: string;
  promo_code: string;
  offer_name: string | null;
  promo_code_description: string | null;
  offered_by: string | null;
  start_time: string | null;
  expiry_time: string | null;
  discount_percentage: string | null;
  max_discount_value: string | null;
  min_order_value: string | null;
  status: number | null;
  room_names: string[];
  created_on: string;
  updated_on: string;
}

export interface OfferWrite {
  promo_code: string;
  offer_name?: string | null;
  promo_code_description?: string | null;
  offered_by?: string | null;
  start_time?: string | null;
  expiry_time?: string | null;
  discount_percentage?: string | null;
  max_discount_value?: string | null;
  min_order_value?: string | null;
  amenity_ids?: string[];
}

export const listOffers = (params?: Record<string, string | number>) =>
  apiClient.get<Page<OfferRead>>("/offers", params);
export const createOffer = (body: OfferWrite) => apiClient.post<OfferRead>("/offers", body);
export const updateOffer = (id: string, body: Partial<OfferWrite>) =>
  apiClient.patch<OfferRead>(`/offers/${id}`, body);

export interface EventRead {
  id: string;
  name: string;
  venue: string | null;
  chief_guests: string | null;
  description: string | null;
  expected_attendees: number | null;
  interested_attendees: number | null;
  start_date_time: string | null;
  end_date_time: string | null;
  cancellation_reason: string | null;
  facility_id: string;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export interface EventWrite {
  name: string;
  venue?: string | null;
  chief_guests?: string | null;
  description?: string | null;
  expected_attendees?: number | null;
  start_date_time?: string | null;
  end_date_time?: string | null;
  /** PATCH only: 0 retires the event. `interested_attendees` is not settable. */
  status?: number | null;
  cancellation_reason?: string | null;
}

export const listEvents = (params?: Record<string, string | number>) =>
  apiClient.get<Page<EventRead>>("/events", params);
export const createEvent = (body: EventWrite) => apiClient.post<EventRead>("/events", body);
export const updateEvent = (id: string, body: Partial<EventWrite>) =>
  apiClient.patch<EventRead>(`/events/${id}`, body);

export interface HolidayRead {
  id: string;
  occasion_name: string | null;
  occasion_type: number;
  occasion_type_name: string | null;
  occasion_start_date: string;
  occasion_end_date: string | null;
  month: number;
  day_of_month: number;
  is_repeatable: number | null;
  notify_to_hub: number | null;
  facility_id: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export interface HolidayWrite {
  occasion_type: number;
  occasion_name?: string | null;
  occasion_start_date: string;
  occasion_end_date?: string | null;
  is_repeatable?: number | null;
  notify_to_hub?: number | null;
  /** PATCH only: 0 retires the occasion; `occasion` has no delete endpoint. */
  status?: number | null;
}

export interface OccasionTypeRead {
  id: number;
  name: string;
}

// ---------------------------------------------------------------------------
// Services Planning (`maintenance_request` + recurrence / amenity / assignee)
// ---------------------------------------------------------------------------

/** A room attached through `maintenance_request_amenity`. */
export interface MaintenanceRoomRef {
  amenity_id: string;
  room_name: string | null;
}

/** `maintenance_request_recurrence`. `days_of_week` is a bitmask, Sunday = 1;
 *  `day_labels` is the same value decoded by the backend. */
export interface MaintenanceRecurrence {
  recurrence_type: string;
  days_of_week: number | null;
  day_labels: string[];
  max_no_of_occurrences: number | null;
}

/**
 * One planned service. `service_type` / `service_type_name` are resolved
 * THROUGH the category -- `maintenance_request` has no service-type column.
 *
 * The two status columns are separate: `maintenance_request_status`
 * (+ `status_name`) is the lifecycle, `status` is the soft-delete flag.
 */
export interface MaintenanceRequestRead {
  id: string;
  maintenance_request_type: "scheduled" | "planned" | "disinfection";
  maintenance_start_date: string | null;
  maintenance_end_date: string | null;
  maintenance_start_time: string | null;
  maintenance_end_time: string | null;
  is_recurring: number | null;
  department_id: string | null;
  department_name: string | null;
  category_id: string | null;
  category_name: string | null;
  service_type: number | null;
  service_type_name: string | null;
  item_id: string | null;
  item_name: string | null;
  facility_id: string | null;
  completed_on: string | null;
  is_room: number | null;
  non_room_comments: string | null;
  parent_id: string | null;
  maintenance_request_status: number;
  status_name: string | null;
  status_reason: string | null;
  delete_comments: string | null;
  under_maintenance: boolean | null;
  status: number | null;
  created_on: string;
  updated_on: string;
  rooms: MaintenanceRoomRef[];
  assignees: UserRef[];
  recurrence: MaintenanceRecurrence | null;
  room_count: number;
  assignee_count: number;
}

export interface MaintenanceRecurrenceWrite {
  recurrence_type?: "weekly";
  days_of_week?: number | null;
  day_labels?: string[] | null;
  max_no_of_occurrences?: number | null;
}

/** `facility_id`, `is_room`, `is_recurring` and both status columns are derived
 *  server-side and deliberately absent here. */
export interface MaintenanceRequestWrite {
  maintenance_request_type: "scheduled" | "planned" | "disinfection";
  maintenance_start_date?: string | null;
  maintenance_end_date?: string | null;
  maintenance_start_time?: string | null;
  maintenance_end_time?: string | null;
  department_id?: string | null;
  /** "Facility Services" on the form -- a `service_category` row. */
  category_id?: string | null;
  item_id?: string | null;
  under_maintenance?: boolean | null;
  non_room_comments?: string | null;
  amenity_ids?: string[];
  assignee_ids?: string[];
  recurrence?: MaintenanceRecurrenceWrite | null;
}

export const listMaintenanceRequests = (params?: QueryParams) =>
  apiClient.get<Page<MaintenanceRequestRead>>("/maintenance-requests", params);
export const getMaintenanceRequest = (id: string) =>
  apiClient.get<MaintenanceRequestRead>(`/maintenance-requests/${id}`);
export const createMaintenanceRequest = (body: MaintenanceRequestWrite) =>
  apiClient.post<MaintenanceRequestRead>("/maintenance-requests", body);
export const updateMaintenanceRequest = (
  id: string,
  body: Partial<MaintenanceRequestWrite> & { maintenance_request_status?: number },
) => apiClient.patch<MaintenanceRequestRead>(`/maintenance-requests/${id}`, body);
export const cancelMaintenanceRequest = (id: string, reason?: string | null) =>
  apiClient.post<MaintenanceRequestRead>(`/maintenance-requests/${id}/cancel`, { reason });
/** Soft delete: `status = 0`. Nothing is physically removed. */
export const removeMaintenanceRequest = (id: string, comments?: string | null) =>
  apiClient.del<MaintenanceRequestRead>(
    `/maintenance-requests/${id}${comments ? `?comments=${encodeURIComponent(comments)}` : ""}`,
  );

// ---------------------------------------------------------------------------
// Job orders: `job_order` + `job_order_amenity` + `job_order_device`
// ---------------------------------------------------------------------------

/** The real `job_order_type_of_work` enum. "Fresh Installation" is `installation`. */
export type JobOrderTypeOfWork = "installation" | "replacement" | "troubleshoot";
/** The real `job_order_status` enum -- the work lifecycle, not the delete flag. */
export type JobOrderStatus = "pending" | "completed";

/** A room attached through `job_order_amenity`. */
export interface JobOrderRoomRef {
  amenity_id: string;
  room_name: string | null;
}

/** A device attached through `job_order_device`. `device_type_name` is what the
 *  screen labels "Caleido Network". */
export interface JobOrderDeviceRef {
  device_id: string;
  device_uid: string | null;
  device_name: string | null;
  device_type: number | null;
  device_type_name: string | null;
  amenity_id: string | null;
  room_name: string | null;
}

/**
 * One job order. `job_order` has no `facility_id` column -- scope is reached
 * through its rooms -- so none is returned.
 *
 * The two status columns are separate: `job_order_status` is the work lifecycle
 * (pending / completed), `status` is the soft-delete flag (1 live, 0 removed).
 */
export interface JobOrderRead {
  id: string;
  order_reference: string;
  description: string | null;
  type_of_work: JobOrderTypeOfWork;
  work_commence: string;
  estimated_completion_date: string;
  /** No `authentication_code`: it is the technician's on-site code and the API
   *  never returns it, the same rule `device.authentication_code` follows. */
  assigned_to: string | null;
  assignee: UserRef | null;
  job_order_status: JobOrderStatus;
  completed_on: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
  rooms: JobOrderRoomRef[];
  devices: JobOrderDeviceRef[];
  room_count: number;
  device_count: number;
}

/**
 * `order_reference` is optional -- omitted, the server continues the seeded
 * `JO-YYYY-NNNN` sequence. `authentication_code` and `job_order_status` are
 * derived server-side and deliberately absent here.
 *
 * `amenity_ids` are `amenity.id` UUIDs and `device_ids` are `device.id` UUIDs.
 * Room numbers and device-type names are rejected by the backend's UUID parsing.
 */
export interface JobOrderWrite {
  order_reference?: string | null;
  description?: string | null;
  type_of_work: JobOrderTypeOfWork;
  work_commence: string;
  estimated_completion_date: string;
  assigned_to?: string | null;
  amenity_ids?: string[];
  device_ids?: string[];
}

export const listJobOrders = (params?: QueryParams) =>
  apiClient.get<Page<JobOrderRead>>("/job-orders", params);
export const getJobOrder = (id: string) =>
  apiClient.get<JobOrderRead>(`/job-orders/${id}`);
export const createJobOrder = (body: JobOrderWrite) =>
  apiClient.post<JobOrderRead>("/job-orders", body);
export const updateJobOrder = (
  id: string,
  body: Partial<JobOrderWrite> & { job_order_status?: JobOrderStatus },
) => apiClient.patch<JobOrderRead>(`/job-orders/${id}`, body);
/** Soft delete: `status = 0`. Nothing is physically removed; the room and
 *  device links are kept so the record of what the job covered survives. */
export const removeJobOrder = (id: string) =>
  apiClient.del<JobOrderRead>(`/job-orders/${id}`);

export const listHolidays = (params?: Record<string, string | number>) =>
  apiClient.get<Page<HolidayRead>>("/holidays", params);
export const listOccasionTypes = () => apiClient.get<OccasionTypeRead[]>("/holidays/types");
export const createHoliday = (body: HolidayWrite) =>
  apiClient.post<HolidayRead>("/holidays", body);
export const updateHoliday = (id: string, body: Partial<HolidayWrite>) =>
  apiClient.patch<HolidayRead>(`/holidays/${id}`, body);
