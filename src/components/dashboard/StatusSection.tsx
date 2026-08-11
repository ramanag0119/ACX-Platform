import { Building2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { useTheme } from "@/contexts/ThemeContext";

interface Building {
  id: string;
  name: string;
  floors: number;
  rooms: number;
}

interface Floor {
  id: string;
  name: string;
  buildingId: string;
}

interface Room {
  id: string;
  number: string;
  type: string;
  floorId: string;
}

interface StatusSectionProps {
  buildings: Building[];
  floors: Floor[];
  rooms: Room[];
  selectedBuilding: string | null;
  selectedFloor: string | null;
  selectedRoom: string | null;
  onBuildingSelect: (id: string) => void;
  onFloorSelect: (id: string) => void;
  onRoomSelect: (id: string) => void;
}

export const StatusSection = ({
  buildings, floors, rooms, selectedBuilding, selectedFloor, selectedRoom,
  onBuildingSelect, onFloorSelect, onRoomSelect,
}: StatusSectionProps) => {
  const { isDark } = useTheme();
  const filteredFloors = floors.filter((f) => f.buildingId === selectedBuilding);
  const filteredRooms = rooms.filter((r) => r.floorId === selectedFloor);

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#8A86A8";
  const selectBg = isDark ? "#252a3e" : "#FFFFFF";
  const selectBorder = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(124,92,255,0.12)";

  // Building card colors
  const bldDefaultBg = isDark ? "#252a3e" : "#F9FAFB";
  const bldSelectedBg = isDark ? "#1e3a5f" : "#E0E7FF";
  const bldDefaultBorder = isDark ? "#3a4158" : "#E5E7EB";
  const bldDefaultText = isDark ? "#dde2ed" : "#111827";
  const bldMutedText = isDark ? "#8b95a9" : "#6B7280";

  // Floor card colors
  const flrDefaultBg = isDark ? "#252a3e" : "#EEF2FF";
  const flrSelectedBg = isDark ? "#3d1f1f" : "#FEE2E2";
  const flrDefaultText = isDark ? "#dde2ed" : "#1F1B3A";
  const flrMutedText = isDark ? "#8b95a9" : "#5E5A7A";

  // Room card colors
  const rmDefaultBg = isDark ? "#252a3e" : "#F3F4F6";
  const rmDefaultText = isDark ? "#dde2ed" : "#1F1B3A";
  const rmMutedText = isDark ? "#8b95a9" : "#5E5A7A";

  return (
    <div className="space-y-4">
      {/* Status Header */}
      <div
        className="rounded-lg p-4 transition-all duration-250 ease hover:-translate-y-0.5"
        style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
      >
        <div className="flex items-center justify-between">
          <h3 style={{ color: titleColor }} className="font-medium">Status</h3>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[hsl(145,70%,45%)] hover:underline cursor-pointer">Good Health</span>
              <span style={{ color: mutedColor }}>|</span>
              <span className="text-[hsl(38,92%,50%)] hover:underline cursor-pointer">Warnings</span>
              <span style={{ color: mutedColor }}>|</span>
              <span className="text-[hsl(0,70%,50%)] hover:underline cursor-pointer">Error</span>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="affected" className="border-[#5E5A7A]/50" />
              <label htmlFor="affected" style={{ color: mutedColor }} className="text-sm">Affected Rooms</label>
            </div>
            <select
              className="text-sm px-3 py-1.5 rounded border-none outline-none transition-colors duration-200"
              style={{ backgroundColor: selectBg, color: titleColor, border: selectBorder }}
            >
              <option>Select All</option>
            </select>
          </div>
        </div>
      </div>

      {/* Buildings Section */}
      <div
        className="rounded-lg p-4 transition-all duration-250 ease hover:-translate-y-0.5"
        style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 style={{ color: titleColor }} className="font-medium">Building</h3>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-[hsl(145,70%,45%)] hover:underline cursor-pointer">Good Health</span>
            <span style={{ color: mutedColor }}>|</span>
            <span className="text-[hsl(38,92%,50%)] hover:underline cursor-pointer">Warnings</span>
            <span style={{ color: mutedColor }}>|</span>
            <span className="text-[hsl(0,70%,50%)] hover:underline cursor-pointer">Error</span>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {buildings.map((building) => (
            <div
              key={building.id}
              onClick={() => onBuildingSelect(building.id)}
              className="cursor-pointer rounded-lg p-4 text-center border transition-all duration-150 hover:-translate-y-0.5"
              style={{
                backgroundColor: selectedBuilding === building.id ? bldSelectedBg : bldDefaultBg,
                borderWidth: selectedBuilding === building.id ? "2px" : "1px",
                borderColor: selectedBuilding === building.id ? "#6366F1" : bldDefaultBorder,
                color: selectedBuilding === building.id ? (isDark ? "#a5b4fc" : "#1E1B4B") : bldDefaultText,
                boxShadow: selectedBuilding === building.id ? "0 4px 12px rgba(99, 102, 241, 0.2)" : "none"
              }}
              onMouseEnter={(e) => {
                if (selectedBuilding !== building.id) {
                  (e.currentTarget as HTMLDivElement).style.backgroundColor = isDark ? "#2e3450" : "#EEF2FF";
                  (e.currentTarget as HTMLDivElement).style.borderColor = isDark ? "#6366f1" : "#A5B4FC";
                }
              }}
              onMouseLeave={(e) => {
                if (selectedBuilding !== building.id) {
                  (e.currentTarget as HTMLDivElement).style.backgroundColor = bldDefaultBg;
                  (e.currentTarget as HTMLDivElement).style.borderColor = bldDefaultBorder;
                }
              }}
            >
              <div className="flex items-center justify-center gap-2 mb-3">
                <Building2 className="h-5 w-5" style={{ color: selectedBuilding === building.id ? (isDark ? "#a5b4fc" : "#1E1B4B") : bldDefaultText }} />
                <span className="font-medium" style={{ color: selectedBuilding === building.id ? (isDark ? "#a5b4fc" : "#1E1B4B") : bldDefaultText }}>
                  {building.name}
                </span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm" style={{ color: bldMutedText }}>Floors</span>
                  <span className="font-bold text-lg" style={{ color: selectedBuilding === building.id ? (isDark ? "#a5b4fc" : "#1E1B4B") : bldDefaultText }}>{building.floors}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm" style={{ color: bldMutedText }}>Rooms</span>
                  <span className="font-bold text-lg" style={{ color: selectedBuilding === building.id ? (isDark ? "#a5b4fc" : "#1E1B4B") : bldDefaultText }}>{building.rooms}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Floors Section */}
      {selectedBuilding && filteredFloors.length > 0 && (
        <div
          className="rounded-lg p-4 animate-fade-in transition-all duration-250 ease hover:-translate-y-0.5"
          style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 style={{ color: titleColor }} className="font-medium">Floor</h3>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[hsl(145,70%,45%)] hover:underline cursor-pointer">Good Health</span>
              <span style={{ color: mutedColor }}>|</span>
              <span className="text-[hsl(0,70%,50%)] hover:underline cursor-pointer">Error</span>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredFloors.map((floor) => (
              <div
                key={floor.id}
                onClick={() => onFloorSelect(floor.id)}
                className="cursor-pointer rounded-lg p-4 text-center border-2 transition-all duration-150 hover:-translate-y-0.5"
                style={{
                  backgroundColor: selectedFloor === floor.id ? flrSelectedBg : flrDefaultBg,
                  borderColor: selectedFloor === floor.id ? "#EF4444" : "transparent",
                  color: selectedFloor === floor.id ? (isDark ? "#fca5a5" : "#7F1D1D") : flrDefaultText,
                  boxShadow: selectedFloor === floor.id ? "0 4px 12px rgba(239, 68, 68, 0.2)" : "none"
                }}
                onMouseEnter={(e) => {
                  if (selectedFloor !== floor.id)
                    (e.currentTarget as HTMLDivElement).style.backgroundColor = isDark ? "#2e3450" : "#E6E9FF";
                }}
                onMouseLeave={(e) => {
                  if (selectedFloor !== floor.id)
                    (e.currentTarget as HTMLDivElement).style.backgroundColor = flrDefaultBg;
                }}
              >
                <p className="font-medium">{floor.name}</p>
                <p className="text-sm" style={{ color: selectedFloor === floor.id ? (isDark ? "#fca5a5" : "#7F1D1D") : flrMutedText }}>Floor</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Occupancy / Rooms Section */}
      {selectedFloor && filteredRooms.length > 0 && (
        <div
          className="rounded-lg p-4 animate-fade-in border transition-all duration-250 ease hover:-translate-y-0.5"
          style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 style={{ color: titleColor }} className="font-medium">Occupancy</h3>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[hsl(145,70%,45%)] hover:underline cursor-pointer">Good Health</span>
              <span style={{ color: mutedColor }}>|</span>
              <span className="text-[hsl(0,70%,50%)] hover:underline cursor-pointer">Error</span>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {filteredRooms.map((room) => {
              const isError = room.type.includes('Error') || room.type.includes('Maintenance');
              const defaultBg = isError ? (isDark ? "#3d1f1f" : "#FEE2E2") : rmDefaultBg;
              const selectedBg = isError ? (isDark ? "#3d1f1f" : "#FEE2E2") : (isDark ? "#1a3d2e" : "#DCFCE7");
              const selectedBorder = isError ? '#EF4444' : '#22C55E';
              const selectedText = isError ? (isDark ? "#fca5a5" : "#7F1D1D") : (isDark ? "#86efac" : "#065F46");
              const inactiveText = rmDefaultText;
              const muteText = rmMutedText;
              return (
                <div
                  key={room.id}
                  onClick={() => onRoomSelect(room.id)}
                  className="cursor-pointer rounded-lg p-4 text-center border-2 transition-all duration-150 hover:-translate-y-0.5"
                  style={{
                    backgroundColor: selectedRoom === room.id ? selectedBg : defaultBg,
                    borderColor: selectedRoom === room.id ? selectedBorder : 'transparent',
                    color: selectedRoom === room.id ? selectedText : inactiveText,
                    boxShadow: selectedRoom === room.id ? (isError ? '0 4px 12px rgba(239, 68, 68, 0.2)' : '0 4px 12px rgba(34, 197, 94, 0.2)') : 'none'
                  }}
                  onMouseEnter={(e) => {
                    if (selectedRoom !== room.id)
                      (e.currentTarget as HTMLDivElement).style.backgroundColor = isError ? (isDark ? "#4d2a2a" : "#FECACA") : (isDark ? "#2e3450" : "#E5E7EB");
                  }}
                  onMouseLeave={(e) => {
                    if (selectedRoom !== room.id)
                      (e.currentTarget as HTMLDivElement).style.backgroundColor = defaultBg;
                  }}
                >
                  <p className="font-bold text-lg" style={{ color: selectedRoom === room.id ? selectedText : inactiveText }}>{room.number}</p>
                  <p className="text-sm" style={{ color: selectedRoom === room.id ? selectedText : muteText }}>{room.type}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
