import { useState } from "react";
import { EnergyConsumptionChart } from "@/components/dashboard/EnergyConsumptionChart";
import { OccupancyStatisticsChart } from "@/components/dashboard/OccupancyStatisticsChart";
import { CaleidoAtWork } from "@/components/dashboard/CaleidoAtWork";
import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { StatusSection } from "@/components/dashboard/StatusSection";
import { RoomDetailsPanel } from "@/components/dashboard/RoomDetailsPanel";
import { useTheme } from "@/contexts/ThemeContext";

// Sample data
const buildings = [
  { id: "1", name: "Building A", floors: 5, rooms: 36 },
  { id: "2", name: "Demo Box", floors: 4, rooms: 5 },
  { id: "3", name: "Dev & Testing", floors: 3, rooms: 28 },
  { id: "4", name: "Building D PILOT", floors: 2, rooms: 5 },
];

const floors = [
  { id: "f1", name: "US Demo", buildingId: "2" },
  { id: "f2", name: "Demo", buildingId: "2" },
  { id: "f3", name: "Senthil MDU Room", buildingId: "2" },
  { id: "f4", name: "Senthil USA", buildingId: "2" },
  { id: "f5", name: "Floor 1", buildingId: "1" },
  { id: "f6", name: "Floor 2", buildingId: "1" },
];

const rooms = [
  { id: "r1", number: "211", type: "Guest Room", floorId: "f2" },
  { id: "r2", number: "212", type: "Guest Room", floorId: "f2" },
  { id: "r3", number: "101", type: "Guest Room", floorId: "f1" },
];

const Dashboard = () => {
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<string | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);

  const handleBuildingSelect = (id: string) => {
    setSelectedBuilding(id);
    setSelectedFloor(null);
    setSelectedRoom(null);
  };

  const handleFloorSelect = (id: string) => {
    setSelectedFloor(id);
    setSelectedRoom(null);
  };

  const handleRoomSelect = (id: string) => {
    setSelectedRoom(id);
  };

  const selectedRoomData = rooms.find((r) => r.id === selectedRoom);
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

      {/* Status Section with Buildings, Floors, Rooms */}
      <StatusSection
        buildings={buildings}
        floors={floors}
        rooms={rooms}
        selectedBuilding={selectedBuilding}
        selectedFloor={selectedFloor}
        selectedRoom={selectedRoom}
        onBuildingSelect={handleBuildingSelect}
        onFloorSelect={handleFloorSelect}
        onRoomSelect={handleRoomSelect}
      />

      {/* Room Details Panel - Only show when room is selected */}
      {selectedRoom && selectedRoomData && (
        <RoomDetailsPanel
          roomNumber={selectedRoomData.number}
          roomType={selectedRoomData.type}
        />
      )}
    </div>
  );
};

export default Dashboard;
