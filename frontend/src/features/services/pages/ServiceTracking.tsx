import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Search, ChevronLeft, ChevronRight, Eye, Edit, Share2, Pencil, Settings, X, ChevronDown, Bed, Briefcase, Building, Utensils, Wrench, HeartPulse, Sparkles } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    Tooltip,
} from "recharts";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useServiceRequests, useServiceStatuses, useServiceTypes } from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  ServiceRequestActionsDialog,
  type ServiceRequestActionTarget,
} from "../components/ServiceRequestActionsDialog";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Service Tracking, connected to the Phase 2.5 APIs.
 *
 *   KPI cards  -> GET /service-types  + GET /service-requests?service_type=N
 *   Donut      -> completed vs not-completed counts of the same requests
 *   Tables     -> GET /service-requests, filtered by the selected type
 *
 * The seven cards are the seven real `service_type` rows. Counts are the API's
 * `total`, never a length of the current page. The donut splits on the real
 * `service_status` name "Completed" -- there is no stored completion ratio.
 *
 * Columns with no source in `service_request`, shown as "-":
 *   Time span (start/stop time), "Maintenance" flag and the per-request staff
 *   list. `maintenance_request` is a separate table with no endpoint.
 *
 * This screen is read-only: assignment and status changes need write
 * endpoints, which Phase 2.10 does not add.
 */

/** Card/tab id -> icon and colour treatment, keyed by the real type name. */
const TYPE_STYLES: Record<string, { icon: typeof Bed; iconColor: string; iconBg: string; barColor: string; hoverBorder: string }> = {
    "Room Service": {
        icon: Bed, iconColor: "text-blue-600 dark:text-blue-400",
        iconBg: "bg-blue-50 dark:bg-blue-950/40", barColor: "bg-blue-500",
        hoverBorder: "hover:border-blue-500 hover:ring-2 hover:ring-blue-500/30",
    },
    "Travel Desk": {
        icon: Briefcase, iconColor: "text-foreground dark:text-purple-400",
        iconBg: "bg-purple-50 dark:bg-purple-950/40", barColor: "bg-purple-500",
        hoverBorder: "hover:border-purple-500 hover:ring-2 hover:ring-purple-500/30",
    },
    "Business Center": {
        icon: Building, iconColor: "text-green-600 dark:text-green-400",
        iconBg: "bg-green-50 dark:bg-green-950/40", barColor: "bg-green-500",
        hoverBorder: "hover:border-green-500 hover:ring-2 hover:ring-green-500/30",
    },
    "Food Order": {
        icon: Utensils, iconColor: "text-cyan-600 dark:text-cyan-400",
        iconBg: "bg-cyan-50 dark:bg-cyan-950/40", barColor: "bg-cyan-500",
        hoverBorder: "hover:border-cyan-500 hover:ring-2 hover:ring-cyan-500/30",
    },
    "Facility Maintenance Service": {
        icon: Wrench, iconColor: "text-orange-500 dark:text-orange-400",
        iconBg: "bg-orange-50 dark:bg-orange-950/40", barColor: "bg-orange-500",
        hoverBorder: "hover:border-orange-500 hover:ring-2 hover:ring-orange-500/30",
    },
    "Health & Fitness": {
        icon: HeartPulse, iconColor: "text-red-600 dark:text-red-400",
        iconBg: "bg-red-50 dark:bg-red-950/40", barColor: "bg-red-500",
        hoverBorder: "hover:border-red-500 hover:ring-2 hover:ring-red-500/30",
    },
    "Sanitation Maintenance Service": {
        icon: Sparkles, iconColor: "text-slate-600 dark:text-slate-400",
        iconBg: "bg-slate-100 dark:bg-slate-800/40", barColor: "bg-slate-500",
        hoverBorder: "hover:border-slate-500 hover:ring-2 hover:ring-slate-500/30",
    },
};

const DEFAULT_STYLE = {
    icon: Wrench, iconColor: "text-slate-600 dark:text-slate-400",
    iconBg: "bg-slate-100 dark:bg-slate-800/40", barColor: "bg-slate-500",
    hoverBorder: "hover:border-slate-500 hover:ring-2 hover:ring-slate-500/30",
};

const formatDate = (value: string | null) => (value ? new Date(value).toLocaleDateString() : "-");
const formatTime = (value: string | null) =>
    value ? new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "-";

const ServiceTracking = () => {
    const [activeService, setActiveService] = useState<number | null>(null);
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [statusModalConfig, setStatusModalConfig] = useState<{ isOpen: boolean; type: "yellow" | "red" | "blue" | null }>({ isOpen: false, type: null });
    // The real action target: assign / change status / cancel.
    const [actionTarget, setActionTarget] = useState<ServiceRequestActionTarget | null>(null);
    const { canWrite } = useAuth();
    const mayWriteTracking = canWrite("service_tracking");
    const [itemsModalConfig, setItemsModalConfig] = useState<{ isOpen: boolean; roomNo: string }>({ isOpen: false, roomNo: "" });

    // --- Live data -------------------------------------------------------
    const typesQuery = useServiceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const statusesQuery = useServiceStatuses({ page: 1, page_size: MAX_PAGE_SIZE });
    // One page of every request: the cards need per-type counts and the donut
    // needs the status split, and the seeded volume fits inside one page.
    const allRequestsQuery = useServiceRequests({ page: 1, page_size: MAX_PAGE_SIZE });

    const serviceTypeRows = typesQuery.data?.items ?? [];
    const allRequests = allRequestsQuery.data?.items ?? [];

    const selectedTypeId = activeService ?? serviceTypeRows[0]?.id ?? null;
    const selectedType = serviceTypeRows.find((type) => type.id === selectedTypeId);

    const serviceTypes = serviceTypeRows.map((type) => {
        const style = TYPE_STYLES[type.name] ?? DEFAULT_STYLE;
        return {
            id: type.id,
            label: type.name,
            count: String(allRequests.filter((request) => request.service_type === type.id).length),
            ...style,
        };
    });

    const requestsForType = allRequests.filter(
        (request) => request.service_type === selectedTypeId,
    );

    const completedCount = requestsForType.filter(
        (request) => request.status_name === "Completed",
    ).length;
    const totalServices = requestsForType.length;
    const currentChartData = totalServices
        ? [
            { name: "Completed", value: Number(((completedCount / totalServices) * 100).toFixed(2)), color: "#22c55e" },
            { name: "Pending", value: Number((((totalServices - completedCount) / totalServices) * 100).toFixed(2)), color: "#ef4444" },
        ]
        : [];

    // One row shape covering every table variant below. Each value is a real
    // `service_request` field; "-" means the schema has no such column.
    const rows = requestsForType.map((request) => ({
        id: request.id,
        statusId: request.status ?? null,
        assignedToId: request.assignee?.id ?? null,
        statusReasonRaw: request.status_reason ?? null,
        refNumber: request.ref_number ?? "-",
        roomNo: request.amenity_name ?? "-",
        serviceType: request.service_type_name ?? "-",
        request: request.category_name ?? "-",
        item: "Items",
        menu: request.category_name ?? "-",
        management: request.request_source ?? "-",
        category: request.category_name ?? "-",
        type: request.service_type_name ?? "-",
        dept: request.department_name ?? "-",
        assignedTo: request.assignee
            ? [request.assignee.emp_id, request.assignee.name].filter(Boolean).join(" / ")
            : "- / -",
        date: formatDate(request.created_on),
        time: formatTime(request.created_on),
        from: formatDate(request.created_on),
        to: formatDate(request.expected_date),
        start: formatTime(request.created_on),
        end: formatTime(request.completed_on),
        maintenance: "-",
        description: request.description ?? "-",
        statusReason: request.status_reason ?? "-",
        status: request.status_name ?? "-",
    }));

    const isLoading =
        typesQuery.isLoading || statusesQuery.isLoading || allRequestsQuery.isLoading;
    const error = typesQuery.error ?? statusesQuery.error ?? allRequestsQuery.error;

    const getStatusBadge = (status: string) => {
        let colorClass = "bg-gray-500/20 text-gray-400";
        const normalised = status.toLowerCase();
        if (normalised === "assigned") colorClass = "bg-cyan-500/20 text-cyan-400";
        else if (normalised === "completed") colorClass = "bg-emerald-500/20 text-emerald-500";
        else if (normalised === "pending") colorClass = "bg-amber-500/20 text-amber-500";
        else if (normalised === "canceled" || normalised === "cancelled") colorClass = "bg-red-500/20 text-red-500";
        else if (normalised === "partially completed") colorClass = "bg-blue-500/20 text-blue-500";

        return (
            <Badge className={`${colorClass} hover:${colorClass} font-medium border-0`}>
                {status}
            </Badge>
        );
    };

    const renderAction = (status: string, row?: (typeof rows)[number]) => {
        let bgColor = "bg-[#808080] hover:bg-[#666666]"; // Default for Completed etc
        let modalType: "yellow" | "red" | "blue" | null = null;
        const normalised = status.toLowerCase();
        if (normalised === "assigned") { bgColor = "bg-[#e5a910] hover:bg-[#cc960e]"; modalType = "yellow"; }
        else if (normalised === "pending" || normalised.startsWith("cancel")) { bgColor = "bg-[#ed5565] hover:bg-[#da4453]"; modalType = "red"; }
        else if (normalised === "partially completed") { bgColor = "bg-[#3eb1c8] hover:bg-[#2e93a8]"; modalType = "blue"; }

        return (
            <div className="flex justify-center gap-2">
                <Button
                    size="icon"
                    className={`h-7 w-7 ${bgColor} text-white rounded-sm`}
                    disabled={!mayWriteTracking || !row}
                    title={
                        mayWriteTracking
                            ? "Assign, change status or cancel"
                            : "Your role cannot change service requests"
                    }
                    onClick={() => {
                        if (!row) return;
                        setActionTarget({
                            id: row.id,
                            ref: row.refNumber,
                            statusId: row.statusId,
                            assignedToId: row.assignedToId,
                            statusReason: row.statusReasonRaw,
                        });
                    }}
                >
                    <Settings className="h-4 w-4" />
                </Button>
            </div>
        );
    };

    const renderTable = () => {
        switch (selectedType?.name) {
            case "Room Service":
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Type</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Request</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Item</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status Reason</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>{row.serviceType}</TableCell>
                                    <TableCell>{row.request}</TableCell>
                                    <TableCell>
                                        <Badge
                                            variant="outline"
                                            className="text-amber-600 border-amber-600 bg-amber-50 hover:bg-amber-100 cursor-pointer transition-colors"
                                            onClick={() => setItemsModalConfig({ isOpen: true, roomNo: row.roomNo })}
                                        >
                                            {row.item}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-muted-foreground">{row.assignedTo}</TableCell>
                                    <TableCell>{row.date}</TableCell>
                                    <TableCell>{row.time}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.description}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.statusReason}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                    <TableCell>
                                        {renderAction(row.status, row)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "Travel Desk":
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Type</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Request</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status Reason</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>{row.serviceType}</TableCell>
                                    <TableCell>{row.request}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.assignedTo}</TableCell>
                                    <TableCell>{row.date}</TableCell>
                                    <TableCell>{row.time}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.description}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.statusReason}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                    <TableCell>
                                        {renderAction(row.status, row)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "Business Center":
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Type</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Request</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status Reason</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>{row.serviceType}</TableCell>
                                    <TableCell>{row.request}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.assignedTo}</TableCell>
                                    <TableCell>{row.date}</TableCell>
                                    <TableCell>{row.time}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.description}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.statusReason}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                    <TableCell>
                                        {renderAction(row.status, row)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "Food Order":
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Food Menu</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status Reason</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>
                                        <Badge
                                            variant="outline"
                                            className="text-amber-600 border-amber-600 bg-amber-50 hover:bg-amber-100 cursor-pointer transition-colors"
                                            onClick={() => setItemsModalConfig({ isOpen: true, roomNo: row.roomNo })}
                                        >
                                            {row.menu}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-muted-foreground">{row.assignedTo}</TableCell>
                                    <TableCell>{row.date}</TableCell>
                                    <TableCell>{row.time}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.description}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.statusReason}</TableCell>
                                    <TableCell>
                                        {renderAction(row.status, row)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "Facility Maintenance Service":
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Service Management</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Category</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Type</TableHead>
                                <TableHead className="text-gray-600 font-medium">Department</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">From Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">To Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Start Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">End Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Under Maintenance</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell>{row.management}</TableCell>
                                    <TableCell>{row.category}</TableCell>
                                    <TableCell>{row.type}</TableCell>
                                    <TableCell>{row.dept}</TableCell>
                                    <TableCell className="text-blue-600 cursor-pointer hover:underline">{row.assignedTo}</TableCell>
                                    <TableCell>{row.from}</TableCell>
                                    <TableCell>{row.to}</TableCell>
                                    <TableCell>{row.start}</TableCell>
                                    <TableCell>{row.end}</TableCell>
                                    <TableCell className="text-blue-600 cursor-pointer hover:underline">{row.roomNo}</TableCell>
                                    <TableCell>{row.maintenance}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                    <TableCell>
                                        {renderAction(row.status, row)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "Sanitation Maintenance Service":
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Service Management</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Category</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Type</TableHead>
                                <TableHead className="text-gray-600 font-medium">Department</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">From Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">To Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Start Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">End Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell>{row.management}</TableCell>
                                    <TableCell>{row.category}</TableCell>
                                    <TableCell>{row.type}</TableCell>
                                    <TableCell>{row.dept}</TableCell>
                                    <TableCell className="text-blue-600 cursor-pointer hover:underline">{row.assignedTo}</TableCell>
                                    <TableCell>{row.from}</TableCell>
                                    <TableCell>{row.to}</TableCell>
                                    <TableCell>{row.start}</TableCell>
                                    <TableCell>{row.end}</TableCell>
                                    <TableCell className="text-blue-600 cursor-pointer hover:underline">{row.roomNo}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                    <TableCell>
                                        {renderAction(row.status, row)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            default:
                // Any other service type uses the standard request columns.
                return (
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Type</TableHead>
                                <TableHead className="text-gray-600 font-medium">Service Request</TableHead>
                                <TableHead className="text-gray-600 font-medium">Assigned To</TableHead>
                                <TableHead className="text-gray-600 font-medium">Date</TableHead>
                                <TableHead className="text-gray-600 font-medium">Time</TableHead>
                                <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status Reason</TableHead>
                                <TableHead className="text-gray-600 font-medium">Status</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>{row.serviceType}</TableCell>
                                    <TableCell>{row.request}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.assignedTo}</TableCell>
                                    <TableCell>{row.date}</TableCell>
                                    <TableCell>{row.time}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.description}</TableCell>
                                    <TableCell className="text-muted-foreground">{row.statusReason}</TableCell>
                                    <TableCell>{getStatusBadge(row.status)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
        }
    };

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            <ServiceRequestActionsDialog
                open={Boolean(actionTarget)}
                onClose={() => setActionTarget(null)}
                target={actionTarget}
                canWrite={mayWriteTracking}
            />

            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
            </div>

            {/* KPI Cards Row */}
            <div className="bg-white/60 rounded-2xl border border-gray-200/60 p-4 shadow-sm">
                <div className="grid grid-cols-2 lg:grid-cols-7 gap-4">
                    {serviceTypes.map((card) => {
                        const IconComp = card.icon;
                        return (
                            <button
                                key={card.id}
                                onClick={() => setActiveService(card.id)}
                                className={`relative bg-white rounded-xl border-2 border-gray-100 shadow-sm overflow-hidden px-5 pt-5 pb-4 transition-all duration-200 cursor-pointer text-left flex flex-col gap-2 ${card.hoverBorder} ${card.id === selectedTypeId ? "ring-2 ring-primary shadow-md" : ""}`}
                            >
                                {/* Icon Badge */}
                                <div className={`w-10 h-10 rounded-full ${card.iconBg} flex items-center justify-center`}>
                                    <IconComp className={`h-5 w-5 ${card.iconColor}`} />
                                </div>
                                {/* Count */}
                                <p className="text-3xl font-bold text-gray-900 mt-1">{card.count}</p>
                                {/* Label */}
                                <p className="text-xs font-medium text-gray-500 truncate w-full">{card.label}</p>
                                {/* Bottom Bar */}
                                <div className={`w-8 h-1 rounded-full ${card.barColor} mt-1`}></div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Donut Chart Section */}
            <div className="flex justify-center py-6">
                <div className="relative">
                    <div className="h-64 w-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={currentChartData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={80}
                                    outerRadius={100}
                                    startAngle={-40}
                                    endAngle={220}
                                    paddingAngle={0}
                                    dataKey="value"
                                    cornerRadius={10}
                                    stroke="none"
                                >
                                    {currentChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: "hsl(var(--card))",
                                        border: "1px solid hsl(var(--border))",
                                        borderRadius: "8px",
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Center text */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-2">
                            <span className="text-5xl font-bold text-foreground">{totalServices}</span>
                            <span className="text-sm text-muted-foreground mt-1">Services</span>
                        </div>
                    </div>
                    <div className="flex justify-center gap-6 mt-2">
                        {currentChartData.map((data, index) => (
                            <div key={index} className="flex flex-col items-center">
                                <span className="text-foreground font-medium">{data.name}</span>
                                <span className="text-muted-foreground text-xs">{data.value}%</span>
                                <div className={`w-8 h-1 mt-1 rounded-full`} style={{ backgroundColor: data.color }}></div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Table Container */}
            {/* Controls */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                    <span className="text-sm">Show</span>
                    <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                        <SelectTrigger className="w-16 h-8 bg-white text-foreground border border-gray-200">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-popover text-popover-foreground border-border">
                            <SelectItem value="10">10</SelectItem>
                            <SelectItem value="25">25</SelectItem>
                            <SelectItem value="50">50</SelectItem>
                            <SelectItem value="100">100</SelectItem>
                        </SelectContent>
                    </Select>
                    <span className="text-sm">entries</span>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-sm">Search:</span>
                    <Input
                        placeholder="Employee First name/ Last name, ID, Room No"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-80 h-8 bg-white text-foreground border border-gray-200"
                    />
                </div>
            </div>

            <div className="rounded-sm overflow-hidden border border-gray-200 bg-white">
                <DataState
                    isLoading={isLoading}
                    error={error}
                    isEmpty={rows.length === 0}
                    emptyTitle="No service requests for this service type"
                    loader={<TableLoading columns={10} />}
                >
                    {renderTable()}
                </DataState>
            </div>
            {/* Footer */}
            <div className="flex items-center justify-between mt-4 text-muted-foreground">
                <span className="text-sm">
                    Showing 1 to {Math.min(parseInt(entriesPerPage), 10)} of {136} entries
                </span>

                <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">First</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">Previous</Button>
                    <Button variant="ghost" size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90 w-8 h-8 p-0">1</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground w-8 h-8 p-0">2</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground w-8 h-8 p-0">3</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground w-8 h-8 p-0">4</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground w-8 h-8 p-0">5</Button>
                    <span className="px-2">...</span>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground w-8 h-8 p-0">14</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">Next</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">Last</Button>
                </div>
            </div>

            {/* Status Update Modal */}
            <Dialog open={statusModalConfig.isOpen} onOpenChange={(open) => setStatusModalConfig({ ...statusModalConfig, isOpen: open })}>
                <DialogContent className="max-w-[650px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-none">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Status Update</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setStatusModalConfig({ ...statusModalConfig, isOpen: false })}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>

                    <div className="px-16 py-12 space-y-8">
                        {statusModalConfig.type === "yellow" && (
                            <>
                                <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-800 text-left">Status <span className="text-red-500">*</span></Label>
                                    <div className="relative">
                                        <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                            <option>Assigned</option>
                                        </select>
                                        <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-800 text-left">Department <span className="text-red-500">*</span></Label>
                                    <div className="relative">
                                        <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                            <option>Housekeeping Manager</option>
                                        </select>
                                        <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-800 text-left">Assign To <span className="text-red-500">*</span></Label>
                                    <div className="relative">
                                        <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                            <option>Alice konyak</option>
                                        </select>
                                        <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                                    </div>
                                </div>
                                <div className="flex justify-end pt-2">
                                    <Button className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white border-0 h-9 px-6 rounded-sm font-normal" onClick={() => setStatusModalConfig({ ...statusModalConfig, isOpen: false })}>Submit</Button>
                                </div>
                            </>
                        )}
                        {statusModalConfig.type === "red" && (
                            <>
                                <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-800 text-left">Status <span className="text-red-500">*</span></Label>
                                    <div className="relative">
                                        <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                            <option>Pending</option>
                                        </select>
                                        <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                                    </div>
                                </div>
                                <div className="flex justify-end pt-2">
                                    <Button className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white border-0 h-9 px-6 rounded-sm font-normal" onClick={() => setStatusModalConfig({ ...statusModalConfig, isOpen: false })}>Submit</Button>
                                </div>
                            </>
                        )}
                        {statusModalConfig.type === "blue" && (
                            <>
                                <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-800 text-left">Status</Label>
                                    <div className="relative">
                                        <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                            <option>Partially completed</option>
                                        </select>
                                        <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-[140px_1fr] gap-6 items-start mt-8">
                                    <Label className="text-sm font-medium text-gray-800 text-left pt-1">Description <span className="text-red-500">*</span></Label>
                                    <div className="relative">
                                        <textarea rows={1} defaultValue={"Test"} className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-2 text-sm outline-none resize-none overflow-hidden" style={{ minHeight: "28px" }}></textarea>
                                        <div className="absolute right-0 bottom-1 pointer-events-none">
                                            <svg width="6" height="6" viewBox="0 0 6 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M6 6L0 6L6 0L6 6Z" fill="#cccccc" />
                                            </svg>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex justify-end pt-2">
                                    <Button className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white border-0 h-9 px-6 rounded-sm font-normal" onClick={() => setStatusModalConfig({ ...statusModalConfig, isOpen: false })}>Submit</Button>
                                </div>
                            </>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Items Modal */}
            <Dialog open={itemsModalConfig.isOpen} onOpenChange={(open) => setItemsModalConfig({ ...itemsModalConfig, isOpen: open })}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[2px]">
                    <div className="flex justify-between items-center p-4 px-6 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-lg font-semibold text-gray-800 tracking-wide">Room {itemsModalConfig.roomNo}</h2>
                        <Button variant="ghost" className="h-[30px] w-[30px] p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setItemsModalConfig({ ...itemsModalConfig, isOpen: false })}>
                            <X className="h-5 w-5 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>

                    <div className="p-8 pb-10">
                        <table className="w-full text-sm text-left text-gray-800 border-collapse">
                            <thead>
                                <tr className="bg-gray-50">
                                    <th className="border border-gray-200 p-4 font-semibold text-gray-700 w-24">S.No</th>
                                    <th className="border border-gray-200 p-4 font-semibold text-gray-700">Item Name</th>
                                    <th className="border border-gray-200 p-4 font-semibold text-gray-700 w-64">Quantity</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td className="border border-gray-200 p-4 font-medium">1</td>
                                    <td className="border border-gray-200 p-4 font-medium">Wipes</td>
                                    <td className="border border-gray-200 p-4 font-medium">1</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-200 p-4 font-medium">2</td>
                                    <td className="border border-gray-200 p-4 font-medium">Trimmer</td>
                                    <td className="border border-gray-200 p-4 font-medium">1</td>
                                </tr>
                                <tr>
                                    <td className="border border-gray-200 p-4 font-medium">3</td>
                                    <td className="border border-gray-200 p-4 font-medium">Soap</td>
                                    <td className="border border-gray-200 p-4 font-medium">1</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default ServiceTracking;
