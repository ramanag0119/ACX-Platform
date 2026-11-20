import type { ReactNode } from "react";
import { AlertTriangle, ArrowDownToLine, ArrowUpFromLine, Clock, Inbox, RotateCcw } from "lucide-react";

import type { IntegrationOverview } from "@/lib/api/integrations";
import { ACCENT, KpiTile } from "../components/KpiTile";
import { Muted, Panel, PanelLink, SectionHeading } from "../components/Panel";
import { ProtocolHealthPanel } from "../components/ProtocolCard";
import { StatusBadge, StatusItem } from "../components/StatusBadge";
import { blockerLabel, explainStatus, formatShortTimestamp, formatTimestamp, sumMeasured } from "../lib/presentation";

/**
 * Pure view of GET /integrations/observability/overview (no fetching here).
 * Recent messages and latest failures come from their own queries and are
 * passed in as slots by the page.
 */
export const OverviewView = ({
  data,
  recentMessages,
  latestFailures,
}: {
  data: IntegrationOverview;
  recentMessages?: ReactNode;
  latestFailures?: ReactNode;
}) => {
  const shared = data.overview.messages;
  const measured = shared.status === "measured";
  const { htng, fias } = data.protocols;
  const hs = data.overview.htng_status;
  const fs = data.overview.fias_status;
  // Derived totals are sums of measured values only; any unmeasured input
  // keeps the total unavailable.
  const inbound = sumMeasured([htng.messages.inbound?.total, fias.messages.inbound?.total]);
  const outbound = sumMeasured([htng.messages.outbound?.total, fias.messages.outbound?.total]);
  const retry = sumMeasured([htng.messages.inbound?.retry_wait, fias.messages.inbound?.retry_wait]);
  const dlq = sumMeasured([shared.failed_dead_letter, shared.outbound_dead_letter]);
  const lastSuccess = shared.last_successful_exchange_at;

  return (
    <div className="space-y-4">
      {/* 1. Overall status: HTNG, FIAS and vendor validation, kept separate. */}
      <Panel
        id="integration-status-heading"
        title="Integration status"
        description={`Your facilities only · updated ${formatTimestamp(data.generated_at)}`}
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <StatusItem label="HTNG · production readiness" status={hs.production_readiness}>
            <ProtocolFacts transport={hs.transport} processing={hs.processing}
              blockedBy={htng.readiness.production_readiness.blocked_by} />
          </StatusItem>
          <StatusItem label="FIAS · production readiness" status={fs.production_readiness}>
            <ProtocolFacts transport={fs.transport} processing={fs.processing}
              blockedBy={fias.readiness.production_readiness.blocked_by} />
          </StatusItem>
          <StatusItem
            label="Vendor validation"
            status={data.overview.readiness_classification}
            explanation="Passing synthetic tests is not vendor certification. Validation stays pending until the vendor decisions are approved with evidence."
          />
        </div>
      </Panel>

      {/* 2. Message KPIs, directly on the page as on the HMS dashboard. */}
      <section aria-labelledby="integration-kpi-heading">
        <SectionHeading
          id="integration-kpi-heading"
          title="Message activity"
          description={measured ? "HTNG and FIAS messages currently retained, not lifetime totals" : "HTNG and FIAS"}
        />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          <KpiTile label="Inbound" value={inbound} blockStatus={shared.status} icon={ArrowDownToLine} accent={ACCENT.blue} detail="Received from vendors" />
          <KpiTile label="Outbound" value={outbound} blockStatus={shared.status} icon={ArrowUpFromLine} accent={ACCENT.violet} detail="Queued or sent to vendors" />
          <KpiTile label="Pending" value={shared.pending} blockStatus={shared.status} icon={Clock} accent={ACCENT.amber} detail="Waiting to be processed" />
          <KpiTile label="Failed" value={shared.failed_dead_letter} blockStatus={shared.status} icon={AlertTriangle} accent={ACCENT.red} detail="Inbound, moved to the DLQ" />
          <KpiTile label="Awaiting retry" value={retry} blockStatus={shared.status} icon={RotateCcw} accent={ACCENT.amber} detail="Scheduled for another attempt" />
          <KpiTile label="DLQ" value={dlq} blockStatus={shared.status} icon={Inbox} accent={ACCENT.red} detail="Inbound and outbound" />
        </div>
      </section>

      {/* 3. Protocol health, side by side on wide screens. */}
      <section aria-label="Protocol health" className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ProtocolHealthPanel protocol="htng" entry={htng} />
        <ProtocolHealthPanel protocol="fias" entry={fias} />
      </section>

      {/* 4. Recent activity. */}
      <section aria-label="Recent activity" className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Panel
          id="integration-recent-heading"
          title="Recent messages"
          description={
            <>
              Last successful processing:{" "}
              <span className="text-foreground" title={lastSuccess ? formatTimestamp(lastSuccess) : undefined}>
                {lastSuccess ? formatShortTimestamp(lastSuccess) : formatTimestamp(null, measured)}
              </span>
            </>
          }
          actions={<PanelLink to="/integrations/messages">All messages</PanelLink>}
        >
          {recentMessages ?? <Muted>Recent messages are shown on the Message Logs screen.</Muted>}
        </Panel>
        <Panel
          id="integration-failures-heading"
          title="Latest failures"
          description="Messages that could not be processed"
          actions={<PanelLink to="/integrations/dlq">Failed messages</PanelLink>}
        >
          {latestFailures ?? <Muted>Failed messages are shown on the Failed Messages screen.</Muted>}
        </Panel>
      </section>
    </div>
  );
};

/** Connection and processing for one protocol inside the status panel. */
const ProtocolFacts = ({
  transport,
  processing,
  blockedBy,
}: {
  transport: string;
  processing: string;
  blockedBy?: string[];
}) => {
  const note = explainStatus("transport", transport);
  return (
    <div className="mt-2.5 space-y-1.5 border-t border-border/60 pt-2.5 text-xs">
      {blockedBy && blockedBy.length ? (
        <div className="flex flex-wrap items-center gap-1.5 pb-1" data-blocked-by={blockedBy.join(" ")}>
          <span className="text-muted-foreground">Blocked by:</span>
          {blockedBy.map((b) => (
            <span key={b} className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] text-foreground/80">
              {blockerLabel(b)}
            </span>
          ))}
        </div>
      ) : null}
      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground">Connection</span>
        <StatusBadge status={transport} />
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground">Processing</span>
        <StatusBadge status={processing} />
      </div>
      {note ? <p className="leading-5 text-muted-foreground">{note}</p> : null}
    </div>
  );
};
