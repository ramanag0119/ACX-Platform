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
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                                Device Details
                            </h3>
                            <div className="rounded-md border border-border">
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
                                            <TableHead className="font-medium">MAC Address</TableHead>
                                            <TableHead className="font-medium">Status</TableHead>
                                            <TableHead className="font-medium text-center">
                                                Health
                                            </TableHead>
                                            <TableHead className="font-medium text-right">
                                                Added On
                                            </TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {devicesData.map((device, index) => (
                                            <TableRow key={index} className="hover:bg-muted/5">
                                                <TableCell className="font-medium">
                                                    {index + 1}
                                                </TableCell>
                                                <TableCell>{device.type}</TableCell>
                                                <TableCell>{roomNo}</TableCell>
                                                <TableCell>{device.name}</TableCell>
                                                <TableCell className="font-mono text-xs">
                                                    {device.mac || "-"}
                                                </TableCell>
                                                <TableCell>
                                                    <span
                                                        className={
                                                            device.status === "Commissioned"
                                                                ? "text-green-600"
                                                                : "text-muted-foreground"
                                                        }
                                                    >
                                                        {device.status}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {device.health === "success" ? (
                                                        <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                                                    ) : (
                                                        <XCircle className="h-4 w-4 text-red-500 mx-auto" />
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-right">
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
                            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                                Maintenance Details
                            </h3>
                            <div className="rounded-md border border-border">
                                <Table>
                                    <TableHeader className="bg-muted/50">
                                        <TableRow>
                                            <TableHead className="font-medium">
                                                Service Category
                                            </TableHead>
                                            <TableHead className="font-medium">
                                                Services Type
                                            </TableHead>
                                            <TableHead className="font-medium">From Date</TableHead>
                                            <TableHead className="font-medium">To Date</TableHead>
                                            <TableHead className="font-medium">Start Time</TableHead>
                                            <TableHead className="font-medium">Stop Time</TableHead>
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
                                        {maintenanceData.map((item, index) => (
                                            <TableRow key={index} className="hover:bg-muted/5">
                                                <TableCell>{item.category}</TableCell>
                                                <TableCell>{item.type}</TableCell>
                                                <TableCell>{item.fromDate}</TableCell>
                                                <TableCell>{item.toDate}</TableCell>
                                                <TableCell>{item.startTime}</TableCell>
                                                <TableCell>{item.stopTime}</TableCell>
                                                <TableCell>{item.department}</TableCell>
                                                <TableCell>{item.emp}</TableCell>
                                                <TableCell className="text-right">
                                                    <Badge
                                                        variant="secondary"
                                                        className="bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400"
                                                    >
                                                        {item.status}
                                                    </Badge>
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
