import type { ReactNode } from "react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { IntegrationProtocol, ProtocolEntry } from "@/lib/api/integrations";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import { CountValue, DetailRow } from "../components/Metric";
import { Muted, Panel, PanelLink } from "../components/Panel";
import { LastErrorText } from "../components/ProtocolCard";
import { ReadinessPanel } from "../components/ReadinessPanel";
import { StatusBadge, StatusItem } from "../components/StatusBadge";
import {
  PROTOCOL_META,
  authFailureLabel,
  explainStatus,
  failureCategoryLabel,
  failureLabel,
  formatAge,
  formatShortTimestamp,
  formatTimestamp,
  humanize,
  specificationLabel,
} from "../lib/presentation";

/** Counter chips (e.g. rejections by category) in business wording. */
const CounterList = ({
  counters,
  label,
}: {
  counters: Record<string, number> | null;
  label: (key: string) => string;
}) => {
  const { textMuted } = useSurfaceTokens();
  if (counters === null) return <span className="text-xs" style={{ color: textMuted }}>Not currently observable</span>;
  const entries = Object.entries(counters);
  if (!entries.length) return <span className="text-xs" style={{ color: textMuted }}>None recorded</span>;
  return (
    <span className="flex flex-wrap justify-end gap-1.5">
      {entries.map(([k, v]) => (
        <span key={k} className="rounded-md bg-muted px-1.5 py-0.5 text-[11px]">
          {label(k)}: {v}
        </span>
      ))}
    </span>
  );
};

const Note = ({ children }: { children: ReactNode }) => <Muted className="mt-3">{children}</Muted>;

/**
 * Pure view of one protocol. HTNG and FIAS share this structure section for
 * section:
 *
 *   dashboard slot   windowed KPIs and charts (GET /observability/metrics),
 *                    built by the page because it owns the time-range filter
 *   1 transport and integration health (current state, from the overview)
 *   2 connection   3 authentication   4 processing
 *   5 recent messages   6 failed messages   7 vendor validation   8 readiness
 *
 * Recent messages and failed-message rows come from their own queries and are
 * passed in as slots.
 */
export const ProtocolView = ({
  protocol,
  entry,
  dashboard,
  recentMessages,
  deadLetters,
}: {
  protocol: IntegrationProtocol;
  entry: ProtocolEntry;
  dashboard?: ReactNode;
  recentMessages: ReactNode;
  deadLetters: ReactNode;
}) => {
  const meta = PROTOCOL_META[protocol];
  const t = entry.transport;
  const auth = entry.authentication;
  const proc = entry.processing;
  const out = entry.outbound_processing;
  const m = entry.messages;
  const measured = m.status === "measured";
  const vendor = entry.readiness.vendor_validation;
  const sid = (s: string) => `${protocol}-${s}`;
  const rejections = entry.intake_rejections;

  return (
    <div className="space-y-4">
      {dashboard}

      {/* 1. Current health: four dimensions, kept separate. */}
      <Panel id={sid("status")} title="Transport and integration health"
        description={`${meta.transport} · current state, not limited to the selected period`}>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatusItem label="Connection" status={t.status} explanation={explainStatus("transport", t.status)} />
          <StatusItem label="Authentication" status={auth.status} explanation={explainStatus("authentication", auth.status)} />
          <StatusItem label="Processing" status={proc.status} explanation={explainStatus("processing", proc.status)} />
          <StatusItem label="Vendor validation" status={vendor.status} explanation={explainStatus("vendor", vendor.status)} />
        </div>
      </Panel>

      {/* 2-4. Operational health. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel id={sid("connection")} title="Connection" description={meta.transport}>
          <dl className="divide-y divide-border/60">
            <DetailRow label="Status"><StatusBadge status={t.status} /></DetailRow>
            {protocol === "htng" ? (
              <>
                <DetailRow label="Integration"><span className="text-xs">{t.integration_enabled ? "Switched on" : "Switched off"}</span></DetailRow>
                <DetailRow label="Inbound endpoint"><span className="text-xs">{t.inbound_endpoint_enabled ? "Enabled" : "Disabled"}</span></DetailRow>
                <DetailRow label="Vendor endpoint (outbound)"><span className="text-xs">{humanize(t.outbound_vendor_endpoint ?? "unknown")}</span></DetailRow>
                <DetailRow label="Availability history">
                  <span className="text-xs text-muted-foreground" title="Endpoint availability is not probed or recorded over time.">Not recorded</span>
                </DetailRow>
              </>
            ) : (
              <>
                <DetailRow label="Active connections"><CountValue value={t.active_connections} blockStatus={t.status} /></DetailRow>
                <DetailRow label="Links">
                  {t.links ? <span className="text-xs">{t.links.length}</span> : <CountValue value={null} blockStatus="not_observable" />}
                </DetailRow>
                <DetailRow label="Connection history">
                  <span className="text-xs text-muted-foreground" title="Connect / disconnect events are not persisted.">Not recorded</span>
                </DetailRow>
                <DetailRow label="ACK / heartbeat">
                  <span className="text-xs text-muted-foreground" title="Not implemented: the FIAS link rules are not specified (HF-06).">Not implemented (HF-06)</span>
                </DetailRow>
              </>
            )}
          </dl>
          {protocol === "fias" && t.links && t.links.length ? (
            <div className="mt-3 overflow-x-auto">
              <Table aria-label="FIAS links">
                <TableHeader>
                  <TableRow>
                    <TableHead className="whitespace-nowrap text-xs">Link</TableHead>
                    <TableHead className="whitespace-nowrap text-xs">State</TableHead>
                    <TableHead className="whitespace-nowrap text-xs">Connected since</TableHead>
                    <TableHead className="whitespace-nowrap text-xs">Last error</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {t.links.map((l) => (
                    <TableRow key={l.name}>
                      <TableCell className="whitespace-nowrap text-xs">{l.name}</TableCell>
                      <TableCell><StatusBadge status={l.state} /></TableCell>
                      <TableCell className="whitespace-nowrap text-xs" title={l.connected_since ? formatTimestamp(l.connected_since) : undefined}>
                        {formatShortTimestamp(l.connected_since)}
                      </TableCell>
                      <TableCell className="text-xs" data-error-code={l.last_error_code ?? undefined}>{failureLabel(l.last_error_code)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : null}
        </Panel>

        <Panel id={sid("auth")} title="Authentication" description="Senders and facility mappings">
          <dl className="divide-y divide-border/60">
            <DetailRow label="Status"><StatusBadge status={auth.status} /></DetailRow>
            <DetailRow label="Active senders"><CountValue value={auth.enabled_clients} blockStatus={auth.status} /></DetailRow>
            <DetailRow label="Facility mappings"><CountValue value={auth.enabled_mappings} blockStatus={auth.status} /></DetailRow>
            <DetailRow label="Rejected messages">
              <CounterList counters={rejections.rejected_by_category} label={failureCategoryLabel} />
            </DetailRow>
            <DetailRow label="Sign-in failures">
              <CounterList counters={rejections.auth_failures_by_reason} label={authFailureLabel} />
            </DetailRow>
          </dl>
          <Note>
            {explainStatus("authentication", auth.status) ?? "Counts cover your facilities only."}{" "}
            {rejections.status === "observed"
              ? "Rejections are counted since the service last started."
              : "Rejections are not visible on this dashboard."}
          </Note>
        </Panel>

        <Panel id={sid("processing")} title="Processing" description="Inbound backlog and outbound delivery">
          <dl className="divide-y divide-border/60">
            <DetailRow label="Status"><StatusBadge status={proc.status} /></DetailRow>
            {proc.classification === "due_work" ? (
              <>
                <DetailRow label="Due now"><CountValue value={proc.due_now} blockStatus={proc.status} /></DetailRow>
                <DetailRow label="Oldest due wait">
                  <span className="text-xs">{proc.due_now ? formatAge(proc.oldest_due_age_seconds) : "Nothing due"}</span>
                </DetailRow>
                <DetailRow label="Retries scheduled later"><CountValue value={proc.scheduled} blockStatus={proc.status} /></DetailRow>
                <DetailRow label="Being processed"><CountValue value={proc.in_progress} blockStatus={proc.status} /></DetailRow>
                {proc.ordering_blocked ? (
                  <DetailRow label="Held behind a failed message"><CountValue value={proc.ordering_blocked} blockStatus={proc.status} /></DetailRow>
                ) : null}
              </>
            ) : (
              <DetailRow label="Oldest pending message">
                <span className="text-xs">
                  {proc.oldest_pending_age_seconds === null && proc.status !== "not_available"
                    ? "No backlog"
                    : formatAge(proc.oldest_pending_age_seconds)}
                </span>
              </DetailRow>
            )}
            <DetailRow label="Stall threshold"><span className="text-xs">{formatAge(proc.stall_threshold_seconds)}</span></DetailRow>
            <DetailRow label="Worker activity">
              {proc.worker_heartbeat.observed ? <span className="text-xs">Reported</span> : <CountValue value={null} blockStatus="not_observable" />}
            </DetailRow>
          </dl>
          {out ? (
            <dl className="mt-3 divide-y divide-border/60 border-t border-border/60" data-outbound-status={out.status}>
              <DetailRow label="Outbound delivery"><StatusBadge status={out.status} /></DetailRow>
              <DetailRow label="Vendor delivery">
                <span className="text-xs" title={out.sender_reason ?? undefined}>{out.sender_configured ? "Configured" : "Not configured"}</span>
              </DetailRow>
              <DetailRow label="Queued outbound"><CountValue value={out.unfinished} blockStatus={out.status} /></DetailRow>
            </dl>
          ) : null}
          <Note>
            {explainStatus("processing", proc.status) ?? ""}{" "}
            {out && !out.sender_configured && out.sender_reason ? `${out.sender_reason} ` : ""}
            Worker activity is not reported to this dashboard, so &ldquo;not currently observable&rdquo; means
            unknown, not stopped.
          </Note>
        </Panel>
      </div>

      {/* 6. Recent messages. */}
      <Panel
        id={sid("recent")}
        title="Recent messages"
        description="Latest inbound messages, newest first"
        actions={<PanelLink to={`/integrations/messages?protocol=${protocol}`}>All {meta.label} messages</PanelLink>}
      >
        {recentMessages}
      </Panel>

      {/* 7. Failed messages. */}
      <Panel
        id={sid("failed")}
        title="Failed messages"
        description="Messages moved to the dead-letter queue (DLQ)"
        actions={<PanelLink to={`/integrations/dlq?protocol=${protocol}`}>{meta.label} failed messages</PanelLink>}
      >
        <dl className="mb-3 border-b border-border/60">
          <DetailRow label="Latest failure"><LastErrorText error={entry.last_error} measured={measured} /></DetailRow>
        </dl>
        {deadLetters}
      </Panel>

      {/* 8-9. Vendor validation and readiness. */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Panel id={sid("vendor")} title="Vendor validation" description={vendor.note}>
          <ul className="divide-y divide-border/60" aria-label={`${meta.label} message adapters`}>
            {entry.configuration.adapters.map((a) => (
              <li key={`${a.direction}-${a.specification}`} className="flex flex-wrap items-center justify-between gap-2 py-2.5" data-adapter={a.direction}>
                <span className="min-w-0">
                  <span className="block text-sm text-foreground">{humanize(a.direction)} messages</span>
                  <span className="block text-xs text-muted-foreground">
                    Specification: {specificationLabel(a.readiness, a.specification)}
                    {a.blocking_decisions.length ? ` · Waiting on ${a.blocking_decisions.join(", ")}` : ""}
                  </span>
                </span>
                <StatusBadge status={a.readiness} />
              </li>
            ))}
          </ul>
          <dl className="mt-1 border-t border-border/60">
            <DetailRow label="Status"><StatusBadge status={vendor.status} /></DetailRow>
            <DetailRow label="Pending decisions">
              <span className="text-xs">{vendor.pending_decisions.join(", ") || "None"}</span>
            </DetailRow>
          </dl>
        </Panel>

        <ReadinessPanel id={sid("readiness")} readiness={entry.readiness} title={`${meta.label} readiness`} />
      </div>
    </div>
  );
};
