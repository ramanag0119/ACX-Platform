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
import { DataState } from "@/core/components/DataState";
import {
    useBuildings,
    useDeviceStats,
    useDevices,
    useFloors,
    useOccupancy,
} from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

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
    powerUsage: number;
    /**
     * The room's real `amenity_status` name -- all FOUR of Available, Occupied,
     * Unavailable and Allotted, as stored. The previous three-value local union
     * folded Allotted (a room held by a stay that has not checked in) into
     * "vacant", which is a different thing.
     */
    status: string;
}

/** Border/label colour per real amenity_status name. */
const STATUS_STYLES: Record<string, { border: string; text: string }> = {
    Occupied: { border: "border-l-primary", text: "text-primary" },
    Available: { border: "border-l-success", text: "text-success" },
    Allotted: { border: "border-l-warning", text: "text-warning" },
    Unavailable: { border: "border-l-destructive", text: "text-destructive" },
};

/**
 * Power View, connected to the Phase 2.6 / 2.9 APIs.
 *
 *   Rooms/status -> GET /occupancy
 *   Power        -> GET /device-stats?param_name=active_power
 *                   (`device_param.unit` for that parameter really is KW)
 *   Power state  -> GET /devices, `is_power_off`
 *   Filters      -> GET /buildings, GET /floors
 *
 * The AC / Light / Fan tiles stay switched off: the schema stores no
 * per-appliance state, and none is guessed. Only the Power tile has a source.
 */

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
            // The unit is whatever `device_param` records for the parameter
            // (KW for active_power), so none is appended here.
            title={`${type}: ${status}${value ? ` (${value})` : ""}`}
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
    const style = STATUS_STYLES[room.status];

    return (
        <div
            className={cn(
                "bg-card rounded-lg border border-border/50 p-4 hover:shadow-md transition-all cursor-pointer border-l-4",
                style?.border ?? "border-l-muted"
            )}
        >
            <div className="flex justify-between items-start mb-3">
                <div>
                    <h4 className="font-semibold text-sm">{room.name}</h4>
                    <p className="text-xs text-muted-foreground">{room.zone}</p>
                </div>
                <div className="text-right">
                    <p className="text-sm font-bold text-primary">{room.powerUsage} kW</p>
                    <span
                        className={cn(
                            "text-[10px] uppercase font-medium",
                            style?.text ?? "text-muted-foreground"
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

const PowerView = () => {
    const [selectedBuilding, setSelectedBuilding] = useState("all");
    const [selectedFloor, setSelectedFloor] = useState("all");
    const [selectedRoom, setSelectedRoom] = useState("all");

    // --- Live data ---------------------------------------------------------
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
    const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE, ...scope });
    const powerQuery = useDeviceStats({
        page: 1,
        page_size: MAX_PAGE_SIZE,
        param_name: "active_power",
        ...scope,
    });

    const isLoading = occupancyQuery.isLoading || devicesQuery.isLoading || powerQuery.isLoading;
    const error = occupancyQuery.error ?? devicesQuery.error ?? powerQuery.error;

    // Latest active_power reading per room, exactly as stored.
    const powerByAmenity = new Map<string, number>();
    for (const stat of powerQuery.data?.items ?? []) {
        if (!stat.amenity_id || powerByAmenity.has(stat.amenity_id)) continue;
        const value = Number(stat.device_param_value);
        if (!Number.isNaN(value)) powerByAmenity.set(stat.amenity_id, value);
    }

    const poweredAmenities = new Set(
        (devicesQuery.data?.items ?? [])
            .filter((device) => device.is_power_off === false)
            .map((device) => device.amenity_id),
    );

    const filteredRooms: Room[] = (occupancyQuery.data?.items ?? []).map((room) => {
        const powerUsage = powerByAmenity.get(room.amenity_id) ?? 0;
        return {
            id: room.amenity_id,
            name: room.room_name,
            zone: room.building_name ?? "-",
            floor: room.floor_name ?? "-",
            devices: [
                // Only the power tile has a source in the schema.
                { type: "ac" as const, status: "off" as const },
                { type: "light" as const, status: "off" as const },
                { type: "fan" as const, status: "off" as const },
                {
                    type: "power" as const,
                    status: poweredAmenities.has(room.amenity_id) ? ("on" as const) : ("off" as const),
                    value: powerUsage,
                },
            ],
            powerUsage,
            status: room.status_name ?? "-",
        };
    });

    const totalPower = filteredRooms.reduce((sum, room) => sum + room.powerUsage, 0);
    const occupiedRooms = filteredRooms.filter((r) => r.status === "Occupied").length;
    const activeDevices = (devicesQuery.data?.items ?? []).filter(
        (device) => device.is_power_off === false,
    ).length;

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Power View</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Monitor real-time power consumption across all rooms and devices
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
                                        {(floorsQuery.data?.items ?? []).map((floor) => (
                                            <SelectItem key={floor.id} value={floor.id}>{floor.name}</SelectItem>
                                        ))}
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

                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-3">
                            <div className="p-3 rounded-lg bg-primary/10">
                                <Zap className="h-6 w-6 text-primary" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">{totalPower.toFixed(1)} kW</p>
                                <p className="text-sm text-muted-foreground">Total Power</p>
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
                    <DataState
                        isLoading={isLoading}
                        error={error}
                        isEmpty={filteredRooms.length === 0}
                        emptyTitle="No rooms match this selection"
                    >
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                            {filteredRooms.map((room) => (
                                <RoomCard key={room.id} room={room} />
                            ))}
                        </div>
                    </DataState>
                </CardContent>
            </Card>
        </div>
    );
};

export default PowerView;
