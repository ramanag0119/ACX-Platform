import { RefreshCw } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useTheme } from "@/contexts/ThemeContext";

const data = [
  { name: "Mon", avgEnergy: 0.2, perRoom: 0.3 },
  { name: "Tue", avgEnergy: 0.4, perRoom: 0.5 },
  { name: "Wed", avgEnergy: 0.3, perRoom: 0.4 },
  { name: "Thu", avgEnergy: 0.6, perRoom: 0.7 },
  { name: "Fri", avgEnergy: 0.5, perRoom: 0.6 },
  { name: "Sat", avgEnergy: 0.4, perRoom: 0.5 },
  { name: "Sun", avgEnergy: 0.3, perRoom: 0.4 },
];

export const EnergyConsumptionChart = () => {
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
  const tooltipBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";
  const gridStroke = isDark ? "rgba(255,255,255,0.06)" : "rgba(124,92,255,0.1)";

  return (
    <div
      className="rounded-[16px] p-4 transition-all duration-250 hover:transform hover:-translate-y-0.5"
      style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium" style={{ color: titleColor }}>Average Energy Consumption</h3>
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

      <div className="flex items-center justify-center gap-6 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-[hsl(35,90%,50%)] rounded-sm" />
          <span className="text-xs" style={{ color: mutedColor }}>Average energy (all rooms)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-[hsl(145,70%,45%)] rounded-sm" />
          <span className="text-xs" style={{ color: mutedColor }}>Energy consumption (per room)</span>
        </div>
      </div>

      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: mutedColor, fontSize: 11 }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fill: mutedColor, fontSize: 11 }} domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]} />
            <Tooltip
              contentStyle={{
                background: tooltipBg,
                border: tooltipBorder,
                borderRadius: "8px",
                color: titleColor,
                boxShadow: "0 8px 24px rgba(17,12,46,0.12)"
              }}
            />
            <Bar dataKey="avgEnergy" fill="hsl(35,90%,50%)" radius={[2, 2, 0, 0]} />
            <Bar dataKey="perRoom" fill="hsl(145,70%,45%)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
