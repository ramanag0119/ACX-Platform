import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Search, ChevronLeft, ChevronRight, Eye, Edit, Check, X, ChevronDown, ChevronUp } from "lucide-react";

type TabType = "scheduled" | "maintenance" | "disinfection";

// Scheduled Services Data
const scheduledServicesData = [
    {
        id: "1",
        facilityServices: "Room Cleaning",
        serviceType: "Housekeeping",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "27-12-2024",
        startTime: "14:00",
        endTime: "18:00",
        roomNo: "View rooms",
    },
    {
        id: "2",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "08-12-2024",
        startTime: "14:00",
        endTime: "19:00",
        roomNo: "View rooms",
    },
    {
        id: "3",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "02-12-2024",
        startTime: "12:00",
        endTime: "14:04",
        roomNo: "View rooms",
    },
    {
        id: "4",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "27-11-2024",
        startTime: "12:48",
        endTime: "19:00",
        roomNo: "View rooms",
    },
    {
        id: "5",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "08-11-2024",
        startTime: "17:30",
        endTime: "14:00",
        roomNo: "View rooms",
    },
    {
        id: "6",
        facilityServices: "Room Cleaning",
        serviceType: "Housekeeping",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "16-11-2024",
        startTime: "14:16",
        endTime: "19:00",
        roomNo: "View rooms",
    },
    {
        id: "7",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "08-11-2024",
        startTime: "18:16",
        endTime: "17:00",
        roomNo: "View rooms",
    },
    {
        id: "8",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "08-11-2024",
        startTime: "11:48",
        endTime: "12:00",
        roomNo: "View rooms",
    },
    {
        id: "9",
        facilityServices: "Room Cleaning",
        serviceType: "Housekeeping",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "29-10-2024",
        startTime: "17:00",
        endTime: "17:04",
        roomNo: "View rooms",
    },
    {
        id: "10",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "29-10-2024",
        startTime: "14:10",
        endTime: "16:00",
        roomNo: "View rooms",
    },
];

// Plan Maintenance Data
const planMaintenanceData = [
    {
        id: "1",
        facilityServices: "Caleido Network Maintenance",
        serviceType: "Networking Maintenance",
        department: "Housekeeping",
        assignTo: "View staff",
        fromDate: "26-03-2025",
        toDate: "26-03-2025",
        startTime: "10:00",
        endTime: "19:00",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
    {
        id: "2",
        facilityServices: "Caleido Network Maintenance",
        serviceType: "Networking Maintenance",
        department: "Housekeeping",
        assignTo: "View staff",
        fromDate: "27-03-2025",
        toDate: "27-07-2025",
        startTime: "13:00",
        endTime: "13:00",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
    {
        id: "3",
        facilityServices: "Caleido Network Maintenance",
        serviceType: "Networking Maintenance",
        department: "NONE",
        assignTo: "View staff",
        fromDate: "16-09-2026",
        toDate: "16-09-2026",
        startTime: "13:04",
        endTime: "42:00",
        roomNo: "View rooms",
        underMaintenance: "No",
    },
    {
        id: "4",
        facilityServices: "Plumbing",
        serviceType: "water works",
        department: "floor house keeper",
        assignTo: "View staff",
        fromDate: "16-09-2026",
        toDate: "16-09-2026",
        startTime: "12:41",
        endTime: "12:42",
        roomNo: "View rooms",
        underMaintenance: "No",
    },
    {
        id: "5",
        facilityServices: "Electrical",
        serviceType: "Installing",
        department: "Room service",
        assignTo: "View staff",
        fromDate: "16-09-2025",
        toDate: "16-09-2025",
        startTime: "14:16",
        endTime: "14:20",
        roomNo: "View rooms",
        underMaintenance: "No",
    },
    {
        id: "6",
        facilityServices: "Caleido Network Maintenance",
        serviceType: "Networking Maintenance",
        department: "Maintenance",
        assignTo: "View staff",
        fromDate: "29-01-2025",
        toDate: "29-01-2025",
        startTime: "13:00",
        endTime: "17:00",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
    {
        id: "7",
        facilityServices: "Electrical",
        serviceType: "Installing",
        department: "Maintenance",
        assignTo: "View staff",
        fromDate: "18-12-2024",
        toDate: "06-12-2024",
        startTime: "12:14",
        endTime: "16:00",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
    {
        id: "8",
        facilityServices: "Room Cleaning",
        serviceType: "Cleaning",
        department: "Housekeeping",
        assignTo: "View staff",
        fromDate: "27-11-2024",
        toDate: "21-11-2024",
        startTime: "11:00",
        endTime: "13:00",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
    {
        id: "9",
        facilityServices: "Electrical",
        serviceType: "Installing",
        department: "Maintenance",
        assignTo: "View staff",
        fromDate: "21-11-2024",
        toDate: "21-11-2024",
        startTime: "13:19",
        endTime: "18:00",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
    {
        id: "10",
        facilityServices: "Electrical",
        serviceType: "Installing",
        department: "Maintenance",
        assignTo: "View staff",
        fromDate: "21-11-2024",
        toDate: "21-11-2024",
        startTime: "13:11",
        endTime: "16:10",
        roomNo: "View rooms",
        underMaintenance: "Yes",
    },
];

// Disinfection Schedule Data
const disinfectionScheduleData = [
    {
        id: "1",
        sanitizerServices: "UVHVDUI",
        serviceType: "Level Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "27-12-2025",
        startTime: "16:01",
        endTime: "17:05",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "2",
        sanitizerServices: "Sanitation",
        serviceType: "Guest Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "27-12-2025",
        startTime: "16:05",
        endTime: "17:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "3",
        sanitizerServices: "Sanitation",
        serviceType: "Guest Room sanitizer",
        department: "Admin",
        assignTo: "View staff",
        date: "27-12-2025",
        startTime: "11:01",
        endTime: "05:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "4",
        sanitizerServices: "UVHVDUI",
        serviceType: "Level Room sanitizer",
        department: "BOSS-BOSS",
        assignTo: "View staff",
        date: "27-12-2025",
        startTime: "06:00",
        endTime: "24:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "5",
        sanitizerServices: "UVHVDUI",
        serviceType: "Level Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "27-12-2024",
        startTime: "02:17",
        endTime: "09:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "6",
        sanitizerServices: "Sanitation",
        serviceType: "Guest Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "08-12-2024",
        startTime: "14:42",
        endTime: "14:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "7",
        sanitizerServices: "Sanitation",
        serviceType: "Guest Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "02-12-2024",
        startTime: "12:51",
        endTime: "14:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "8",
        sanitizerServices: "UVHVDUI",
        serviceType: "Level Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "27-11-2024",
        startTime: "12:41",
        endTime: "14:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "9",
        sanitizerServices: "UVHVDUI",
        serviceType: "Level Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "26-11-2024",
        startTime: "11:44",
        endTime: "14:00",
        roomNo: "9 Rooms (All)",
    },
    {
        id: "10",
        sanitizerServices: "Sanitation",
        serviceType: "Guest Room sanitizer",
        department: "Housekeeping",
        assignTo: "View staff",
        date: "16-11-2024",
        startTime: "17:01",
        endTime: "14:00",
        roomNo: "9 Rooms (All)",
    },
];

const ServicePlanning = () => {
    const [activeTab, setActiveTab] = useState<TabType>("scheduled");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [editModalOpen, setEditModalOpen] = useState(false);

    // Form states for Scheduled Services
    const [scheduledForm, setScheduledForm] = useState({
        facilityServices: "",
        serviceType: "",
        department: "",
        assignTo: "",
        startTime: "",
        endTime: "",
        rooms: "rooms",
        roomNo: "",
        frequency: [] as string[],
        repeatWeekly: false,
    });

    // Form states for Plan Maintenance
    const [maintenanceForm, setMaintenanceForm] = useState({
        facilityServices: "",
        serviceType: "",
        department: "",
        assignTo: "",
        fromDate: "",
        toDate: "",
        startTime: "",
        endTime: "",
        rooms: "rooms",
        roomNo: "",
        underMaintenance: false,
    });

    // Form states for Disinfection
    const [disinfectionForm, setDisinfectionForm] = useState({
        sanitizerServices: "",
        serviceType: "",
        department: "",
        assignTo: "",
        startTime: "",
        endTime: "",
        rooms: "rooms",
        roomNo: "",
        frequency: [] as string[],
        repeatWeekly: false,
    });

    const tabs = [
        { id: "scheduled" as TabType, label: "Scheduled Services" },
        { id: "maintenance" as TabType, label: "Plan Maintenance" },
        { id: "disinfection" as TabType, label: "Disinfection Schedule" },
    ];

    const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    const handleSubmit = () => {
        console.log("Submitting form for tab:", activeTab);
    };

    const handleReset = () => {
        if (activeTab === "scheduled") {
            setScheduledForm({
                facilityServices: "",
                serviceType: "",
                department: "",
                assignTo: "",
                startTime: "",
                endTime: "",
                rooms: "rooms",
                roomNo: "",
                frequency: [],
                repeatWeekly: false,
            });
        } else if (activeTab === "maintenance") {
            setMaintenanceForm({
                facilityServices: "",
                serviceType: "",
                department: "",
                assignTo: "",
                fromDate: "",
                toDate: "",
                startTime: "",
                endTime: "",
                rooms: "rooms",
                roomNo: "",
                underMaintenance: false,
            });
        } else {
            setDisinfectionForm({
                sanitizerServices: "",
                serviceType: "",
                department: "",
                assignTo: "",
                startTime: "",
                endTime: "",
                rooms: "rooms",
                roomNo: "",
                frequency: [],
                repeatWeekly: false,
            });
        }
    };

    const toggleFrequency = (day: string, formType: "scheduled" | "disinfection") => {
        if (formType === "scheduled") {
            setScheduledForm((prev) => ({
                ...prev,
                frequency: prev.frequency.includes(day)
                    ? prev.frequency.filter((d) => d !== day)
                    : [...prev.frequency, day],
            }));
        } else {
            setDisinfectionForm((prev) => ({
                ...prev,
                frequency: prev.frequency.includes(day)
                    ? prev.frequency.filter((d) => d !== day)
                    : [...prev.frequency, day],
            }));
        }
    };

    const renderScheduledServicesForm = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Facility Services <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={scheduledForm.facilityServices}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, facilityServices: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Facility Services" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="room-cleaning">Room Cleaning</SelectItem>
                            <SelectItem value="laundry">Laundry</SelectItem>
                            <SelectItem value="maintenance">Maintenance</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Services Type <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={scheduledForm.serviceType}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, serviceType: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Service Type" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="housekeeping">Housekeeping</SelectItem>
                            <SelectItem value="cleaning">Cleaning</SelectItem>
                            <SelectItem value="maintenance">Maintenance</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Department</Label>
                    <Select
                        value={scheduledForm.department}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, department: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Department" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="housekeeping">Housekeeping</SelectItem>
                            <SelectItem value="maintenance">Maintenance</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Assign To</Label>
                    <Select
                        value={scheduledForm.assignTo}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, assignTo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Employee" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="emp1">Employee 1</SelectItem>
                            <SelectItem value="emp2">Employee 2</SelectItem>
                            <SelectItem value="emp3">Employee 3</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Start Time <span className="text-red-500">*</span>
                    </Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={23}
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={59}
                        />
                        <Button variant="outline" size="sm" className="bg-[#5865F2] hover:bg-[#4752c4] text-white border-0 font-medium rounded-xl h-10 px-3.5 shadow-sm">
                            AM
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">End Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={23}
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={59}
                        />
                        <Button variant="outline" size="sm" className="bg-[#5865F2] hover:bg-[#4752c4] text-white border-0 font-medium rounded-xl h-10 px-3.5 shadow-sm">
                            AM
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Rooms</Label>
                    <RadioGroup
                        value={scheduledForm.rooms}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, rooms: v })}
                        className="flex gap-4"
                    >
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="rooms" id="rooms" />
                            <Label htmlFor="rooms" className="cursor-pointer">Rooms</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="non-rooms" id="non-rooms" />
                            <Label htmlFor="non-rooms" className="cursor-pointer">Non-Rooms</Label>
                        </div>
                    </RadioGroup>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Room No</Label>
                    <Select
                        value={scheduledForm.roomNo}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, roomNo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Room" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="101">Room 101</SelectItem>
                            <SelectItem value="102">Room 102</SelectItem>
                            <SelectItem value="201">Room 201</SelectItem>
                            <SelectItem value="202">Room 202</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Frequency</Label>
                    <div className="flex flex-wrap gap-2">
                        {weekDays.map((day) => (
                            <Button
                                key={day}
                                variant={scheduledForm.frequency.includes(day) ? "default" : "outline"}
                                size="sm"
                                className={`w-12 rounded-xl transition-all ${scheduledForm.frequency.includes(day)
                                    ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-medium shadow-sm"
                                    : "bg-muted/30 border-border/50"
                                    }`}
                                onClick={() => toggleFrequency(day, "scheduled")}
                            >
                                {day}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium">Repeat Weekly</Label>
                    <Switch
                        checked={scheduledForm.repeatWeekly}
                        onCheckedChange={(v) => setScheduledForm({ ...scheduledForm, repeatWeekly: v })}
                    />
                </div>
            </div>
        </div>
    );

    const renderPlanMaintenanceForm = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Facility Services</Label>
                    <Select
                        value={maintenanceForm.facilityServices}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, facilityServices: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Facility Services" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="network">Caleido Network Maintenance</SelectItem>
                            <SelectItem value="electrical">Electrical</SelectItem>
                            <SelectItem value="plumbing">Plumbing</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Service Type <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={maintenanceForm.serviceType}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, serviceType: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Service Type" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="networking">Networking Maintenance</SelectItem>
                            <SelectItem value="installing">Installing</SelectItem>
                            <SelectItem value="water-works">Water Works</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Department <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={maintenanceForm.department}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, department: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Department" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="housekeeping">Housekeeping</SelectItem>
                            <SelectItem value="maintenance">Maintenance</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Assign To</Label>
                    <Select
                        value={maintenanceForm.assignTo}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, assignTo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Employee" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="emp1">Employee 1</SelectItem>
                            <SelectItem value="emp2">Employee 2</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        From Date <span className="text-red-500">*</span>
                    </Label>
                    <Input
                        type="date"
                        className="h-10 bg-muted/30 border-border/50"
                        value={maintenanceForm.fromDate}
                        onChange={(e) => setMaintenanceForm({ ...maintenanceForm, fromDate: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">To Date</Label>
                    <Input
                        type="date"
                        className="h-10 bg-muted/30 border-border/50"
                        value={maintenanceForm.toDate}
                        onChange={(e) => setMaintenanceForm({ ...maintenanceForm, toDate: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Start Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-[#5865F2] hover:bg-[#4752c4] text-white border-0 font-medium rounded-xl h-10 px-3.5 shadow-sm">
                            AM
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">End Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-[#5865F2] hover:bg-[#4752c4] text-white border-0 font-medium rounded-xl h-10 px-3.5 shadow-sm">
                            AM
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Rooms</Label>
                    <RadioGroup
                        value={maintenanceForm.rooms}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, rooms: v })}
                        className="flex gap-4"
                    >
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="rooms" id="maint-rooms" />
                            <Label htmlFor="maint-rooms" className="cursor-pointer">Rooms</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="non-rooms" id="maint-non-rooms" />
                            <Label htmlFor="maint-non-rooms" className="cursor-pointer">Non-Rooms</Label>
                        </div>
                    </RadioGroup>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Room No</Label>
                    <Select
                        value={maintenanceForm.roomNo}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, roomNo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Room" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="101">Room 101</SelectItem>
                            <SelectItem value="102">Room 102</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium">Under Maintenance</Label>
                    <Switch
                        checked={maintenanceForm.underMaintenance}
                        onCheckedChange={(v) => setMaintenanceForm({ ...maintenanceForm, underMaintenance: v })}
                    />
                </div>
            </div>
        </div>
    );

    const renderDisinfectionForm = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Sanitizer Services <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={disinfectionForm.sanitizerServices}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, sanitizerServices: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Sanitizer Services" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="uvhvdui">UVHVDUI</SelectItem>
                            <SelectItem value="sanitation">Sanitation</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Service Type <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={disinfectionForm.serviceType}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, serviceType: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Service Type" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="level-room">Level Room sanitizer</SelectItem>
                            <SelectItem value="guest-room">Guest Room sanitizer</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Department</Label>
                    <Select
                        value={disinfectionForm.department}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, department: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Department" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="housekeeping">Housekeeping</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Assign To</Label>
                    <Select
                        value={disinfectionForm.assignTo}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, assignTo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Employee" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="emp1">Employee 1</SelectItem>
                            <SelectItem value="emp2">Employee 2</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Start Time <span className="text-red-500">*</span>
                    </Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-[#5865F2] hover:bg-[#4752c4] text-white border-0 font-medium rounded-xl h-10 px-3.5 shadow-sm">
                            AM
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">End Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-[#5865F2] hover:bg-[#4752c4] text-white border-0 font-medium rounded-xl h-10 px-3.5 shadow-sm">
                            AM
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Rooms</Label>
                    <RadioGroup
                        value={disinfectionForm.rooms}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, rooms: v })}
                        className="flex gap-4"
                    >
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="rooms" id="dis-rooms" />
                            <Label htmlFor="dis-rooms" className="cursor-pointer">Rooms</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="non-rooms" id="dis-non-rooms" />
                            <Label htmlFor="dis-non-rooms" className="cursor-pointer">Non-Rooms</Label>
                        </div>
                    </RadioGroup>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Room No</Label>
                    <Select
                        value={disinfectionForm.roomNo}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, roomNo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Room" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            <SelectItem value="101">Room 101</SelectItem>
                            <SelectItem value="102">Room 102</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Frequency</Label>
                    <div className="flex flex-wrap gap-2">
                        {weekDays.map((day) => (
                            <Button
                                key={day}
                                variant={disinfectionForm.frequency.includes(day) ? "default" : "outline"}
                                size="sm"
                                className={`w-12 rounded-xl transition-all ${disinfectionForm.frequency.includes(day)
                                    ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-medium shadow-sm"
                                    : "bg-muted/30 border-border/50"
                                    }`}
                                onClick={() => toggleFrequency(day, "disinfection")}
                            >
                                {day}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium">Repeat Weekly</Label>
                    <Switch
                        checked={disinfectionForm.repeatWeekly}
                        onCheckedChange={(v) => setDisinfectionForm({ ...disinfectionForm, repeatWeekly: v })}
                    />
                </div>
            </div>
        </div>
    );

    const getActiveData = () => {
        if (activeTab === "scheduled") return scheduledServicesData;
        if (activeTab === "maintenance") return planMaintenanceData;
        return disinfectionScheduleData;
    };

    const filterData = <T extends Record<string, any>>(data: T[]) => {
        if (!searchQuery.trim()) return data;
        const query = searchQuery.toLowerCase().trim();
        return data.filter((item) =>
            Object.values(item).some((val) =>
                val !== null && val !== undefined && String(val).toLowerCase().includes(query)
            )
        );
    };

    const filteredData = filterData(getActiveData());
    const totalEntries = filteredData.length;
    const pageSize = parseInt(entriesPerPage) || 10;
    const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalEntries);
    const paginatedData = filteredData.slice(startIndex, endIndex);

    const renderTable = () => {
        let columns: { key: string; label: string }[] = [];

        if (activeTab === "scheduled") {
            columns = [
                { key: "facilityServices", label: "Facility Services" },
                { key: "serviceType", label: "Service Type" },
                { key: "department", label: "Department" },
                { key: "assignTo", label: "Assign To" },
                { key: "date", label: "Date" },
                { key: "startTime", label: "Start Time" },
                { key: "endTime", label: "End Time" },
                { key: "roomNo", label: "Room No" },
            ];
        } else if (activeTab === "maintenance") {
            columns = [
                { key: "facilityServices", label: "Facility Services" },
                { key: "serviceType", label: "Service Type" },
                { key: "department", label: "Department" },
                { key: "assignTo", label: "Assign To" },
                { key: "fromDate", label: "From Date" },
                { key: "toDate", label: "To Date" },
                { key: "startTime", label: "Start Time" },
                { key: "endTime", label: "End Time" },
                { key: "roomNo", label: "Room No" },
                { key: "underMaintenance", label: "Under Maintenance" },
            ];
        } else {
            columns = [
                { key: "sanitizerServices", label: "Sanitizer Services" },
                { key: "serviceType", label: "Service Type" },
                { key: "department", label: "Department" },
                { key: "assignTo", label: "Assign To" },
                { key: "date", label: "Date" },
                { key: "startTime", label: "Start Time" },
                { key: "endTime", label: "End Time" },
                { key: "roomNo", label: "Room No" },
            ];
        }

        return (
            <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                            {columns.map((col) => (
                                <TableHead key={col.key} className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">
                                    {col.label}
                                </TableHead>
                            ))}
                            <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {paginatedData.length > 0 ? (
                            paginatedData.map((row, index) => (
                                <TableRow
                                    key={row.id}
                                    className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}
                                >
                                    {columns.map((col) => (
                                        <TableCell key={col.key} className="text-xs text-foreground/90 py-3 px-4">
                                            {col.key === "assignTo" || col.key === "roomNo" ? (
                                                <span className="text-cyan-600 dark:text-cyan-400 cursor-pointer hover:underline">
                                                    {row[col.key]}
                                                </span>
                                            ) : col.key === "underMaintenance" ? (
                                                <Badge
                                                    className={
                                                        row[col.key] === "Yes"
                                                            ? "bg-green-500/20 text-green-600 dark:text-green-400"
                                                            : "bg-gray-500/20 text-muted-foreground"
                                                    }
                                                >
                                                    {row[col.key]}
                                                </Badge>
                                            ) : (
                                                row[col.key]
                                            )}
                                        </TableCell>
                                    ))}
                                    <TableCell className="py-3 px-4">
                                        <div className="flex items-center justify-center gap-2">
                                            <Button
                                                size="sm"
                                                className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-md"
                                                onClick={() => setEditModalOpen(true)}
                                            >
                                                <Edit className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={columns.length + 1} className="text-center py-6 text-muted-foreground text-xs">
                                    No records found {searchQuery ? `matching "${searchQuery}"` : ""}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        );
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Services Planning</h1>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 border-b border-border dark:border-slate-800">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => { setActiveTab(tab.id); setCurrentPage(1); }}
                        className={`relative px-1 pb-3 text-xs font-semibold uppercase tracking-wider transition-all duration-200 ${activeTab === tab.id
                            ? "text-foreground"
                            : "text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {tab.label}
                        {activeTab === tab.id && (
                            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-t-full" />
                        )}
                    </button>
                ))}
            </div>

            {/* Form Section */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                <CardContent className="p-6">
                    {activeTab === "scheduled" && renderScheduledServicesForm()}
                    {activeTab === "maintenance" && renderPlanMaintenanceForm()}
                    {activeTab === "disinfection" && renderDisinfectionForm()}

                    {/* Action Buttons */}
                    <div className="flex justify-center gap-4 pt-6 border-t border-border/30">
                        <Button
                            type="button"
                            onClick={handleReset}
                            variant="outline"
                            className="h-10 px-8 min-w-[120px] rounded-xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                        >
                            Reset
                        </Button>
                        <Button
                            type="button"
                            onClick={handleSubmit}
                            className="h-10 px-8 min-w-[120px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                        >
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Data Table Section */}
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
                                    placeholder="Facility services, Service type, Room No"
                                    value={searchQuery}
                                    onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                                    className="pl-9 w-64 md:w-80 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Table */}
                    {renderTable()}

                    {/* Footer */}
                    <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
                        <span className="text-muted-foreground text-xs">
                            Showing {totalEntries > 0 ? startIndex + 1 : 0} to {endIndex} of {totalEntries} entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(1)}
                                disabled={currentPage === 1}
                            >
                                First
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                disabled={currentPage === 1}
                            >
                                <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                                Previous
                            </Button>
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                <Button
                                    key={page}
                                    variant={currentPage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page
                                        ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    onClick={() => setCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                                disabled={currentPage === totalPages}
                            >
                                Next
                                <ChevronRight className="h-3.5 w-3.5 ml-1" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(totalPages)}
                                disabled={currentPage === totalPages}
                            >
                                Last
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Edit Service Planning Modal */}
            <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
                <DialogContent className="max-w-[650px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-none">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Service Planning</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditModalOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>

                    <div className="px-12 py-10 space-y-6">
                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Sanitation Services <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-gray-100 border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-3 py-2 text-sm appearance-none outline-none rounded-t-[2px]">
                                    <option>Sanitation</option>
                                </select>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Services Type <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                    <option>Guest Room sanitation</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Department <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                    <option>Admin</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Assign To <span className="text-red-500">*</span></Label>
                            <div className="relative bg-gray-500 border border-gray-500 rounded-[2px] p-[2px] pr-8 flex items-center gap-1 h-[34px]">
                                <div className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-[2px] flex items-center gap-1">
                                    System User <X className="h-3 w-3 cursor-pointer hover:opacity-80" />
                                </div>
                                <div className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-[2px] flex items-center gap-1">
                                    Namas s <X className="h-3 w-3 cursor-pointer hover:opacity-80" />
                                </div>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-300 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-start">
                            <Label className="text-sm font-medium text-gray-800 text-left pt-6">Start Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="11" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <span className="text-xl font-bold pb-6">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="00" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <div className="pb-6">
                                    <div className="bg-[#5865F2] hover:bg-[#4752c4] text-white rounded-xl px-4 py-1.5 text-sm font-semibold cursor-pointer shadow-sm transition-all">AM</div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-start">
                            <Label className="text-sm font-medium text-gray-800 text-left pt-6">End Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#5865F2] cursor-pointer" />
                                    <input type="text" value="12" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#5865F2] cursor-pointer" />
                                </div>
                                <span className="text-xl font-bold pb-6">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#5865F2] cursor-pointer" />
                                    <input type="text" value="00" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#5865F2] cursor-pointer" />
                                </div>
                                <div className="pb-6">
                                    <div className="bg-[#5865F2] hover:bg-[#4752c4] text-white rounded-xl px-4 py-1.5 text-sm font-semibold cursor-pointer shadow-sm transition-all">AM</div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Rooms <span className="text-red-500">*</span></Label>
                            <RadioGroup defaultValue="rooms" className="flex flex-col gap-2">
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="rooms" id="edit-rooms" className="text-[#3eb1c8] border-[#3eb1c8]" />
                                    <Label htmlFor="edit-rooms" className="cursor-pointer text-gray-900 font-normal">Rooms</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="non-rooms" id="edit-non-rooms" className="text-[#3eb1c8] border-gray-300" />
                                    <Label htmlFor="edit-non-rooms" className="cursor-pointer text-gray-900 font-normal">Non Rooms</Label>
                                </div>
                            </RadioGroup>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Room No <span className="text-red-500">*</span></Label>
                            <div className="relative border border-gray-500 rounded-[2px] p-[2px] pr-8 flex items-center gap-1 h-[34px]">
                                <div className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-[2px] flex items-center gap-1">
                                    211 <X className="h-3 w-3 cursor-pointer hover:opacity-80" />
                                </div>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Frequency <span className="text-red-500">*</span></Label>
                            <div className="flex bg-transparent border border-[#3eb1c8] rounded-[2px] w-fit overflow-hidden">
                                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day, idx) => (
                                    <div key={day} className={`px-3 py-1 text-xs font-medium cursor-pointer border-r border-[#3eb1c8] last:border-r-0 ${idx === 6 ? "bg-[#3eb1c8] text-white" : "text-gray-800 hover:bg-gray-100"}`}>
                                        {day}
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Repeat Weekly <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-2">
                                <Switch checked={true} className="data-[state=checked]:bg-[#4ad970]" />
                            </div>
                        </div>

                        <div className="flex justify-center gap-4 pt-6 border-t border-gray-200 dark:border-slate-800">
                            <Button
                                type="button"
                                variant="outline"
                                className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                                onClick={() => setEditModalOpen(false)}
                            >
                                Reset
                            </Button>
                            <Button
                                type="button"
                                className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                                onClick={() => setEditModalOpen(false)}
                            >
                                Submit
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default ServicePlanning;




