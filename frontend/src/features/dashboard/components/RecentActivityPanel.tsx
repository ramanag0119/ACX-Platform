import { useState } from "react";
import { RefreshCw } from "lucide-react";

import { DataState } from "@/core/components/DataState";
import { useActivities } from "@/lib/api/hooks";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";

/**
 * Recent operational activity from GET /activities.
 *
 * WHAT IS SHOWN is limited by what the endpoint returns, which is deliberately
 * narrow. `activity.data` -- the JSON payload that carries OTPs, keypad codes
 * and rendered notification bodies for the key-generation and access activity
 * types -- is never selected by the backend, so there is no message text here
 * and none is reconstructed. The row is: activity type, entity type, who acted,
 * when, and the real notifier/unread counters.
 *
 * `unread_only` is a real backend filter over `activity_notifier`, not a
 * client-side pass over the current page.
 */

const RANGE_DAYS: Record<string, number> = { Today: 0, Week: 6, Month: 29, All: -1 };

const isoDaysAgo = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  date.setHours(0, 0, 0, 0);
  return date.toISOString();
};

/** Exported so the KPI tile that jumps here cannot drift from the element id. */
export const ACTIVITY_PANEL_ID = "dashboard-activity-panel";

export const RecentActivityPanel = () => {
  const [range, setRange] = useState<keyof typeof RANGE_DAYS>("Week");
  const [unreadOnly, setUnreadOnly] = useState(false);

  const days = RANGE_DAYS[range];
  const query = useActivities({
    page: 1,
    page_size: 10,
    ...(days >= 0 ? { created_from: isoDaysAgo(days) } : {}),
    ...(unreadOnly ? { unread_only: true } : {}),
  });

  const rows = query.data?.items ?? [];

  const {
    cardBg,
    cardBorder,
    cardShadow,
    titleColor,
    textMuted: mutedColor,
    controlBg: selectBg,
    controlBorder: selectBorder,
  } = useSurfaceTokens();

  return (
    /* Jump target for the dashboard's "Activities" KPI tile: this panel IS
       that tile's list (GET /activities), so the tile reveals it rather than
       routing away. Renaming means updating ACTIVITY_PANEL_ID's usage. */
    <div
      id={ACTIVITY_PANEL_ID}
      className="rounded-[16px] p-4 h-full min-w-0 flex flex-col transition-all duration-250 hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: cardShadow }}
    >
      <div className="flex flex-wrap items-center justify-between mb-4 gap-2 shrink-0">
        <h3 className="font-medium" style={{ color: titleColor }}>Recent Activity</h3>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs cursor-pointer" style={{ color: mutedColor }}>
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(event) => setUnreadOnly(event.target.checked)}
            />
            Unread only
          </label>
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors"
            style={{ background: selectBg, color: titleColor, border: selectBorder }}
            value={range}
            onChange={(event) => setRange(event.target.value as keyof typeof RANGE_DAYS)}
          >
            <option>Today</option>
            <option>Week</option>
            <option>Month</option>
            <option>All</option>
          </select>
          <button
            className="transition-opacity opacity-70 hover:opacity-100"
            style={{ color: mutedColor }}
            onClick={() => query.refetch()}
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-[120px] min-w-0 flex flex-col">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={rows.length === 0}
          emptyTitle="No activity recorded"
          emptyDescription="Nothing in `activity` matches this window."
        >
          {/* Same treatment as Alerts: the cap is a ceiling on a flex-1 list
              rather than the list's only height. */}
          <ul className="space-y-2 flex-1 min-h-0 max-h-[260px] overflow-y-auto overflow-x-hidden scrollbar-thin">
            {rows.map((row) => (
              <li key={row.id} className="flex items-start justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate" style={{ color: titleColor }}>
                    {row.activity_type_name ?? `Activity type ${row.activity_type_id}`}
                  </p>
                  <p className="truncate text-xs" style={{ color: mutedColor }}>
                    {[
                      row.entity_type_name,
                      row.actor?.name,
                      new Date(row.created_on).toLocaleString(),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <span
                  className="shrink-0 text-xs rounded-full px-2 py-0.5 border"
                  style={{ color: mutedColor }}
                  title={`${row.unread_count} unread of ${row.notifier_count} notified`}
                >
                  {row.unread_count}/{row.notifier_count}
                </span>
              </li>
            ))}
          </ul>
        </DataState>
      </div>
    </div>
  );
};
