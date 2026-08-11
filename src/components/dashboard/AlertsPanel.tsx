import { List } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

export const AlertsPanel = () => {
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
      className="rounded-lg p-4 h-full transition-all duration-250 ease hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ color: titleColor }} className="font-medium">Alerts</h3>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-[hsl(199,89%,48%)] hover:underline cursor-pointer">Service</span>
            <span style={{ color: mutedColor }}>|</span>
            <span className="text-[hsl(199,89%,48%)] hover:underline cursor-pointer">Caleido</span>
          </div>
          <button style={{ color: mutedColor }} className="hover:opacity-100 opacity-70 transition-opacity">
            <List className="h-4 w-4" />
          </button>
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors duration-200"
            style={{ backgroundColor: selectBg, color: titleColor, border: selectBorder }}
          >
            <option>Today</option>
            <option>Week</option>
            <option>Month</option>
          </select>
        </div>
      </div>

      <div className="flex items-center justify-center h-[120px]">
        <p style={{ color: mutedColor }} className="text-sm">No alerts found</p>
      </div>
    </div>
  );
};
