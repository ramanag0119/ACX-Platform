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
import { Search, ChevronLeft, ChevronRight, Eye, Edit, Share2, Pencil, Settings, X, ChevronDown } from "lucide-react";
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

// KPI Card data
const serviceTypes = [
    { id: "room-service", label: "Room Service", count: "55", color: "bg-slate-700 border border-white" },
    { id: "travel-desk", label: "Travel Desk", count: "1", color: "bg-amber-700" },
    { id: "business-center", label: "Business Center", count: "3", color: "bg-green-700" },
    { id: "food-order", label: "Food Order", count: "51", color: "bg-teal-800" },
    { id: "facility-services", label: "Facility Services", count: "104174", color: "bg-yellow-700" },
    { id: "health-fitness", label: "Health & Fitness", count: "0", color: "bg-red-900" },
    { id: "sanitization", label: "Sanitization", count: "22", color: "bg-red-800" },
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

    const currentChartData = chartDataMap[activeService] || chartDataMap["room-service"];
    const totalServices = totalServicesMap[activeService] || 136;

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

    const renderTable = () => {
        switch (activeService) {
            case "room-service":
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
                            {roomServiceData.map((row) => (
                                <TableRow key={row.id} className="border-b border-gray-200 bg-white hover:bg-muted/50">
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
                                        {renderAction(row.status)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "travel-desk":
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
                            {travelDeskData.map((row) => (
                                <TableRow key={row.id} className="border-b border-gray-200 bg-white hover:bg-muted/50">
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
                                        {renderAction(row.status)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "business-center":
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
                            {businessCenterData.map((row) => (
                                <TableRow key={row.id} className="border-b border-gray-200 bg-white hover:bg-muted/50">
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
                                        {renderAction(row.status)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "food-order":
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
                            {foodOrderData.map((row) => (
                                <TableRow key={row.id} className="border-b border-gray-200 bg-white hover:bg-muted/50">
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
                                        {renderAction(row.status)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "facility-services":
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
                            {facilityServicesData.map((row) => (
                                <TableRow key={row.id} className="border-b border-gray-200 bg-white hover:bg-muted/50">
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
                                        {renderAction(row.status)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
            case "sanitization":
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
                            {sanitizationData.map((row) => (
                                <TableRow key={row.id} className="border-b border-gray-200 bg-white hover:bg-muted/50">
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
                                        {renderAction(row.status)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                );
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
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
            </div>

            {/* KPI Cards Row */}
            <div className="grid grid-cols-2 lg:grid-cols-7 gap-4">
                {serviceTypes.map((card) => (
                    <button
                        key={card.id}
                        onClick={() => setActiveService(card.id)}
                        className={`${card.id === activeService ? "ring-2 ring-gray-900" : ""} ${card.color} border-0 text-white overflow-hidden rounded-sm px-4 py-3 hover:opacity-90 transition-all cursor-pointer text-left flex flex-col justify-center h-[90px]`}
                    >
                        <p className="text-3xl font-bold">{card.count}</p>
                        <p className="text-xs font-medium mt-1 truncate w-full">{card.label}</p>
                    </button>
                ))}
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
                        <SelectContent className="bg-white">
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
                {renderTable()}
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
