import { useState } from "react";
import { Zap, Thermometer, Lightbulb, Fan, Power } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { DataState } from "@/core/components/DataState";
import {
  useBuildings,
  useDeviceStats,
  useDevices,
  useEnergySummary,
  useFloors,
  useOccupancy,
} from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

interface Room {
  id: string;
  name: string;
  zone: string;
  floor: string;
  theme: "purple" | "blue" | "green" | "orange";
  temp?: number;
  acActive: boolean;
  lightActive: boolean;
  fanActive: boolean;
  powerActive: boolean;
  powerVariant?: "orange" | "green" | "purple" | "gray";
  energyUsage: number;
  /** The room's real `amenity_status` name, as stored -- one of four values. */
  status: string;
}

/**
 * Energy View, connected to the Phase 2.8 / 2.9 APIs.
 *
 *   Rooms and status -> GET /occupancy
 *   Energy per room  -> GET /energy-stats/summary?group_by=amenity (a stored SUM)
 *   Temperature      -> GET /device-stats, the `temperature` parameter
 *   Power state      -> GET /devices, `is_power_off`
 *   Filters          -> GET /buildings, GET /floors
 *
 * NO UNIT IS SHOWN for energy: `energy_stat` stores none and the API returns
 * `energy_unit: null`. Nothing here is converted, costed or carbon-weighted.
 *
 * The AC / Light / Fan indicators are always inactive: the schema records no
 * per-appliance on/off state. They are left in place, disabled, rather than
 * driven by a guess -- see the phase report's gap list.
 */

const THEMES: Room["theme"][] = ["purple", "blue", "green", "orange"];

const DoubleDoorIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <line x1="12" y1="3" x2="12" y2="21" />
    <circle cx="9.5" cy="12" r="0.8" fill="currentColor" />
    <circle cx="14.5" cy="12" r="0.8" fill="currentColor" />
  </svg>
);

const RoomCard = ({ room }: { room: Room }) => {
  // Theme styles for door container
  const doorStyles = {
    purple: "bg-purple-100/70 text-purple-600 dark:bg-purple-950/70 dark:text-purple-400",
    blue: "bg-blue-100/70 text-blue-500 dark:bg-blue-950/70 dark:text-blue-400",
    green: "bg-emerald-100/70 text-emerald-600 dark:bg-emerald-950/70 dark:text-emerald-400",
    orange: "bg-amber-100/70 text-amber-600 dark:bg-amber-950/70 dark:text-amber-400",
  };

  // Inactive button style
  const inactiveBtn = "bg-gray-50/90 border-gray-100 text-slate-400 dark:bg-slate-800/50 dark:border-slate-700/60 dark:text-slate-400";

  // AC Button style
  const acBtnStyles = room.acActive
    ? {
        purple: "bg-purple-100/70 border-purple-200/80 text-purple-600 dark:bg-purple-950/70 dark:border-purple-800/60 dark:text-purple-300",
        green: "bg-emerald-100/70 border-emerald-200/80 text-emerald-600 dark:bg-emerald-950/70 dark:border-emerald-800/60 dark:text-emerald-300",
        blue: "bg-blue-100/70 border-blue-200/80 text-blue-600 dark:bg-blue-950/70 dark:border-blue-800/60 dark:text-blue-300",
        orange: "bg-amber-100/70 border-amber-200/80 text-amber-600 dark:bg-amber-950/70 dark:border-amber-800/60 dark:text-amber-300",
      }[room.theme]
    : inactiveBtn;

  // Temp badge style
  const tempBadgeStyles = {
    purple: "bg-purple-600 text-white",
    green: "bg-emerald-600 text-white",
    blue: "bg-blue-600 text-white",
    orange: "bg-amber-600 text-white",
  }[room.theme];

  // Light Button style
  const lightBtnStyles = room.lightActive
    ? {
        purple: "bg-purple-100/70 border-purple-200/80 text-purple-600 dark:bg-purple-950/70 dark:border-purple-800/60 dark:text-purple-300",
        green: "bg-emerald-100/70 border-emerald-200/80 text-emerald-600 dark:bg-emerald-950/70 dark:border-emerald-800/60 dark:text-emerald-300",
        blue: "bg-blue-100/70 border-blue-200/80 text-blue-600 dark:bg-blue-950/70 dark:border-blue-800/60 dark:text-blue-300",
        orange: "bg-amber-100/70 border-amber-200/80 text-amber-600 dark:bg-amber-950/70 dark:border-amber-800/60 dark:text-amber-300",
      }[room.theme]
    : inactiveBtn;

  // Fan Button style
  const fanBtnStyles = room.fanActive
    ? {
        purple: "bg-purple-100/70 border-purple-200/80 text-purple-600 dark:bg-purple-950/70 dark:border-purple-800/60 dark:text-purple-300",
        green: "bg-emerald-100/70 border-emerald-200/80 text-emerald-600 dark:bg-emerald-950/70 dark:border-emerald-800/60 dark:text-emerald-300",
        blue: "bg-blue-100/70 border-blue-200/80 text-blue-600 dark:bg-blue-950/70 dark:border-blue-800/60 dark:text-blue-300",
        orange: "bg-amber-100/70 border-amber-200/80 text-amber-600 dark:bg-amber-950/70 dark:border-amber-800/60 dark:text-amber-300",
      }[room.theme]
    : inactiveBtn;

  // Power Button style
  const powerBtnStyles = {
    orange: "bg-amber-50/90 border-amber-200/80 text-amber-600 dark:bg-amber-950/70 dark:border-amber-800/60 dark:text-amber-300",
    green: "bg-emerald-100/70 border-emerald-200/80 text-emerald-600 dark:bg-emerald-950/70 dark:border-emerald-800/60 dark:text-emerald-300",
    purple: "bg-purple-100/70 border-purple-200/80 text-purple-600 dark:bg-purple-950/70 dark:border-purple-800/60 dark:text-purple-300",
    gray: inactiveBtn,
  }[room.powerVariant || "gray"];

  // Status badge, keyed on the real `amenity_status` name. All FOUR statuses
  // get their own colour: the previous three-value map folded Allotted -- a
  // room held by a stay that has not checked in -- into "VACANT".
  const statusStyles = {
    Occupied: { dot: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" },
    Available: { dot: "bg-sky-500", text: "text-sky-600 dark:text-sky-400" },
    Allotted: { dot: "bg-amber-500", text: "text-amber-600 dark:text-amber-400" },
    Unavailable: { dot: "bg-red-500", text: "text-red-600 dark:text-red-400" },
  }[room.status] ?? { dot: "bg-slate-400", text: "text-slate-400" };

  return (
    <div className="bg-card text-card-foreground rounded-2xl border border-border/60 dark:border-slate-800/80 p-4 px-6 shadow-sm hover:shadow-md transition-all flex items-center">
      {/* Left: Door Icon & Room Name - Fixed column width for vertical alignment */}
      <div className="w-48 sm:w-56 shrink-0 flex items-center gap-4">
        <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center shrink-0", doorStyles[room.theme])}>
          <DoubleDoorIcon className="w-5 h-5" />
        </div>
        <div className="truncate">
          <h4 className="text-base font-bold text-foreground truncate">{room.name}</h4>
          <p className="text-xs font-medium text-muted-foreground truncate">{room.zone}</p>
        </div>
      </div>

      {/* Center: Device Controls - Centered & aligned in straight vertical columns */}
      <div className="flex-1 flex items-center justify-center gap-3">
        {/* Thermometer / AC */}
        <div className="relative inline-flex shrink-0 w-10 h-10 items-center justify-center">
          <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center border transition-all", acBtnStyles)}>
            <Thermometer className="w-4 h-4" />
          </div>
          {room.temp && (
            <span className={cn("absolute -top-1.5 -right-1.5 px-1 py-0.5 min-w-[18px] h-4.5 text-[10px] font-bold rounded-full flex items-center justify-center leading-none shadow-sm z-10 pointer-events-none", tempBadgeStyles)}>
              {room.temp}°
            </span>
          )}
        </div>

        {/* Light */}
        <div className={cn("w-10 h-10 shrink-0 rounded-xl flex items-center justify-center border transition-all", lightBtnStyles)}>
          <Lightbulb className="w-4 h-4" />
        </div>

        {/* Fan */}
        <div className={cn("w-10 h-10 shrink-0 rounded-xl flex items-center justify-center border transition-all", fanBtnStyles)}>
          <Fan className="w-4 h-4" />
        </div>

        {/* Power */}
        <div className={cn("w-10 h-10 shrink-0 rounded-xl flex items-center justify-center border transition-all", powerBtnStyles)}>
          <Power className="w-4 h-4" />
        </div>
      </div>

      {/* Right: Energy Usage & Status - Fixed column width for vertical alignment */}
      <div className="w-36 sm:w-44 shrink-0 text-right">
        <p className="text-base font-bold text-foreground">{room.energyUsage} kWh</p>
        <div className="flex items-center justify-end gap-1.5 mt-0.5">
          <span className={cn("w-2 h-2 rounded-full shrink-0", statusStyles.dot)} />
          <span className={cn("text-[11px] font-bold tracking-wider uppercase", statusStyles.text)}>
            {room.status}
          </span>
        </div>
      </div>
    </div>
  );
};

const EnergyView = () => {
  const [selectedBuilding, setSelectedBuilding] = useState("all");
  const [selectedFloor, setSelectedFloor] = useState("all");
  const [selectedRoom, setSelectedRoom] = useState("all");

  // --- Live data -----------------------------------------------------------
  const buildingsQuery = useBuildings({ page: 1, page_size: MAX_PAGE_SIZE });
  const floorsQuery = useFloors({
    page: 1,
    page_size: MAX_PAGE_SIZE,
    ...(selectedBuilding !== "all" ? { building_id: selectedBuilding } : {}),
  });

  const scope = {
    ...(selectedBuilding !== "all" ? { building_id: selectedBuilding } : {}),
    ...(selectedFloor !== "all" ? { floor_id: selectedFloor } : {}),
    ...(selectedRoom !== "all" ? { amenity_id: selectedRoom } : {}),
  };

  const occupancyQuery = useOccupancy({ page: 1, page_size: MAX_PAGE_SIZE, ...scope });
  const energyQuery = useEnergySummary({ group_by: "amenity", ...scope });
  const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE, ...scope });
  const temperatureQuery = useDeviceStats({
    page: 1,
    page_size: MAX_PAGE_SIZE,
    param_name: "temperature",
    ...scope,
  });

  const isLoading =
    occupancyQuery.isLoading || energyQuery.isLoading || devicesQuery.isLoading;
  const error = occupancyQuery.error ?? energyQuery.error ?? devicesQuery.error;

  // Stored SUM per room, keyed by amenity id (the summary's bucket).
  const energyByAmenity = new Map(
    (energyQuery.data?.buckets ?? []).map((bucket) => [bucket.bucket, bucket.total_energy_consumed]),
  );

  // Latest temperature reading per room, as stored (a string in the database).
  const temperatureByAmenity = new Map<string, number>();
  for (const stat of temperatureQuery.data?.items ?? []) {
    if (!stat.amenity_id || temperatureByAmenity.has(stat.amenity_id)) continue;
    const value = Number(stat.device_param_value);
    if (!Number.isNaN(value)) temperatureByAmenity.set(stat.amenity_id, value);
  }

  // A room counts as powered when at least one of its devices is not off.
  const poweredAmenities = new Set(
    (devicesQuery.data?.items ?? [])
      .filter((device) => device.is_power_off === false)
      .map((device) => device.amenity_id),
  );

  const filteredRooms: Room[] = (occupancyQuery.data?.items ?? []).map((room, index) => {
    const powered = poweredAmenities.has(room.amenity_id);
    return {
      id: room.amenity_id,
      name: room.room_name,
      zone: room.building_name ?? "-",
      floor: room.floor_name ?? "-",
      theme: THEMES[index % THEMES.length],
      temp: temperatureByAmenity.get(room.amenity_id),
      // No per-appliance state exists in the schema.
      acActive: false,
      lightActive: false,
      fanActive: false,
      powerActive: powered,
      powerVariant: powered ? "green" : "gray",
      energyUsage: energyByAmenity.get(room.amenity_id) ?? 0,
      status: room.status_name ?? "-",
    };
  });

  const totalEnergy = energyQuery.data?.total_energy_consumed ?? 0;
  const occupiedRooms = filteredRooms.filter((r) => r.status === "Occupied").length;
  // Devices actually reporting as powered on, from `device.is_power_off`.
  const activeDevices = (devicesQuery.data?.items ?? []).filter(
    (device) => device.is_power_off === false,
  ).length;

  return (
    <div className="space-y-6 animate-fade-in bg-background text-foreground min-h-screen -m-6 p-6">
      {/* Page Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Energy View</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor real-time energy consumption across all rooms and devices
        </p>
      </div>

      {/* Filters and Summary */}
      <div className="grid gap-6 lg:grid-cols-4 items-stretch">
        <Card className="lg:col-span-2 border border-border/60 dark:border-slate-800 shadow-sm flex flex-col justify-center">
          <CardContent className="p-5">
            <div className="grid grid-cols-3 gap-4 items-center">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Buildings</label>
                <Select value={selectedBuilding} onValueChange={setSelectedBuilding}>
                  <SelectTrigger className="h-9 bg-muted/30 border-border/50 dark:border-slate-700 text-xs">
                    <SelectValue placeholder="All Buildings" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    <SelectItem value="all">All Buildings</SelectItem>
                    {(buildingsQuery.data?.items ?? []).map((building) => (
                      <SelectItem key={building.id} value={building.id}>{building.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Floors</label>
                <Select value={selectedFloor} onValueChange={setSelectedFloor}>
                  <SelectTrigger className="h-9 bg-muted/30 border-border/50 dark:border-slate-700 text-xs">
                    <SelectValue placeholder="All Floors" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    <SelectItem value="all">All Floors</SelectItem>
                    {(floorsQuery.data?.items ?? []).map((floor) => (
                      <SelectItem key={floor.id} value={floor.id}>{floor.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Rooms</label>
                <Select value={selectedRoom} onValueChange={setSelectedRoom}>
                  <SelectTrigger className="h-9 bg-muted/30 border-border/50 dark:border-slate-700 text-xs">
                    <SelectValue placeholder="All Rooms" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    <SelectItem value="all">All Rooms</SelectItem>
                    {(occupancyQuery.data?.items ?? []).map((room) => (
                      <SelectItem key={room.amenity_id} value={room.amenity_id}>
                        {room.room_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border/60 dark:border-slate-800 shadow-sm flex flex-col justify-center">
          <CardContent className="p-5">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <Zap className="h-5.5 w-5.5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground leading-none">{totalEnergy.toFixed(3)}</p>
                <p className="text-xs font-medium text-muted-foreground mt-1.5">
                  Total Energy <span className="opacity-70">(no unit stored)</span>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border/60 dark:border-slate-800 shadow-sm flex flex-col justify-center">
          <CardContent className="p-4 sm:p-5">
            <div className="grid grid-cols-3 divide-x divide-border/60 dark:divide-slate-800/80 items-center text-center">
              <div className="flex flex-col items-center justify-center px-1">
                <p className="text-2xl font-bold text-foreground leading-none">{occupiedRooms}</p>
                <p className="text-xs font-medium text-muted-foreground mt-2 whitespace-nowrap">Occupied</p>
              </div>
              <div className="flex flex-col items-center justify-center px-1">
                <p className="text-2xl font-bold text-foreground leading-none">{activeDevices}</p>
                <p className="text-xs font-medium text-muted-foreground mt-2 whitespace-nowrap">Active Devices</p>
              </div>
              <div className="flex flex-col items-center justify-center px-1">
                <p className="text-2xl font-bold text-foreground leading-none">{filteredRooms.length}</p>
                <p className="text-xs font-medium text-muted-foreground mt-2 whitespace-nowrap">Total Rooms</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Room Stack List */}
      <div className="space-y-3.5">
        <DataState
          isLoading={isLoading}
          error={error}
          isEmpty={filteredRooms.length === 0}
          emptyTitle="No rooms match this selection"
        >
          <>
            {filteredRooms.map((room) => (
              <RoomCard key={room.id} room={room} />
            ))}
          </>
        </DataState>
      </div>
    </div>
  );
};

export default EnergyView;
