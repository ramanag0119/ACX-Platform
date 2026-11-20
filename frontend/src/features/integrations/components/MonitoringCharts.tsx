import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import type { IntegrationMetrics, StatusShare } from "@/lib/api/integrations";
import {
  failureCategoryLabel,
  failureLabel,
  formatBucket,
  formatDuration,
  formatTimestamp,
  messageTypeLabel,
  presentStatus,
  unavailableLabel,
} from "../lib/presentation";
import { Muted, Panel } from "./Panel";

/**
 * Charts for the HTNG / FIAS monitoring pages. Every value comes from
 * GET /integrations/observability/metrics (server-side aggregates); nothing is
 * computed from message rows in the browser, nothing is sampled or invented.
 * Each chart carries a visually hidden data table with the exact values it
 * plots, for screen readers (and tests).
 */

/** Semantic colours, readable on the light and dark card surfaces. */
export const SERIES = {
  received: "#38bdf8",
  processed: "#22c55e",
  failed: "#ef4444",
  retry: "#f59e0b",
  outbound: "#7c5cff",
  queued: "#94a3b8",
} as const;

const STATUS_COLOR: Record<string, string> = {
  SUCCEEDED: SERIES.processed,
  SENT: SERIES.processed,
  PENDING: SERIES.queued,
  PROCESSING: SERIES.received,
  RETRY_WAIT: SERIES.retry,
  DEAD_LETTER: SERIES.failed,
};

const useChartStyle = () => {
  const t = useSurfaceTokens();
  return {
    tokens: t,
    axis: { axisLine: false, tickLine: false, tick: { fill: t.textMuted, fontSize: 11 } },
    tooltip: {
      contentStyle: { background: t.tooltipBg, border: t.tooltipBorder, borderRadius: 8, color: t.titleColor, fontSize: 12 },
      labelStyle: { color: t.titleColor },
    },
  };
};

/* The wrapper carries `sr-only`, not the table: a table ignores the 1px width
   and would keep its content width, widening the page on phones (found in the
   390px browser check). */
const SrTable = ({ caption, head, rows }: { caption: string; head: string[]; rows: (string | number)[][] }) => (
  <div className="sr-only" data-chart-table={caption}>
    <table>
      <caption>{caption}</caption>
      <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
    </table>
  </div>
);

const ChartEmpty = ({ text }: { text: string }) => (
  <div className="flex h-full min-h-[180px] items-center justify-center text-center" data-chart-empty="true">
    <Muted>{text}</Muted>
  </div>
);

function points(m: IntegrationMetrics) {
  return m.series.map((b) => ({
    ...b,
    name: formatBucket(b.bucket_start, m.window.bucket_seconds),
    fullName: formatTimestamp(b.bucket_start),
  }));
}

const labelFromPayload = (_l: unknown, payload?: { payload?: { fullName?: string } }[]) =>
  payload?.[0]?.payload?.fullName ?? "";

// ------------------------------------------------------------------ traffic
export const TrafficTrendChart = ({ id, metrics, unit }: { id: string; metrics: IntegrationMetrics; unit: string }) => {
  const { tokens, axis, tooltip } = useChartStyle();
  const data = points(metrics);
  const empty = data.every((p) => !p.received && !p.processed && !p.outbound_created);
  return (
    <Panel id={id} title={`${unit} traffic`} description="Received and processed per interval; outbound queued for vendors">
      <div className="h-[240px] min-w-0" data-chart="traffic">
        {empty ? (
          <ChartEmpty text={`No ${unit.toLowerCase()} in this period.`} />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={tokens.gridStroke} vertical={false} />
              <XAxis dataKey="name" {...axis} minTickGap={16} />
              <YAxis allowDecimals={false} {...axis} />
              <Tooltip {...tooltip} labelFormatter={labelFromPayload} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="received" name="Received" stroke={SERIES.received} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="processed" name="Processed" stroke={SERIES.processed} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="outbound_created" name="Outbound queued" stroke={SERIES.outbound} strokeWidth={2} strokeDasharray="4 3" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
      <SrTable caption={`${unit} traffic per interval`} head={["Interval", "Received", "Processed", "Outbound queued"]}
        rows={data.map((p) => [p.fullName, p.received, p.processed, p.outbound_created])} />
    </Panel>
  );
};

// ------------------------------------------------------------- distribution
export const StatusDonut = ({ id, metrics, unit }: { id: string; metrics: IntegrationMetrics; unit: string }) => {
  const { tooltip, tokens } = useChartStyle();
  const shares: StatusShare[] = metrics.status_distribution?.inbound ?? [];
  const total = shares.reduce((n, s) => n + s.count, 0);
  const data = shares.map((s) => ({ ...s, label: presentStatus(s.status).label }));
  return (
    <Panel id={id} title="Processing status" description={`Current status of ${unit.toLowerCase()} received in this period`}>
      {total === 0 ? (
        <ChartEmpty text={`No ${unit.toLowerCase()} received in this period.`} />
      ) : (
        <div className="flex flex-col items-center gap-4 sm:flex-row" data-chart="status">
          <div className="relative h-[200px] w-full max-w-[220px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="count" nameKey="label" innerRadius="62%" outerRadius="92%" paddingAngle={1} stroke="none">
                  {data.map((d) => <Cell key={d.status} fill={STATUS_COLOR[d.status] ?? SERIES.queued} />)}
                </Pie>
                <Tooltip {...tooltip} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-semibold tabular-nums" style={{ color: tokens.titleColor }}>{total}</span>
              <span className="text-[11px]" style={{ color: tokens.textMuted }}>total</span>
            </div>
          </div>
          <ul className="w-full min-w-0 space-y-2" aria-label="Status breakdown">
            {data.map((d) => (
              <li key={d.status} className="flex items-center justify-between gap-3 text-sm" data-status-share={d.status}>
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: STATUS_COLOR[d.status] ?? SERIES.queued }} />
                  <span className="truncate">{d.label}</span>
                </span>
                <span className="tabular-nums" style={{ color: tokens.textMuted }}>
                  {d.count} · {d.share === null ? "—" : `${Math.round(d.share * 1000) / 10}%`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
};

// ---------------------------------------------------------- errors / retries
export const ErrorRetryChart = ({ id, metrics, unit }: { id: string; metrics: IntegrationMetrics; unit: string }) => {
  const { tokens, axis, tooltip } = useChartStyle();
  const data = points(metrics);
  const empty = data.every((p) => !p.failed && !p.retried_received);
  const errors = metrics.errors ?? [];
  return (
    <Panel id={id} title="Failures and retries" description="Moved to the DLQ (by failure time) and needing a retry (by arrival time)">
      <div className="h-[200px] min-w-0" data-chart="errors">
        {empty ? (
          <ChartEmpty text="No failures or retries in this period." />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={tokens.gridStroke} vertical={false} />
              <XAxis dataKey="name" {...axis} minTickGap={16} />
              <YAxis allowDecimals={false} {...axis} />
              <Tooltip {...tooltip} labelFormatter={labelFromPayload} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="failed" name="Failed (DLQ)" fill={SERIES.failed} radius={[2, 2, 0, 0]} />
              <Bar dataKey="retried_received" name={`${unit} retried`} fill={SERIES.retry} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      <div className="mt-3 border-t border-border/60 pt-3">
        <p className="mb-1.5 text-xs font-medium" style={{ color: tokens.textMuted }}>Current failure reasons</p>
        {errors.length ? (
          <ul className="space-y-1" aria-label="Failure reasons">
            {errors.slice(0, 5).map((e) => (
              <li key={`${e.category}-${e.code}`} className="flex items-center justify-between gap-3 text-sm" data-error-code={e.code ?? undefined}>
                <span className="min-w-0 truncate">{failureLabel(e.code)}</span>
                <span className="shrink-0 text-xs tabular-nums" style={{ color: tokens.textMuted }}>
                  {failureCategoryLabel(e.category)} · {e.count}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Muted>No failing or retrying {unit.toLowerCase()} in this period.</Muted>
        )}
      </div>
      <SrTable caption="Failures and retries per interval" head={["Interval", "Failed", "Retried"]}
        rows={data.map((p) => [p.fullName, p.failed, p.retried_received])} />
    </Panel>
  );
};

// ------------------------------------------------------------------ latency
export const LatencyPanel = ({ id, metrics }: { id: string; metrics: IntegrationMetrics }) => {
  const { tokens, axis, tooltip } = useChartStyle();
  const lat = metrics.latency;
  const data = points(metrics);
  const stats: [string, number | null | undefined][] = [
    ["Average", lat?.avg], ["Median", lat?.p50], ["95th percentile", lat?.p95], ["Slowest", lat?.max],
  ];
  return (
    <Panel id={id} title="Processing time" description="From intake to completed processing (end to end)">
      {!lat || lat.count === 0 ? (
        <ChartEmpty text="No message completed processing in this period." />
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-latency-count={lat.count}>
            {stats.map(([label, v]) => (
              <div key={label} className="min-w-0 rounded-xl border border-border/60 px-3 py-2">
                <dt className="text-[11px] uppercase tracking-wide" style={{ color: tokens.textMuted }}>{label}</dt>
                <dd className="text-lg font-semibold tabular-nums" style={{ color: tokens.titleColor }}>{formatDuration(v)}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-3 h-[150px] min-w-0" data-chart="latency">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.gridStroke} vertical={false} />
                <XAxis dataKey="name" {...axis} minTickGap={16} />
                <YAxis {...axis} tickFormatter={(v: number) => formatDuration(v)} width={64} />
                <Tooltip {...tooltip} labelFormatter={labelFromPayload} formatter={(v: number) => formatDuration(v)} />
                <Line type="monotone" dataKey="avg_latency_seconds" name="Average" stroke={SERIES.received} strokeWidth={2} connectNulls={false} dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <Muted className="mt-2">
            Based on {lat.count} completed {lat.count === 1 ? "message" : "messages"}. Worker processing time alone is not
            recorded, so this includes time spent waiting in the queue.
          </Muted>
        </>
      )}
      <SrTable caption="Average processing time per interval" head={["Interval", "Average seconds"]}
        rows={data.map((p) => [p.fullName, p.avg_latency_seconds === null ? "no completions" : p.avg_latency_seconds])} />
    </Panel>
  );
};

// ------------------------------------------------------- message / record types
export const MessageTypeChart = ({ id, metrics, unit }: { id: string; metrics: IntegrationMetrics; unit: string }) => {
  const { tokens, axis, tooltip } = useChartStyle();
  const data = (metrics.message_types ?? []).map((t) => ({ name: messageTypeLabel(t.message_type), count: t.count }));
  return (
    <Panel id={id} title={`${unit.replace(/s$/, "")} types`} description={`${unit} received in this period, by type`}>
      {data.length === 0 ? (
        <ChartEmpty text={`No ${unit.toLowerCase()} received in this period.`} />
      ) : (
        <div className="min-w-0" style={{ height: Math.max(120, data.length * 34) }} data-chart="types">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={tokens.gridStroke} horizontal={false} />
              <XAxis type="number" allowDecimals={false} {...axis} />
              <YAxis type="category" dataKey="name" width={110} {...axis} />
              <Tooltip {...tooltip} />
              <Bar dataKey="count" name="Received" fill={SERIES.received} radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <SrTable caption={`${unit} by type`} head={["Type", "Count"]} rows={data.map((d) => [d.name, d.count])} />
    </Panel>
  );
};

// ---------------------------------------------------------- unavailable list
export const UnavailableMetrics = ({ id, metrics, only }: { id: string; metrics: IntegrationMetrics; only?: string[] }) => {
  const { tokens } = useChartStyle();
  const rows = metrics.unavailable.filter((u) => !only || only.includes(u.metric));
  if (!rows.length) return null;
  return (
    <Panel id={id} title="Not measured" description="Shown as unavailable rather than as zero, with the reason">
      <ul className="divide-y divide-border/60">
        {rows.map((u) => (
          <li key={u.metric} className="py-2" data-unavailable-metric={u.metric}>
            <p className="text-sm" style={{ color: tokens.titleColor }}>{unavailableLabel(u.metric)}</p>
            <Muted>{u.reason}</Muted>
          </li>
        ))}
      </ul>
    </Panel>
  );
};
