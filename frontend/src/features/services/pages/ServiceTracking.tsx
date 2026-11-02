import { useState, useMemo } from "react";
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
import { Search, Settings, X, Bed, Briefcase, Building, Utensils, Wrench, HeartPulse, Sparkles } from "lucide-react";
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
} from "recharts";
import { DonutHoleTooltip } from "@/core/components/DonutHoleTooltip";
import {
    Dialog,
    DialogContent,
} from "@/components/ui/dialog";
import { DataState, TableLoading } from "@/core/components/DataState";
import { TablePagination } from "@/core/components/TablePagination";
import { useServiceRequests, useServiceTypes, useServiceTrackingSummary, useServiceRequest } from "@/lib/api/hooks";
import { serviceStatusBadgeClass } from "@/features/occupancy/lib/serviceStatus";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  ServiceRequestActionsDialog,
  type ServiceRequestActionTarget,
} from "../components/ServiceRequestActionsDialog";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";

/**
 * Service Tracking, connected to the Phase 2.5 APIs.
 *
 *   KPI cards  -> GET /service-types + one page of GET /service-requests
 *   Donut      -> completed vs not-completed counts of the same requests
 *   Tables     -> the same requests, filtered by the selected type
 *
 * The seven cards are the seven real `service_type` rows. Card counts and the
 * donut are tallied from that single page (MAX_PAGE_SIZE rows), so they
 * undercount once there are more requests than fit on it. The donut splits on
 * the real `service_status` name "Completed" -- there is no stored ratio.
 *
 * Columns with no source in `service_request`, shown as "-":
 *   the "Maintenance" flag (`maintenance_request` is a separate table).
 *
 * Assignment, status changes and cancellation go through
 * ServiceRequestActionsDialog (PATCH / cancel on /service-requests).
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

const INACTIVE_SLICE_OPACITY = 0.2;

const ServiceTracking = () => {
    const [activeService, setActiveService] = useState<number | null>(null);
    const [hoveredCategory, setHoveredCategory] = useState<string | null>(null);
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    // Pagination sits at the bottom of the table; without this the new
    // page kept the old scroll offset and the sticky header stayed
    // above the fold. See use-scroll-to-top.
    useScrollToTop(currentPage);
    // The real action target: assign / change status / cancel.
    const [actionTarget, setActionTarget] = useState<ServiceRequestActionTarget | null>(null);
    const { canWrite } = useAuth();
    const mayWriteTracking = canWrite("service_tracking");
    const [itemsModalConfig, setItemsModalConfig] = useState<{ isOpen: boolean; roomNo: string; requestId: string | null }>({ isOpen: false, roomNo: "", requestId: null });
    const selectedItemRequest = useServiceRequest(itemsModalConfig.requestId);

    // --- Live data -------------------------------------------------------
    const summaryQuery = useServiceTrackingSummary();
    const typesQuery = useServiceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const serviceTypeRows = typesQuery.data?.items ?? [];

    const selectedTypeId = activeService ?? serviceTypeRows[0]?.id ?? null;
    const selectedType = serviceTypeRows.find((type) => type.id === selectedTypeId);

    const pageSize = parseInt(entriesPerPage) || 10;
    const requestsQuery = useServiceRequests({
        page: currentPage,
        page_size: pageSize,
        service_type: selectedTypeId ?? undefined,
        q: searchQuery || undefined,
    });

    const summaryByType = new Map(
        (summaryQuery.data?.by_type ?? []).map((t) => [t.service_type_id, t])
    );

    const serviceTypes = serviceTypeRows.map((type) => {
        const style = TYPE_STYLES[type.name] ?? DEFAULT_STYLE;
        const typeSum = summaryByType.get(type.id);
        return {
            id: type.id,
            label: type.name,
            count: String(typeSum?.total_count ?? 0),
            ...style,
        };
    });

    const currentTypeSummary = summaryByType.get(selectedTypeId ?? 0);
    const completedCount = currentTypeSummary?.completed_count ?? 0;
    const totalServices = currentTypeSummary?.total_count ?? 0;
    const pendingCount = currentTypeSummary?.pending_count ?? 0;

    const currentChartData = useMemo(() => {
        if (!totalServices) return [];
        return [
            {
                name: "Completed",
                value: completedCount,
                count: completedCount,
                percent: Number(((completedCount / totalServices) * 100).toFixed(1)).toString().replace(/\.0$/, ""),
                color: "#22c55e",
            },
            {
                name: "Pending",
                value: pendingCount,
                count: pendingCount,
                percent: Number(((pendingCount / totalServices) * 100).toFixed(1)).toString().replace(/\.0$/, ""),
                color: "#ef4444",
            },
        ].filter((slice) => slice.value > 0);
    }, [totalServices, completedCount, pendingCount]);

    const hoveredName = useMemo(
        () =>
            hoveredCategory && currentChartData.some((slice) => slice.name === hoveredCategory)
                ? hoveredCategory
                : null,
        [hoveredCategory, currentChartData]
    );

    const isDimmed = (name: string) => hoveredName !== null && name !== hoveredName;

    const hoveredSlice = hoveredName
        ? currentChartData.find((slice) => slice.name === hoveredName)
        : undefined;

    // One row shape covering every table variant below. Each value is a real
    // `service_request` field; "-" means the schema has no such column.
    const rows = (requestsQuery.data?.items ?? []).map((request) => ({
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

    const isLoading = typesQuery.isLoading || requestsQuery.isLoading || summaryQuery.isLoading;
    const error = typesQuery.error ?? requestsQuery.error ?? summaryQuery.error;

    const getStatusBadge = (status: string) => (
        <Badge variant="secondary" className={`${serviceStatusBadgeClass(status)} font-medium border-0`}>
            {status}
        </Badge>
    );

    const renderAction = (status: string, row?: (typeof rows)[number]) => {
        let bgColor = "bg-[#808080] hover:bg-[#666666]"; // Default for Completed etc
        const normalised = status.toLowerCase();
        if (normalised === "assigned") { bgColor = "bg-[#e5a910] hover:bg-[#cc960e]"; }
        else if (normalised === "pending" || normalised.startsWith("cancel")) { bgColor = "bg-[#ed5565] hover:bg-[#da4453]"; }
        else if (normalised === "in progress") { bgColor = "bg-brand-teal hover:bg-[#2e93a8]"; }

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

    const totalEntries = requestsQuery.data?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
    const startIndex = totalEntries === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const endIndex = Math.min(currentPage * pageSize, totalEntries);
    const paginatedData = rows;

    const renderTable = () => {
        switch (selectedType?.name) {
            case "Room Service":
                return (
                    <Table stickyFirstColumn>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Room No</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Type</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Request</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Item</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Assigned To</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Description</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status Reason</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedData.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>{row.serviceType}</TableCell>
                                    <TableCell>{row.request}</TableCell>
                                    <TableCell>
                                        <Badge
                                            variant="outline"
                                            className="text-amber-600 border-amber-600 bg-amber-50 hover:bg-amber-100 cursor-pointer transition-colors"
                                            onClick={() => setItemsModalConfig({ isOpen: true, roomNo: row.roomNo, requestId: row.id })}
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
                    <Table stickyFirstColumn>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Room No</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Type</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Request</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Assigned To</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Description</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status Reason</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedData.map((row) => (
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
                    <Table stickyFirstColumn>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Room No</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Type</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Request</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Assigned To</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Description</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status Reason</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedData.map((row) => (
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
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Room No</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Food Menu</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Assigned To</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Description</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status Reason</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedData.map((row) => (
                                <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                    <TableCell className="font-medium text-foreground">{row.roomNo}</TableCell>
                                    <TableCell>
                                        <Badge
                                            variant="outline"
                                            className="text-amber-600 border-amber-600 bg-amber-50 hover:bg-amber-100 cursor-pointer transition-colors"
                                            onClick={() => setItemsModalConfig({ isOpen: true, roomNo: row.roomNo, requestId: row.id })}
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
                    <Table stickyFirstColumn>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Management</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Category</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Type</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Department</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Assigned To</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">From Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">To Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Start Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">End Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Room No</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Under Maintenance</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedData.map((row) => (
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
                    <Table stickyFirstColumn>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Management</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Category</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Service Type</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Department</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Assigned To</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">From Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">To Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Start Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">End Time</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Room No</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Status</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedData.map((row) => (
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
                    <Table stickyFirstColumn>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
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
                            {paginatedData.map((row) => (
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
        <div className="space-y-5 animate-fade-in text-foreground">
            <ServiceRequestActionsDialog
                open={Boolean(actionTarget)}
                onClose={() => setActionTarget(null)}
                target={actionTarget}
                canWrite={mayWriteTracking}
            />

            <PageHeader title="Services Tracking" />

            {/* KPI Cards Row */}
            <div className="bg-card dark:bg-[#0c101d] rounded-2xl border border-border/80 dark:border-slate-800 p-4 shadow-md">
                <div className="grid grid-cols-2 lg:grid-cols-7 gap-4">
                    {serviceTypes.map((card) => {
                        const IconComp = card.icon;
                        return (
                            <button
                                key={card.id}
                                onClick={() => {
                                    setActiveService(card.id);
                                    // Drop any hover left on the old chart, so the
                                    // centre shows the newly selected type.
                                    setHoveredCategory(null);
                                }}
                                className={`relative bg-white rounded-xl border-2 border-gray-100 shadow-sm overflow-hidden px-5 pt-5 pb-4 transition-all duration-200 cursor-pointer text-left flex flex-col gap-2 ${card.hoverBorder} ${card.id === selectedTypeId ? "ring-2 ring-primary shadow-md" : ""}`}
                            >
                                {/* Icon Badge */}
                                <div className={`w-9 h-9 rounded-full ${card.iconBg} flex items-center justify-center`}>
                                    <IconComp className={`h-4 w-4 ${card.iconColor}`} />
                                </div>
                                {/* Count */}
                                <p className="text-2xl font-bold text-foreground mt-0.5">{card.count}</p>
                                {/* Label */}
                                <p className="text-xs font-medium text-muted-foreground truncate w-full">{card.label}</p>
                                {/* Bottom Bar */}
                                <div className={`w-8 h-1 rounded-full ${card.barColor} mt-0.5`}></div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Donut Chart Section */}
            <div className="bg-card dark:bg-[#0c101d] rounded-2xl border border-border/80 dark:border-slate-800 p-6 shadow-md max-w-lg mx-auto transition-all">
                <div className="flex flex-col items-center">
                    {/* Which type the chart describes. Keyed so it fades in again
                        on every selection, even when the numbers do not change. */}
                    {selectedType && (
                        <p
                            key={selectedTypeId ?? undefined}
                            className="animate-fade-in mb-2 text-sm text-muted-foreground"
                        >
                            Viewing: <span className="font-semibold text-foreground">{selectedType.name}</span>
                        </p>
                    )}
                    <div
                        className="relative w-64 h-64 flex items-center justify-center [&_*:focus:not(:focus-visible)]:outline-none [&_.recharts-sector]:transition-[fill-opacity] [&_.recharts-sector]:duration-300 [&_.recharts-sector]:ease-out"
                        onMouseLeave={() => setHoveredCategory(null)}
                    >
                        <ResponsiveContainer width="100%" height="100%">
                            {/* Keyed on the selected type: Recharts only animates a
                                Pie on mount or on a data change, so two types with
                                the same split (2 and 2) would otherwise show no
                                movement at all. A new key remounts it and the
                                segments redraw from zero on every card click. */}
                            <PieChart key={selectedTypeId ?? undefined}>
                                <Pie
                                    data={currentChartData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius="60%"
                                    outerRadius="90%"
                                    startAngle={90}
                                    endAngle={-270}
                                    paddingAngle={2}
                                    cornerRadius={5}
                                    stroke="none"
                                    dataKey="value"
                                    className="cursor-pointer"
                                    onMouseEnter={(entry, index) => {
                                        const name = entry?.name ?? currentChartData[index]?.name ?? null;
                                        setHoveredCategory(name);
                                    }}
                                >
                                    {currentChartData.map((entry) => (
                                        <Cell
                                            key={entry.name}
                                            fill={entry.color}
                                            fillOpacity={isDimmed(entry.name) ? INACTIVE_SLICE_OPACITY : 1}
                                        />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Centered Donut Hole Tooltip Presentation */}
                        <DonutHoleTooltip
                            hoveredSlice={hoveredSlice}
                            totalValue={totalServices.toLocaleString()}
                            totalLabel={selectedType?.name ?? "services"}
                            restingTitle={selectedType?.name}
                        />
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
                            <span className="text-muted-foreground text-xs font-medium">Search:</span>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                                <Input
                                    placeholder="Search records..."
                                    value={searchQuery}
                                    onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                                    className="pl-9 w-64 md:w-72 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                                />
                            </div>
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
            <TablePagination
                currentPage={currentPage}
                onPageChange={setCurrentPage}
                totalEntries={totalEntries}
                pageSize={pageSize}
                className="mt-4"
            />

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
                        {selectedItemRequest.isLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground animate-pulse">Loading items from database...</div>
                        ) : selectedItemRequest.isError ? (
                            <div className="p-8 text-center text-sm text-red-500">Failed to load request items.</div>
                        ) : (selectedItemRequest.data?.items ?? []).length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">No specific line items recorded for this request.</div>
                        ) : (
                            <table className="w-full text-sm text-left text-gray-800 border-collapse">
                                <thead>
                                    <tr className="bg-gray-50">
                                        <th className="border border-gray-200 p-4 font-semibold text-gray-700 w-24">S.No</th>
                                        <th className="border border-gray-200 p-4 font-semibold text-gray-700">Item Name</th>
                                        <th className="border border-gray-200 p-4 font-semibold text-gray-700 w-64">Quantity</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(selectedItemRequest.data?.items ?? []).map((item, idx) => (
                                        <tr key={item.id || idx}>
                                            <td className="border border-gray-200 p-4 font-medium">{idx + 1}</td>
                                            <td className="border border-gray-200 p-4 font-medium">{item.item_name ?? "Item"}</td>
                                            <td className="border border-gray-200 p-4 font-medium">{item.quantity ?? 1}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default ServiceTracking;
