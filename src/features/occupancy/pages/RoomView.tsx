import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

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

  return (
    <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Room View</h1>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {statsData.map((stat, index) => (
          <Card key={index} className={`border-t-4 ${stat.borderColor} shadow-lg`}>
            <CardContent className="p-4">
              <p className={`text-sm ${index === 0 ? 'text-cyan-600' : 'text-muted-foreground'}`}>{stat.label}</p>
              <div className="mt-4 text-center">
                <span className="text-3xl font-bold text-cyan-600">{stat.value}</span>
                <p className="text-sm text-muted-foreground mt-1">{stat.unit}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Formula Legend */}
      <div className="text-right text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Current in House</span> = Total Occupied Rooms |
        <span className="font-medium text-foreground"> End of Day</span> = Total Available Rooms
      </div>

      {/* Current Status and Room Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Current Status Table */}
        <Card className="shadow-lg">
          <div className="bg-gradient-to-r from-[#5a5a5a] to-[#6a6a6a] text-white px-4 py-2 rounded-t-lg">
            <h2 className="text-sm font-medium">Current Status</h2>
          </div>
          <CardContent className="p-4">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dashed border-gray-300">
                  <th className="text-left py-2 text-sm font-medium text-muted-foreground"></th>
                  <th className="text-center py-2 text-sm font-medium text-muted-foreground">Room</th>
                  <th className="text-center py-2 text-sm font-medium text-muted-foreground">Percent(%)</th>
                </tr>
              </thead>
              <tbody>
                {currentStatusData.map((row, index) => (
                  <tr key={index} className="border-b border-dashed border-gray-200">
                    <td className={`py-2 text-sm ${row.isLink ? 'text-cyan-600 cursor-pointer hover:underline' : 'text-foreground'}`}>
                      {row.label}
                    </td>
                    <td className="text-center py-2 text-sm text-cyan-600">{row.room}</td>
                    <td className="text-center py-2 text-sm text-foreground">{row.percent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Room Status Pie Chart */}
        <Card className="shadow-lg">
          <div className="bg-gradient-to-r from-[#5a5a5a] to-[#6a6a6a] text-white px-4 py-2 rounded-t-lg">
            <h2 className="text-sm font-medium">Room Status</h2>
          </div>
          <CardContent className="p-4 flex items-center justify-center">
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
                  <span className="text-sm text-muted-foreground">Occupied</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                  <span className="text-sm text-muted-foreground">Vacant</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Status Bar */}
      <Card className="shadow-lg">
        <div className="bg-gradient-to-r from-[#5a5a5a] to-[#6a6a6a] text-white px-4 py-2 rounded-t-lg">
          <h2 className="text-sm font-medium">Status</h2>
        </div>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            {/* Status Legend */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-sm text-muted-foreground">Perfect</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-sm text-muted-foreground">Dirty</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
                <span className="text-sm text-muted-foreground">Maintenance</span>
              </div>
            </div>

            {/* Right Section */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-cyan-600">Occupied</span>
                <span className="text-gray-400">|</span>
                <span className="text-cyan-600">Available</span>
                <span className="text-gray-400">|</span>
                <span className="text-cyan-600">Dirty</span>
                <span className="text-gray-400">|</span>
                <span className="text-cyan-600">Maintenance</span>
              </div>
              <Select value={selectedFloor} onValueChange={setSelectedFloor}>
                <SelectTrigger className="w-40 h-8 bg-muted/30 border-border/50">
                  <SelectValue placeholder="Select All" />
                </SelectTrigger>
                <SelectContent className="bg-white">
                  <SelectItem value="select-all">Select All</SelectItem>
                  <SelectItem value="occupied">Occupied</SelectItem>
                  <SelectItem value="available">Available</SelectItem>
                  <SelectItem value="dirty-maintenance">Dirty / Maintenance</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RoomView;
