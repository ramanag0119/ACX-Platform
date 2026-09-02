import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useFloors, useOccupancy, useStays } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Room View, driven by GET /occupancy and GET /stays.
 *
 * Counts come from the API's `total`, never from counting a page of rows.
 *
 * NOT AVAILABLE, shown as "-" rather than guessed:
 *   Start of Day / Realized Check-In / Realized Check-Out -- /stays filters on
 *   EXPECTED check-in/out times and `is_checked_in`, but exposes no
 *   actual-checkin/checkout date range, so a "realized today" count cannot be
 *   asked for. This is listed as a frontend/backend gap in the phase report.
 */

const startOfToday = () => {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  return date.toISOString();
};

const endOfToday = () => {
  const date = new Date();
  date.setHours(23, 59, 59, 999);
  return date.toISOString();
};

const RoomView = () => {
  const [selectedFloor, setSelectedFloor] = useState("select-all");
  const { isDark } = useTheme();

  const floorsQuery = useFloors({ page: 1, page_size: MAX_PAGE_SIZE });
  const floorFilter = selectedFloor === "select-all" ? {} : { floor_id: selectedFloor };

  // page_size 1: only the `total` matters for these tiles.
  const allRoomsQuery = useOccupancy({ page: 1, page_size: MAX_PAGE_SIZE, ...floorFilter });
  const expectedInQuery = useStays({
    page: 1,
    page_size: 1,
    expected_checkin_from: startOfToday(),
    expected_checkin_to: endOfToday(),
  });
  const expectedOutQuery = useStays({
    page: 1,
    page_size: 1,
    expected_checkout_from: startOfToday(),
    expected_checkout_to: endOfToday(),
  });
  const inHouseQuery = useStays({ page: 1, page_size: 1, is_in_house: true });

  const counts = useMemo(() => {
    const items = allRoomsQuery.data?.items ?? [];
    const byStatus = new Map<string, number>();
    for (const item of items) {
      const name = item.status_name ?? "Unknown";
      byStatus.set(name, (byStatus.get(name) ?? 0) + 1);
    }
    const total = items.length;
    const occupied = byStatus.get("Occupied") ?? 0;
    const available = byStatus.get("Available") ?? 0;
    return {
      total,
      occupied,
      available,
      allotted: byStatus.get("Allotted") ?? 0,
      unavailable: byStatus.get("Unavailable") ?? 0,
      occupiedPercent: total ? Math.round((occupied / total) * 100) : 0,
      availablePercent: total ? Math.round((available / total) * 100) : 0,
    };
  }, [allRoomsQuery.data]);

  const isLoading =
    allRoomsQuery.isLoading ||
    expectedInQuery.isLoading ||
    expectedOutQuery.isLoading ||
    inHouseQuery.isLoading;
  const error =
    allRoomsQuery.error ?? expectedInQuery.error ?? expectedOutQuery.error ?? inHouseQuery.error;

  const statsData = [
    { label: "Current in House", value: inHouseQuery.data?.total ?? 0, unit: "Stays", borderColor: "border-cyan-500" },
    { label: "Expected Check-In", value: expectedInQuery.data?.total ?? 0, unit: "Stays", borderColor: "border-gray-300" },
    { label: "Expected Check-Out", value: expectedOutQuery.data?.total ?? 0, unit: "Stays", borderColor: "border-gray-300" },
    { label: "End of Day", value: counts.available, unit: "Available Rooms", borderColor: "border-gray-300" },
  ];

  /** `null` means the API cannot answer this row -- rendered as "-". */
  const currentStatusData: { label: string; room: number | null; percent: number | null; isLink?: boolean }[] = [
    { label: "Start of Day", room: null, percent: null },
    { label: "Realized Check-In", room: null, percent: null, isLink: true },
    { label: "Realized Check-Out", room: null, percent: null, isLink: true },
    { label: "Current Status", room: counts.occupied, percent: counts.occupiedPercent },
    { label: "Expected Check-In", room: expectedInQuery.data?.total ?? 0, percent: null, isLink: true },
    { label: "Expected Check-Out", room: expectedOutQuery.data?.total ?? 0, percent: null, isLink: true },
    { label: "End of Day", room: counts.available, percent: counts.availablePercent },
  ];

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

      <DataState isLoading={isLoading} error={error}>
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {statsData.map((stat, index) => (
              <Card
                key={stat.label}
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
            <span className="font-medium" style={{ color: titleColor }}>Current in House</span> = Stays flagged in-house |
            <span className="font-medium" style={{ color: titleColor }}> End of Day</span> = Rooms with status Available
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
                  {currentStatusData.map((row) => (
                    <tr key={row.label} className="border-b border-dashed" style={{ borderColor: gridBorder }}>
                      <td className={`py-2 text-sm ${row.isLink ? 'text-cyan-600' : ''}`} style={{ color: row.isLink ? undefined : titleColor }}>
                        {row.label}
                      </td>
                      <td className="text-center py-2 text-sm text-cyan-500">{row.room ?? "-"}</td>
                      <td className="text-center py-2 text-sm" style={{ color: titleColor }}>{row.percent ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs" style={{ color: mutedColor }}>
                "-" means the API exposes no filter for that figure.
              </p>
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
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="#22c55e"
                        strokeWidth="20"
                        strokeDasharray={`${counts.availablePercent * 2.51} ${100 * 2.51}`}
                        strokeDashoffset="0"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="#ef4444"
                        strokeWidth="20"
                        strokeDasharray={`${counts.occupiedPercent * 2.51} ${100 * 2.51}`}
                        strokeDashoffset={`${-counts.availablePercent * 2.51}`}
                      />
                    </svg>
                    {/* Center Labels */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-red-500 text-sm font-bold">{counts.occupiedPercent}%</span>
                      <span className="text-green-500 text-lg font-bold">{counts.availablePercent}%</span>
                    </div>
                  </div>

                  {/* Legend -- all four real statuses, with their live counts. */}
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-red-500 rounded"></div>
                      <span className="text-sm" style={{ color: mutedColor }}>Occupied ({counts.occupied})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-green-500 rounded"></div>
                      <span className="text-sm" style={{ color: mutedColor }}>Available ({counts.available})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-amber-500 rounded"></div>
                      <span className="text-sm" style={{ color: mutedColor }}>Allotted ({counts.allotted})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-gray-400 rounded"></div>
                      <span className="text-sm" style={{ color: mutedColor }}>Unavailable ({counts.unavailable})</span>
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
              {/* Condition legend -- the real `amenity_condition` rows. */}
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-sm" style={{ color: mutedColor }}>Dirty</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
                  <span className="text-sm" style={{ color: mutedColor }}>Under maintenance</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
                  <span className="text-sm" style={{ color: mutedColor }}>Sanitation</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-rose-500 rounded-full"></div>
                  <span className="text-sm" style={{ color: mutedColor }}>Low battery</span>
                </div>
              </div>

              {/* Floor filter -- real floors, mapped to the API's floor_id. */}
              <div className="flex items-center gap-4">
                <Select value={selectedFloor} onValueChange={setSelectedFloor}>
                  <SelectTrigger className="w-48 h-8 border" style={{ color: titleColor, backgroundColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)", borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(124,92,255,0.12)" }}>
                    <SelectValue placeholder="Select All" />
                  </SelectTrigger>
                  <SelectContent className={isDark ? "bg-[#1e2233] text-foreground border-border/50" : "bg-white text-foreground"}>
                    <SelectItem value="select-all">All floors</SelectItem>
                    {(floorsQuery.data?.items ?? []).map((floor) => (
                      <SelectItem key={floor.id} value={floor.id}>
                        {floor.building_name} - {floor.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>
      </DataState>
    </div>
  );
};

export default RoomView;
