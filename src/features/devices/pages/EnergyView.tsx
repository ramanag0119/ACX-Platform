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
  status: "occupied" | "vacant" | "maintenance";
}

const mockRooms: Room[] = [
  {
    id: "101",
    name: "Room 101",
    zone: "Zone A",
    floor: "Floor 1",
    theme: "purple",
    temp: 22,
    acActive: true,
    lightActive: true,
    fanActive: true,
    powerActive: true,
    powerVariant: "orange",
    energyUsage: 2.4,
    status: "occupied",
  },
  {
    id: "102",
    name: "Room 102",
    zone: "Zone A",
    floor: "Floor 1",
    theme: "blue",
    acActive: false,
    lightActive: false,
    fanActive: false,
    powerActive: false,
    powerVariant: "gray",
    energyUsage: 0.1,
    status: "vacant",
  },
  {
    id: "103",
    name: "Room 103",
    zone: "Zone A",
    floor: "Floor 1",
    theme: "green",
    temp: 24,
    acActive: true,
    lightActive: true,
    fanActive: true,
    powerActive: true,
    powerVariant: "green",
    energyUsage: 3.8,
    status: "occupied",
  },
  {
    id: "201",
    name: "Room 201",
    zone: "Zone B",
    floor: "Floor 2",
    theme: "orange",
    acActive: false,
    lightActive: false,
    fanActive: false,
    powerActive: false,
    powerVariant: "orange",
    energyUsage: 0.5,
    status: "maintenance",
  },
  {
    id: "202",
    name: "Room 202",
    zone: "Zone B",
    floor: "Floor 2",
    theme: "purple",
    temp: 21,
    acActive: true,
    lightActive: true,
    fanActive: true,
    powerActive: true,
    powerVariant: "purple",
    energyUsage: 2.9,
    status: "occupied",
  },
  {
    id: "203",
    name: "Room 203",
    zone: "Zone B",
    floor: "Floor 2",
    theme: "blue",
    acActive: false,
    lightActive: false,
    fanActive: false,
    powerActive: false,
    powerVariant: "gray",
    energyUsage: 0.0,
    status: "vacant",
  },
];

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

  // Status Badge styles
  const statusStyles = {
    occupied: {
      dot: "bg-emerald-500",
      text: "text-emerald-600 dark:text-emerald-400",
      label: "OCCUPIED",
    },
    vacant: {
      dot: "bg-slate-400",
      text: "text-slate-400 dark:text-slate-400",
      label: "VACANT",
    },
    maintenance: {
      dot: "bg-amber-500",
      text: "text-amber-600 dark:text-amber-400",
      label: "MAINTENANCE",
    },
  }[room.status];

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
            {statusStyles.label}
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

  const filteredRooms = mockRooms.filter((room) => {
    if (selectedFloor !== "all" && room.floor !== selectedFloor) return false;
    if (selectedRoom !== "all" && room.zone !== selectedRoom) return false;
    return true;
  });

  const totalEnergy = filteredRooms.reduce((sum, room) => sum + room.energyUsage, 0);
  const occupiedRooms = filteredRooms.filter((r) => r.status === "occupied").length;
  const activeDevices = filteredRooms.reduce(
    (sum, room) => sum + (room.acActive ? 1 : 0) + (room.lightActive ? 1 : 0) + (room.fanActive ? 1 : 0),
    0
  );

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
                    <SelectItem value="Building A">Building A</SelectItem>
                    <SelectItem value="Building B">Building B</SelectItem>
                    <SelectItem value="Building C">Building C</SelectItem>
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
                    <SelectItem value="Floor 1">Floor 1</SelectItem>
                    <SelectItem value="Floor 2">Floor 2</SelectItem>
                    <SelectItem value="Floor 3">Floor 3</SelectItem>
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
                    <SelectItem value="Room 01">Room 01</SelectItem>
                    <SelectItem value="Room 02">Room 02</SelectItem>
                    <SelectItem value="Room 03">Room 03</SelectItem>
                    <SelectItem value="Room 04">Room 04</SelectItem>
                    <SelectItem value="Room 05">Room 05</SelectItem>
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
                <p className="text-2xl font-bold text-foreground leading-none">{totalEnergy.toFixed(1)} kWh</p>
                <p className="text-xs font-medium text-muted-foreground mt-1.5">Total Energy</p>
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
        {filteredRooms.map((room) => (
          <RoomCard key={room.id} room={room} />
        ))}
      </div>
    </div>
  );
};

export default EnergyView;
