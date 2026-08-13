import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTheme } from "@/core/contexts/ThemeContext";

// Stat card data
const statsData = [
  { label: "Current in House", value: 2, unit: "Rooms", borderColor: "border-cyan-500" },
  { label: "Expected Check-In", value: 0, unit: "Rooms", borderColor: "border-gray-300" },
  { label: "Expected Check-Out", value: 0, unit: "Rooms", borderColor: "border-gray-300" },
  { label: "End of Day", value: 10, unit: "Available Rooms", borderColor: "border-gray-300" },
];

// Current status table data
const currentStatusData = [
  { label: "Start of Day", room: 0, percent: 0 },
  { label: "Realized Check-In", room: 0, percent: 0, isLink: true },
  { label: "Realized Check-Out", room: 0, percent: 0, isLink: true },
  { label: "Current Status", room: 0, percent: 0 },
  { label: "Expected Check-In", room: 0, percent: 0, isLink: true },
  { label: "Expected Check-Out", room: 0, percent: 0, isLink: true },
  { label: "End of Day", room: 0, percent: 0 },
];

// Pie chart data
const pieData = {
  occupied: 17,
  vacant: 83,
};

const RoomView = () => {
  const [selectedFloor, setSelectedFloor] = useState("select");
  const { isDark } = useTheme();

  const pageBg = isDark ? "linear-gradient(180deg, #0f1117, #131824)" : "linear-gradient(180deg, #F4F2FA, #ECE9F6)";
  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#5E5A7A";
  const gridBorder = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)";

  return (
    <div className="space-y-6 animate-fade-in min-h-screen -m-6 p-6" style={{ background: pageBg }}>
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold" style={{ color: titleColor }}>Room View</h1>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {statsData.map((stat, index) => (
          <Card
            key={index}
            className={`border-t-4 ${stat.borderColor} shadow-lg`}
            style={{
              background: cardBg,
              borderLeft: cardBorder,
              borderRight: cardBorder,
              borderBottom: cardBorder,
              boxShadow: "0 8px 24px rgba(17,12,46,0.08)"
            }}
          >
            <CardContent className="p-4">
              <p className="text-sm font-medium" style={{ color: index === 0 ? "hsl(199, 89%, 48%)" : mutedColor }}>{stat.label}</p>
              <div className="mt-4 text-center">
                <span className="text-3xl font-bold" style={{ color: "hsl(199, 89%, 48%)" }}>{stat.value}</span>
                <p className="text-sm mt-1" style={{ color: mutedColor }}>{stat.unit}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Formula Legend */}
      <div className="text-right text-sm" style={{ color: mutedColor }}>
        <span className="font-medium" style={{ color: titleColor }}>Current in House</span> = Total Occupied Rooms |
        <span className="font-medium" style={{ color: titleColor }}> End of Day</span> = Total Available Rooms
      </div>

      {/* Current Status and Room Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Current Status Table */}
        <div
          className="rounded-lg p-5 transition-all duration-250 ease hover:-translate-y-0.5"
          style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 style={{ color: titleColor }} className="font-medium">Current Status</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-dashed" style={{ borderColor: gridBorder }}>
                <th className="text-left py-2 text-sm font-medium" style={{ color: mutedColor }}></th>
                <th className="text-center py-2 text-sm font-medium" style={{ color: mutedColor }}>Room</th>
                <th className="text-center py-2 text-sm font-medium" style={{ color: mutedColor }}>Percent(%)</th>
              </tr>
            </thead>
            <tbody>
              {currentStatusData.map((row, index) => (
                <tr key={index} className="border-b border-dashed" style={{ borderColor: gridBorder }}>
                  <td className={`py-2 text-sm ${row.isLink ? 'text-cyan-600 cursor-pointer hover:underline' : ''}`} style={{ color: row.isLink ? undefined : titleColor }}>
                    {row.label}
                  </td>
                  <td className="text-center py-2 text-sm text-cyan-500">{row.room}</td>
                  <td className="text-center py-2 text-sm" style={{ color: titleColor }}>{row.percent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Room Status Pie Chart */}
        <div
          className="rounded-lg p-5 transition-all duration-250 ease hover:-translate-y-0.5"
          style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 style={{ color: titleColor }} className="font-medium">Room Status</h3>
          </div>
          <div className="flex items-center justify-center py-4">
            <div className="flex items-center gap-8">
              {/* Pie Chart */}
              <div className="relative w-40 h-40">
                <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                  {/* Vacant (Green) - 83% */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="transparent"
                    stroke="#22c55e"
                    strokeWidth="20"
                    strokeDasharray={`${pieData.vacant * 2.51} ${100 * 2.51}`}
                    strokeDashoffset="0"
                  />
                  {/* Occupied (Red) - 17% */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="transparent"
                    stroke="#ef4444"
                    strokeWidth="20"
                    strokeDasharray={`${pieData.occupied * 2.51} ${100 * 2.51}`}
                    strokeDashoffset={`${-pieData.vacant * 2.51}`}
                  />
                </svg>
                {/* Center Labels */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-red-500 text-sm font-bold">{pieData.occupied}%</span>
                  <span className="text-green-500 text-lg font-bold">{pieData.vacant}%</span>
                </div>
              </div>

              {/* Legend */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500 rounded"></div>
                  <span className="text-sm" style={{ color: mutedColor }}>Occupied</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                  <span className="text-sm" style={{ color: mutedColor }}>Vacant</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div
        className="rounded-lg p-5 transition-all duration-250 ease hover:-translate-y-0.5"
        style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
      >
        <div className="flex items-center justify-between">
          {/* Status Legend */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-sm" style={{ color: mutedColor }}>Perfect</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span className="text-sm" style={{ color: mutedColor }}>Dirty</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
              <span className="text-sm" style={{ color: mutedColor }}>Maintenance</span>
            </div>
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-cyan-600 font-medium">Occupied</span>
              <span style={{ color: gridBorder }}>|</span>
              <span className="text-cyan-600 font-medium">Available</span>
              <span style={{ color: gridBorder }}>|</span>
              <span className="text-cyan-600 font-medium">Dirty</span>
              <span style={{ color: gridBorder }}>|</span>
              <span className="text-cyan-600 font-medium">Maintenance</span>
            </div>
            <Select value={selectedFloor} onValueChange={setSelectedFloor}>
              <SelectTrigger className="w-40 h-8 border" style={{ color: titleColor, backgroundColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)", borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(124,92,255,0.12)" }}>
                <SelectValue placeholder="Select All" />
              </SelectTrigger>
              <SelectContent className={isDark ? "bg-[#1e2233] text-foreground border-border/50" : "bg-white text-foreground"}>
                <SelectItem value="select-all">Select All</SelectItem>
                <SelectItem value="occupied">Occupied</SelectItem>
                <SelectItem value="available">Available</SelectItem>
                <SelectItem value="dirty-maintenance">Dirty / Maintenance</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RoomView;
