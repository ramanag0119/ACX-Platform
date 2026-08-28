import { useMemo } from "react";
import { Building2, Info } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { useTheme } from "@/core/contexts/ThemeContext";
import { useAuth } from "@/core/contexts/AuthContext";
import { DataState, InlineLoading } from "@/core/components/DataState";
import { useCount, useFloors, useOccupancy } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { QueryParams } from "@/lib/api/client";

/**
 * Building -> floor -> room drill-down, filtered BY THE BACKEND at every level.
 *
 * Floors are fetched with `?building_id=`, rooms with `?floor_id=`; neither is
 * a client-side pass over an unbounded list, so the drill-down stays correct
 * for a property with more rooms than one page holds.
 *
 * Two things the previous version showed are gone because the schema does not
 * back them:
 *
 *   - The "Good Health | Warnings | Error" legends were static text. Device
 *     health in `device_health_status` has exactly TWO values, Active and
 *     Inactive; there is no warning or error state. The real Active/Inactive
 *     counts for the selected scope are shown instead.
 *   - Room tiles were coloured by `room.type.includes('Error')` -- a guess at
 *     health from an amenity TYPE NAME. Tiles are now coloured by the room's
 *     real `amenity_status`, the same four values the occupancy chart uses.
 *
 * "Affected rooms" is a real condition: at least one active `amenity_condition`
 * (Dirty, Low battery, Under maintenance, Sanitation) on the room.
 */

interface Building {
  id: string;
  name: string;
  floors: number;
  rooms: number;
}

interface StatusSectionProps {
  buildings: Building[];
  selectedBuilding: string | null;
  selectedFloor: string | null;
  selectedRoom: string | null;
  affectedOnly: boolean;
  onBuildingSelect: (id: string) => void;
  onFloorSelect: (id: string) => void;
  onRoomSelect: (id: string) => void;
  onAffectedOnlyChange: (value: boolean) => void;
}

/** The four `amenity_status` rows, coloured as on the occupancy chart. */
const STATUS_TINT: Record<string, { light: string; dark: string; border: string; text: string }> = {
  Available: { light: "#E0F2FE", dark: "#12354a", border: "#38BDF8", text: "#075985" },
  Occupied: { light: "#DCFCE7", dark: "#12341f", border: "#22C55E", text: "#065F46" },
  Allotted: { light: "#FEF3C7", dark: "#3a2e12", border: "#F59E0B", text: "#78350F" },
  Unavailable: { light: "#FEE2E2", dark: "#3d1f1f", border: "#EF4444", text: "#7F1D1D" },
};

/**
 * The real device-health split for a scope, as two backend COUNT(*) calls
 * against the `device_health_status` enum. Rendered only where the role can
 * read the device module; the API enforces that regardless.
 */
const DeviceHealthLegend = ({ scope }: { scope: QueryParams }) => {
  const { canRead } = useAuth();
  const enabled = canRead("caleido_network");
  const active = useCount("devices", { ...scope, health_status: "Active" }, enabled);
  const inactive = useCount("devices", { ...scope, health_status: "Inactive" }, enabled);
  const { isDark } = useTheme();
  const mutedColor = isDark ? "#8b95a9" : "#8A86A8";

  if (!enabled) return null;
  if (active.isLoading || inactive.isLoading) {
    return <span className="text-xs" style={{ color: mutedColor }}>Loading device health...</span>;
  }
  if (active.error || inactive.error) {
    return <span className="text-xs" style={{ color: mutedColor }}>Device health unavailable</span>;
  }
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-[hsl(145,70%,45%)]">{active.total} Active</span>
      <span style={{ color: mutedColor }}>|</span>
      <span className="text-[hsl(0,70%,50%)]">{inactive.total} Inactive</span>
    </div>
  );
};

export const StatusSection = ({
  buildings,
  selectedBuilding,
  selectedFloor,
  selectedRoom,
  affectedOnly,
  onBuildingSelect,
  onFloorSelect,
  onRoomSelect,
  onAffectedOnlyChange,
}: StatusSectionProps) => {
  const { isDark } = useTheme();

  // Server-side: only the selected building's floors are ever requested.
  const floorsQuery = useFloors(
    selectedBuilding
      ? { page: 1, page_size: MAX_PAGE_SIZE, building_id: selectedBuilding }
      : undefined,
  );
  const floors = floorsQuery.data?.items ?? [];

  // Server-side: only the selected floor's rooms, with their real status and
  // conditions, straight from the occupancy projection.
  const roomsQuery = useOccupancy(
    selectedFloor ? { page: 1, page_size: MAX_PAGE_SIZE, floor_id: selectedFloor } : undefined,
  );

  const rooms = useMemo(() => {
    const items = roomsQuery.data?.items ?? [];
    const mapped = items.map((item) => ({
      id: item.amenity_id,
      number: item.room_name,
      type: item.amenity_type_name ?? "-",
      statusName: item.status_name ?? "-",
      conditions: item.conditions.map((condition) => condition.name),
    }));
    return affectedOnly ? mapped.filter((room) => room.conditions.length > 0) : mapped;
  }, [roomsQuery.data, affectedOnly]);

  /** True when the floor holds more rooms than the page returned. */
  const roomsTruncated =
    (roomsQuery.data?.total ?? 0) > (roomsQuery.data?.items.length ?? 0);

  const cardBg = isDark
    ? "linear-gradient(180deg, #1e2233, #1a1e30)"
    : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const mutedColor = isDark ? "#8b95a9" : "#8A86A8";

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

  const cardStyle = {
    background: cardBg,
    border: cardBorder,
    boxShadow: "0 8px 24px rgba(17,12,46,0.12)",
  };

  /** The scope the health legend and room list currently describe. */
  const scope: QueryParams = selectedFloor
    ? { floor_id: selectedFloor }
    : selectedBuilding
      ? { building_id: selectedBuilding }
      : {};

  return (
    <div className="space-y-4">
      {/* Status Header */}
      <div className="rounded-lg p-4 transition-all duration-250 ease hover:-translate-y-0.5" style={cardStyle}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 style={{ color: titleColor }} className="font-medium">Status</h3>
          <div className="flex flex-wrap items-center gap-4">
            <DeviceHealthLegend scope={scope} />
            <div className="flex items-center gap-2">
              <Checkbox
                id="affected"
                className="border-[#5E5A7A]/50"
                checked={affectedOnly}
                onCheckedChange={(value) => onAffectedOnlyChange(value === true)}
              />
              <label htmlFor="affected" style={{ color: mutedColor }} className="text-sm">
                Affected rooms only
              </label>
            </div>
          </div>
        </div>
        <p className="mt-2 flex items-start gap-1.5 text-[11px]" style={{ color: mutedColor }}>
          <Info className="mt-px h-3 w-3 shrink-0" />
          <span>
            Health is the real <span className="font-mono">device_health_status</span> enum
            (Active / Inactive). "Affected" means the room carries at least one active
            amenity condition.
          </span>
        </p>
      </div>

      {/* Buildings Section */}
      <div className="rounded-lg p-4 transition-all duration-250 ease hover:-translate-y-0.5" style={cardStyle}>
        <div className="flex items-center justify-between mb-4">
          <h3 style={{ color: titleColor }} className="font-medium">Building</h3>
          <DeviceHealthLegend scope={{}} />
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
      {selectedBuilding && (
        <div
          className="rounded-lg p-4 animate-fade-in transition-all duration-250 ease hover:-translate-y-0.5"
          style={cardStyle}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 style={{ color: titleColor }} className="font-medium">Floor</h3>
            <DeviceHealthLegend scope={{ building_id: selectedBuilding }} />
          </div>
          <DataState
            isLoading={floorsQuery.isLoading}
            error={floorsQuery.error}
            isEmpty={floors.length === 0}
            emptyTitle="No floors in this building"
            emptyDescription="No property_chain row resolves to a floor here."
            loader={<InlineLoading label="Loading floors..." />}
          >
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {floors.map((floor) => (
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
                  <p className="text-sm" style={{ color: selectedFloor === floor.id ? (isDark ? "#fca5a5" : "#7F1D1D") : flrMutedText }}>
                    {floor.room_count} rooms
                  </p>
                </div>
              ))}
            </div>
          </DataState>
        </div>
      )}

      {/* Occupancy / Rooms Section */}
      {selectedFloor && (
        <div
          className="rounded-lg p-4 animate-fade-in border transition-all duration-250 ease hover:-translate-y-0.5"
          style={cardStyle}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h3 style={{ color: titleColor }} className="font-medium">Occupancy</h3>
            <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: mutedColor }}>
              {Object.entries(STATUS_TINT).map(([name, tint]) => (
                <span key={name} className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: tint.border }} />
                  {name}
                </span>
              ))}
            </div>
          </div>
          <DataState
            isLoading={roomsQuery.isLoading}
            error={roomsQuery.error}
            isEmpty={rooms.length === 0}
            emptyTitle={affectedOnly ? "No affected rooms on this floor" : "No rooms on this floor"}
            emptyDescription={
              affectedOnly ? "No room here carries an active amenity condition." : undefined
            }
            loader={<InlineLoading label="Loading rooms..." />}
          >
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              {rooms.map((room) => {
                const tint = STATUS_TINT[room.statusName];
                const bg = tint
                  ? (isDark ? tint.dark : tint.light)
                  : (isDark ? "#252a3e" : "#F3F4F6");
                const text = selectedRoom === room.id && tint
                  ? (isDark ? "#e5e7eb" : tint.text)
                  : (isDark ? "#dde2ed" : "#1F1B3A");
                return (
                  <div
                    key={room.id}
                    onClick={() => onRoomSelect(room.id)}
                    title={
                      room.conditions.length
                        ? `${room.statusName} · ${room.conditions.join(", ")}`
                        : room.statusName
                    }
                    className="cursor-pointer rounded-lg p-4 text-center border-2 transition-all duration-150 hover:-translate-y-0.5"
                    style={{
                      backgroundColor: bg,
                      borderColor: selectedRoom === room.id ? (tint?.border ?? "#6366F1") : "transparent",
                      color: text,
                      boxShadow: selectedRoom === room.id ? "0 4px 12px rgba(17,12,46,0.18)" : "none",
                    }}
                  >
                    <p className="font-bold text-lg" style={{ color: text }}>{room.number}</p>
                    <p className="text-xs" style={{ color: text, opacity: 0.75 }}>{room.type}</p>
                    <p className="text-[11px] mt-1" style={{ color: text, opacity: 0.9 }}>
                      {room.statusName}
                    </p>
                    {room.conditions.length > 0 && (
                      <p className="text-[10px] mt-0.5 truncate" style={{ color: text, opacity: 0.75 }}>
                        {room.conditions.join(", ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            {roomsTruncated && (
              <p className="mt-3 text-[11px]" style={{ color: mutedColor }}>
                Showing {roomsQuery.data?.items.length} of {roomsQuery.data?.total} rooms on this
                floor -- one page is the backend's maximum.
              </p>
            )}
          </DataState>
        </div>
      )}
    </div>
  );
};
