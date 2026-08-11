import { useState } from "react";
import { Zap, Thermometer, Lightbulb, Fan, Power } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  devices: {
    type: "ac" | "light" | "fan" | "power";
    status: "on" | "off" | "standby";
    value?: number;
  }[];
  energyUsage: number;
  status: "occupied" | "vacant" | "maintenance";
}

const mockRooms: Room[] = [
  {
    id: "101",
    name: "Room 101",
    zone: "Zone A",
    floor: "Floor 1",
    devices: [
      { type: "ac", status: "on", value: 22 },
      { type: "light", status: "on" },
      { type: "fan", status: "off" },
      { type: "power", status: "standby" },
    ],
    energyUsage: 2.4,
    status: "occupied",
  },
  {
    id: "102",
    name: "Room 102",
    zone: "Zone A",
    floor: "Floor 1",
    devices: [
      { type: "ac", status: "off" },
      { type: "light", status: "off" },
      { type: "fan", status: "off" },
      { type: "power", status: "off" },
    ],
    energyUsage: 0.1,
    status: "vacant",
  },
  {
    id: "103",
    name: "Room 103",
    zone: "Zone A",
    floor: "Floor 1",
    devices: [
      { type: "ac", status: "on", value: 24 },
      { type: "light", status: "on" },
      { type: "fan", status: "on" },
      { type: "power", status: "on" },
    ],
    energyUsage: 3.8,
    status: "occupied",
  },
  {
    id: "201",
    name: "Room 201",
    zone: "Zone B",
    floor: "Floor 2",
    devices: [
      { type: "ac", status: "standby" },
      { type: "light", status: "off" },
      { type: "fan", status: "off" },
      { type: "power", status: "standby" },
    ],
    energyUsage: 0.5,
    status: "maintenance",
  },
  {
    id: "202",
    name: "Room 202",
    zone: "Zone B",
    floor: "Floor 2",
    devices: [
      { type: "ac", status: "on", value: 21 },
      { type: "light", status: "on" },
      { type: "fan", status: "off" },
      { type: "power", status: "on" },
    ],
    energyUsage: 2.9,
    status: "occupied",
  },
  {
    id: "203",
    name: "Room 203",
    zone: "Zone B",
    floor: "Floor 2",
    devices: [
      { type: "ac", status: "off" },
      { type: "light", status: "off" },
      { type: "fan", status: "off" },
      { type: "power", status: "off" },
    ],
    energyUsage: 0.0,
    status: "vacant",
  },
];

const DeviceIcon = ({
  type,
  status,
  value,
}: {
  type: string;
  status: string;
  value?: number;
}) => {
  const iconMap = {
    ac: Thermometer,
    light: Lightbulb,
    fan: Fan,
    power: Power,
  };

  const Icon = iconMap[type as keyof typeof iconMap] || Zap;

  return (
    <div
      className={cn(
        "relative p-2 rounded-lg transition-all",
        status === "on" && "bg-primary/20 text-primary",
        status === "standby" && "bg-warning/20 text-warning",
        status === "off" && "bg-muted text-muted-foreground"
      )}
      title={`${type}: ${status}${value ? ` (${value}°C)` : ""}`}
    >
      <Icon className="h-4 w-4" />
      {value && (
        <span className="absolute -top-1 -right-1 text-[10px] font-bold bg-primary text-primary-foreground rounded-full w-4 h-4 flex items-center justify-center">
          {value}
        </span>
      )}
    </div>
  );
};

const RoomCard = ({ room }: { room: Room }) => {
  const statusColors = {
    occupied: "border-l-primary",
    vacant: "border-l-success",
    maintenance: "border-l-warning",
  };

  return (
    <div
      className={cn(
        "bg-card rounded-lg border border-border/50 p-4 hover:shadow-md transition-all cursor-pointer border-l-4",
        statusColors[room.status]
      )}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <h4 className="font-semibold text-sm">{room.name}</h4>
          <p className="text-xs text-muted-foreground">{room.zone}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-primary">{room.energyUsage} kWh</p>
          <span
            className={cn(
              "text-[10px] uppercase font-medium",
              room.status === "occupied" && "text-primary",
              room.status === "vacant" && "text-success",
              room.status === "maintenance" && "text-warning"
            )}
          >
            {room.status}
          </span>
        </div>
      </div>
      <div className="flex gap-2">
        {room.devices.map((device, index) => (
          <DeviceIcon
            key={index}
            type={device.type}
            status={device.status}
            value={device.value}
          />
        ))}
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
    (sum, room) => sum + room.devices.filter((d) => d.status === "on").length,
    0
  );

  return (
    <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
      {/* Page Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Energy View</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor real-time energy consumption across all rooms and devices
        </p>
      </div>

      {/* Filters and Summary */}
      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="lg:col-span-2">
          <CardContent className="pt-6">
            <div className="flex gap-4">
              <div className="space-y-2 flex-1">
                <label className="text-sm font-medium">Buildings</label>
                <Select value={selectedBuilding} onValueChange={setSelectedBuilding}>
                  <SelectTrigger className="bg-muted/30 border-border/50">
                    <SelectValue placeholder="All Buildings" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="all">All Buildings</SelectItem>
                    <SelectItem value="Building A">Building A</SelectItem>
                    <SelectItem value="Building B">Building B</SelectItem>
                    <SelectItem value="Building C">Building C</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 flex-1">
                <label className="text-sm font-medium">Floors</label>
                <Select value={selectedFloor} onValueChange={setSelectedFloor}>
                  <SelectTrigger className="bg-muted/30 border-border/50">
                    <SelectValue placeholder="All Floors" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="all">All Floors</SelectItem>
                    <SelectItem value="Floor 1">Floor 1</SelectItem>
                    <SelectItem value="Floor 2">Floor 2</SelectItem>
                    <SelectItem value="Floor 3">Floor 3</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 flex-1">
                <label className="text-sm font-medium">Rooms</label>
                <Select value={selectedRoom} onValueChange={setSelectedRoom}>
                  <SelectTrigger className="bg-muted/30 border-border/50">
                    <SelectValue placeholder="All Rooms" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
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

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-primary/10">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalEnergy.toFixed(1)} kWh</p>
                <p className="text-sm text-muted-foreground">Total Energy</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex justify-between text-sm">
              <div>
                <p className="font-bold text-lg">{occupiedRooms}</p>
                <p className="text-muted-foreground">Occupied</p>
              </div>
              <div>
                <p className="font-bold text-lg">{activeDevices}</p>
                <p className="text-muted-foreground">Active Devices</p>
              </div>
              <div>
                <p className="font-bold text-lg">{filteredRooms.length}</p>
                <p className="text-muted-foreground">Total Rooms</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Legend */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-6 items-center">
            <span className="text-sm font-medium">Status:</span>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-primary" />
              <span className="text-sm">Occupied</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-success" />
              <span className="text-sm">Vacant</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-warning" />
              <span className="text-sm">Maintenance</span>
            </div>
            <span className="text-sm font-medium ml-4">Devices:</span>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-primary/20" />
              <span className="text-sm">On</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-warning/20" />
              <span className="text-sm">Standby</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-muted" />
              <span className="text-sm">Off</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Room Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Room Grid</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid-energy">
            {filteredRooms.map((room) => (
              <RoomCard key={room.id} room={room} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EnergyView;
