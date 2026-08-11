import { RefreshCw } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { useTheme } from "@/core/contexts/ThemeContext";

const data = [
  { name: "Occupied", value: 94, color: "hsl(145,70%,45%)" },
  { name: "Vacant", value: 6, color: "hsl(0,70%,50%)" },
];

export const OccupancyStatisticsChart = () => {
  const { isDark } = useTheme();

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const selectBg = isDark ? "#252a3e" : "#FFFFFF";
  const selectBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";
  const tooltipBg = isDark ? "#1e2233" : "#FFFFFF";

  return (
    <div
      className="rounded-[16px] p-4 transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium" style={{ color: titleColor }}>Occupancy Statistics</h3>
        <div className="flex items-center gap-2">
          <select
            className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors"
            style={{ background: selectBg, color: titleColor, border: selectBorder }}
          >
            <option>Today</option>
            <option>Week</option>
            <option>Month</option>
          </select>
          <button className="transition-colors" style={{ color: mutedColor }}>
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="relative w-[160px] h-[160px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
                startAngle={90}
                endAngle={-270}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: tooltipBg,
                  border: "1px solid rgba(124,92,255,0.12)",
                  borderRadius: "8px",
                  color: titleColor,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[hsl(0,70%,50%)] text-xs font-medium">6%</span>
            <span className="text-[hsl(145,70%,45%)] text-lg font-bold">94%</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[hsl(0,70%,50%)] rounded-sm" />
            <span className="text-sm" style={{ color: mutedColor }}>Vacant</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[hsl(145,70%,45%)] rounded-sm" />
            <span className="text-sm" style={{ color: mutedColor }}>Occupied</span>
          </div>
        </div>
      </div>
    </div>
  );
};
