/**
 * HTNG / FIAS integration observability API client (read-only).
 *
 *   GET /integrations/observability/overview   dashboard model, HTNG + FIAS + shared
 *   GET /integrations/observability/messages   inbound message metadata, paginated
 *   GET /integrations/observability/dlq        dead letters, paginated
 *
 * Contract source: backend/app/integrations/observability.py and
 * api/router.py (see docs/HTNG_FIAS_OBSERVABILITY_API_DESIGN.md). The backend
 * gates all three on `facility_management` read and scopes every figure to
 * the caller's facilities.
 *
 * THE NULL RULE. The backend returns `null` (with a `status` such as
 * `not_available` / `not_observable` and a `reason`) for anything it cannot
 * measure. Those nulls are typed as nulls here and must never be coerced to 0
 * by a screen: 0 means "measured, and there are none".
 *
 * No payloads, client codes, credentials or guest data exist in these
 * responses; nothing here asks for them.
 */

import { apiClient, type QueryParams } from "./client";
import type { Page } from "./types";

export type IntegrationProtocol = "htng" | "fias";
export const INTEGRATION_PROTOCOLS: readonly IntegrationProtocol[] = ["htng", "fias"];

/** Inbound processing statuses the message search accepts as a filter. */
export const MESSAGE_STATUSES = [
  "PENDING",
  "PROCESSING",
  "SUCCEEDED",
  "RETRY_WAIT",
  "DEAD_LETTER",
] as const;
export type MessageStatus = (typeof MESSAGE_STATUSES)[number];

/** Error code + category only; the backend redacts anything not identifier-shaped. */
export interface SanitizedError {
  code: string | null;
  category: string | null;
}

export interface AdapterState {
  direction: string;
  readiness: string;
  specification: string | null;
  blocking_decisions: string[];
}

export interface FiasLinkState {
  name: string;
  state: string;
  connected_since: string | null;
  connections: number | null;
  reconnect_attempts: number | null;
  frames_received: number | null;
  framing_errors: number | null;
  last_error_code: string | null;
  last_error_at: string | null;
}

/** HTNG and FIAS transports share `kind` / `status`; the rest is per protocol. */
export interface TransportBlock {
  kind: string;
  status: string;
  reason?: string;
  scope?: string;
  // HTNG (http-soap inbound endpoint)
  integration_enabled?: boolean;
  inbound_endpoint_enabled?: boolean;
  outbound_vendor_endpoint?: string;
  // FIAS (tcp link)
  links?: FiasLinkState[] | null;
  active_connections?: number | null;
}

export interface AuthenticationBlock {
  status: string;
  reason?: string | null;
  scope?: string;
  enabled_clients: number | null;
  enabled_mappings: number | null;
}

export interface WorkerHeartbeat {
  scope: string;
  observed: boolean;
  last: Record<string, string | null>;
}

export interface ProcessingBlock {
  status: string;
  reason?: string | null;
  basis?: string;
  /** "due_work" (backlog breakdown available) or "received_age" (fallback). */
  classification?: string;
  oldest_pending_age_seconds: number | null;
  stall_threshold_seconds: number;
  worker_heartbeat: WorkerHeartbeat;
  /** Unfinished messages whose next attempt time has passed. */
  due_now?: number | null;
  /** Unfinished messages waiting for a FUTURE retry time. */
  scheduled?: number | null;
  /** Messages under a live worker lease. */
  in_progress?: number | null;
  /** Messages held behind an earlier dead-lettered message of the same stay. */
  ordering_blocked?: number | null;
  oldest_due_age_seconds?: number | null;
}

/** Outbound (outbox) delivery state; the relay itself is in another process. */
export interface OutboundProcessingBlock {
  status: string;
  reason?: string | null;
  sender_configured: boolean;
  sender_reason: string | null;
  relay_heartbeat_observed: boolean;
  unfinished: number | null;
  due_now: number | null;
  scheduled: number | null;
  oldest_due_age_seconds: number | null;
  stall_threshold_seconds: number;
}

export interface DirectionCounts {
  total: number;
  by_status: Record<string, number>;
  pending: number;
  retry_wait: number;
  failed_dead_letter: number;
  /** inbound only */
  succeeded?: number;
  /** outbound only */
  sent?: number;
}

export interface MessagesBlock {
  status: "measured" | "not_available" | string;
  reason?: string | null;
  /** "retained_rows": counts are over rows still held, not lifetime totals. */
  basis?: string;
  inbound: DirectionCounts | null;
  outbound: DirectionCounts | null;
  retried_messages: number | null;
  extra_attempts: number | null;
  last_received_at: string | null;
  last_succeeded_at: string | null;
  last_outbound_sent_at: string | null;
}

export interface LastErrorBlock {
  message_id: string;
  status: string;
  error: SanitizedError | null;
  received_at: string | null;
  dead_lettered_at: string | null;
}

export interface IntakeRejectionsBlock {
  status: string;
  reason?: string;
  scope?: string;
  rejected_by_category: Record<string, number> | null;
  auth_failures_by_reason: Record<string, number> | null;
}

export interface ReadinessBlock {
  transport: { status: string };
  authentication: { status: string };
  processing: { status: string };
  synthetic_certification: { status: string | null; reason?: string; scope: string };
  vendor_validation: {
    status: string;
    adapter_readiness: string[];
    pending_decisions: string[];
    blocking_decisions: string[];
    note: string;
  };
  business_approval: {
    status: string;
    pending_decisions: string[];
    live_domain_writes: { open: boolean; blocking: string[] };
  };
  dba_schema_approval: { status: string; pending_decisions: string[]; persistence: string };
  production_readiness: { status: string; reasons: string[]; blocked_by?: string[] };
}

export interface ProtocolEntry {
  protocol: IntegrationProtocol;
  configuration: { adapters: AdapterState[] };
  transport: TransportBlock;
  authentication: AuthenticationBlock;
  processing: ProcessingBlock;
  outbound_processing?: OutboundProcessingBlock;
  messages: MessagesBlock;
  last_error: LastErrorBlock | null;
  intake_rejections: IntakeRejectionsBlock;
  readiness: ReadinessBlock;
}

export interface ProtocolSummary {
  transport: string;
  processing: string;
  vendor_validation: string;
  production_readiness: string;
}

export interface SharedMessages {
  status: string;
  reason?: string | null;
  basis?: string;
  protocols_counted?: string[];
  processed: number | null;
  pending: number | null;
  failed_dead_letter: number | null;
  outbound_dead_letter: number | null;
  last_successful_exchange_at: string | null;
}

export interface IntegrationOverview {
  generated_at: string;
  facility_scope: string;
  overview: {
    htng_status: ProtocolSummary;
    fias_status: ProtocolSummary;
    readiness_classification: string;
    messages: SharedMessages;
  };
  protocols: Record<IntegrationProtocol, ProtocolEntry>;
  other_protocols: string[];
}

export interface IntegrationMessage {
  message_id: string;
  protocol: string;
  facility_id: string;
  direction: string;
  message_type: string;
  status: string;
  received_at: string | null;
  /** When the message reached SUCCEEDED or DEAD_LETTER. */
  completed_at: string | null;
  attempt_count: number;
  retry_count: number;
  max_attempts: number;
  next_attempt_at: string | null;
  correlation_id: string;
  error: SanitizedError | null;
}

export interface DeadLetterEntry {
  message_id: string;
  protocol: string;
  facility_id: string;
  direction: string;
  message_type: string;
  status: string;
  failure_category: string | null;
  failure_code: string | null;
  attempt_count: number;
  retry_count: number;
  received_at: string | null;
  last_attempt_at: string | null;
  correlation_id: string;
  redrive: { state_eligible: boolean; caller_has_permission: boolean; eligible: boolean };
}

/** The HMS `Page` envelope plus the date window the backend applied. */
export interface IntegrationPage<T> extends Page<T> {
  window: { received_from: string; received_to: string };
}

export const getIntegrationOverview = (signal?: AbortSignal) =>
  apiClient.get<IntegrationOverview>("/integrations/observability/overview", undefined, signal);

export const searchIntegrationMessages = (params: QueryParams, signal?: AbortSignal) =>
  apiClient.get<IntegrationPage<IntegrationMessage>>(
    "/integrations/observability/messages",
    params,
    signal,
  );

export const listIntegrationDeadLetters = (params: QueryParams, signal?: AbortSignal) =>
  apiClient.get<IntegrationPage<DeadLetterEntry>>("/integrations/observability/dlq", params, signal);

// ------------------------------------------------------------------ metrics
/** GET /observability/metrics windows (span / bucket fixed by the backend). */
export const METRIC_RANGES = ["1h", "24h", "7d", "30d"] as const;
export type MetricRange = (typeof METRIC_RANGES)[number];

export interface MetricsBucket {
  bucket_start: string;
  /** messages RECEIVED in the bucket (intake time) */
  received: number;
  /** messages COMPLETED successfully in the bucket */
  processed: number;
  /** messages DEAD-LETTERED in the bucket */
  failed: number;
  /** messages received in the bucket that needed more than one attempt */
  retried_received: number;
  outbound_created: number;
  outbound_sent: number;
  /** mean intake-to-completion seconds of the bucket's completions; null = none */
  avg_latency_seconds: number | null;
}

export interface MetricsKpis {
  inbound_total: number;
  processed: number;
  failed: number;
  queued: number;
  awaiting_retry: number;
  /** processed / (processed + failed); null when nothing completed */
  success_rate: number | null;
  retried_messages: number;
  extra_attempts: number;
  outbound_total: number;
  outbound_sent: number;
  outbound_queued: number;
  outbound_failed: number;
}

export interface StatusShare {
  status: string;
  count: number;
  share: number | null;
}

export interface IntegrationMetrics {
  protocol: IntegrationProtocol;
  status: "measured" | "not_available" | string;
  reason?: string;
  generated_at: string;
  facility_scope: string;
  window: { range: MetricRange; from: string; to: string; bucket_seconds: number; tz_offset_minutes: number };
  basis: "retained_rows" | string;
  retention_days: number | null;
  kpis: MetricsKpis | null;
  series: MetricsBucket[];
  status_distribution: { inbound: StatusShare[]; outbound: StatusShare[] } | null;
  latency: {
    basis: string;
    scope: string;
    count: number;
    avg: number | null;
    p50: number | null;
    p95: number | null;
    max: number | null;
  } | null;
  errors: { category: string | null; code: string | null; count: number }[] | null;
  message_types: { message_type: string | null; count: number }[] | null;
  /** Metrics the data cannot support, with the reason (never shown as zero). */
  unavailable: { metric: string; reason: string }[];
}

export const getIntegrationMetrics = (params: QueryParams, signal?: AbortSignal) =>
  apiClient.get<IntegrationMetrics>("/integrations/observability/metrics", params, signal);
