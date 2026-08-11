import { RefreshCw } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";

interface CircularProgressProps {
  value: number;
  label: string;
  color: string;
  showDash?: boolean;
  isDark: boolean;
}

const CircularProgress = ({ value, label, color, showDash, isDark }: CircularProgressProps) => {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;
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
      </div>
    </div>
  );
};

export const CaleidoAtWork = () => {
  const { isDark } = useTheme();

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
          >
            <option>Today</option>
            <option>Week</option>
            <option>Month</option>
          </select>
          <button style={{ color: mutedColor }} className="hover:opacity-100 opacity-70 transition-opacity">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <CircularProgress value={0} label="Smart Rooms Online" color="hsl(0,70%,50%)" isDark={isDark} />
        <CircularProgress value={0} label="Service Request Status" color="hsl(145,70%,45%)" showDash isDark={isDark} />
        <CircularProgress value={0} label="Rooms For Check-Out" color="hsl(145,70%,45%)" showDash isDark={isDark} />
        <CircularProgress value={0} label="Pending Bookings" color="hsl(145,70%,45%)" showDash isDark={isDark} />
      </div>
    </div>
  );
};
