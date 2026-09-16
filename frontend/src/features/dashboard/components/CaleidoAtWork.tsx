import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useDailyDataPoints } from "@/lib/api/hooks";

/**
 * The four rings are the real `daily_dual_data_point` KPI rows.
 *
 * dp_1 / dp_2 are the stored numerator and denominator; the percentage is a
 * FRONTEND PRESENTATION calculation over those two stored values, not a
 * backend aggregation and not a business rule. The metric_type strings are
 * exactly the ones the table stores.
 */

interface CircularProgressProps {
  value: number;
  label: string;
  color: string;
  showDash?: boolean;
  isDark: boolean;
  detail?: string;
}

const CircularProgress = ({ value, label, color, showDash, isDark, detail }: CircularProgressProps) => {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(Math.max(value, 0), 100) / 100) * circumference;
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#8A86A8";

  return (
    <div className="flex items-center gap-3">
      <div className="relative w-12 h-12">
        <svg className="w-12 h-12 -rotate-90" viewBox="0 0 44 44">
          <circle cx="22" cy="22" r={radius} fill="none" stroke={isDark ? "rgba(255,255,255,0.08)" : "rgba(124,92,255,0.1)"} strokeWidth="3" />
          <circle
            cx="22" cy="22" r={radius} fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} strokeLinecap="round"
          />
        </svg>
      </div>
      <div>
        <p style={{ color: titleColor }} className="font-medium text-lg">
          {showDash ? "-" : `${value}%`}
        </p>
        <p style={{ color: mutedColor }} className="text-xs uppercase tracking-wide">{label}</p>
        {detail && <p style={{ color: mutedColor }} className="text-[10px]">{detail}</p>}
      </div>
    </div>
  );
};

/** Ring label -> the `metric_type` value stored in the table. */
const RINGS: { metricType: string; label: string; color: string }[] = [
  { metricType: "smart room", label: "Smart Rooms Online", color: "hsl(0,70%,50%)" },
  { metricType: "service request", label: "Service Request Status", color: "hsl(145,70%,45%)" },
  { metricType: "checkout", label: "Rooms For Check-Out", color: "hsl(145,70%,45%)" },
  { metricType: "booking", label: "Pending Bookings", color: "hsl(145,70%,45%)" },
];

/** The existing Today/Week/Month picker, mapped to a real date filter. */
const RANGE_DAYS: Record<string, number> = { Today: 0, Week: 6, Month: 29 };

const isoDaysAgo = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
};

export const CaleidoAtWork = () => {
  const { isDark } = useTheme();
  const [range, setRange] = useState<keyof typeof RANGE_DAYS>("Today");

  // The most recent stored point within the chosen window. Points are daily
  // snapshots, so they are selected, never averaged together.
  const query = useDailyDataPoints({
    page: 1,
    page_size: 20,
    metric_date_from: isoDaysAgo(RANGE_DAYS[range]),
  });

  const latest = useMemo(() => {
    const items = query.data?.items ?? [];
    if (!items.length) return new Map<string, { value: number; detail: string }>();
    // The API sorts by metric_date descending, so the first row per type wins.
    const map = new Map<string, { value: number; detail: string }>();
    for (const item of items) {
      if (map.has(item.metric_type)) continue;
      const numerator = Number(item.dp_1);
      const denominator = Number(item.dp_2);
      map.set(item.metric_type, {
        value: denominator > 0 ? Math.round((numerator / denominator) * 100) : 0,
        detail: `${numerator} / ${denominator}`,
      });
    }
    return map;
  }, [query.data]);

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const selectBg = isDark ? "#252a3e" : "#FFFFFF";
  const selectBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";

  return (
    <div
      className="rounded-lg p-4 transition-all duration-250 ease hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ color: titleColor }} className="font-medium">Caleido At work</h3>
        <div className="flex items-center gap-2">
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
          <button
            style={{ color: mutedColor }}
            className="hover:opacity-100 opacity-70 transition-opacity"
            onClick={() => query.refetch()}
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <DataState
        isLoading={query.isLoading}
        error={query.error}
        isEmpty={latest.size === 0}
        emptyTitle="No daily KPI data points recorded"
      >
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {RINGS.map((ring) => {
            const point = latest.get(ring.metricType);
            return (
              <CircularProgress
                key={ring.metricType}
                value={point?.value ?? 0}
                detail={point?.detail}
                label={ring.label}
                color={ring.color}
                showDash={!point}
                isDark={isDark}
              />
            );
          })}
        </div>
      </DataState>
    </div>
  );
};
