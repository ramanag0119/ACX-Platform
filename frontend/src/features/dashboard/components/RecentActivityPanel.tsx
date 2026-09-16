import { useState } from "react";
import { RefreshCw } from "lucide-react";

import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useActivities } from "@/lib/api/hooks";

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

export const RecentActivityPanel = () => {
  const { isDark } = useTheme();
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

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark
    ? "1px solid rgba(255,255,255,0.07)"
    : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const selectBg = isDark ? "#252a3e" : "#FFFFFF";
  const selectBorder = isDark
    ? "1px solid rgba(255,255,255,0.1)"
    : "1px solid rgba(124,92,255,0.12)";

  return (
    <div
      className="rounded-[16px] p-4 h-full transition-all duration-250 hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4 gap-2">
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

      <div className="min-h-[120px]">
        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={rows.length === 0}
          emptyTitle="No activity recorded"
          emptyDescription="Nothing in `activity` matches this window."
        >
          <ul className="space-y-2 max-h-[260px] overflow-y-auto scrollbar-thin">
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
