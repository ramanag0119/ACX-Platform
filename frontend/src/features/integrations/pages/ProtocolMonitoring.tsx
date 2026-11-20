import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { RotateCw } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataState, InlineLoading, TableLoading } from "@/core/components/DataState";
import {
  useIntegrationDeadLetters,
  useIntegrationMessages,
  useIntegrationMetrics,
  useIntegrationOverview,
} from "@/lib/api/hooks";
import { METRIC_RANGES, type IntegrationProtocol, type MetricRange } from "@/lib/api/integrations";
import { DeadLetterTable, MessageTable } from "../components/MessageTables";
import { Muted } from "../components/Panel";
import { QueryErrorState } from "../components/QueryErrorState";
import { StatusBadge } from "../components/StatusBadge";
import { useFacilityScope } from "../lib/hooks";
import { PROTOCOL_META, RANGE_LABELS, formatTimestamp } from "../lib/presentation";
import { MonitoringDashboard, UNIT } from "../views/MonitoringDashboard";
import { ProtocolView } from "../views/ProtocolView";

const RECENT_ROWS = 10;
const FAILED_ROWS = 5;
const SPAN_SECONDS: Record<MetricRange, number> = { "1h": 3600, "24h": 86400, "7d": 7 * 86400, "30d": 30 * 86400 };
const ALL = "__all__";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Range and facility live in the URL (`?range=7d&facility=<uuid>`), so a view can be shared. */
function useMonitoringFilters(scopeIds: string[]) {
  const [search, setSearch] = useSearchParams();
  const raw = search.get("range");
  const range: MetricRange = (METRIC_RANGES as readonly string[]).includes(raw ?? "") ? (raw as MetricRange) : "24h";
  const f = search.get("facility");
  // Only a facility inside the user's scope is ever requested (403 otherwise).
  const facility = f && UUID.test(f) && scopeIds.includes(f) ? f : undefined;
  const update = (patch: { range?: MetricRange; facility?: string | undefined }) => {
    const next = new URLSearchParams(search);
    const r = patch.range ?? range;
    if (r === "24h") next.delete("range");
    else next.set("range", r);
    const fac = "facility" in patch ? patch.facility : facility;
    if (fac) next.set("facility", fac);
    else next.delete("facility");
    setSearch(next, { replace: true });
  };
  return { range, facility, update };
}

/**
 * HTNG / FIAS monitoring dashboard.
 *
 * * KPIs and charts: GET /observability/metrics (server-side aggregates for the
 *   selected window and facility; nothing is aggregated in the browser).
 * * Current health: the shared overview query (current state, not windowed).
 * * Recent and failed messages: two small server-filtered pages restricted to
 *   the same window and facility. No payload is ever requested.
 */
export const ProtocolMonitoring = ({ protocol }: { protocol: IntegrationProtocol }) => {
  const meta = PROTOCOL_META[protocol];
  const { names, options, scopeIds } = useFacilityScope();
  const { range, facility, update } = useMonitoringFilters(scopeIds);
  const tz = useMemo(() => -new Date().getTimezoneOffset() || 0, []); // "|| 0": no -0 in the query key
  // Start of the window for the row lists, rounded to the minute so the query
  // key is stable between renders.
  const since = useMemo(
    () => new Date(Math.floor((Date.now() - SPAN_SECONDS[range] * 1000) / 60000) * 60000).toISOString(),
    [range],
  );

  const overview = useIntegrationOverview();
  const metrics = useIntegrationMetrics({ protocol, range, facility_id: facility, tz_offset_minutes: tz });
  const recent = useIntegrationMessages({ protocol, page: 1, page_size: RECENT_ROWS, facility_id: facility, received_from: since });
  const failed = useIntegrationDeadLetters({ protocol, page: 1, page_size: FAILED_ROWS, facility_id: facility, received_from: since });
  const entry = overview.data?.protocols[protocol];
  const unit = UNIT[protocol].toLowerCase();

  const refresh = () => {
    overview.refetch();
    metrics.refetch();
    recent.refetch();
    failed.refetch();
  };
  const busy = overview.isFetching || metrics.isFetching;

  return (
    <div className="space-y-4 animate-fade-in text-foreground">
      <PageHeader
        title={`${meta.label} Monitoring`}
        description={`Protocol: ${meta.label} ${protocol === "htng" ? "SOAP" : "TCP"} · vendor validation pending`}
        actions={
          <Button variant="outline" size="sm" onClick={refresh} disabled={busy} className="gap-1.5">
            <RotateCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} aria-hidden />
            Refresh
          </Button>
        }
      />

      {/* Filters: every control changes the server requests below. */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3" role="toolbar" aria-label="Monitoring filters">
        <div className="flex flex-wrap items-center gap-1 rounded-lg border border-border bg-background/60 p-1" role="group" aria-label="Time range">
          {METRIC_RANGES.map((r) => (
            <button
              key={r}
              type="button"
              aria-pressed={r === range}
              onClick={() => update({ range: r })}
              className={`min-h-[32px] rounded-md px-3 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                r === range ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
              }`}
              title={RANGE_LABELS[r]}
            >
              {r}
            </button>
          ))}
        </div>
        <div className="w-full min-w-0 sm:w-56">
          <Select value={facility ?? ALL} onValueChange={(v) => update({ facility: v === ALL ? undefined : v })}>
            <SelectTrigger aria-label="Facility filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All my facilities</SelectItem>
              {options.map((o) => <SelectItem key={o.id} value={o.id}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {entry ? (
            <span className="inline-flex items-center gap-1.5">
              {protocol === "htng" ? "Endpoint" : "Link"} <StatusBadge status={entry.transport.status} />
            </span>
          ) : null}
          <span data-updated-at={metrics.data?.generated_at ?? ""}>
            {metrics.data ? `Updated ${formatTimestamp(metrics.data.generated_at)}` : ""}
          </span>
        </div>
      </div>

      {overview.isLoading ? (
        <InlineLoading label={`Loading ${meta.label} status...`} />
      ) : overview.error ? (
        <QueryErrorState error={overview.error} onRetry={() => overview.refetch()} />
      ) : entry ? (
        <ProtocolView
          protocol={protocol}
          entry={entry}
          dashboard={
            <MonitoringDashboard
              protocol={protocol}
              metrics={metrics.data}
              isLoading={metrics.isLoading}
              error={metrics.error}
              onRetry={() => metrics.refetch()}
            />
          }
          recentMessages={
            recent.error ? (
              <QueryErrorState error={recent.error} onRetry={() => recent.refetch()} />
            ) : (
              <DataState
                isLoading={recent.isLoading}
                error={null}
                isEmpty={(recent.data?.items.length ?? 0) === 0}
                emptyTitle={`No ${meta.label} ${unit} in this period`}
                emptyDescription={`${RANGE_LABELS[range]}${facility ? " · selected facility" : ""}.`}
                loader={<TableLoading columns={7} rows={3} />}
              >
                <MessageTable rows={recent.data?.items ?? []} facilityNames={names} inProtocolContext caption={`Recent ${meta.label} messages`} />
              </DataState>
            )
          }
          deadLetters={
            failed.error ? (
              <QueryErrorState error={failed.error} onRetry={() => failed.refetch()} />
            ) : (
              <DataState
                isLoading={failed.isLoading}
                error={null}
                isEmpty={(failed.data?.items.length ?? 0) === 0}
                emptyTitle={`No failed ${meta.label} ${unit} in this period`}
                loader={<TableLoading columns={8} rows={2} />}
              >
                <DeadLetterTable rows={failed.data?.items ?? []} facilityNames={names} inProtocolContext caption={`Failed ${meta.label} messages`} />
                {failed.data && failed.data.total > FAILED_ROWS ? (
                  <Muted className="mt-2">Showing the {FAILED_ROWS} most recent of {failed.data.total}.</Muted>
                ) : null}
              </DataState>
            )
          }
        />
      ) : null}
    </div>
  );
};

export const HtngMonitoring = () => <ProtocolMonitoring protocol="htng" />;
export const FiasMonitoring = () => <ProtocolMonitoring protocol="fias" />;
