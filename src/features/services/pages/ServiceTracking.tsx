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
    Sector,
} from "recharts";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

// KPI Card data
const serviceTypes = [
    { 
        id: "room-service", 
        label: "Room Service", 
        count: "55", 
        icon: Bed, 
        iconColor: "text-blue-600 dark:text-blue-400", 
        iconBg: "bg-blue-50 dark:bg-blue-950/40", 
        barColor: "bg-blue-500",
        hoverBorder: "hover:border-blue-500 hover:ring-2 hover:ring-blue-500/30" 
    },
    { 
        id: "travel-desk", 
        label: "Travel Desk", 
        count: "1", 
        icon: Briefcase, 
        iconColor: "text-purple-600 dark:text-purple-400", 
        iconBg: "bg-purple-50 dark:bg-purple-950/40", 
        barColor: "bg-purple-500",
        hoverBorder: "hover:border-purple-500 hover:ring-2 hover:ring-purple-500/30" 
    },
    { 
        id: "business-center", 
        label: "Business Center", 
        count: "3", 
        icon: Building, 
        iconColor: "text-green-600 dark:text-green-400", 
        iconBg: "bg-green-50 dark:bg-green-950/40", 
        barColor: "bg-green-500",
        hoverBorder: "hover:border-green-500 hover:ring-2 hover:ring-green-500/30" 
    },
    { 
        id: "food-order", 
        label: "Food Order", 
        count: "51", 
        icon: Utensils, 
        iconColor: "text-cyan-600 dark:text-cyan-400", 
        iconBg: "bg-cyan-50 dark:bg-cyan-950/40", 
        barColor: "bg-cyan-500",
        hoverBorder: "hover:border-cyan-500 hover:ring-2 hover:ring-cyan-500/30" 
    },
    { 
        id: "facility-services", 
        label: "Facility Services", 
        count: "104174", 
        icon: Wrench, 
        iconColor: "text-orange-500 dark:text-orange-400", 
        iconBg: "bg-orange-50 dark:bg-orange-950/40", 
        barColor: "bg-orange-500",
        hoverBorder: "hover:border-orange-500 hover:ring-2 hover:ring-orange-500/30" 
    },
    { 
        id: "health-fitness", 
        label: "Health & Fitness", 
        count: "0", 
        icon: HeartPulse, 
        iconColor: "text-red-600 dark:text-red-400", 
        iconBg: "bg-red-50 dark:bg-red-950/40", 
        barColor: "bg-red-500",
        hoverBorder: "hover:border-red-500 hover:ring-2 hover:ring-red-500/30" 
    },
    { 
        id: "sanitization", 
        label: "Sanitization", 
        count: "22", 
        icon: Sparkles, 
        iconColor: "text-slate-600 dark:text-slate-400", 
        iconBg: "bg-slate-100 dark:bg-slate-800/40", 
        barColor: "bg-slate-500",
        hoverBorder: "hover:border-slate-500 hover:ring-2 hover:ring-slate-500/30" 
    },
];

// Chart data for the donut
// Chart Data Map
const chartDataMap: Record<string, { name: string; value: number; color: string }[]> = {
    "room-service": [
        { name: "Completed", value: 59.56, color: "#22c55e" },
        { name: "Pending", value: 40.44, color: "#ef4444" },
    ],
    "travel-desk": [
        { name: "Completed", value: 80.00, color: "#22c55e" },
        { name: "Pending", value: 20.00, color: "#ef4444" },
    ],
    "business-center": [
        { name: "Pending", value: 100.00, color: "#ef4444" },
        { name: "Completed", value: 0.00, color: "#22c55e" },
    ],
    "food-order": [
        { name: "Pending", value: 50.50, color: "#ef4444" },
        { name: "Completed", value: 49.50, color: "#22c55e" },
    ],
    "facility-services": [
        { name: "Pending", value: 97.31, color: "#ef4444" },
        { name: "Completed", value: 2.69, color: "#22c55e" },
    ],
    "health-fitness": [
        { name: "Pending", value: 0, color: "#ef4444" },
        { name: "Completed", value: 0, color: "#22c55e" },
    ],
    "sanitization": [
        { name: "Sanitized", value: 98.15, color: "#22c55e" },
        { name: "Un-Sanitized", value: 1.85, color: "#ef4444" },
    ],
};

const totalServicesMap: Record<string, number> = {
    "room-service": 136,
    "travel-desk": 5,
    "business-center": 3,
    "food-order": 101,
    "facility-services": 107414,
    "health-fitness": 0,
    "sanitization": 572,
};

// Mock Data Definitions
const roomServiceData = [
    { id: 1, roomNo: "221", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "A-101 / Alice konyak", date: "05-12-2024", time: "17:43", description: "-", statusReason: "-", status: "Assigned" },
    { id: 2, roomNo: "221", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "PE0018 / Marudhu Pandian M", date: "03-12-2024", time: "10:51", description: "-", statusReason: "-", status: "Completed" },
    { id: 3, roomNo: "211", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "A-101 / Alice konyak", date: "25-11-2024", time: "10:35", description: "-", statusReason: "-", status: "Completed" },
    { id: 4, roomNo: "211", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "- / -", date: "21-11-2024", time: "12:43", description: "-", statusReason: "-", status: "Completed" },
    { id: 5, roomNo: "211", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "- / -", date: "21-11-2024", time: "12:41", description: "-", statusReason: "-", status: "Completed" },
    { id: 6, roomNo: "211", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "- / -", date: "21-11-2024", time: "12:39", description: "-", statusReason: "-", status: "Completed" },
    { id: 7, roomNo: "221", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "A-101 / Alice konyak", date: "15-11-2024", time: "17:15", description: "-", statusReason: "-", status: "Completed" },
    { id: 8, roomNo: "221", serviceType: "Room Service", request: "Bath Amenities", item: "Items", assignedTo: "A-101 / Alice konyak", date: "11-11-2024", time: "12:09", description: "-", statusReason: "-", status: "Completed" },
    { id: 9, roomNo: "221", serviceType: "Room Service", request: "Bath Amenities", item: "Items", assignedTo: "A-101 / Alice konyak", date: "09-11-2024", time: "13:22", description: "-", statusReason: "-", status: "Completed" },
    { id: 10, roomNo: "201", serviceType: "Room Service", request: "Room Amenities", item: "Items", assignedTo: "- / -", date: "08-11-2024", time: "15:59", description: "-", statusReason: "-", status: "Pending" },
];

const travelDeskData = [
    { id: 1, roomNo: "414", serviceType: "Travel Desk", request: "Car rental service", assignedTo: "12 / N.B. Rajesh Kanna", date: "01-07-2024", time: "12:35", description: "-", statusReason: "-", status: "Assigned" },
    { id: 2, roomNo: "108", serviceType: "Travel Desk", request: "Transfer and chauffeur driven limousine services", assignedTo: "PE0010 / Queen Evangelin S", date: "11-05-2023", time: "12:12", description: "-", statusReason: "-", status: "Completed" },
    { id: 3, roomNo: "108", serviceType: "Travel Desk", request: "Car rental service", assignedTo: "PE0010 / Queen Evangelin S", date: "11-05-2023", time: "11:14", description: "test", statusReason: "-", status: "Completed" },
    { id: 4, roomNo: "108", serviceType: "Travel Desk", request: "Car rental service", assignedTo: "PE0010 / Queen Evangelin S", date: "26-04-2023", time: "17:30", description: "test", statusReason: "test", status: "Completed" },
    { id: 5, roomNo: "2001", serviceType: "Travel Desk", request: "Ticket Bookings - Air, Train, Bus", assignedTo: "000001 / System User", date: "10-12-2022", time: "18:15", description: "test", statusReason: "-", status: "Completed" },
];

const businessCenterData = [
    { id: 1, roomNo: "501", serviceType: "Business Center", request: "Conference and meeting facilities", assignedTo: "Place14 / Manoj A", date: "19-07-2023", time: "22:22", description: "cweyh", statusReason: "-", status: "Partially Completed" },
    { id: 2, roomNo: "108", serviceType: "Business Center", request: "Computer desk facility", assignedTo: "PE0010 / Queen Evangelin S", date: "11-05-2023", time: "12:00", description: "-", statusReason: "-", status: "Assigned" },
    { id: 3, roomNo: "108", serviceType: "Business Center", request: "Meeting rooms", assignedTo: "CXP001 / Pradhiksha A", date: "09-05-2023", time: "17:37", description: "-", statusReason: "-", status: "Assigned" },
];

const foodOrderData = [
    { id: 1, roomNo: "211", menu: "Food Order", assignedTo: "- / -", date: "21-11-2024", time: "12:42", description: "-", statusReason: "-", status: "Pending" },
    { id: 2, roomNo: "211", menu: "Food Order", assignedTo: "- / -", date: "21-11-2024", time: "12:38", description: "-", statusReason: "-", status: "Pending" },
    { id: 3, roomNo: "211", menu: "Food Order", assignedTo: "- / -", date: "21-11-2024", time: "12:38", description: "-", statusReason: "-", status: "Pending" },
    { id: 4, roomNo: "201", menu: "Food Order", assignedTo: "- / -", date: "08-11-2024", time: "16:00", description: "-", statusReason: "I want it tomorrow", status: "Cancelled" },
    { id: 5, roomNo: "201", menu: "Food Order", assignedTo: "PE-04 / Radha Krishnan", date: "16-10-2024", time: "14:51", description: "-", statusReason: "-", status: "Completed" },
    { id: 6, roomNo: "201", menu: "Food Order", assignedTo: "PE-04 / Radha Krishnan", date: "14-10-2024", time: "14:47", description: "-", statusReason: "-", status: "Completed" },
    { id: 7, roomNo: "201", menu: "Food Order", assignedTo: "- / -", date: "14-10-2024", time: "13:20", description: "-", statusReason: "-", status: "Completed" },
    { id: 8, roomNo: "412", menu: "Food Order", assignedTo: "12 / N.B. Rajesh Kanna", date: "27-09-2024", time: "16:51", description: "test", statusReason: "test", status: "Completed" },
    { id: 9, roomNo: "412", menu: "Food Order", assignedTo: "- / -", date: "26-09-2024", time: "16:44", description: "test test", statusReason: "-", status: "Pending" },
    { id: 10, roomNo: "201", menu: "Food Order", assignedTo: "PE00015 / Brindha G", date: "26-04-2024", time: "11:22", description: "-", statusReason: "-", status: "Assigned" },
];

const facilityServicesData = [
    { id: 1, management: "Scheduled", category: "Room Cleaning", type: "Housekeeping", dept: "Maintenance", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "11:05", end: "11:20", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 2, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Room service", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "15:41", end: "19:01", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 3, management: "Scheduled", category: "Room Cleaning", type: "Housekeeping", dept: "Housekeeping", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "16:53", end: "17:01", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 4, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Maintenance", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "12:14", end: "12:15", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 5, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Maintenance", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "13:01", end: "13:02", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 6, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Maintenance", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "13:17", end: "13:18", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 7, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Maintenance", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "14:28", end: "14:29", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 8, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Room service", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "14:48", end: "18:03", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 9, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Housekeeping", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "15:18", end: "16:01", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
    { id: 10, management: "Scheduled", category: "Room Cleaning", type: "Cleaning", dept: "Maintenance", assignedTo: "View staff", from: "27-01-2026", to: "27-01-2026", start: "03:18", end: "19:19", roomNo: "View rooms", maintenance: "No", status: "Assigned" },
];

const sanitizationData = [
    { id: 1, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "05-12-2024", to: "05-12-2024", start: "14:42", end: "19:00", roomNo: "View rooms", status: "Completed" },
    { id: 2, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "02-12-2024", to: "02-12-2024", start: "12:33", end: "14:20", roomNo: "View rooms", status: "Completed" },
    { id: 3, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "27-11-2024", to: "27-11-2024", start: "12:47", end: "19:00", roomNo: "View rooms", status: "Completed" },
    { id: 4, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "26-11-2024", to: "26-11-2024", start: "11:44", end: "14:30", roomNo: "View rooms", status: "Completed" },
    { id: 5, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "15-11-2024", to: "15-11-2024", start: "17:00", end: "19:00", roomNo: "View rooms", status: "Completed" },
    { id: 6, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "12-11-2024", to: "12-11-2024", start: "12:45", end: "12:48", roomNo: "View rooms", status: "Completed" },
    { id: 7, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "08-11-2024", to: "08-11-2024", start: "15:42", end: "17:00", roomNo: "View rooms", status: "Completed" },
    { id: 8, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "30-10-2024", to: "30-10-2024", start: "11:50", end: "12:00", roomNo: "View rooms", status: "Completed" },
    { id: 9, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "29-10-2024", to: "29-10-2024", start: "17:25", end: "17:55", roomNo: "View rooms", status: "Completed" },
    { id: 10, management: "Disinfection", category: "Sanitation", type: "Guest Room sanitation", dept: "Housekeeping", assignedTo: "View staff", from: "28-10-2024", to: "28-10-2024", start: "11:05", end: "11:10", roomNo: "View rooms", status: "Completed" },
];

const ServiceTracking = () => {
    const [activeService, setActiveService] = useState("room-service");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [statusModalConfig, setStatusModalConfig] = useState<{ isOpen: boolean; type: "yellow" | "red" | "blue" | null }>({ isOpen: false, type: null });
    const [itemsModalConfig, setItemsModalConfig] = useState<{ isOpen: boolean; roomNo: string }>({ isOpen: false, roomNo: "" });

    const [activeChartIndex, setActiveChartIndex] = useState<number | undefined>(undefined);

    const currentChartData = chartDataMap[activeService] || chartDataMap["room-service"];
    const totalServices = totalServicesMap[activeService] || 136;

    const renderActiveShape = (props: { cx?: number; cy?: number; innerRadius?: number; outerRadius?: number; startAngle?: number; endAngle?: number; fill?: string }) => {
        const { cx = 0, cy = 0, innerRadius = 0, outerRadius = 0, startAngle = 0, endAngle = 0, fill = "#3eb1c8" } = props;
        return (
            <g>
                <Sector
                    cx={cx}
                    cy={cy}
                    innerRadius={innerRadius - 2}
                    outerRadius={outerRadius + 6}
                    startAngle={startAngle}
                    endAngle={endAngle}
                    fill={fill}
                    style={{
                        filter: `drop-shadow(0 0 10px ${fill}80)`,
                        transition: "all 0.3s ease-out",
                    }}
                />
            </g>
        );
    };

    const getStatusBadge = (status: string) => {
        let colorClass = "bg-gray-500/20 text-gray-400";
        if (status === "Assigned") colorClass = "bg-cyan-500/20 text-cyan-400";
        else if (status === "Completed") colorClass = "bg-emerald-500/20 text-emerald-500";
        else if (status === "Pending") colorClass = "bg-amber-500/20 text-amber-500";
        else if (status === "Cancelled") colorClass = "bg-red-500/20 text-red-500";
        else if (status === "Partially Completed") colorClass = "bg-blue-500/20 text-blue-500";

        return (
            <Badge className={`${colorClass} hover:${colorClass} font-medium border-0`}>
                {status}
            </Badge>
        );
    };

    const renderAction = (status: string) => {
        let bgColor = "bg-[#808080] hover:bg-[#666666]"; // Default for Completed etc
        let modalType: "yellow" | "red" | "blue" | null = null;
        if (status === "Assigned") { bgColor = "bg-[#e5a910] hover:bg-[#cc960e]"; modalType = "yellow"; }
        else if (status === "Pending" || status === "Cancelled") { bgColor = "bg-[#ed5565] hover:bg-[#da4453]"; modalType = "red"; }
        else if (status === "Partially Completed") { bgColor = "bg-[#3eb1c8] hover:bg-[#2e93a8]"; modalType = "blue"; }

        return (
            <div className="flex justify-center gap-2">
                <Button
                    size="icon"
                    className={`h-7 w-7 ${bgColor} text-white rounded-sm`}
                    onClick={() => {
                        if (modalType) {
                            setStatusModalConfig({ isOpen: true, type: modalType });
                        }
                    }}
                >
                    <Settings className="h-4 w-4" />
                </Button>
            </div>
        );
    };

    const filterData = <T extends Record<string, unknown>>(data: T[]) => {
        if (!searchQuery.trim()) return data;
        const query = searchQuery.toLowerCase().trim();
        return data.filter((item) =>
            Object.values(item).some((val) =>
                val !== null && val !== undefined && String(val).toLowerCase().includes(query)
            )
        );
    };

    const getActiveData = () => {
        switch (activeService) {
            case "room-service": return roomServiceData;
            case "travel-desk": return travelDeskData;
            case "business-center": return businessCenterData;
            case "food-order": return foodOrderData;
            case "facility-services": return facilityServicesData;
            case "sanitization": return sanitizationData;
            default: return [];
        }
    };

    const filteredData = filterData(getActiveData());
    const totalEntries = filteredData.length;
    const pageSize = parseInt(entriesPerPage) || 10;
    const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalEntries);
    const paginatedData = filteredData.slice(startIndex, endIndex);

    const renderTable = () => {
        switch (activeService) {
            case "room-service": {
                return (
                    <Table>
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
                            {paginatedData.length > 0 ? (
                                (paginatedData as typeof roomServiceData).map((row) => (
                                    <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                        <TableCell className="font-medium text-foreground text-xs py-3 px-4">{row.roomNo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.serviceType}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.request}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            <Badge
                                                variant="outline"
                                                className="text-amber-600 border-amber-600 bg-amber-50 dark:bg-amber-950/40 dark:text-amber-400 hover:bg-amber-100 cursor-pointer transition-colors"
                                                onClick={() => setItemsModalConfig({ isOpen: true, roomNo: row.roomNo })}
                                            >
                                                {row.item}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.assignedTo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.date}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.time}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.description}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.statusReason}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">{getStatusBadge(row.status)}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            {renderAction(row.status)}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={11} className="text-center py-6 text-muted-foreground text-xs">
                                        No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                );
            }
            case "travel-desk": {
                return (
                    <Table>
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
                            {paginatedData.length > 0 ? (
                                (paginatedData as typeof travelDeskData).map((row) => (
                                    <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                        <TableCell className="font-medium text-foreground text-xs py-3 px-4">{row.roomNo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.serviceType}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.request}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.assignedTo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.date}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.time}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.description}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.statusReason}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">{getStatusBadge(row.status)}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            {renderAction(row.status)}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={10} className="text-center py-6 text-muted-foreground text-xs">
                                        No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                );
            }
            case "business-center": {
                return (
                    <Table>
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
                            {paginatedData.length > 0 ? (
                                (paginatedData as typeof businessCenterData).map((row) => (
                                    <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                        <TableCell className="font-medium text-foreground text-xs py-3 px-4">{row.roomNo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.serviceType}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.request}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.assignedTo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.date}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.time}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.description}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.statusReason}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">{getStatusBadge(row.status)}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            {renderAction(row.status)}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={10} className="text-center py-6 text-muted-foreground text-xs">
                                        No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                );
            }
            case "food-order": {
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
                            {paginatedData.length > 0 ? (
                                (paginatedData as typeof foodOrderData).map((row) => (
                                    <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                        <TableCell className="font-medium text-foreground text-xs py-3 px-4">{row.roomNo}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            <Badge
                                                variant="outline"
                                                className="text-amber-600 border-amber-600 bg-amber-50 dark:bg-amber-950/40 dark:text-amber-400 hover:bg-amber-100 cursor-pointer transition-colors"
                                                onClick={() => setItemsModalConfig({ isOpen: true, roomNo: row.roomNo })}
                                            >
                                                {row.menu}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.assignedTo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.date}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.time}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.description}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">{getStatusBadge(row.status)}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs py-3 px-4">{row.statusReason}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            {renderAction(row.status)}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={9} className="text-center py-6 text-muted-foreground text-xs">
                                        No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                );
            }
            case "facility-services": {
                return (
                    <Table>
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
                            {paginatedData.length > 0 ? (
                                (paginatedData as typeof facilityServicesData).map((row) => (
                                    <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.management}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.category}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.type}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.dept}</TableCell>
                                        <TableCell className="text-blue-600 dark:text-blue-400 cursor-pointer hover:underline text-xs py-3 px-4">{row.assignedTo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.from}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.to}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.start}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.end}</TableCell>
                                        <TableCell className="text-blue-600 dark:text-blue-400 cursor-pointer hover:underline text-xs py-3 px-4">{row.roomNo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.maintenance}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">{getStatusBadge(row.status)}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            {renderAction(row.status)}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={13} className="text-center py-6 text-muted-foreground text-xs">
                                        No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                );
            }
            case "sanitization": {
                return (
                    <Table>
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
                            {paginatedData.length > 0 ? (
                                (paginatedData as typeof sanitizationData).map((row) => (
                                    <TableRow key={row.id} className="border-b border-border/50 dark:border-slate-800/70 bg-card dark:bg-[#101526]/80 hover:bg-muted/30 dark:hover:bg-slate-800/50 transition-colors">
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.management}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.category}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.type}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.dept}</TableCell>
                                        <TableCell className="text-blue-600 dark:text-blue-400 cursor-pointer hover:underline text-xs py-3 px-4">{row.assignedTo}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.from}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.to}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.start}</TableCell>
                                        <TableCell className="text-xs text-foreground/90 py-3 px-4">{row.end}</TableCell>
                                        <TableCell className="text-blue-600 dark:text-blue-400 cursor-pointer hover:underline text-xs py-3 px-4">{row.roomNo}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">{getStatusBadge(row.status)}</TableCell>
                                        <TableCell className="text-xs py-3 px-4">
                                            {renderAction(row.status)}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={12} className="text-center py-6 text-muted-foreground text-xs">
                                        No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                );
            }
            default:
                return (
                    <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
                        <div className="bg-muted p-4 rounded-full mb-4">
                            <Eye className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-medium text-foreground mb-1">No Data Available</h3>
                        <p className="text-sm">Details for {serviceTypes.find(s => s.id === activeService)?.label} will be available soon.</p>
                    </div>
                );
        }
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Services Tracking</h1>
            </div>

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
                                    setCurrentPage(1);
                                }}
                                className={`relative bg-background dark:bg-[#111628] rounded-xl border border-border/80 dark:border-slate-800 shadow-sm overflow-hidden px-4 pt-4 pb-3 transition-all duration-200 cursor-pointer text-left flex flex-col gap-2 ${card.hoverBorder} ${card.id === activeService ? "ring-2 ring-primary shadow-md border-primary/50" : ""}`}
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
                    <div className="relative w-64 h-64 flex items-center justify-center">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={currentChartData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={56}
                                    outerRadius={98}
                                    startAngle={90}
                                    endAngle={-270}
                                    paddingAngle={0}
                                    dataKey="value"
                                    stroke="hsl(var(--card))"
                                    strokeWidth={2}
                                    activeIndex={activeChartIndex}
                                    activeShape={renderActiveShape}
                                    onMouseEnter={(_, index) => setActiveChartIndex(index)}
                                    onMouseLeave={() => setActiveChartIndex(undefined)}
                                    className="cursor-pointer"
                                >
                                    {currentChartData.map((entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={entry.color}
                                            className="transition-all duration-300 cursor-pointer"
                                            opacity={activeChartIndex === undefined || activeChartIndex === index ? 1 : 0.6}
                                        />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value: unknown) => [`${value}%`, 'Percentage']}
                                    contentStyle={{
                                        backgroundColor: "hsl(var(--card))",
                                        border: "1px solid hsl(var(--border))",
                                        borderRadius: "10px",
                                        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.2)",
                                        fontSize: "12px",
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Center Metric Display (dynamic on hover) */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center transition-all duration-200">
                            {activeChartIndex !== undefined && currentChartData[activeChartIndex] ? (
                                <>
                                    <span className="text-3xl font-bold tracking-tight text-foreground transition-all">
                                        {currentChartData[activeChartIndex].value}%
                                    </span>
                                    <span className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mt-0.5">
                                        {currentChartData[activeChartIndex].name}
                                    </span>
                                </>
                            ) : (
                                <>
                                    <span className="text-3xl font-bold tracking-tight text-foreground transition-all">
                                        {totalServices.toLocaleString()}
                                    </span>
                                    <span className="text-sm text-muted-foreground font-normal mt-0.5">
                                        services
                                    </span>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Stats Legend Cards (interactive hover synced with chart) */}
                    <div className="flex flex-wrap items-center justify-center gap-4 mt-5 w-full">
                        {currentChartData.map((data, index) => {
                            const isGreen = data.name.toLowerCase().includes("complete") || data.name.toLowerCase().includes("sanitized");
                            const isHovered = activeChartIndex === index;
                            return (
                                <div
                                    key={index}
                                    onMouseEnter={() => setActiveChartIndex(index)}
                                    onMouseLeave={() => setActiveChartIndex(undefined)}
                                    className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border cursor-pointer transition-all duration-200 ${
                                        isHovered
                                            ? "scale-105 shadow-md ring-2 ring-primary/40 brightness-105"
                                            : "hover:scale-102 hover:shadow-sm"
                                    } ${
                                        isGreen
                                            ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-500/30 dark:text-emerald-300"
                                            : "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:border-rose-500/30 dark:text-rose-300"
                                    }`}
                                >
                                    <div
                                        className={`w-2.5 h-2.5 rounded-full shrink-0 transition-transform duration-200 ${
                                            isHovered ? "scale-125 shadow-sm" : ""
                                        }`}
                                        style={{ backgroundColor: data.color }}
                                    />
                                    <div className="flex flex-col text-left">
                                        <span className="text-xs font-semibold text-foreground/90">{data.name}</span>
                                        <span className="text-sm font-bold">{data.value}%</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Table Container Card */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
                <CardContent className="p-5">
                    {/* Controls */}
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
                                    <SelectItem value="100">100</SelectItem>
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-xs font-medium">entries</span>
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

                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800">
                        {renderTable()}
                    </div>

                    {/* Pagination */}
                    <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
                        <span className="text-muted-foreground text-xs">
                            Showing {totalEntries > 0 ? startIndex + 1 : 0} to {endIndex} of {totalEntries} entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                <Button
                                    key={page}
                                    variant={currentPage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                                    onClick={() => setCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

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
