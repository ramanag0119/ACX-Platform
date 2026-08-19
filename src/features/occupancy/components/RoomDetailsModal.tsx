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

interface RoomDetailsModalProps {
    roomNo: string | null;
    isOpen: boolean;
    onClose: () => void;
    roomType?: string;
    guestName?: string;
    status?: string;
}

// Mock data (replace with real data fetching later)
const maintenanceData = [
    {
        category: "Installing",
        type: "Electrical",
        fromDate: "20-03-2023",
        toDate: "20-03-2023",
        startTime: "18:29",
        stopTime: "19:15",
        department: "Maintenance",
        emp: "Jegan G",
        status: "Completed",
    },
    {
        category: "Cleaning",
        type: "Room Cleaning",
        fromDate: "21-03-2023",
        toDate: "21-03-2023",
        startTime: "01:34",
        stopTime: "14:00",
        department: "Housekeeping",
        emp: "Balaji G",
        status: "Completed",
    },
    {
        category: "Cleaning",
        type: "Room Cleaning",
        fromDate: "21-03-2023",
        toDate: "21-03-2023",
        startTime: "17:04",
        stopTime: "17:15",
        department: "Housekeeping",
        emp: "Balaji G",
        status: "Completed",
    },
    {
        category: "Cleaning",
        type: "Room Cleaning",
        fromDate: "21-03-2023",
        toDate: "21-03-2023",
        startTime: "17:09",
        stopTime: "17:50",
        department: "Housekeeping",
        emp: "Balaji G",
        status: "Completed",
    },
    {
        category: "Installing",
        type: "Electrical",
        fromDate: "25-03-2023",
        toDate: "25-03-2023",
        startTime: "18:08",
        stopTime: "18:10",
        department: "Maintenance",
        emp: "Queen Evang...",
        status: "Completed",
    },
    {
        category: "Housekeeping",
        type: "Room Cleaning",
        fromDate: "25-03-2023",
        toDate: "25-03-2023",
        startTime: "18:12",
        stopTime: "18:45",
        department: "Housekeeping",
        emp: "Balaji G",
        status: "Completed",
    },
];

const devicesData = [
    {
        type: "Intellihub",
        name: "106HUB01",
        mac: "0101060000000001",
        status: "Decommissioned",
        health: "error",
        addedOn: "05-04-2023",
    },
    {
        type: "Kleio",
        name: "106KLE01",
        mac: "0401060000000001",
        status: "Decommissioned",
        health: "error",
        addedOn: "20-03-2023",
    },
    {
        type: "Mikos",
        name: "106MIK01",
        mac: "0301060000000001",
        status: "Decommissioned",
        health: "error",
        addedOn: "20-03-2023",
    },
    {
        type: "AirQ",
        name: "106AIR01",
        mac: "0201060000000001",
        status: "Decommissioned",
        health: "error",
        addedOn: "20-03-2023",
    },
    {
        type: "Intellihub",
        name: "106HUB01",
        mac: "0101060000000001",
        status: "Decommissioned",
        health: "error",
        addedOn: "20-03-2023",
    },
    {
        type: "Kleio",
        name: "106KLE01",
        mac: "",
        status: "Commissioned",
        health: "success",
        addedOn: "06-04-2023",
    },
    {
        type: "Mikos",
        name: "106MIK01",
        mac: "",
        status: "Commissioned",
        health: "success",
        addedOn: "06-04-2023",
    },
];

export function RoomDetailsModal({
    roomNo,
    isOpen,
    onClose,
    roomType = "Delux Package",
    guestName = "-",
    status = "Available",
}: RoomDetailsModalProps) {
    if (!roomNo) return null;

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0 bg-background text-foreground border-border">
                <DialogHeader className="p-6 pb-2 border-b border-border">
                    <div className="flex items-center justify-between">
                        <DialogTitle className="text-xl font-semibold">
                            Occupancy No: {roomNo}
                        </DialogTitle>
                        <Badge variant={status === "Available" ? "outline" : "destructive"} className="mr-8">
                            {status}
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
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-4 text-sm">
                                <div className="space-y-1">
                                    <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                        Room Allotted :
                                    </span>
                                    <span className="font-medium">{roomNo}</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                        Room Category :
                                    </span>
                                    <span className="font-medium">{roomType}</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                        Floor :
                                    </span>
                                    <span className="font-medium">Building A - Floor 1</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                        Checkin Date :
                                    </span>
                                    <span className="font-medium">{status === "Unavailable" ? "12-Oct-2023" : "-"}</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-muted-foreground block text-xs uppercase tracking-wider">
                                        Checkout Date :
                                    </span>
                                    <span className="font-medium">{status === "Unavailable" ? "15-Oct-2023" : "-"}</span>
                                </div>
                            </div>
                        </section>

                        {/* Occupants Details Section */}
                        <section>
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                                Occupants Details
                            </h3>
                            {guestName !== "-" && status === "Unavailable" ? (
                                <div className="rounded-md border border-border p-4">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Primary Guest</span>
                                            <span className="font-medium text-base">{guestName}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Contact</span>
                                            <span className="font-medium">+1 (555) 123-4567</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Email</span>
                                            <span className="font-medium">{guestName.toLowerCase().replace(/\s+/g, '.')}@example.com</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">ID Proof</span>
                                            <span className="font-medium">Passport (Active)</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Nationality</span>
                                            <span className="font-medium">United States</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Pax</span>
                                            <span className="font-medium">2 Adults, 1 Child</span>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-sm text-muted-foreground italic border border-dashed border-border p-4 rounded-md bg-muted/30">
                                    No active occupants recorded for this room.
                                </div>
                            )}
                        </section>

                        {/* Device Details Section */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Device Details
                            </h3>
                            <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800">
                                <Table>
                                    <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                                        <TableRow className="border-b border-border dark:border-slate-800">
                                            <TableHead className="w-[50px] text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                S.No
                                            </TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Device Type</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                Occupancy No
                                            </TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Name/Tag</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">MAC Address</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Status</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 text-center">
                                                Health
                                            </TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 text-right">
                                                Added On
                                            </TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {devicesData.map((device, index) => (
                                            <TableRow key={index} className="hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 text-[13px]">
                                                <TableCell className="font-medium py-2.5 px-3">
                                                    {index + 1}
                                                </TableCell>
                                                <TableCell className="py-2.5 px-3">{device.type}</TableCell>
                                                <TableCell className="py-2.5 px-3">{roomNo}</TableCell>
                                                <TableCell className="py-2.5 px-3">{device.name}</TableCell>
                                                <TableCell className="font-mono text-xs py-2.5 px-3">
                                                    {device.mac || "-"}
                                                </TableCell>
                                                <TableCell className="py-2.5 px-3">
                                                    <span
                                                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11.5px] font-medium border ${
                                                            device.status === "Commissioned"
                                                                ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:border-emerald-500/40 dark:bg-emerald-950/60 dark:text-emerald-400"
                                                                : "bg-slate-100 text-slate-600 border-slate-200 dark:border-slate-700/60 dark:bg-slate-800/60 dark:text-slate-400"
                                                        }`}
                                                    >
                                                        {device.status}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-center py-2.5 px-3">
                                                    {device.health === "success" ? (
                                                        <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400 mx-auto" />
                                                    ) : (
                                                        <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 mx-auto" />
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-right py-2.5 px-3 text-muted-foreground">
                                                    {device.addedOn}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        </section>

                        {/* Maintenance Details Section */}
                        <section>
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                                Maintenance Details
                            </h3>
                            <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800">
                                <Table>
                                    <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                                        <TableRow className="border-b border-border dark:border-slate-800">
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                Service Category
                                            </TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">
                                                Services Type
                                            </TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">From Date</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">To Date</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Start Time</TableHead>
                                            <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">Stop Time</TableHead>
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
                                        {maintenanceData.map((item, index) => (
                                            <TableRow key={index} className="hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 text-[13px]">
                                                <TableCell className="py-2.5 px-3">{item.category}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.type}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.fromDate}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.toDate}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.startTime}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.stopTime}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.department}</TableCell>
                                                <TableCell className="py-2.5 px-3">{item.emp}</TableCell>
                                                <TableCell className="text-right py-2.5 px-3">
                                                    <span
                                                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11.5px] font-medium border bg-emerald-50 text-emerald-700 border-emerald-200 dark:border-emerald-500/40 dark:bg-emerald-950/60 dark:text-emerald-400"
                                                    >
                                                        {item.status}
                                                    </span>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        </section>
                    </div>
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
}
