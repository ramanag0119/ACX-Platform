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
                            Occupancy No: {roomNo}
                        </DialogTitle>
                        <Badge variant={status === "Available" ? "outline" : "destructive"} className="mr-8">
                            {occupancy?.status_name ?? status}
                        </Badge>
                    </div>
                </DialogHeader>

                <ScrollArea className="flex-1 px-6">
                    <div className="py-6 space-y-8">
                        {/* Room Details Section */}
                        <section>
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                                Room Details
                            </h3>
                            <DataState isLoading={occupancyQuery.isLoading} error={occupancyQuery.error}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-4 text-sm">
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Room Allotted :
                                        </span>
                                        <span className="font-medium">{occupancy?.room_name ?? roomNo}</span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Room Category :
                                        </span>
                                        <span className="font-medium">
                                            {occupancy?.amenity_type_name ?? roomType}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Floor :
                                        </span>
                                        <span className="font-medium">
                                            {[occupancy?.building_name, occupancy?.floor_name]
                                                .filter(Boolean)
                                                .join(" - ") || "-"}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Checkin Date :
                                        </span>
                                        <span className="font-medium">
                                            {formatDateTime(stay?.actual_checkin_time)}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                            Checkout Date :
                                        </span>
                                        <span className="font-medium">
                                            {formatDateTime(stay?.expected_checkout_time)}
                                        </span>
                                    </div>
                                </div>
                            </DataState>
                        </section>

                        {/* Occupants Details Section */}
                        <section>
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
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
                                            <span className="font-medium">
                                                {stay?.internal_stay_ref_number ?? "-"}
                                            </span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Stay Status</span>
                                            <span className="font-medium">{stay?.status ?? "-"}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Guests</span>
                                            <span className="font-medium">{stay?.no_of_guests ?? "-"}</span>
                                        </div>
                                        <div className="flex flex-col gap-1 md:col-span-2">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Occupants</span>
                                            <span className="font-medium">
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
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                                Device Details
                            </h3>
                            <div className="rounded-md border border-border">
                                <DataState
                                    isLoading={devicesQuery.isLoading}
                                    error={devicesQuery.error}
                                    isEmpty={devices.length === 0}
                                    emptyTitle="No devices installed in this room"
                                >
                                    <Table>
                                        <TableHeader className="bg-muted/50">
                                            <TableRow>
                                                <TableHead className="w-[50px] font-medium">
                                                    S.No
                                                </TableHead>
                                                <TableHead className="font-medium">Device Type</TableHead>
                                                <TableHead className="font-medium">
                                                    Occupancy No
                                                </TableHead>
                                                <TableHead className="font-medium">Name/Tag</TableHead>
                                                <TableHead className="font-medium">Device UID</TableHead>
                                                <TableHead className="font-medium">Config Status</TableHead>
                                                <TableHead className="font-medium text-center">
                                                    Health
                                                </TableHead>
                                                <TableHead className="font-medium text-right">
                                                    Installed On
                                                </TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {devices.map((device, index) => (
                                                <TableRow key={device.id} className="hover:bg-muted/5">
                                                    <TableCell className="font-medium">
                                                        {index + 1}
                                                    </TableCell>
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

                        {/* Service Requests Section (see the file header: the
                            maintenance_request table has no endpoint) */}
                        <section>
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                                Service Requests
                            </h3>
                            <div className="rounded-md border border-border">
                                <DataState
                                    isLoading={requestsQuery.isLoading}
                                    error={requestsQuery.error}
                                    isEmpty={requests.length === 0}
                                    emptyTitle="No service requests recorded for this room"
                                >
                                    <Table>
                                        <TableHeader className="bg-muted/50">
                                            <TableRow>
                                                <TableHead className="font-medium">
                                                    Service Category
                                                </TableHead>
                                                <TableHead className="font-medium">
                                                    Services Type
                                                </TableHead>
                                                <TableHead className="font-medium">Requested On</TableHead>
                                                <TableHead className="font-medium">Expected</TableHead>
                                                <TableHead className="font-medium">Completed</TableHead>
                                                <TableHead className="font-medium">Department</TableHead>
                                                <TableHead className="font-medium">
                                                    Emp ID/Name
                                                </TableHead>
                                                <TableHead className="font-medium text-right">
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
