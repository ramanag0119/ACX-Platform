import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useAmenityConditions, useFloors, useOccupancySummary } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { conditionLabel, roomStatusColor } from "../lib/roomStatus";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";

/**
 * Room View, driven by authoritative database-aggregated GET /occupancy/summary.
 *
 * All room counts and daily operational metrics are computed directly by PostgreSQL
 * aggregate queries covering the entire authorized property/floor scope, completely
 * eliminating the 100-record pagination limitation and null placeholder rows.
 */

const RoomView = () => {
  const [selectedFloor, setSelectedFloor] = useState("select-all");
  const { isDark } = useTheme();

  const floorsQuery = useFloors({ page: 1, page_size: MAX_PAGE_SIZE });
  const conditionsQuery = useAmenityConditions();
  const floorFilter = selectedFloor === "select-all" ? {} : { floor_id: selectedFloor };

  const summaryQuery = useOccupancySummary({
    amenity_category: "room",
    ...floorFilter,
  });

  const summary = summaryQuery.data;
  const daily = summary?.daily_metrics;

  const counts = useMemo(() => {
    const total = summary?.total_rooms ?? 0;
    const occupied = summary?.occupied ?? 0;
    const available = summary?.available ?? 0;
    const allotted = summary?.allotted ?? 0;
    const unavailable = summary?.unavailable ?? 0;
    const unknown = summary?.unknown ?? 0;
    return {
      total,
      occupied,
      available,
      allotted,
      unavailable,
      unknown,
      occupiedPercent: summary?.occupied_percent ?? 0,
      availablePercent: summary?.available_percent ?? 0,
    };
  }, [summary]);

  const isLoading = summaryQuery.isLoading || floorsQuery.isLoading;
  const error = summaryQuery.error || floorsQuery.error;

  const statsData = [
    {
      label: "Current in House",
      value: daily?.current_status ?? counts.occupied,
      unit: "Stays",
      borderColor: "border-cyan-500",
    },
    {
      label: "Expected Check-In",
      value: daily?.expected_check_in ?? 0,
      unit: "Stays",
      borderColor: "border-gray-300",
    },
    {
      label: "Expected Check-Out",
      value: daily?.expected_check_out ?? 0,
      unit: "Stays",
      borderColor: "border-gray-300",
    },
    {
      label: "End of Day",
      value: daily?.end_of_day ?? counts.available,
      unit: "Available Rooms",
      borderColor: "border-gray-300",
    },
  ];

  /** Database-derived daily metrics — zero artificial null placeholders. */
  const currentStatusData: { label: string; room: number; percent: number; isLink?: boolean }[] = [
    {
      label: "Start of Day",
      room: daily?.start_of_day ?? 0,
      percent: daily?.start_of_day_percent ?? 0,
    },
    {
      label: "Realized Check-In",
      room: daily?.realized_check_in ?? 0,
      percent: daily?.realized_check_in_percent ?? 0,
      isLink: true,
    },
    {
      label: "Realized Check-Out",
      room: daily?.realized_check_out ?? 0,
      percent: daily?.realized_check_out_percent ?? 0,
      isLink: true,
    },
    {
      label: "Current Status",
      room: daily?.current_status ?? counts.occupied,
      percent: daily?.current_status_percent ?? counts.occupiedPercent,
    },
    {
      label: "Expected Check-In",
      room: daily?.expected_check_in ?? 0,
      percent: daily?.expected_check_in_percent ?? 0,
      isLink: true,
    },
    {
      label: "Expected Check-Out",
      room: daily?.expected_check_out ?? 0,
      percent: daily?.expected_check_out_percent ?? 0,
      isLink: true,
    },
    {
      label: "End of Day",
      room: daily?.end_of_day ?? counts.available,
      percent: daily?.end_of_day_percent ?? counts.availablePercent,
    },
  ];

  const {
    cardBg,
    cardBorder,
    cardShadow,
    titleColor,
    textMuted: mutedColor,
  } = useSurfaceTokens();
  const gridBorder = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)";

  return (
    <div className="space-y-5 animate-fade-in text-foreground">
      <PageHeader title="Room View" />

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
              style={{ background: cardBg, border: cardBorder, boxShadow: cardShadow }}
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
                Authoritative database-driven metrics across all authorized rooms.
              </p>
            </div>

            {/* Room Status Pie Chart */}
            <div
              className="rounded-lg p-5 transition-all duration-250 ease hover:-translate-y-0.5"
              style={{ background: cardBg, border: cardBorder, boxShadow: cardShadow }}
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
                        stroke={roomStatusColor("Available")}
                        strokeWidth="20"
                        strokeDasharray={`${counts.availablePercent * 2.51} ${100 * 2.51}`}
                        strokeDashoffset="0"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke={roomStatusColor("Occupied")}
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

                  {/* Legend -- all real statuses, with their live counts.
                      Swatches come from the module's shared status colours. */}
                  <div className="flex flex-col gap-2">
                    {[
                      { status: "Occupied", count: counts.occupied },
                      { status: "Available", count: counts.available },
                      { status: "Allotted", count: counts.allotted },
                      { status: "Unavailable", count: counts.unavailable },
                      ...(counts.unknown > 0 ? [{ status: "Unknown", count: counts.unknown }] : []),
                    ].map(({ status, count }) => (
                      <div key={status} className="flex items-center gap-2">
                        <div
                          className="w-4 h-4 rounded"
                          style={{ background: roomStatusColor(status) }}
                        />
                        <span className="text-sm" style={{ color: mutedColor }}>
                          {status} ({count})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Status Bar */}
          <div className="py-2">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              {/* Condition legend -- the real `amenity_condition` rows with database-driven labels. */}
              <div className="flex items-center gap-6">
                {(conditionsQuery.data?.items?.length
                  ? conditionsQuery.data.items.filter((c) => c.name.toLowerCase() !== "ready for occupant").slice(0, 4)
                  : [
                      { id: 1, name: "Dirty", display_name: "Need Maintenance" },
                      { id: 3, name: "Under maintenance", display_name: "Under Maintenance" },
                      { id: 4, name: "Sanitation", display_name: "Sanitation Required" },
                      { id: 2, name: "Low battery", display_name: "Low Battery" },
                    ]
                ).map((cond) => {
                  const dotColor =
                    cond.id === 1
                      ? "bg-red-500"
                      : cond.id === 3
                      ? "bg-amber-500"
                      : cond.id === 4
                      ? "bg-emerald-500"
                      : "bg-rose-500";
                  return (
                    <div key={cond.id} className="flex items-center gap-2">
                      <div className={`w-3 h-3 ${dotColor} rounded-full`}></div>
                      <span className="text-sm" style={{ color: mutedColor }}>
                        {conditionLabel(cond)}
                      </span>
                    </div>
                  );
                })}
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
