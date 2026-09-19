import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useCaleidoAtWork } from "@/lib/api/hooks";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";

/**
 * The four rings are the real `daily_dual_data_point` KPI rows.
 *
 * dp_1 / dp_2 are the stored numerator and denominator, and the percentage the
 * ring draws is computed FROM THEM BY THE BACKEND -- GET
 * /daily-data-points/summary returns one aggregated row per metric_type (the
 * most recent snapshot in the window) with the ratio already resolved. Nothing
 * here selects a record or does arithmetic on the data. The metric_type strings
 * are exactly the ones the table stores.
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
    /* min-w-0 + shrink-0: a long label ("Service Request Status") truncates
       rather than widening the grid track. */
    <div className="flex items-center gap-3 min-w-0">
      <div className="relative w-12 h-12 shrink-0">
        <svg className="w-12 h-12 -rotate-90" viewBox="0 0 44 44">
          <circle cx="22" cy="22" r={radius} fill="none" stroke={isDark ? "rgba(255,255,255,0.08)" : "rgba(124,92,255,0.1)"} strokeWidth="3" />
          <circle
            cx="22" cy="22" r={radius} fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} strokeLinecap="round"
          />
        </svg>
      </div>
      <div className="min-w-0">
        <p style={{ color: titleColor }} className="font-medium text-lg truncate">
          {showDash ? "-" : `${value}%`}
        </p>
        <p style={{ color: mutedColor }} className="text-xs uppercase tracking-wide truncate" title={label}>{label}</p>
        {detail && <p style={{ color: mutedColor }} className="text-[10px] truncate" title={detail}>{detail}</p>}
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

  /**
   * One aggregated row per metric, straight from the backend.
   *
   * This used to request a PAGE of raw `daily_dual_data_point` rows -- every
   * metric type, up to twenty of them -- then pick the newest row per type
   * here and divide dp_1 by dp_2 in the browser. Both the record selection and
   * the percentage now happen in SQL, so the component receives exactly the
   * four ratios it draws and nothing to choose between.
   *
   * The window is sent to the API and is part of the query key, so switching
   * period refetches instead of re-reading the previous period's rows.
   */
  const query = useCaleidoAtWork({
    metric_date_from: isoDaysAgo(RANGE_DAYS[range]),
  });

  const latest = useMemo(() => {
    const map = new Map<string, { value: number; detail: string }>();
    for (const metric of query.data?.metrics ?? []) {
      map.set(metric.metric_type, {
        value: metric.percentage,
        detail: `${metric.dp_1} / ${metric.dp_2}`,
      });
    }
    return map;
  }, [query.data]);

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
    /* h-full: Alerts sits beside this card and sets the row height, so without
       it the card stopped short and the page showed through the grid cell. */
    <div
      className="rounded-lg p-4 h-full min-w-0 flex flex-col transition-all duration-250 ease hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: cardShadow }}
    >
      <div className="flex items-center justify-between mb-4 shrink-0 gap-3">
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

      {/* Body starts at the top, the same contract every other dashboard panel
          uses (Energy, Occupancy, Alerts, Recent Activity). This card used to
          be the one exception -- `justify-center` floated the dials down the
          middle so their spare height sat above AND below them, which left its
          content on a different line from the Alerts list beside it.

          The dials are fixed size, so spare height has to go somewhere; it now
          collects at the bottom like any other short panel rather than pushing
          the content out of alignment with its neighbour. */}
      <div className="flex-1 min-h-0 min-w-0 flex flex-col">
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
    </div>
  );
};
