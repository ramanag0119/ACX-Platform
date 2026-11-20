/**
 * Pure presentation rules for the Integrations screens. No React, no I/O, so
 * every rule here is unit-tested (see ../__tests__/integrations.test.cjs).
 *
 * Two rules matter more than the rest:
 *
 *   1. NULL IS NOT ZERO. A metric the backend could not measure arrives as
 *      `null` beside a status of `not_available` / `not_observable`. It is
 *      shown as "Unavailable" / "Not currently observable", never as 0.
 *   2. UNKNOWN IS NOT DOWN. `not_observable` means the dashboard cannot see
 *      the component (e.g. the FIAS link state). It gets the neutral
 *      "unknown" tone, never the failure tone.
 */

import type { QueryParams } from "@/lib/api/client";
import {
  INTEGRATION_PROTOCOLS,
  MESSAGE_STATUSES,
  type IntegrationProtocol,
  type MessageStatus,
  type ReadinessBlock,
} from "@/lib/api/integrations";

export type Tone = "positive" | "warning" | "negative" | "neutral" | "unknown";

export interface StatusPresentation {
  label: string;
  tone: Tone;
}

/** Every status value the backend currently emits, with its label and tone. */
const STATUS: Record<string, StatusPresentation> = {
  // unknown / unmeasurable -- never rendered as healthy or failed
  not_observable: { label: "Not observable", tone: "unknown" },
  not_available: { label: "Unavailable", tone: "unknown" },
  not_reported: { label: "Not reported", tone: "unknown" },
  unknown: { label: "Unknown", tone: "unknown" },
  probe_failed: { label: "Check failed", tone: "unknown" },
  // transport
  disabled: { label: "Disabled", tone: "neutral" },
  enabled: { label: "Enabled", tone: "positive" },
  enabled_adapter_blocked: { label: "Enabled · awaiting vendor spec", tone: "warning" },
  connected: { label: "Connected", tone: "positive" },
  degraded: { label: "Degraded", tone: "warning" },
  connecting: { label: "Connecting", tone: "warning" },
  disconnected: { label: "Disconnected", tone: "negative" },
  closed: { label: "Closed", tone: "neutral" },
  // authentication
  configured: { label: "Configured", tone: "positive" },
  not_configured: { label: "Not configured", tone: "warning" },
  // processing
  idle: { label: "Idle · no backlog", tone: "positive" },
  backlog_within_threshold: { label: "Processing backlog", tone: "positive" },
  backlog_stalled: { label: "Backlog stalled", tone: "negative" },
  processing: { label: "Processing", tone: "positive" },
  waiting_for_retry: { label: "Waiting for scheduled retry", tone: "neutral" },
  queued_no_sender: { label: "Queued · no sender", tone: "warning" },
  // certification / validation / approvals
  passed: { label: "Passed (synthetic)", tone: "positive" },
  pending: { label: "Pending", tone: "warning" },
  validated: { label: "Validated", tone: "positive" },
  approved: { label: "Approved", tone: "positive" },
  // production readiness
  ready: { label: "Ready", tone: "positive" },
  not_ready: { label: "Not ready", tone: "negative" },
  // shared classification
  production_ready: { label: "Production ready", tone: "positive" },
  partially_ready: { label: "Partially ready", tone: "warning" },
  vendor_validation_pending: { label: "Vendor validation pending", tone: "warning" },
  // persistence
  ok: { label: "Provisioned", tone: "positive" },
  in_memory: { label: "Temporary storage", tone: "warning" },
  tables_missing: { label: "Storage not provisioned", tone: "negative" },
  database_unavailable: { label: "Storage unavailable", tone: "negative" },
  // adapters
  test_only: { label: "Test only", tone: "warning" },
  blocked: { label: "Blocked", tone: "negative" },
  // message processing
  PENDING: { label: "Pending", tone: "neutral" },
  PROCESSING: { label: "Processing", tone: "neutral" },
  SUCCEEDED: { label: "Processed", tone: "positive" },
  RETRY_WAIT: { label: "Awaiting retry", tone: "warning" },
  DEAD_LETTER: { label: "Failed", tone: "negative" },
};

/** Human label for an identifier the backend did not list above. */
export function humanize(value: string): string {
  const text = value.replace(/[_-]+/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1).toLowerCase() : value;
}

export function presentStatus(status: string | null | undefined): StatusPresentation {
  if (status === null || status === undefined || status === "") return STATUS.unknown;
  return STATUS[status] ?? { label: humanize(status), tone: "neutral" };
}

/** True when a block's status says its figures were actually measured. */
export function isUnmeasured(status: string | null | undefined): boolean {
  return status === "not_available" || status === "not_observable" || status === "not_reported";
}

/**
 * Text for a numeric metric. `null`/`undefined` NEVER becomes "0": the
 * caller's block status decides between "Not currently observable" and
 * "Unavailable".
 */
export function formatMetric(value: number | null | undefined, blockStatus?: string | null): string {
  if (value === null || value === undefined) {
    return blockStatus === "not_observable" ? "Not currently observable" : "Unavailable";
  }
  return value.toLocaleString();
}

/**
 * A timestamp. `measured` distinguishes "the backend looked and there is
 * none" (shown as "None recorded") from "the backend could not look".
 */
export function formatTimestamp(iso: string | null | undefined, measured = true): string {
  if (!iso) return measured ? "None recorded" : "Unavailable";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Unavailable";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Table timestamp: "20 Nov, 03:20 am", with the year only when it is not the
 * current one. Keeps wide tables readable; the full value is in `title`.
 */
export function formatShortTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleString(undefined, {
    ...(sameYear ? {} : { year: "numeric" }),
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Readable labels for production-readiness reason codes. */
const REASON_LABELS: Record<string, string> = {
  vendor_validation_pending: "Vendor validation pending",
  business_approval_pending: "Business approval pending",
  dba_schema_approval_pending: "DBA / schema approval pending",
  synthetic_certification_not_passed_or_not_reported: "Synthetic test results not published",
  integration_disabled: "Integration switched off",
  live_domain_writes_gated: "Live HMS updates switched off",
  transport_disabled: "Connection disabled",
  persistence_in_memory: "Message storage not provisioned",
  persistence_tables_missing: "Message storage not provisioned",
  persistence_database_unavailable: "Message storage unavailable",
};

export function reasonLabel(code: string): string {
  return REASON_LABELS[code] ?? humanize(code);
}

// ------------------------------------------------- business wording layer
/*
 * The backend reports identifiers (error codes, categories, message types,
 * reason strings). Operators see business wording instead; the identifier is
 * kept only where support needs it (data-* attributes), never as visible text.
 */

/** "stay.check_in" -> "Check-in"; "test.guest_arrival" -> "Guest arrival". */
const MESSAGE_TYPE_LABELS: Record<string, string> = {
  check_in: "Check-in",
  check_out: "Check-out",
  guest_arrival: "Guest arrival",
  guest_departure: "Guest departure",
  room_move: "Room move",
  stay_update: "Stay update",
};

export function messageTypeLabel(type: string | null | undefined): string {
  if (!type) return "Unknown type";
  const last = type.split(".").pop() ?? type;
  return MESSAGE_TYPE_LABELS[last] ?? humanize(last);
}

const FAILURE_LABELS: Record<string, string> = {
  hms_business_rule: "Rejected by HMS business rule",
  hms_unavailable: "HMS temporarily unavailable",
  stay_not_found: "Stay not found",
  stay_without_room: "Stay has no room assigned",
  stay_facility_mismatch: "Stay belongs to another facility",
  property_not_mapped: "Property is not mapped to a facility",
  property_mapping_disabled: "Property mapping is disabled",
  property_mapping_ambiguous: "Property maps to more than one facility",
  property_code_missing: "Property code missing",
  facility_unknown: "Unknown facility",
  facility_not_authorized: "Facility not authorised for this sender",
  authentication_failed: "Sender authentication failed",
  approval_required: "Awaiting business approval",
  vendor_specification_missing: "Awaiting vendor specification",
  unsupported_message: "Unsupported message type",
  validation_failed: "Message failed validation",
  missing_mandatory_fields: "Required fields missing",
  missing_required_elements: "Required fields missing",
  malformed_xml: "Malformed message",
  unsafe_xml: "Message rejected for safety",
  invalid_status_transition: "Invalid stay status change",
  idempotency_conflict: "Duplicate message with different content",
  transient_failure: "Temporary processing failure",
  permanent_failure: "Permanent processing failure",
  unexpected_error: "Unexpected processing error",
  connect_failed: "Could not connect",
  connect_timeout: "Connection timed out",
  read_timeout: "Read timed out",
  write_timeout: "Write timed out",
  connection_closed: "Connection closed",
  not_connected: "Not connected",
  soap_timeout: "Vendor did not respond in time",
  soap_fault_client: "Vendor rejected the request",
  soap_fault_server: "Vendor system error",
  lease_lost: "Processing interrupted",
};

/** Business wording for a failure / error code; "—" when there is none. */
export function failureLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return FAILURE_LABELS[code] ?? humanize(code);
}

const CATEGORY_LABELS: Record<string, string> = {
  permanent: "Permanent",
  transient: "Temporary",
  validation: "Validation",
  protocol: "Message format",
  security: "Security",
  conflict: "Conflict",
  unsupported: "Unsupported",
  vendor_blocked: "Awaiting vendor",
  approval_blocked: "Awaiting approval",
  lease_lost: "Interrupted",
};

export function failureCategoryLabel(category: string | null | undefined): string {
  if (!category) return "—";
  return CATEGORY_LABELS[category] ?? humanize(category);
}

const AUTH_FAILURE_LABELS: Record<string, string> = {
  invalid_secret: "Invalid credentials",
  secret_too_long: "Invalid credentials",
  missing_credentials: "Missing credentials",
  unknown_client: "Unknown sender",
  client_disabled: "Sender disabled",
  malformed_client_code: "Malformed sender code",
  protocol_not_permitted: "Protocol not permitted for sender",
  client_secret_misconfigured: "Sender misconfigured",
  no_client_store_configured: "Sender configuration unavailable",
};

export function authFailureLabel(reason: string): string {
  return AUTH_FAILURE_LABELS[reason] ?? humanize(reason);
}

export type StatusDimension = "transport" | "authentication" | "processing" | "outbound" | "messages" | "vendor";

/** Production-readiness blocker categories (backend `blocked_by`), in business wording. */
const BLOCKER_LABELS: Record<string, string> = {
  vendor_specification: "Vendor specification",
  business_approval: "Business approval",
  dba_approval: "DBA approval",
  infrastructure: "Infrastructure",
  certification_not_reported: "Test results not published",
  switched_off: "Switched off",
};

export function blockerLabel(category: string): string {
  return BLOCKER_LABELS[category] ?? humanize(category);
}

/**
 * Fixed, user-facing explanations keyed by dimension and status. Backend
 * reason strings describe runtimes and storage; they are not shown.
 */
const EXPLANATIONS: Record<string, string> = {
  "transport:not_observable": "Live link state is not reported to this dashboard, so it is shown as unknown rather than connected or disconnected.",
  "transport:disabled": "The integration is switched off.",
  "transport:enabled_adapter_blocked": "Switched on, but the vendor message specification has not been received.",
  "transport:degraded": "At least one link is not connected.",
  "transport:disconnected": "No link is connected.",
  "transport:connecting": "A link is being established.",
  "authentication:not_available": "Sender configuration cannot be read in this environment.",
  "authentication:not_configured": "No enabled sender or facility mapping is set up yet.",
  "authentication:configured": "Senders and facility mappings are configured.",
  "processing:backlog_stalled":
    "Messages are due for processing and the oldest has waited longer than the stall threshold; nothing appears to be processing them.",
  "processing:backlog_within_threshold": "Messages are due for processing, within the expected time.",
  "processing:idle": "No messages are waiting.",
  "processing:processing": "A worker is processing messages now.",
  "processing:waiting_for_retry": "Only retries scheduled for later are waiting; this is not a stall.",
  "outbound:idle": "No outbound messages are waiting.",
  "outbound:queued_no_sender": "Outbound messages are queued; no vendor delivery is configured yet, so they wait.",
  "outbound:backlog_stalled": "Outbound messages are due and the oldest has waited longer than the stall threshold.",
  "outbound:backlog_within_threshold": "Outbound messages are being delivered, within the expected time.",
  "outbound:waiting_for_retry": "Outbound deliveries are waiting for a scheduled retry.",
  "outbound:not_available": "Message storage is not available, so outbound delivery cannot be assessed.",
  "processing:not_available": "Message storage is not available, so processing cannot be assessed.",
  "processing:not_observable": "Processing state is not visible on this dashboard.",
  "messages:not_available": "Message storage is not available, so counts cannot be measured.",
  "messages:not_observable": "Message counts are not visible on this dashboard.",
  "vendor:pending": "Waiting for the vendor's official specification and validation.",
};

export function explainStatus(dimension: StatusDimension, status: string | null | undefined): string | null {
  return EXPLANATIONS[`${dimension}:${status ?? ""}`] ?? null;
}

/** Short explanation for a figure that could not be measured. */
export function unavailableExplanation(blockStatus: string | null | undefined): string {
  if (blockStatus === "not_observable") return "Not reported to this dashboard.";
  // The request itself failed (network / server error); nothing is known
  // about storage, so say only what happened.
  if (blockStatus === LOAD_FAILED) return "Could not be loaded right now.";
  return "Message storage is not available.";
}

/** Block status a screen passes when the request for the figures failed. */
export const LOAD_FAILED = "load_failed";

/** An adapter's specification, as an operator would describe it. */
export function specificationLabel(readiness: string, specification: string | null): string {
  if (readiness === "validated" || readiness === "approved") return "Vendor verified";
  if (!specification) return "Not received";
  if (readiness === "test_only") return "Test specification only";
  if (readiness === "blocked") return "Not received";
  return "Received";
}

/** Compact age: 45s, 12m, 3h 5m, 9d 14h. */
export function formatAge(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "Unavailable";
  const s = Math.max(0, Math.floor(seconds));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m`;
  const d = Math.floor(h / 24);
  return `${d}d ${h % 24}h`;
}

/** Sum of measured values; null as soon as any input is unmeasured. */
export function sumMeasured(values: (number | null | undefined)[]): number | null {
  let total = 0;
  for (const v of values) {
    if (v === null || v === undefined) return null;
    total += v;
  }
  return total;
}

export const PROTOCOL_META: Record<
  IntegrationProtocol,
  { label: string; family: string; transport: string; path: string }
> = {
  htng: { label: "HTNG", family: "SOAP/XML", transport: "SOAP/XML web service", path: "/integrations/htng" },
  fias: { label: "FIAS", family: "TCP", transport: "TCP socket link", path: "/integrations/fias" },
};

// ------------------------------------------------------------------ readiness
export interface ReadinessRow {
  key: string;
  label: string;
  status: string;
  /** Decision IDs or reasons that explain the status. */
  details: string[];
  note?: string;
}

/** The eight dimensions, in a fixed order, never merged into one verdict. */
export function readinessRows(r: ReadinessBlock): ReadinessRow[] {
  return [
    { key: "transport", label: "Transport", status: r.transport.status, details: [] },
    { key: "authentication", label: "Authentication", status: r.authentication.status, details: [] },
    { key: "processing", label: "Processing", status: r.processing.status, details: [] },
    {
      key: "synthetic_certification",
      label: "Synthetic certification",
      status: r.synthetic_certification.status ?? "unknown",
      details: [],
      // The backend's reason names the test harness location; operators get
      // a fixed explanation instead.
      note:
        r.synthetic_certification.status === "not_reported" || !r.synthetic_certification.status
          ? "Synthetic test results are not published to this dashboard. Synthetic tests are not vendor certification."
          : "Synthetic messages only; this is not vendor certification.",
    },
    {
      key: "vendor_validation",
      label: "Official vendor validation",
      status: r.vendor_validation.status,
      details: r.vendor_validation.pending_decisions,
      note: r.vendor_validation.note,
    },
    {
      key: "business_approval",
      label: "Business approval",
      status: r.business_approval.status,
      details: r.business_approval.pending_decisions,
    },
    {
      key: "dba_schema_approval",
      label: "DBA / schema approval",
      status: r.dba_schema_approval.status,
      details: r.dba_schema_approval.pending_decisions,
    },
    {
      key: "production_readiness",
      label: "Production readiness",
      status: r.production_readiness.status,
      details: r.production_readiness.reasons.map(reasonLabel),
    },
  ];
}

// ---------------------------------------------------------------- filters
export const PAGE_SIZES = [10, 20, 50, 100] as const;
/** The backend refuses a message-search window over 31 days (422). */
export const MAX_WINDOW_DAYS = 31;

export interface MessageFilters {
  protocol?: IntegrationProtocol;
  status?: MessageStatus;
  facilityId?: string;
  /** yyyy-mm-dd, local calendar day */
  from?: string;
  to?: string;
  page: number;
  pageSize: number;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DAY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Read filters from the URL, accepting ONLY values the backend accepts.
 * Anything else is dropped rather than sent (it would only answer 422).
 */
export function parseFilters(search: URLSearchParams, defaultPageSize = 20): MessageFilters {
  const protocol = search.get("protocol");
  const status = search.get("status");
  const facility = search.get("facility");
  const from = search.get("from");
  const to = search.get("to");
  const page = Number.parseInt(search.get("page") ?? "", 10);
  const size = Number.parseInt(search.get("size") ?? "", 10);
  return {
    protocol: (INTEGRATION_PROTOCOLS as readonly string[]).includes(protocol ?? "")
      ? (protocol as IntegrationProtocol)
      : undefined,
    status: (MESSAGE_STATUSES as readonly string[]).includes(status ?? "") ? (status as MessageStatus) : undefined,
    facilityId: facility && UUID.test(facility) ? facility : undefined,
    from: from && DAY.test(from) ? from : undefined,
    to: to && DAY.test(to) ? to : undefined,
    page: Number.isFinite(page) && page >= 1 ? page : 1,
    pageSize: (PAGE_SIZES as readonly number[]).includes(size) ? size : defaultPageSize,
  };
}

/** The inverse of parseFilters, omitting defaults to keep URLs short. */
export function filtersToSearch(f: MessageFilters, defaultPageSize = 20): Record<string, string> {
  const out: Record<string, string> = {};
  if (f.protocol) out.protocol = f.protocol;
  if (f.status) out.status = f.status;
  if (f.facilityId) out.facility = f.facilityId;
  if (f.from) out.from = f.from;
  if (f.to) out.to = f.to;
  if (f.page > 1) out.page = String(f.page);
  if (f.pageSize !== defaultPageSize) out.size = String(f.pageSize);
  return out;
}

function startOfDay(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d, 0, 0, 0, 0);
}

function endOfDay(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d, 23, 59, 59, 999);
}

/**
 * A client-side check that mirrors the backend's rules, so the user sees the
 * problem next to the inputs instead of a 422. The backend still enforces it.
 */
export function validateDateRange(from?: string, to?: string, maxDays: number | null = MAX_WINDOW_DAYS): string | null {
  if (!from || !to) return null;
  const start = startOfDay(from);
  const end = endOfDay(to);
  if (end < start) return "The end date is before the start date.";
  if (maxDays !== null && end.getTime() - start.getTime() > maxDays * 24 * 3600 * 1000) {
    return `The date range may not exceed ${maxDays} days.`;
  }
  return null;
}

/**
 * Server query params. Dates go out as ISO-8601 instants (UTC, with offset),
 * which is what the backend requires; omitted dates use the backend default
 * window (messages: last 7 days; DLQ: everything).
 */
export function toQueryParams(f: MessageFilters, opts: { withStatus?: boolean } = {}): QueryParams {
  const withStatus = opts.withStatus ?? true;
  const params: QueryParams = {
    page: f.page,
    page_size: Math.min(Math.max(1, f.pageSize), 100),
    protocol: f.protocol,
    facility_id: f.facilityId,
    received_from: f.from ? startOfDay(f.from).toISOString() : undefined,
    received_to: f.to ? endOfDay(f.to).toISOString() : undefined,
  };
  if (withStatus) params.status = f.status;
  return params;
}

// --------------------------------------------------------------- facilities
export interface FacilityOption {
  id: string;
  label: string;
}

/**
 * Filter choices: ONLY the facilities in the signed-in user's scope. A scoped
 * facility the facility list did not return still appears (by short id), so
 * the scope, not the list, decides what may be chosen.
 */
export function facilityOptions(
  facilities: { id: string; name: string }[],
  scopeIds: string[],
): FacilityOption[] {
  const names = new Map(facilities.map((f) => [f.id, f.name]));
  return [...new Set(scopeIds)]
    .map((id) => ({ id, label: names.get(id) ?? `Facility ${id.slice(0, 8)}` }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Drop a facility filter that is outside the user's scope (e.g. typed into
 * the URL) instead of sending it: the backend would answer 403, and the UI
 * must never ask for another facility's data in the first place.
 */
export function restrictToScope(filters: MessageFilters, scopeIds: string[]): MessageFilters {
  if (!filters.facilityId || scopeIds.includes(filters.facilityId)) return filters;
  return { ...filters, facilityId: undefined };
}

export function facilityLabel(id: string, names: Map<string, string>): string {
  return names.get(id) ?? `Facility ${id.slice(0, 8)}`;
}

// ------------------------------------------------------------ monitoring metrics
export const RANGE_LABELS: Record<string, string> = {
  "1h": "Last hour",
  "24h": "Last 24 hours",
  "7d": "Last 7 days",
  "30d": "Last 30 days",
};

/** Short label for a chart bucket: time of day for sub-day buckets, date otherwise. */
export function formatBucket(iso: string, bucketSeconds: number): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return bucketSeconds < 86400
    ? d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}

/** 0.42 s -> "420 ms", 3.2 s -> "3.2 s", 125 s -> "2m 5s". null stays "Unavailable". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "Unavailable";
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  return formatAge(seconds);
}

/** 0.6667 -> "66.7%". null (nothing completed) is not 0 %. */
export function formatPercent(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined || Number.isNaN(ratio)) return "No completed messages";
  return `${(ratio * 100).toFixed(1)}%`;
}

/** Plain-language names for the backend's `unavailable[].metric` keys. */
const UNAVAILABLE_LABELS: Record<string, string> = {
  retry_attempt_timeline: "Retry attempts over time",
  processing_latency: "Worker processing time",
  rejected_intake: "Rejected messages (before storage)",
  worker_health: "Worker health",
  endpoint_availability_history: "SOAP endpoint availability history",
  connection_history: "Connection history",
  ack_statistics: "ACK / NAK statistics",
  timeout_statistics: "Timeout statistics",
  parse_failures: "Parse / framing failures",
};

export function unavailableLabel(metric: string): string {
  return UNAVAILABLE_LABELS[metric] ?? humanize(metric);
}
