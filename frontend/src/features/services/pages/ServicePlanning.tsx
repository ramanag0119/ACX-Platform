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
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
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
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
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
                                className={`w-12 ${scheduledForm.frequency.includes(day)
                                    ? "bg-cyan-600 text-white"
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
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
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
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
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
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
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
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
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
                                className={`w-12 ${disinfectionForm.frequency.includes(day)
                                    ? "bg-cyan-600 text-white"
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

    const renderTable = () => {
        let data: any[] = [];
        let columns: { key: string; label: string }[] = [];

        if (activeTab === "scheduled") {
            data = scheduledServicesData;
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
            data = planMaintenanceData;
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
            data = disinfectionScheduleData;
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
            <div className="rounded-xl overflow-hidden border border-gray-200">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                            {columns.map((col) => (
                                <TableHead key={col.key} className="text-gray-600 font-medium">
                                    {col.label}
                                </TableHead>
                            ))}
                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.map((row, index) => (
                            <TableRow
                                key={row.id}
                                className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"
                                    } hover:bg-muted/40 transition-colors`}
                            >
                                {columns.map((col) => (
                                    <TableCell key={col.key}>
                                        {col.key === "assignTo" || col.key === "roomNo" ? (
                                            <span className="text-cyan-400 cursor-pointer hover:underline">
                                                {row[col.key]}
                                            </span>
                                        ) : col.key === "underMaintenance" ? (
                                            <Badge
                                                className={
                                                    row[col.key] === "Yes"
                                                        ? "bg-green-500/20 text-green-500"
                                                        : "bg-gray-500/20 text-gray-400"
                                                }
                                            >
                                                {row[col.key]}
                                            </Badge>
                                        ) : (
                                            row[col.key]
                                        )}
                                    </TableCell>
                                ))}
                                <TableCell>
                                    <div className="flex items-center justify-center gap-2">
                                        <Button
                                            size="sm"
                                            className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]"
                                            onClick={() => setEditModalOpen(true)}
                                        >
                                            <Edit className="h-[14px] w-[14px]" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        );
    };

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Services Planning</h1>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 border-b border-gray-200">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === tab.id
                            ? "text-foreground"
                            : "text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {tab.label}
                        {activeTab === tab.id && (
                            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-600 rounded-t-full" />
                        )}
                    </button>
                ))}
            </div>

            {/* Form Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {activeTab === "scheduled" && renderScheduledServicesForm()}
                    {activeTab === "maintenance" && renderPlanMaintenanceForm()}
                    {activeTab === "disinfection" && renderDisinfectionForm()}

                    {/* Action Buttons */}
                    <div className="flex justify-center gap-4 pt-4 border-t border-border/30">
                        <Button
                            onClick={handleReset}
                            variant="outline"
                            className="h-10 px-8 bg-cyan-600 text-white border-0 hover:bg-cyan-700"
                        >
                            Reset
                        </Button>
                        <Button
                            onClick={handleSubmit}
                            className="h-10 px-8 bg-amber-500 hover:bg-amber-600 text-white"
                        >
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Data Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {/* Controls */}
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    <SelectItem value="10">10</SelectItem>
                                    <SelectItem value="25">25</SelectItem>
                                    <SelectItem value="50">50</SelectItem>
                                    <SelectItem value="100">100</SelectItem>
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Facility services, Service type, Room No"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10 w-80 h-9 bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Table */}
                    {renderTable()}

                    {/* Footer */}
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing 1 to 10 of 136 entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(1)}
                                disabled={currentPage === 1}
                            >
                                First
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                disabled={currentPage === 1}
                            >
                                <ChevronLeft className="h-4 w-4 mr-1" />
                                Previous
                            </Button>
                            {[1, 2, 3, 4, 5].map((page) => (
                                <Button
                                    key={page}
                                    variant={currentPage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`w-9 h-9 p-0 ${currentPage === page
                                        ? "bg-primary text-white"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    onClick={() => setCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            <span className="text-muted-foreground px-2">...</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(Math.min(14, currentPage + 1))}
                            >
                                Next
                                <ChevronRight className="h-4 w-4 ml-1" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(14)}
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
                                    <div className="border border-[#3eb1c8] text-[#3eb1c8] rounded-[2px] px-3 py-[2px] text-[13px] font-medium cursor-pointer">AM</div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-start">
                            <Label className="text-sm font-medium text-gray-800 text-left pt-6">End Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="12" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <span className="text-xl font-bold pb-6">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="00" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <div className="pb-6">
                                    <div className="border border-[#3eb1c8] text-[#3eb1c8] rounded-[2px] px-3 py-[2px] text-[13px] font-medium cursor-pointer">AM</div>
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

                        <div className="flex justify-center gap-4 pt-4">
                            <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Reset</Button>
                            <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Submit</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default ServicePlanning;




