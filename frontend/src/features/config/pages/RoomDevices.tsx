import { useState } from "react";
import { Trash2 } from "lucide-react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { PageHeader } from "@/components/layout/PageHeader";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";
import { useDevices, useRoomDevices, useRooms } from "@/lib/api/hooks";
import { useAssignRoomDevice, useUnassignRoomDevice } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { RoomDeviceRead } from "@/lib/api/writes";

/**
 * Room Devices: which OSS device is installed in which room.
 *
 *   Rooms    -> GET /rooms           (HMS)
 *   Devices  -> GET /devices         (OSS, with each device's room filled in by HMS)
 *   Table    -> GET /room-devices    (the mapping, HMS data)
 *   Install  -> POST /room-devices   (HMS confirms the device exists in OSS first)
 *   Remove   -> DELETE /room-devices/{id}
 *
 * OSS knows devices but not rooms, so this mapping is the only thing that puts
 * a device in a room: the room filters on /devices, a device's room on every
 * screen, and occupancy's device count all read it. Nothing is written to OSS.
 *
 * Gated on `caleido_network`, the same grant as the backend routes.
 */

const ALL_ROOMS = "all";

const deviceLabel = (device: { device_name: string | null; appliance_name: string | null; device_uid: string | null; id: string }) =>
    [device.device_name, device.appliance_name].filter(Boolean).join(" - ")
    || device.device_uid
    || device.id;

const RoomDevices = () => {
    // Table state
    const [roomFilter, setRoomFilter] = useState(ALL_ROOMS);
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = parseInt(entriesPerPage) || 10;

    // Form state
    const [roomId, setRoomId] = useState("");
    const [deviceId, setDeviceId] = useState("");
    const [pendingRemoval, setPendingRemoval] = useState<RoomDeviceRead | null>(null);

    // --- Live data -------------------------------------------------------
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
    const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE });
    const mappingsQuery = useRoomDevices({
        page: currentPage,
        page_size: pageSize,
        amenity_id: roomFilter === ALL_ROOMS ? undefined : roomFilter,
    });

    const assign = useAssignRoomDevice();
    const unassign = useUnassignRoomDevice();

    useScrollToTop(currentPage);

    const rooms = [...(roomsQuery.data?.items ?? [])].sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { numeric: true }),
    );
    const devices = devicesQuery.data?.items ?? [];
    const deviceNames = new Map(devices.map((device) => [device.id, deviceLabel(device)]));
    // A device is in at most one room, so only devices without one are offered.
    const unplacedDevices = devices.filter((device) => !device.amenity_id);

    const totalEntries = mappingsQuery.data?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
    const startIndex = totalEntries === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const endIndex = Math.min(currentPage * pageSize, totalEntries);
    const mappings = mappingsQuery.data?.items ?? [];

    const handleReset = () => {
        setRoomId("");
        setDeviceId("");
    };

    const handleSubmit = () => {
        if (!roomId || !deviceId) return;
        assign.mutate({ amenity_id: roomId, oss_device_id: deviceId }, { onSuccess: handleReset });
    };

    const confirmRemoval = () => {
        if (pendingRemoval) unassign.mutate(pendingRemoval.id);
        setPendingRemoval(null);
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            <PageHeader title="Room Devices" />

            {/* Form Section */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                <CardContent className="p-6">
                    <div className="space-y-6">
                        {/* Room */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Room<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={roomId} onValueChange={setRoomId}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Room" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {rooms.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            rooms.map((room) => (
                                                <SelectItem key={room.id} value={room.id}>{room.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Device */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Device<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={deviceId} onValueChange={setDeviceId}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select a device not yet in a room" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {unplacedDevices.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">Every device is already in a room</div>
                                        ) : (
                                            unplacedDevices.map((device) => (
                                                <SelectItem key={device.id} value={device.id}>{deviceLabel(device)}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex justify-center gap-4">
                            <Button onClick={handleReset} variant="outline" className="px-8 border-red-500 text-red-500 hover:bg-red-50">
                                Reset
                            </Button>
                            <Button
                                onClick={handleSubmit}
                                disabled={!roomId || !deviceId || assign.isPending}
                                className="h-10 px-8 min-w-[160px] rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                            >
                                Install
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table Section */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
                <CardContent className="p-5">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-xs font-medium">Show</span>
                            <Select value={entriesPerPage} onValueChange={(val) => { setEntriesPerPage(val); setCurrentPage(1); }}>
                                <SelectTrigger className="w-18 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                                    <SelectItem value="10">10</SelectItem>
                                    <SelectItem value="25">25</SelectItem>
                                    <SelectItem value="50">50</SelectItem>
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-xs font-medium">entries</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-xs font-medium">Room:</span>
                            <Select value={roomFilter} onValueChange={(val) => { setRoomFilter(val); setCurrentPage(1); }}>
                                <SelectTrigger className="w-48 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                                    <SelectItem value={ALL_ROOMS}>All rooms</SelectItem>
                                    {rooms.map((room) => (
                                        <SelectItem key={room.id} value={room.id}>{room.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Room No.</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Floor</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Building</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Device</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Installed On</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {mappingsQuery.isLoading || mappingsQuery.error || mappings.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="py-2">
                                            <DataState
                                                isLoading={mappingsQuery.isLoading}
                                                error={mappingsQuery.error}
                                                isEmpty
                                                emptyTitle="No devices installed in rooms yet"
                                                loader={<TableLoading columns={6} />}
                                            >
                                                <span />
                                            </DataState>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    mappings.map((mapping) => (
                                        <TableRow key={mapping.id} className="hover:bg-[var(--hms-table-row-hover-bg)] border-b border-border/50 dark:border-slate-800/70 transition-colors">
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 font-medium text-foreground">{mapping.amenity_name}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{mapping.floor_name ?? "-"}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{mapping.building_name ?? "-"}</TableCell>
                                            {/* A device OSS no longer lists still shows, by id, so it can be removed. */}
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{deviceNames.get(mapping.oss_device_id) ?? mapping.oss_device_id}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{new Date(mapping.created_on).toLocaleString()}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <Button
                                                    size="sm"
                                                    aria-label="Remove device from room"
                                                    className="bg-red-500 hover:bg-red-600 h-7 w-7 p-0 rounded-md"
                                                    onClick={() => setPendingRemoval(mapping)}
                                                >
                                                    <Trash2 className="h-3.5 w-3.5 text-white" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
                        <span className="text-muted-foreground text-xs">
                            Showing {startIndex} to {endIndex} of {totalEntries} entries
                        </span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <AlertDialog open={pendingRemoval !== null} onOpenChange={(open) => { if (!open) setPendingRemoval(null); }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remove device from room?</AlertDialogTitle>
                        <AlertDialogDescription>
                            {pendingRemoval && (
                                <>
                                    {deviceNames.get(pendingRemoval.oss_device_id) ?? pendingRemoval.oss_device_id} will
                                    no longer be shown in room {pendingRemoval.amenity_name}. The device itself is not
                                    changed in OSS.
                                </>
                            )}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={confirmRemoval} className="bg-red-500 hover:bg-red-600">
                            Remove
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
};

export default RoomDevices;
