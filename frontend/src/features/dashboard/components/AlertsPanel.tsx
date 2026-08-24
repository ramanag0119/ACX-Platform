import { useState } from "react";
import { List } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useAlerts, useServiceRequests } from "@/lib/api/hooks";

/**
 * The existing Service | Caleido toggle, backed by the two real sources:
 *
 *   Caleido -> GET /alerts          (device alerts; carries SEVERITY)
 *   Service -> GET /service-requests (carries a service STATUS)
 *
 * Alert severity and incident lifecycle status are separate things in the
 * schema; an alert has no status and none is displayed for one.
 */

const RANGE_DAYS: Record<string, number> = { Today: 0, Week: 6, Month: 29 };

const isoDaysAgo = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  date.setHours(0, 0, 0, 0);
  return date.toISOString();
};

export const AlertsPanel = () => {
  const { isDark } = useTheme();
  const [source, setSource] = useState<"caleido" | "service">("caleido");
  const [range, setRange] = useState<keyof typeof RANGE_DAYS>("Month");

  const createdFrom = isoDaysAgo(RANGE_DAYS[range]);
  const alertsQuery = useAlerts(
    source === "caleido" ? { page: 1, page_size: 10, created_from: createdFrom } : undefined,
  );
  const requestsQuery = useServiceRequests(
    source === "service" ? { page: 1, page_size: 10, created_from: createdFrom } : undefined,
  );

  const query = source === "caleido" ? alertsQuery : requestsQuery;

  const rows =
    source === "caleido"
      ? (alertsQuery.data?.items ?? []).map((alert) => ({
          id: `alert-${alert.id}`,
          title: alert.alert_type_name ?? "Alert",
          meta: [alert.amenity_name, alert.device_name].filter(Boolean).join(" · "),
          tag: alert.alert_severity ?? "-",
          at: alert.created_on,
        }))
      : (requestsQuery.data?.items ?? []).map((request) => ({
          id: `request-${request.id}`,
          title: request.category_name ?? request.service_type_name ?? "Service request",
          meta: [request.amenity_name, request.ref_number].filter(Boolean).join(" · "),
          tag: request.status_name ?? "-",
          at: request.created_on,
        }));

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const selectBg = isDark ? "#252a3e" : "#FFFFFF";
  const selectBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";

  const linkClass = (active: boolean) =>
    active
      ? "text-[hsl(199,89%,48%)] underline cursor-pointer font-medium"
      : "text-[hsl(199,89%,48%)] hover:underline cursor-pointer opacity-70";

  return (
    <div
      className="rounded-lg p-4 h-full transition-all duration-250 ease hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ color: titleColor }} className="font-medium">Alerts</h3>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className={linkClass(source === "service")} onClick={() => setSource("service")}>
              Service
            </span>
            <span style={{ color: mutedColor }}>|</span>
            <span className={linkClass(source === "caleido")} onClick={() => setSource("caleido")}>
              Caleido
            </span>
          </div>
          <button
            style={{ color: mutedColor }}
            className="hover:opacity-100 opacity-70 transition-opacity"
            onClick={() => query.refetch()}
            title="Refresh"
          >
            <List className="h-4 w-4" />
          </button>
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors duration-200"
            style={{ backgroundColor: selectBg, color: titleColor, border: selectBorder }}
            value={range}
            onChange={(event) => setRange(event.target.value as keyof typeof RANGE_DAYS)}
          >
            <option>Today</option>
            <option>Week</option>
            <option>Month</option>
          </select>
        </div>
      </div>

      <div className="min-h-[120px]">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={rows.length === 0}
          emptyTitle="No alerts found"
        >
          <ul className="space-y-2 max-h-[220px] overflow-y-auto scrollbar-thin">
            {rows.map((row) => (
              <li key={row.id} className="flex items-start justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate" style={{ color: titleColor }}>{row.title}</p>
                  <p className="truncate text-xs" style={{ color: mutedColor }}>
                    {row.meta || "-"} · {new Date(row.at).toLocaleString()}
                  </p>
                </div>
                <span className="shrink-0 text-xs rounded-full px-2 py-0.5 border" style={{ color: mutedColor }}>
                  {row.tag}
                </span>
              </li>
            ))}
          </ul>
        </DataState>
      </div>
    </div>
  );
};
