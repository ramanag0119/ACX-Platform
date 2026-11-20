import { AlertTriangle, ArrowDownToLine, ArrowUpFromLine, CheckCircle2, Clock, Gauge, Percent, RotateCcw } from "lucide-react";

import { TableLoading } from "@/core/components/DataState";
import type { IntegrationMetrics, IntegrationProtocol } from "@/lib/api/integrations";
import { ACCENT, KpiTile } from "../components/KpiTile";
import {
  ErrorRetryChart,
  LatencyPanel,
  MessageTypeChart,
  StatusDonut,
  TrafficTrendChart,
  UnavailableMetrics,
} from "../components/MonitoringCharts";
import { Muted, Panel, SectionHeading } from "../components/Panel";
import { QueryErrorState } from "../components/QueryErrorState";
import { RANGE_LABELS, explainStatus, formatDuration, formatPercent } from "../lib/presentation";

/** What one counted unit is on each protocol: one stored message. On FIAS one
 *  framed record that passes intake becomes exactly one stored message. */
export const UNIT: Record<IntegrationProtocol, string> = { htng: "Messages", fias: "Records" };

const PROTOCOL_UNAVAILABLE: Record<IntegrationProtocol, string[]> = {
  htng: ["endpoint_availability_history", "rejected_intake", "retry_attempt_timeline", "processing_latency", "worker_health"],
  fias: ["connection_history", "ack_statistics", "timeout_statistics", "parse_failures", "retry_attempt_timeline", "worker_health"],
};

/**
 * Windowed KPIs and charts for one protocol, from GET /observability/metrics.
 * Pure: the page owns the query (and therefore the filters).
 */
export const MonitoringDashboard = ({
  protocol,
  metrics,
  isLoading,
  error,
  onRetry,
}: {
  protocol: IntegrationProtocol;
  metrics: IntegrationMetrics | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}) => {
  const unit = UNIT[protocol];
  const sid = (s: string) => `${protocol}-dash-${s}`;
  if (error && !metrics) return <QueryErrorState error={error} onRetry={onRetry} />;
  if (!metrics) {
    return isLoading ? (
      <div className="space-y-4" aria-busy="true" data-dashboard-loading="true">
        <TableLoading columns={4} rows={1} />
        <TableLoading columns={2} rows={4} />
      </div>
    ) : null;
  }
  const k = metrics.kpis;
  const block = metrics.status === "measured" ? "measured" : "not_available";
  const period = RANGE_LABELS[metrics.window.range] ?? metrics.window.range;
  const lat = metrics.latency;

  return (
    <div className="space-y-4" data-dashboard={protocol} data-range={metrics.window.range}>
      <section aria-labelledby={sid("kpis")}>
        <SectionHeading
          id={sid("kpis")}
          title={`Activity · ${period}`}
          description={`${unit} received in this period, in their current status · retained data only`}
        />
        <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 xl:grid-cols-4">
          <KpiTile label={`Total ${unit.toLowerCase()}`} value={k?.inbound_total} blockStatus={block}
            icon={ArrowDownToLine} accent={ACCENT.blue} detail="Received from vendors" />
          <KpiTile label="Successfully processed" value={k?.processed} blockStatus={block}
            icon={CheckCircle2} accent={ACCENT.green} detail="Completed in HMS" />
          <KpiTile label="Failed" value={k?.failed} blockStatus={block}
            icon={AlertTriangle} accent={ACCENT.red} detail="Moved to the DLQ" />
          <KpiTile label="Queued" value={k?.queued} blockStatus={block} icon={Clock} accent={ACCENT.amber}
            detail={k ? `${k.awaiting_retry} awaiting retry` : undefined} />
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 xl:grid-cols-4">
          <KpiTile label="Success rate" value={k ? k.success_rate : null} blockStatus={block} icon={Percent}
            accent={ACCENT.green} format={formatPercent} detail="Processed ÷ (processed + failed)"
            emptyText={k ? "No completed messages" : undefined}
            emptyExplanation={k ? "Nothing finished processing in this period." : undefined} />
          <KpiTile label="Average processing time" value={lat ? lat.avg : null} blockStatus={block} icon={Gauge}
            accent={ACCENT.violet} format={(v) => formatDuration(v)} detail="Intake to completion"
            emptyText={lat ? "No completions" : undefined}
            emptyExplanation={lat ? "Nothing finished processing in this period." : undefined} />
          <KpiTile label="Needed a retry" value={k?.retried_messages} blockStatus={block} icon={RotateCcw}
            accent={ACCENT.amber} detail={k ? `${k.extra_attempts} extra attempts` : undefined} />
          <KpiTile label="Outbound" value={k?.outbound_total} blockStatus={block} icon={ArrowUpFromLine}
            accent={ACCENT.violet}
            detail={k ? `${k.outbound_sent} sent · ${k.outbound_queued} queued · ${k.outbound_failed} failed` : undefined} />
        </div>
      </section>

      {metrics.status !== "measured" ? (
        <Panel id={sid("unavailable")} title="Charts unavailable">
          <Muted>{explainStatus("messages", "not_available")}</Muted>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TrafficTrendChart id={sid("traffic")} metrics={metrics} unit={unit} />
          <StatusDonut id={sid("status")} metrics={metrics} unit={unit} />
          <ErrorRetryChart id={sid("errors")} metrics={metrics} unit={unit} />
          <LatencyPanel id={sid("latency")} metrics={metrics} />
          <MessageTypeChart id={sid("types")} metrics={metrics} unit={unit} />
          <UnavailableMetrics id={sid("gaps")} metrics={metrics} only={PROTOCOL_UNAVAILABLE[protocol]} />
        </div>
      )}
    </div>
  );
};
