import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckCircle, XCircle } from "lucide-react";
import { DataState } from "@/core/components/DataState";
import { useDevices, useOccupancyDetail, useServiceRequests } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { roomStatusBadgeClass, roomStatusTextClass } from "../lib/roomStatus";
import { RoomPowerEnergy } from "./RoomPowerEnergy";

interface RoomDetailsModalProps {
    /** `amenity.id` -- everything in this dialog is fetched with it. */
    amenityId: string | null;
    roomNo: string | null;
    isOpen: boolean;
    onClose: () => void;
    roomType?: string;
    guestName?: string;
    status?: string;
}

const formatDate = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleDateString() : "-";

const formatDateTime = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString() : "-";

/**
 * Room detail dialog, fully backend-driven.
 *
 * Two deliberate changes to the mock's columns, because the data does not
 * exist and must not be invented:
 *
 *   - "MAC Address" is now "Device UID". Phase 2.6 established that `device`
 *     stores no MAC or IP address.
 *   - The maintenance table now shows the room's SERVICE REQUESTS with their
 *     real columns. `maintenance_request` exists in the schema but no Phase
 *     2.x endpoint exposes it, so its own columns (from/to date, start/stop
 *     time) have no source.
 *
 * Guest contact details, ID proof, nationality and pax are likewise absent:
 * the occupancy projection returns only `UserRef` (id, name, emp_id).
 *
 * The Power & Energy section is where the retired Power View and Energy View
 * live now. It reuses their reads, narrowed to this room's amenity id -- see
 * `RoomPowerEnergy` for the parameters, units and permission handling.
 */
export function RoomDetailsModal({
    amenityId,
    roomNo,
    isOpen,
    onClose,
    roomType = "-",
    guestName = "-",
    status = "-",
}: RoomDetailsModalProps) {
    const enabled = isOpen ? amenityId : null;
    const occupancyQuery = useOccupancyDetail(enabled);
    const devicesQuery = useDevices(
        enabled ? { amenity_id: enabled, page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    );
    const requestsQuery = useServiceRequests(
        enabled ? { amenity_id: enabled, page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    );

    if (!roomNo) return null;

    const occupancy = occupancyQuery.data;
    const stay = occupancy?.current_stay;
    const devices = devicesQuery.data?.items ?? [];
    const requests = requestsQuery.data?.items ?? [];
    const occupants = occupancy?.occupants ?? [];

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0 bg-background text-foreground border-border">
                <DialogHeader className="p-6 pb-2 border-b border-border">
                    <div className="flex items-center justify-between">
                        <DialogTitle className="text-xl font-semibold">
                            Room No: {roomNo}
                        </DialogTitle>
                        {/* Same status -> same colour as the room list. */}
                        <Badge
                            variant="outline"
                            className={`mr-8 ${roomStatusBadgeClass(occupancy?.status_name ?? status)}`}
                        >
                            {occupancy?.status_name ?? status}
                        </Badge>
                    </div>
                </DialogHeader>

                {/* `[&>[data-radix-scroll-area-viewport]>div]:!block` is what makes
                    the tables below scroll sideways.

                    Radix's ScrollArea viewport wraps its children in a div with
                    `display: table`, which shrink-wraps to the WIDEST child. The
                    device/energy/service tables are wider than the modal, so that
                    wrapper grew to fit them and the `overflow-x-auto` containers
                    inside never had anything to scroll -- the columns were simply
                    pushed past the modal edge and clipped.

                    Forcing it to `block` makes it take the viewport's width, so
                    each table now scrolls within its own container. Scoped to this
                    modal; other ScrollAreas are untouched. */}
                <ScrollArea className="flex-1 px-6 [&>[data-radix-scroll-area-viewport]>div]:!block">
                    <div className="py-6 space-y-8">
                        {/* Room Details Section */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Room Details
                            </h3>
                            <DataState isLoading={occupancyQuery.isLoading} error={occupancyQuery.error}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-4 text-sm">
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Room Allotted :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">{occupancy?.room_name ?? roomNo}</span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Room Category :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {occupancy?.amenity_type_name ?? roomType}
                                        </span>
                                    </div>
                                    {/* Building and floor are separate columns on
                                        the occupancy projection, so they are shown
                                        separately rather than concatenated. */}
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Tower / Building :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {occupancy?.building_name ?? "-"}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Floor :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {occupancy?.floor_name ?? "-"}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Room Status :
                                        </span>
                                        <span
                                            className={`text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 ${roomStatusTextClass(
                                                occupancy?.status_name ?? status,
                                            )}`}
                                        >
                                            {occupancy?.status_name ?? status}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Room Allocations :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {occupancy?.allocation_count ?? "-"}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Checkin Date :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {formatDateTime(stay?.actual_checkin_time)}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Expected Checkin :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {formatDateTime(stay?.expected_checkin_time)}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Expected Checkout :
                                        </span>
                                        <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                            {formatDateTime(stay?.expected_checkout_time)}
                                        </span>
                                    </div>
                                </div>
                            </DataState>
                        </section>

                        {/* Occupants Details Section */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Occupants Details
                            </h3>
                            <DataState
                                isLoading={occupancyQuery.isLoading}
                                error={occupancyQuery.error}
                                isEmpty={!stay && occupants.length === 0}
                                emptyTitle="No active occupants recorded for this room."
                            >
                                <div className="rounded-md border border-border p-4">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Primary Guest</span>
                                            <span className="font-medium text-base">
                                                {stay?.booker?.name ?? guestName}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Stay Reference</span>
                                            <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                {stay?.internal_stay_ref_number ?? "-"}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Stay Status</span>
                                            <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">{stay?.status ?? "-"}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Guests</span>
                                            <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">{stay?.no_of_guests ?? "-"}</span>
                                        </div>
                                        <div className="flex flex-col gap-1 md:col-span-2">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Occupants</span>
                                            <span className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                {occupants.length
                                                    ? occupants.map((occupant) => occupant.guest.name).join(", ")
                                                    : "-"}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </DataState>
                        </section>

                        {/* Device Details Section */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Device Details
                            </h3>
                            <div className="rounded-lg overflow-hidden overflow-x-auto scrollbar-thin border border-border/80 dark:border-slate-800">
                                <DataState
                                    isLoading={devicesQuery.isLoading}
                                    error={devicesQuery.error}
                                    isEmpty={devices.length === 0}
                                    emptyTitle="No devices installed in this room"
                                >
                                    <Table>
                                        <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                                            <TableRow>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Device Type</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                    Occupancy No
                                                </TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Name/Tag</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Device UID</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Config Status</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 text-center">
                                                    Health
                                                </TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 text-right">
                                                    Installed On
                                                </TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {devices.map((device) => (
                                                <TableRow key={device.id} className="hover:bg-muted/5">
                                                    <TableCell>{device.device_type_name ?? "-"}</TableCell>
                                                    <TableCell>{device.amenity_name ?? roomNo}</TableCell>
                                                    <TableCell>{device.device_name ?? "-"}</TableCell>
                                                    <TableCell className="font-mono text-xs">
                                                        {device.device_uid || "-"}
                                                    </TableCell>
                                                    <TableCell>
                                                        <span
                                                            className={
                                                                // The enum label is lower-case; "Commissioned"
                                                                // never matched, so this always read as muted.
                                                                device.device_config_status === "commissioned"
                                                                    ? "text-green-600"
                                                                    : "text-muted-foreground"
                                                            }
                                                        >
                                                            {device.device_config_status ?? "-"}
                                                        </span>
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {device.health_status === "Active" ? (
                                                            <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                                                        ) : (
                                                            <XCircle className="h-4 w-4 text-red-500 mx-auto" />
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        {formatDate(device.installed_on)}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </DataState>
                            </div>
                        </section>

                        {/* Power & Energy Section -- what the retired Power View
                            and Energy View used to show, narrowed to this room.
                            See RoomPowerEnergy for the parameters and units. */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Power &amp; Energy
                            </h3>
                            <RoomPowerEnergy amenityId={enabled} />
                        </section>

                        {/* Service Requests Section (see the file header: the
                            maintenance_request table has no endpoint) */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Service Requests
                            </h3>
                            <div className="rounded-lg overflow-hidden overflow-x-auto scrollbar-thin border border-border/80 dark:border-slate-800">
                                <DataState
                                    isLoading={requestsQuery.isLoading}
                                    error={requestsQuery.error}
                                    isEmpty={requests.length === 0}
                                    emptyTitle="No service requests recorded for this room"
                                >
                                    <Table>
                                        <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                                            <TableRow>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                    Service Category
                                                </TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                    Services Type
                                                </TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Requested On</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Expected</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Completed</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Department</TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                    Emp ID/Name
                                                </TableHead>
                                                <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 text-right">
                                                    Status
                                                </TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {requests.map((item) => (
                                                <TableRow key={item.id} className="hover:bg-muted/5">
                                                    <TableCell>{item.category_name ?? "-"}</TableCell>
                                                    <TableCell>{item.service_type_name ?? "-"}</TableCell>
                                                    <TableCell>{formatDate(item.created_on)}</TableCell>
                                                    <TableCell>{formatDate(item.expected_date)}</TableCell>
                                                    <TableCell>{formatDate(item.completed_on)}</TableCell>
                                                    <TableCell>{item.department_name ?? "-"}</TableCell>
                                                    <TableCell>
                                                        {item.assignee
                                                            ? [item.assignee.emp_id, item.assignee.name]
                                                                  .filter(Boolean)
                                                                  .join(" / ")
                                                            : "-"}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <Badge
                                                            variant="secondary"
                                                            className="bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400"
                                                        >
                                                            {item.status_name ?? "-"}
                                                        </Badge>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </DataState>
                            </div>
                        </section>
                    </div>
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
}
