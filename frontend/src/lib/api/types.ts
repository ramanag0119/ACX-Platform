/**
 * TypeScript mirrors of the FastAPI response schemas (Phases 2.1 - 2.9).
 *
 * Every field here exists in the backend OpenAPI document. Nothing is added
 * "for convenience": if a screen wants a field that is absent below, the
 * backend does not return it and the gap is documented rather than filled in.
 */

/** The shared envelope returned by every list endpoint. */
export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

/** The shared FastAPI error envelope: {"error": {...}}. */
export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: unknown;
}

export interface ApiErrorResponse {
  error: ApiErrorBody;
}

export const DEFAULT_PAGE_SIZE = 20;
/** The backend rejects anything above this with 422. */
export const MAX_PAGE_SIZE = 100;

// ---------------------------------------------------------------------------
// PostgreSQL enum labels
// ---------------------------------------------------------------------------
/**
 * These mirror `app/schemas/filters.py`, which mirrors the `pg_enum` labels.
 * The backend declares the matching query filters as Literal, so the OpenAPI
 * document names the same values and sending anything else is a 422 -- these
 * unions are the contract, not a convenience.
 *
 * Nothing here is invented. In particular there is no "Open", "Info", "good",
 * "warning" or "error" DEVICE state: `device_health_status` has exactly two
 * labels, and incident lifecycle is a separate lookup TABLE.
 */

export type DeviceHealthStatus = "Active" | "Inactive";
export const DEVICE_HEALTH_STATUSES: DeviceHealthStatus[] = ["Active", "Inactive"];

export type DeviceConfigStatus =
  | "configured"
  | "bad_configuration"
  | "commissioned"
  | "decommissioned"
  | "under_maintenance"
  | "missing";

export type FirmwareStatus = "active" | "decommissioned";

/** Carried by an ALERT. An alert has no lifecycle status of its own. */
export type AlertSeverity = "warning" | "critical";
export const ALERT_SEVERITIES: AlertSeverity[] = ["warning", "critical"];

export type AmenityCategory = "room" | "restaurant" | "others";

export type StayStatus =
  | "pending"
  | "active"
  | "checkout accepted"
  | "checkout pending"
  | "checkout rejected"
  | "checked out"
  | "cancelled";

export type DocumentApprovalStatus = "pending" | "approved";

export type RequestSource = "ikanos" | "porta";

/** Notification DELIVERY state. Not read/unread -- that lives on activities. */
export type NotificationStatus = "pending" | "processing" | "processed" | "error";

export type NotificationChannel =
  | "email"
  | "sms"
  | "push notification"
  | "silent notification";

export type DailyMetricType =
  | "smart room"
  | "service request"
  | "checkout"
  | "booking"
  | "guest room";

export type ParamDataType = "Integer" | "Double" | "String" | "Date Time";

export type RoleType = "admin" | "system_user" | "manager" | "guest" | "staff";

/**
 * LOOKUP TABLES, not enums. `amenity_status`, `incident_status` and
 * `service_status` are rows, so a deployment can hold values these constants do
 * not list -- which is why the corresponding `status_name` fields stay
 * `string | null` and every screen reads the options from the lookup endpoint.
 * The constants below are only for ordering and colouring what is known today.
 */
export const KNOWN_AMENITY_STATUSES = [
  "Available",
  "Occupied",
  "Unavailable",
  "Allotted",
] as const;

export const KNOWN_INCIDENT_STATUSES = [
  "Unread",
  "Read",
  "Assigned",
  "Resolved",
] as const;

/** Referenced user. The backend never returns more than this for a person. */
export interface UserRef {
  id: string;
  name: string;
  emp_id: string | null;
}

// ---------------------------------------------------------------------------
// Auth & RBAC (Phase 2.3 / 2.4)
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserRoleRead {
  role_id: string;
  role_name: string;
  role_type: string;
  facility_id: string;
}

export interface UserPermissionRead {
  module_id: number;
  module_name: string;
  read_access: boolean;
  write_access: boolean;
  granted_by_roles: string[];
}

export interface CurrentUser {
  id: string;
  user_name: string | null;
  first_name: string;
  last_name: string | null;
  email: string | null;
  is_staff: number | null;
  platform: string;
  role_types: string[];
  roles: UserRoleRead[];
  facility_ids: string[];
  permissions: UserPermissionRead[];
}

export interface RoleRead {
  id: string;
  name: string;
  description: string | null;
  role_type: RoleType;
  status: number | null;
  facility_id: string;
  created_on: string;
  updated_on: string;
}

export interface RolePermissionRead {
  module_id: number;
  module_name: string;
  read_access: boolean;
  write_access: boolean | null;
  read_applicable: boolean | null;
  write_applicable: boolean | null;
}

export interface ModuleRead {
  id: number;
  module_name: string;
  read_applicable: boolean | null;
  write_applicable: boolean | null;
  created_on: string;
  updated_on: string;
}

export interface PermissionRead {
  role_id: string;
  role_name: string;
  module_id: number;
  module_name: string;
  read_access: boolean;
  write_access: boolean | null;
  created_on: string;
  updated_on: string;
}

export interface UserRead {
  id: string;
  user_uid: string;
  user_name: string | null;
  first_name: string;
  last_name: string | null;
  email: string | null;
  phone_number: string;
  alternate_phone_number: string | null;
  gender: string | null;
  dob: string | null;
  age: number | null;
  is_child: number;
  is_staff: number | null;
  emp_id: string | null;
  date_of_joining: string | null;
  date_of_termination: string | null;
  supervisor: string | null;
  address: string | null;
  country: number | null;
  nationality: number | null;
  marital_status: string | null;
  department_id: string | null;
  department_name: string | null;
  job_function_id: string | null;
  job_function_name: string | null;
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Facility & property hierarchy (Phase 2.2)
// ---------------------------------------------------------------------------

export interface FacilityRead {
  id: string;
  facility_uid: string;
  name: string;
  org_id: string;
  city: string | null;
  state: string | null;
  pin_code: string | null;
  guest_rooms: number | null;
  email: string;
  additional_email: string | null;
  google_map_link: string | null;
  currency_id: number | null;
  facility_image_id: string | null;
  default_key_user: string | null;
  created_on: string;
  updated_on: string;
}

export interface PropertyRead {
  id: string;
  property_name: string;
  property_type_id: string;
  property_type_name: string | null;
  property_type_levels: number | null;
  facility_id: string | null;
  status: number;
  created_on: string;
  updated_on: string;
}

/** Projection over `property` + `property_chain.level_one_id`. Not a table. */
export interface BuildingRead {
  id: string;
  name: string;
  facility_id: string | null;
  property_type_id: string;
  property_type_name: string | null;
  status: number;
  floor_count: number;
  room_count: number;
}

/** Projection over `property` + `property_chain.level_two_id`. Not a table. */
export interface FloorRead {
  id: string;
  name: string;
  facility_id: string | null;
  property_chain_id: string;
  building_id: string;
  building_name: string;
  status: number;
  room_count: number;
}

export interface AmenityConditionRef {
  id: number;
  name: string;
}

export interface RoomRead {
  id: string;
  name: string;
  facility_id: string | null;
  amenity_type_id: string;
  amenity_type_name: string | null;
  amenity_category: AmenityCategory | null;
  package_id: string;
  package_name: string | null;
  status: number | null;
  status_name: string | null;
  property_chain_id: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  parent_amenity_id: string | null;
  is_dnd: number | null;
  power_save_mode: number | null;
  conditions: AmenityConditionRef[];
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Services (Phase 2.5)
// ---------------------------------------------------------------------------

export interface ServiceTypeRead {
  id: number;
  name: string;
  created_on: string;
  updated_on: string;
}

export interface ServiceStatusRead {
  id: number;
  name: string;
  created_on: string;
  updated_on: string;
}

export interface ServiceCategoryRead {
  id: string;
  category_name: string | null;
  description: string | null;
  service_type: number;
  service_type_name: string | null;
  service_category_key: string | null;
  category_icon: string | null;
  facility_id: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export interface ServiceItemRead {
  id: string;
  item_name: string;
  description: string | null;
  category_id: string;
  category_name: string | null;
  service_type: number | null;
  service_type_name: string | null;
  price_per_unit: string | null;
  amenity_id: string | null;
  item_icon: string | null;
  facility_id: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export interface ServiceRequestRead {
  id: string;
  ref_number: string | null;
  description: string | null;
  service_type: number;
  service_type_name: string | null;
  category_id: string | null;
  category_name: string | null;
  status: number | null;
  status_name: string | null;
  status_reason: string | null;
  request_source: RequestSource | null;
  facility_id: string | null;
  amenity_id: string | null;
  amenity_name: string | null;
  stay_id: string | null;
  stay_ref_number: string | null;
  department_id: string | null;
  department_name: string | null;
  requester: UserRef | null;
  assignee: UserRef | null;
  promo_code_id: string | null;
  net_amount: string | null;
  total_tax: string | null;
  total_amount: string | null;
  expected_date: string | null;
  completed_on: string | null;
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Devices & firmware (Phase 2.6)
// ---------------------------------------------------------------------------

export interface DeviceTypeRead {
  id: number;
  name: string | null;
  device_short_code: string | null;
  created_on: string;
  updated_on: string;
}

/** `authentication_code` and `metadata` are deliberately absent: the backend
 *  never selects them, so there is nothing here to leak. */
export interface DeviceRead {
  id: string;
  device_uid: string | null;
  device_name: string | null;
  appliance_name: string | null;
  part_number: string | null;
  model: string | null;
  manufacturer_name: string | null;
  mfg_date: string;
  installed_on: string | null;
  device_type: number;
  device_type_name: string | null;
  device_short_code: string | null;
  facility_id: string;
  amenity_id: string;
  amenity_name: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  parent_device_id: string | null;
  health_status: DeviceHealthStatus | null;
  device_config_status: DeviceConfigStatus | null;
  device_temperature: string | null;
  is_power_off: boolean | null;
  operational_mode: number | null;
  is_other_device: number | null;
  status: number | null;
  current_firmware_version: string | null;
  current_firmware: string | null;
  expected_firmware_version: string | null;
  expected_firmware: string | null;
  firmware_up_to_date: boolean | null;
  created_on: string;
  updated_on: string;
}

export interface DeviceHealthSample {
  id: number;
  device_health_status: DeviceHealthStatus | null;
  device_temperature: string | null;
  created_on: string;
}

export interface BatteryCycle {
  cycle_number: number | null;
  initial_battery_percentage: string | null;
  latest_battery_percentage: string | null;
  battery_life: string | null;
  created_on: string;
}

export interface OperationSample {
  stats_date: string;
  operation_percentage: string | null;
}

export interface DeviceHealthRead {
  device_id: string;
  device_uid: string | null;
  device_name: string | null;
  device_type_name: string | null;
  health_status: DeviceHealthStatus | null;
  device_config_status: DeviceConfigStatus | null;
  device_temperature: string | null;
  is_power_off: boolean | null;
  operational_mode: number | null;
  last_reported_on: string | null;
  health_sample_count: number;
  recent_samples: DeviceHealthSample[];
  battery_cycles: BatteryCycle[];
  operation_history: OperationSample[];
}

export interface FirmwareRead {
  id: string;
  firmware_version: string;
  device_type_id: number;
  device_type_name: string | null;
  firmware_filename: string;
  firmware_url: string;
  firmware_size: string | null;
  crc: string;
  release_date: string | null;
  release_notes: string | null;
  decommission_reason: string | null;
  status: FirmwareStatus;
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Alerts, incidents, notifications (Phase 2.7)
// ---------------------------------------------------------------------------

export interface AlertTypeRead {
  id: number;
  name: string;
  created_on: string;
  updated_on: string;
}

/** Severity lives on the alert; lifecycle status lives on the incident.
 *  They are separate entities and must not be conflated. */
export interface AlertRead {
  id: number;
  alert_type: number;
  alert_type_name: string | null;
  alert_severity: AlertSeverity | null;
  alert_data: Record<string, unknown> | null;
  device_id: string;
  device_uid: string | null;
  device_name: string | null;
  device_type_name: string | null;
  amenity_id: string;
  amenity_name: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  facility_id: string | null;
  created_on: string;
  updated_on: string;
}

export interface IncidentRead {
  id: string;
  subject: string | null;
  description: string | null;
  alert_type: number;
  alert_type_name: string | null;
  current_incident_status: number | null;
  status_name: string | null;
  facility_id: string;
  device_id: string;
  device_uid: string | null;
  device_name: string | null;
  amenity_id: string;
  amenity_name: string | null;
  latest_alert_id: number | null;
  latest_alert_severity: AlertSeverity | null;
  assignee: UserRef | null;
  updated_by_user: UserRef | null;
  created_on: string;
  updated_on: string;
}

export interface ValueAlertRead {
  id: string;
  device_id: string;
  device_uid: string | null;
  device_name: string;
  device_type_id: number;
  device_type_name: string | null;
  amenity_id: string;
  amenity_name: string | null;
  facility_id: string;
  limit_config_id: string;
  parameter: string | null;
  limit_type: string;
  limit_value: string;
  description: string;
  status: number;
  device_status_id: number;
  timestamp: string;
  created_on: string;
  updated_on: string;
}

/** Delivery metadata only. The backend withholds the rendered body/params,
 *  which can carry OTPs and keypad keys. */
export interface NotificationRead {
  id: number;
  status: NotificationStatus;
  created_by: string;
  template_id: string | null;
  template_name: string | null;
  template_type: NotificationChannel | null;
  reference_id: number | null;
  receiver_count: number;
  created_on: string;
  updated_on: string;
}

export interface NotificationTemplateRead {
  id: string;
  name: string;
  type: NotificationChannel;
  path: string;
  created_on: string;
  updated_on: string;
}

export interface ActivityRead {
  id: number;
  activity_type_id: number;
  activity_type_name: string | null;
  entity_type_id: number;
  entity_type_name: string | null;
  entity_id: number;
  facility_id: string;
  actor: UserRef | null;
  stay_id: string | null;
  data_version: number;
  activity_response_ids: string | null;
  notifier_count: number;
  unread_count: number;
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Occupancy & stays (Phase 2.8)
// ---------------------------------------------------------------------------

export interface AmenityStatusRead {
  id: number;
  amenity_status_name: string;
  created_on: string;
  updated_on: string;
}

export interface AmenityConditionRead {
  id: number;
  name: string;
  created_on: string;
  updated_on: string;
}

export interface CurrentStayRef {
  stay_id: string;
  internal_stay_ref_number: string;
  status: string | null;
  booker: UserRef | null;
  expected_checkout_time: string;
  actual_checkin_time: string | null;
  no_of_guests: number;
}

/** `status_name` is the real `amenity_status` row: Available, Occupied,
 *  Unavailable or Allotted -- four states, not two. */
export interface OccupancyRead {
  amenity_id: string;
  room_name: string;
  amenity_type_id: string;
  amenity_type_name: string | null;
  amenity_category: AmenityCategory | null;
  package_id: string;
  package_name: string | null;
  status: number | null;
  status_name: string | null;
  conditions: AmenityConditionRead[];
  facility_id: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  is_dnd: number | null;
  power_save_mode: number | null;
  current_stay: CurrentStayRef | null;
  allocation_count: number;
}

export interface OccupantRef {
  guest: UserRef;
  is_key_required: number | null;
}

export interface OccupancyDetail extends OccupancyRead {
  occupants: OccupantRef[];
  device_count: number;
}

export interface StayRead {
  id: string;
  internal_stay_ref_number: string;
  external_stay_ref_number: string | null;
  status: StayStatus | null;
  document_approval_status: DocumentApprovalStatus;
  request_source: RequestSource | null;
  booker: UserRef | null;
  no_of_rooms: number | null;
  no_of_guests: number;
  expected_checkin_time: string;
  expected_checkout_time: string;
  actual_checkin_time: string | null;
  actual_checkout_time: string | null;
  is_checked_in: boolean;
  is_in_house: boolean;
  gst: string | null;
  comments: string | null;
  checkout_initiated_by: string | null;
  occupant_count: number;
  room_count: number;
  created_on: string;
  updated_on: string;
}

export interface StayOccupantRead {
  id: string;
  guest: UserRef;
  room_id: string | null;
  room_name: string | null;
  is_key_required: number | null;
  status: number | null;
  created_on: string;
}

export interface RoomAllocationRead {
  id: string;
  stay_id: string;
  room_id: string;
  room_name: string | null;
  amenity_type_name: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  facility_id: string | null;
  package_id: string | null;
  package_name: string | null;
  status: number | null;
  created_on: string;
  updated_on: string;
}

export interface InvoiceRead {
  id: string;
  invoice_number: string;
  invoice_date: string;
  invoice_due_date: string | null;
  stay_id: string;
  stay_ref_number: string | null;
  billing_user_id: string;
  billing_user_name: string | null;
  billing_address: string | null;
  facility_id: string | null;
  facility_name: string | null;
  facility_address: string | null;
  net_amount: string | null;
  total_tax: string | null;
  total_amount: string | null;
  created_on: string;
  updated_on: string;
}

// ---------------------------------------------------------------------------
// Telemetry & energy (Phase 2.9)
// ---------------------------------------------------------------------------

export interface DeviceParamRead {
  id: number;
  param_name: string;
  device_type: number;
  device_type_name: string | null;
  device_short_code: string | null;
  data_type: string | null;
  unit: string | null;
  created_on: string;
  updated_on: string;
}

/** `device_param_value` is VARCHAR(500) in the database and is returned as
 *  stored. Interpret it with `data_type`; do not assume it is numeric. */
export interface DeviceStatRead {
  id: number;
  device_id: string;
  device_uid: string | null;
  device_name: string | null;
  device_type_name: string | null;
  amenity_id: string | null;
  amenity_name: string | null;
  facility_id: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  device_param_id: number;
  param_name: string | null;
  data_type: string | null;
  unit: string | null;
  device_param_value: string | null;
  timestamp: string;
  is_other_device: number | null;
  created_on: string;
}

export interface DeviceCurrentStatRead {
  id: string;
  device_id: string;
  device_uid: string | null;
  device_name: string | null;
  device_type_name: string | null;
  amenity_id: string | null;
  amenity_name: string | null;
  facility_id: string | null;
  device_stats: Record<string, unknown> | null;
  is_other_device: number | null;
  created_on: string;
  updated_on: string;
}

export interface OtherDeviceReadingRead {
  id: number;
  msg_id: string | null;
  device_name: string | null;
  voltage: number | null;
  current: number | null;
  power: number | null;
  power_factor: number | null;
  all_energy: number | null;
  thirty_day_energy: number | null;
  today_energy: number | null;
  current_hour_energy: number | null;
  ec: number | null;
  timestamp: string;
  created_on: string;
}

/** `energy_unit` is ALWAYS null: `energy_stat` stores no unit column.
 *  Never label these values kWh. */
export interface EnergyStatRead {
  device_name: string;
  facility_id: string;
  amenity_id: string;
  amenity_name: string | null;
  building_id: string | null;
  building_name: string | null;
  floor_id: string | null;
  floor_name: string | null;
  hour: number;
  hour_timestamp: string;
  energy_consumed: number;
  energy_unit: null;
  created_on: string;
  updated_on: string;
}

export interface EnergySummaryBucket {
  bucket: string;
  bucket_label: string | null;
  total_energy_consumed: number;
  reading_count: number;
}

/** SUM and COUNT only. No tariff, carbon factor, baseline or efficiency. */
export interface EnergySummaryRead {
  group_by: string;
  bucket_count: number;
  total_energy_consumed: number;
  reading_count: number;
  energy_unit: null;
  buckets: EnergySummaryBucket[];
}

export interface DailyDataPointRead {
  metric_date: string;
  metric_type: DailyMetricType;
  dp_1: string;
  dp_2: string;
  facility_id: string;
  created_on: string;
  updated_on: string;
}
