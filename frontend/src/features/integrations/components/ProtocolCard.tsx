import type { IntegrationProtocol, LastErrorBlock, ProtocolEntry } from "@/lib/api/integrations";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import {
  PROTOCOL_META,
  explainStatus,
  failureCategoryLabel,
  failureLabel,
  formatShortTimestamp,
  formatTimestamp,
  sumMeasured,
} from "../lib/presentation";
import { CountValue, DetailRow } from "./Metric";
import { Panel, PanelLink } from "./Panel";
import { StatusBadge } from "./StatusBadge";

/** "Rejected by HMS business rule · Permanent · 10 Nov, 08:02" -- business wording only. */
export const LastErrorText = ({ error, measured }: { error: LastErrorBlock | null; measured: boolean }) => {
  const { textMuted } = useSurfaceTokens();
  if (!error) {
    return (
      <span className="text-xs" style={{ color: textMuted }}>
        {measured ? "None recorded" : "Unavailable"}
      </span>
    );
  }
  const category = error.error?.category;
  const when = error.dead_lettered_at ?? error.received_at;
  return (
    <span className="inline-flex flex-col items-end gap-0.5 text-right" data-error-code={error.error?.code ?? undefined}>
      <span className="text-sm text-foreground">{failureLabel(error.error?.code ?? "unexpected_error")}</span>
      <span className="text-xs" style={{ color: textMuted }} title={when ? formatTimestamp(when) : undefined}>
        {category ? `${failureCategoryLabel(category)} · ` : ""}
        {formatShortTimestamp(when)}
      </span>
    </span>
  );
};

/**
 * One protocol's health on the Overview. Every figure comes from
 * GET /integrations/observability/overview; nothing is derived except the
 * DLQ total (inbound + outbound), which stays unavailable if either side is.
 */
export const ProtocolHealthPanel = ({ protocol, entry }: { protocol: IntegrationProtocol; entry: ProtocolEntry }) => {
  const { textMuted } = useSurfaceTokens();
  const meta = PROTOCOL_META[protocol];
  const m = entry.messages;
  const measured = m.status === "measured";
  const vendor = entry.readiness.vendor_validation;
  const notes = [
    explainStatus("transport", entry.transport.status),
    measured ? null : explainStatus("messages", m.status),
  ].filter((n): n is string => Boolean(n));

  return (
    <Panel
      id={`integration-health-${protocol}`}
      title={`${meta.label} health`}
      description={meta.transport}
      data-protocol={protocol}
      actions={<StatusBadge status={entry.readiness.production_readiness.status} title="Production readiness" />}
    >
      <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
        <dl className="divide-y divide-border/60">
          <DetailRow label="Connection"><StatusBadge status={entry.transport.status} /></DetailRow>
          <DetailRow label="Authentication"><StatusBadge status={entry.authentication.status} /></DetailRow>
          <DetailRow label="Processing"><StatusBadge status={entry.processing.status} /></DetailRow>
          <DetailRow label="Vendor validation"><StatusBadge status={vendor.status} /></DetailRow>
          <DetailRow label="Last successful processing">
            <span className="whitespace-nowrap text-xs" title={m.last_succeeded_at ? formatTimestamp(m.last_succeeded_at) : undefined}>
              {m.last_succeeded_at ? formatShortTimestamp(m.last_succeeded_at) : formatTimestamp(null, measured)}
            </span>
          </DetailRow>
        </dl>
        <dl className="divide-y divide-border/60 border-t border-border/60 sm:border-t-0">
          <DetailRow label="Inbound"><CountValue value={m.inbound?.total} blockStatus={m.status} /></DetailRow>
          <DetailRow label="Outbound"><CountValue value={m.outbound?.total} blockStatus={m.status} /></DetailRow>
          <DetailRow label="Pending"><CountValue value={m.inbound?.pending} blockStatus={m.status} /></DetailRow>
          <DetailRow label="Awaiting retry"><CountValue value={m.inbound?.retry_wait} blockStatus={m.status} /></DetailRow>
          <DetailRow label="Failed (DLQ)">
            <CountValue
              value={sumMeasured([m.inbound?.failed_dead_letter, m.outbound?.failed_dead_letter])}
              blockStatus={m.status}
            />
          </DetailRow>
        </dl>
      </div>
      <dl className="border-t border-border/60">
        <DetailRow label="Latest failure"><LastErrorText error={entry.last_error} measured={measured} /></DetailRow>
      </dl>
      {notes.length ? (
        <ul className="mt-2 space-y-1">
          {notes.map((n) => (
            <li key={n} className="text-xs leading-5" style={{ color: textMuted }}>{n}</li>
          ))}
        </ul>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <PanelLink to={meta.path}>{meta.label} monitoring</PanelLink>
        <PanelLink to={`/integrations/messages?protocol=${protocol}`}>{meta.label} message logs</PanelLink>
      </div>
    </Panel>
  );
};
