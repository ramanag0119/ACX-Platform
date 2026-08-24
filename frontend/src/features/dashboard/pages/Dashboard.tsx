import { useMemo, useState } from "react";
import { EnergyConsumptionChart } from "../components/EnergyConsumptionChart";
import { OccupancyStatisticsChart } from "@/features/occupancy/components/OccupancyStatisticsChart";
import { CaleidoAtWork } from "../components/CaleidoAtWork";
import { AlertsPanel } from "../components/AlertsPanel";
import { RecentActivityPanel } from "../components/RecentActivityPanel";
import { DashboardKPIs } from "../components/DashboardKPIs";
import { StatusSection } from "../components/StatusSection";
import { RoomDetailsPanel } from "@/features/occupancy/components/RoomDetailsPanel";
import { useTheme } from "@/core/contexts/ThemeContext";
import { useAuth } from "@/core/contexts/AuthContext";
import { DataState } from "@/core/components/DataState";
import { useBuildings } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Building and floor are PROJECTIONS over `property` + `property_chain`, not
 * tables. `floor_count` / `room_count` are counted by the backend; nothing on
 * this page is computed from invented data.
 *
 * Widgets each own their query, so one failing endpoint degrades its own box
 * and nothing else. Floors and rooms are no longer fetched wholesale and
 * filtered here -- StatusSection asks the backend with `building_id` /
 * `floor_id`, so the drill-down cannot silently truncate.
 */
const Dashboard = () => {
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<string | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);
  const [affectedOnly, setAffectedOnly] = useState(false);

  const { canRead } = useAuth();
  const buildingsQuery = useBuildings(
    canRead("facility_management") ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
  );

  const buildings = useMemo(
    () =>
      (buildingsQuery.data?.items ?? []).map((building) => ({
        id: building.id,
        name: building.name,
        floors: building.floor_count,
        rooms: building.room_count,
      })),
    [buildingsQuery.data],
  );

  const handleBuildingSelect = (id: string) => {
    setSelectedBuilding(id);
    setSelectedFloor(null);
    setSelectedRoom(null);
  };

  const handleFloorSelect = (id: string) => {
    setSelectedFloor(id);
    setSelectedRoom(null);
  };

  const { isDark } = useTheme();
  const pageBg = isDark ? "linear-gradient(180deg, #0f1117, #131824)" : "linear-gradient(180deg, #F4F2FA, #ECE9F6)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const subtitleColor = isDark ? "#8b95a9" : "#5E5A7A";

  return (
    <div className="space-y-4 animate-fade-in min-h-screen -m-6 p-6" style={{ background: pageBg }}>
      {/* Page Header */}
      <div className="mb-4">
        <h1 className="text-xl font-semibold" style={{ color: titleColor }}>Dashboard</h1>
        <p className="text-sm mt-0.5" style={{ color: subtitleColor }}>
          Welcome back! Here's an overview of your property operations.
        </p>
      </div>

      {/* KPI row - every figure is a backend total */}
      <DashboardKPIs />

      {/* Top Row - Charts */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <EnergyConsumptionChart />
        </div>
        <div>
          <OccupancyStatisticsChart />
        </div>
      </div>

      {/* Second Row - Caleido & Alerts */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <CaleidoAtWork />
        </div>
        <div>
          <AlertsPanel />
        </div>
      </div>

      {/* Third Row - Recent activity */}
      {canRead("dashboard") && (
        <div className="grid gap-4 grid-cols-1">
          <RecentActivityPanel />
        </div>
      )}

      {/* Status Section with Buildings, Floors, Rooms */}
      <DataState
        isLoading={buildingsQuery.isLoading}
        error={buildingsQuery.error}
        isEmpty={buildings.length === 0}
        emptyTitle="No buildings configured"
        emptyDescription="No property chain rows resolve to a building for this facility."
      >
        <StatusSection
          buildings={buildings}
          selectedBuilding={selectedBuilding}
          selectedFloor={selectedFloor}
          selectedRoom={selectedRoom}
          affectedOnly={affectedOnly}
          onBuildingSelect={handleBuildingSelect}
          onFloorSelect={handleFloorSelect}
          onRoomSelect={setSelectedRoom}
          onAffectedOnlyChange={setAffectedOnly}
        />
      </DataState>

      {/* Room Details Panel - Only show when room is selected */}
      {selectedRoom && <RoomDetailsPanel amenityId={selectedRoom} />}
    </div>
  );
};

export default Dashboard;
