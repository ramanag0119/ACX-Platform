import { useState } from "react";
import { useLocation } from "react-router-dom";
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
import { Card, CardContent } from "@/components/ui/card";
import { Pencil, Eye, Upload, Edit, Trash2, RefreshCw, Search, X, ChevronDown, Server } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// Device types for Add Device form
const deviceTypes = [
  { value: "intellihub", label: "Intellihub" },
  { value: "airq", label: "AirQ" },
  { value: "mikos", label: "Mikos" },
  { value: "kleio", label: "Kleio" },
];

// Room numbers
const roomNumbers = [
  "101", "102", "103", "104", "105", "106", "108", "109", "111", "115",
  "1238", "1309", "192001", "2001", "201", "202", "203", "204", "205"
];

// Initial device data matching the image
const initialDevicesData = [
  { id: "1", roomNo: "101", typeOfDevice: "Mikos", nameOfDevice: "101M001", nameOfManufacturer: "CDL", nameOfAppliance: "" },
  { id: "2", roomNo: "101", typeOfDevice: "AirQ", nameOfDevice: "101AR01", nameOfManufacturer: "CDL", nameOfAppliance: "" },
  { id: "3", roomNo: "102", typeOfDevice: "Mikos", nameOfDevice: "102M002", nameOfManufacturer: "cdl", nameOfAppliance: "" },
  { id: "4", roomNo: "102", typeOfDevice: "Mikos", nameOfDevice: "102M001", nameOfManufacturer: "CDL", nameOfAppliance: "Refriger" },
  { id: "5", roomNo: "103", typeOfDevice: "Mikos", nameOfDevice: "103M001", nameOfManufacturer: "CDL", nameOfAppliance: "" },
  { id: "6", roomNo: "104", typeOfDevice: "AirQ", nameOfDevice: "104AR01", nameOfManufacturer: "CDL", nameOfAppliance: "" },
  { id: "7", roomNo: "105", typeOfDevice: "Mikos", nameOfDevice: "105M001", nameOfManufacturer: "CDL", nameOfAppliance: "" },
  { id: "8", roomNo: "106", typeOfDevice: "Kleio", nameOfDevice: "1001E01", nameOfManufacturer: "Caleido Xenia", nameOfAppliance: "" },
  { id: "9", roomNo: "106", typeOfDevice: "Mikos", nameOfDevice: "106M101", nameOfManufacturer: "Caleido Xenia", nameOfAppliance: "" },
  { id: "10", roomNo: "106", typeOfDevice: "AirQ", nameOfDevice: "106AR01", nameOfManufacturer: "Caleido Xenia", nameOfAppliance: "" },
];

// Network Alert data matching the image
const initialNetworkAlerts = [
  { id: "1", roomNo: "211", deviceId: "283", deviceName: "211HUB01", severity: "Critical", alert: "Hub Offline", dateTime: "05-01-2026 22:33", status: "Unsent", assignedTo: "-" },
  { id: "2", roomNo: "211", deviceId: "236", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:51", status: "Unsent", assignedTo: "-" },
  { id: "3", roomNo: "211", deviceId: "298", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:50", status: "Unsent", assignedTo: "-" },
  { id: "4", roomNo: "211", deviceId: "296", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:48", status: "Unsent", assignedTo: "-" },
  { id: "5", roomNo: "211", deviceId: "290", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 15:48", status: "Unsent", assignedTo: "Unsent" },
  { id: "6", roomNo: "211", deviceId: "290", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:47", status: "Unsent", assignedTo: "-" },
  { id: "7", roomNo: "211", deviceId: "290", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:46", status: "Unsent", assignedTo: "-" },
  { id: "8", roomNo: "211", deviceId: "298", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:45", status: "Unsent", assignedTo: "-" },
  { id: "9", roomNo: "211", deviceId: "298", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:44", status: "Unsent", assignedTo: "-" },
  { id: "10", roomNo: "211", deviceId: "298", deviceName: "211AR01", severity: "Warning", alert: "Room Air Quality Poor", dateTime: "05-01-2026 19:43", status: "Unsent", assignedTo: "-" },
];

// Maintenance Predictor Data - Kleio
const kleioMaintenanceData = [
  { id: "1", roomNo: "906", deviceId: "82", installedDate: "26-09-2021 22:14", shaftOperations: "42648617305", expectedShaftLife: "-843", batteryStatus: "100.00", avgBatteryLife: "NaN", expectedBatteryLife: "NaN" },
  { id: "2", roomNo: "1309", deviceId: "205", installedDate: "16-09-2024 11:15", shaftOperations: "", expectedShaftLife: "", batteryStatus: "", avgBatteryLife: "", expectedBatteryLife: "" },
  { id: "3", roomNo: "201", deviceId: "254", installedDate: "30-01-2025 12:20", shaftOperations: "", expectedShaftLife: "", batteryStatus: "100.00", avgBatteryLife: "", expectedBatteryLife: "" },
  { id: "4", roomNo: "211", deviceId: "207", installedDate: "25-01-2026 17:55", shaftOperations: "", expectedShaftLife: "", batteryStatus: "100.00", avgBatteryLife: "", expectedBatteryLife: "" },
  { id: "5", roomNo: "221", deviceId: "208", installedDate: "10-02-2025 16:01", shaftOperations: "", expectedShaftLife: "", batteryStatus: "100.00", avgBatteryLife: "", expectedBatteryLife: "" },
  { id: "6", roomNo: "4004", deviceId: "120", installedDate: "08-08-2023 18:39", shaftOperations: "76", expectedShaftLife: "51/17083", batteryStatus: "100.00", avgBatteryLife: "114", expectedBatteryLife: "121" },
  { id: "7", roomNo: "6006", deviceId: "209", installedDate: "19-08-2023 13:16", shaftOperations: "152", expectedShaftLife: "38630", batteryStatus: "68.30", avgBatteryLife: "-2550", expectedBatteryLife: "-2532" },
  { id: "8", roomNo: "401", deviceId: "201", installedDate: "31-01-2025 12:17", shaftOperations: "", expectedShaftLife: "", batteryStatus: "68.10", avgBatteryLife: "", expectedBatteryLife: "" },
  { id: "9", roomNo: "4013", deviceId: "158", installedDate: "09-07-2023 12:02", shaftOperations: "42649617305", expectedShaftLife: "-403", batteryStatus: "-", avgBatteryLife: "180", expectedBatteryLife: "-81" },
  { id: "10", roomNo: "4017", deviceId: "163", installedDate: "08-07-2023 14:57", shaftOperations: "42648617305", expectedShaftLife: "-103", batteryStatus: "", avgBatteryLife: "", expectedBatteryLife: "" },
];

// Maintenance Predictor Data - Intellihub
const intellihubMaintenanceData = [
  { id: "1", roomNo: "201", deviceId: "231", installedDate: "30-01-2025 12:20", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "2", roomNo: "211", deviceId: "203", installedDate: "25-01-2026 11:54", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "3", roomNo: "221", deviceId: "258", installedDate: "01-02-2025 15:01", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "4", roomNo: "411", deviceId: "239", installedDate: "10-02-2025 16:00", roomRelayOperations: "-", expectedRelayLife: "-" },
];

// Maintenance Predictor Data - AirQ
const airqMaintenanceData = [
  { id: "1", roomNo: "104", deviceId: "45", installedDate: "04-11-2023 10:49", roomRelayOperations: "-83", expectedRelayLife: "-467154" },
  { id: "2", roomNo: "109", deviceId: "213", installedDate: "06-10-2021 12:30", roomRelayOperations: "440", expectedRelayLife: "2038" },
  { id: "3", roomNo: "211", deviceId: "206", installedDate: "05-01-2024 11:55", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "4", roomNo: "221", deviceId: "259", installedDate: "01-02-2025 15:54", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "5", roomNo: "241", deviceId: "202", installedDate: "21-04-2024 09:48", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "6", roomNo: "306", deviceId: "155", installedDate: "10-06-2023 17:30", roomRelayOperations: "-", expectedRelayLife: "NaN" },
  { id: "7", roomNo: "401", deviceId: "226", installedDate: "05-12-2023 16:42", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "8", roomNo: "402", deviceId: "263", installedDate: "05-02-2025 10:57", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "9", roomNo: "411", deviceId: "241", installedDate: "01-12-2025 15:19", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "10", roomNo: "603", deviceId: "222", installedDate: "05-04-2024 23:10", roomRelayOperations: "-", expectedRelayLife: "-" },
];

// Maintenance Predictor Data - Mikos
const mikosMaintenanceData = [
  { id: "1", roomNo: "101", deviceId: "156", installedDate: "17-07-2023 11:53", roomRelayOperations: "147", expectedRelayLife: "37325" },
  { id: "2", roomNo: "102", deviceId: "1", installedDate: "11-09-2023 04:13", roomRelayOperations: "80", expectedRelayLife: "470302" },
  { id: "3", roomNo: "103", deviceId: "51", installedDate: "25-23-2023 14:29", roomRelayOperations: "15", expectedRelayLife: "2805435" },
  { id: "4", roomNo: "109", deviceId: "88", installedDate: "13-09-2023 15:45", roomRelayOperations: "651", expectedRelayLife: "65193" },
  { id: "5", roomNo: "201", deviceId: "252", installedDate: "30-01-2025 12:20", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "6", roomNo: "211", deviceId: "295", installedDate: "25-07-2026 11:56", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "7", roomNo: "221", deviceId: "280", installedDate: "01-02-2025 15:05", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "8", roomNo: "3003", deviceId: "304", installedDate: "30-01-2025 18:35", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "9", roomNo: "303", deviceId: "176", installedDate: "06-06-2023 14:17", roomRelayOperations: "-", expectedRelayLife: "-" },
  { id: "10", roomNo: "307", deviceId: "280", installedDate: "18-09-2024 11:06", roomRelayOperations: "-", expectedRelayLife: "-" },
];

const DeviceManagement = () => {
  const location = useLocation();
  const isFirmwareManagement = location.pathname === "/devices/firmware-management";

  // Tab state
  const [activeTab, setActiveTab] = useState<"add-device" | "view-inventory" | "network-alert" | "maintenance">("add-device");

  // Form state for Add Device
  const [roomNo, setRoomNo] = useState("");
  const [typeOfDevice, setTypeOfDevice] = useState("");
  const [nameOfDevice, setNameOfDevice] = useState("");
  const [nameOfManufacturer, setNameOfManufacturer] = useState("");
  const [nameOfAppliance, setNameOfAppliance] = useState("");
  const [errors, setErrors] = useState<{ typeOfDevice?: string }>({});

  // Table state
  const [devicesData, setDevicesData] = useState(initialDevicesData);
  const [networkAlerts] = useState(initialNetworkAlerts);
  const [search, setSearch] = useState("");
  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [currentPage, setCurrentPage] = useState(1);

  // Maintenance Predictor state
  const [maintenanceDeviceType, setMaintenanceDeviceType] = useState<"kleio" | "intellihub" | "airq" | "mikos">("kleio");
  const [maintenanceSearch, setMaintenanceSearch] = useState("");
  const [maintenanceEntriesPerPage, setMaintenanceEntriesPerPage] = useState("10");
  const [maintenanceCurrentPage, setMaintenanceCurrentPage] = useState(1);

  // Modal States
  const [editDeviceOpen, setEditDeviceOpen] = useState(false);
  const [decommissionOpen, setDecommissionOpen] = useState(false);
  const [editAlertOpen, setEditAlertOpen] = useState(false);
  const [editFirmwareOpen, setEditFirmwareOpen] = useState(false);
  const [deleteFirmwareOpen, setDeleteFirmwareOpen] = useState(false);

  // Handle form submit
  const handleSubmit = () => {
    const newErrors: typeof errors = {};
    if (!typeOfDevice) {
      newErrors.typeOfDevice = "Type of Device is Required";
    }
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    const newDevice = {
      id: String(Date.now()),
      roomNo,
      typeOfDevice: deviceTypes.find(d => d.value === typeOfDevice)?.label || "",
      nameOfDevice,
      nameOfManufacturer,
      nameOfAppliance,
    };
    setDevicesData(prev => [newDevice, ...prev]);
    handleReset();
  };

  // Handle reset
  const handleReset = () => {
    setRoomNo("");
    setTypeOfDevice("");
    setNameOfDevice("");
    setNameOfManufacturer("");
    setNameOfAppliance("");
    setErrors({});
  };

  // Get device name
  const getDeviceName = () => {
    // This would normally be fetched from API
    return "";
  };

  // Filter data based on search
  const filteredData = devicesData.filter(item =>
    item.roomNo.toLowerCase().includes(search.toLowerCase()) ||
    item.typeOfDevice.toLowerCase().includes(search.toLowerCase()) ||
    item.nameOfDevice.toLowerCase().includes(search.toLowerCase()) ||
    item.nameOfManufacturer.toLowerCase().includes(search.toLowerCase()) ||
    item.nameOfAppliance.toLowerCase().includes(search.toLowerCase())
  );

  // Pagination calculations
  const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
  const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
  const endIndex = startIndex + parseInt(entriesPerPage);
  const paginatedData = filteredData.slice(startIndex, endIndex);

  // Network alerts pagination
  const [networkSearch, setNetworkSearch] = useState("");
  const [networkEntriesPerPage, setNetworkEntriesPerPage] = useState("10");
  const [networkCurrentPage, setNetworkCurrentPage] = useState(1);

  const filteredNetworkAlerts = networkAlerts.filter(item =>
    item.roomNo.toLowerCase().includes(networkSearch.toLowerCase()) ||
    item.deviceName.toLowerCase().includes(networkSearch.toLowerCase()) ||
    item.alert.toLowerCase().includes(networkSearch.toLowerCase())
  );

  const networkTotalPages = Math.ceil(filteredNetworkAlerts.length / parseInt(networkEntriesPerPage));
  const networkStartIndex = (networkCurrentPage - 1) * parseInt(networkEntriesPerPage);
  const networkEndIndex = networkStartIndex + parseInt(networkEntriesPerPage);
  const paginatedNetworkAlerts = filteredNetworkAlerts.slice(networkStartIndex, networkEndIndex);

  // Get maintenance data based on device type
  const getMaintenanceData = () => {
    switch (maintenanceDeviceType) {
      case "kleio": return kleioMaintenanceData;
      case "intellihub": return intellihubMaintenanceData;
      case "airq": return airqMaintenanceData;
      case "mikos": return mikosMaintenanceData;
      default: return kleioMaintenanceData;
    }
  };

  const maintenanceData = getMaintenanceData();
  const filteredMaintenanceData = maintenanceData.filter(item =>
    item.roomNo.toLowerCase().includes(maintenanceSearch.toLowerCase()) ||
    item.deviceId.toLowerCase().includes(maintenanceSearch.toLowerCase())
  );
  const maintenanceTotalPages = Math.ceil(filteredMaintenanceData.length / parseInt(maintenanceEntriesPerPage));
  const maintenanceStartIndex = (maintenanceCurrentPage - 1) * parseInt(maintenanceEntriesPerPage);
  const maintenanceEndIndex = maintenanceStartIndex + parseInt(maintenanceEntriesPerPage);
  const paginatedMaintenanceData = filteredMaintenanceData.slice(maintenanceStartIndex, maintenanceEndIndex);

  // Generate page numbers
  const getPageNumbers = (total: number, current: number) => {
    const pages = [];
    const maxVisiblePages = 5;
    let start = Math.max(1, current - Math.floor(maxVisiblePages / 2));
    const end = Math.min(total, start + maxVisiblePages - 1);

    if (end - start + 1 < maxVisiblePages) {
      start = Math.max(1, end - maxVisiblePages + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  };

  const tabs = [
    { id: "add-device", label: "Add device" },
    { id: "view-inventory", label: "View Caleido Inventory" },
    { id: "network-alert", label: "Network Alert Tracking" },
    { id: "maintenance", label: "Maintenance Predictor" },
  ];

  // Device type buttons for Maintenance Predictor
  const maintenanceDeviceTabs = [
    { id: "kleio", label: "Kleio" },
    { id: "intellihub", label: "Intellihub" },
    { id: "airq", label: "AirQ" },
    { id: "mikos", label: "Mikos" },
  ];

  // Caleido Network Page (default)
  if (!isFirmwareManagement) {
    return (
      <div className="space-y-6 animate-fade-in text-foreground">
        {/* Page Header */}
        <div className="mb-2">
          <h1 className="text-xl font-semibold text-foreground tracking-tight">Device Management</h1>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-6 border-b border-border dark:border-slate-800">
          <div className="flex gap-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
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
        </div>

        {/* Content Area */}
        <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
          <CardContent className="p-6">
            {/* Add Device Tab */}
            {activeTab === "add-device" && (
              <div className="space-y-6">
                <h2 className="text-base font-semibold text-foreground">Add Devices</h2>

                <div className="max-w-4xl space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Room No */}
                  <div className="space-y-2">
                    <Label className="text-foreground">
                      Room No<span className="text-red-500">*</span>
                    </Label>
                    <Select value={roomNo} onValueChange={setRoomNo}>
                      <SelectTrigger className="bg-muted/20 border-border dark:border-slate-700/80 text-foreground">
                        <SelectValue placeholder="Select Room Number" />
                      </SelectTrigger>
                      <SelectContent className="bg-popover text-popover-foreground border-border max-h-60">
                        {roomNumbers.map((room) => (
                          <SelectItem key={room} value={room}>
                            {room}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Type of Device */}
                  <div className="space-y-2">
                    <Label className="text-foreground">
                      Type of Device<span className="text-red-500">*</span>
                    </Label>
                    <Select
                      value={typeOfDevice}
                      onValueChange={(value) => {
                        setTypeOfDevice(value);
                        if (errors.typeOfDevice) setErrors(prev => ({ ...prev, typeOfDevice: undefined }));
                      }}
                    >
                      <SelectTrigger className={`bg-muted/30 border-border/50 text-foreground ${errors.typeOfDevice ? 'border-red-500' : ''}`}>
                        <SelectValue placeholder="Select Device type" />
                      </SelectTrigger>
                      <SelectContent className="bg-white">
                        {deviceTypes.map((device) => (
                          <SelectItem key={device.value} value={device.value}>
                            {device.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.typeOfDevice && (
                      <p className="text-red-400 text-xs bg-red-500/10 p-2 rounded">{errors.typeOfDevice}</p>
                    )}
                  </div>

                  {/* Name of Device */}
                  <div className="space-y-2 md:col-span-2">
                    <Label className="text-foreground">
                      Name of Device<span className="text-red-500">*</span>
                    </Label>
                    <div className="flex gap-2">
                      <Input
                        value={nameOfDevice}
                        onChange={(e) => setNameOfDevice(e.target.value)}
                        placeholder=""
                        className="bg-muted/30 border-border/50 text-foreground flex-1"
                      />
                      <Button
                        className="h-10 px-6 rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                        onClick={getDeviceName}
                      >
                        Get device name
                      </Button>
                    </div>
                  </div>

                  {/* Name of Manufacturer */}
                  <div className="space-y-2 md:col-span-2">
                    <Label className="text-foreground">
                      Name of Manufacturer<span className="text-red-500">*</span>
                    </Label>
                    <Input
                      value={nameOfManufacturer}
                      onChange={(e) => setNameOfManufacturer(e.target.value)}
                      placeholder="Enter Name of Manufacturer"
                      className="bg-muted/30 border-border/50 text-foreground"
                    />
                  </div>

                  {/* Name of Appliance */}
                  <div className="space-y-2 md:col-span-2">
                    <Label className="text-foreground">
                      Name of Appliance
                    </Label>
                    <Input
                      value={nameOfAppliance}
                      onChange={(e) => setNameOfAppliance(e.target.value)}
                      placeholder="Enter Name of Appliance"
                      className="bg-muted/30 border-border/50 text-foreground"
                    />
                  </div>
                </div>

                {/* Form Buttons */}
                <div className="flex justify-center gap-4 pt-6 border-t border-border/30">
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                  >
                    Reset
                  </Button>
                  <Button
                    onClick={handleSubmit}
                    className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                  >
                    Submit
                  </Button>
                </div>
              </div>

                {/* Table Section */}
                <div className="mt-8">
                  {/* Controls */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-sm">Show</span>
                      <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-white">
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
                      <Input
                        placeholder="Room no / Name of device"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-64 h-9 bg-muted/30 border-border/50 text-foreground"
                      />
                    </div>
                  </div>

                  {/* Table */}
                  <div className="rounded-xl overflow-hidden border border-gray-200">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                          <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                          <TableHead className="text-gray-600 font-medium">Type Of Device</TableHead>
                          <TableHead className="text-gray-600 font-medium">Name of Device</TableHead>
                          <TableHead className="text-gray-600 font-medium">Name of Manufacturer</TableHead>
                          <TableHead className="text-gray-600 font-medium">Name of Appliance</TableHead>
                          <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {paginatedData.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                              No devices found
                            </TableCell>
                          </TableRow>
                        ) : (
                          paginatedData.map((item, index) => (
                            <TableRow
                              key={item.id}
                              className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}
                            >
                              <TableCell className="text-foreground">{item.roomNo}</TableCell>
                              <TableCell className="text-foreground">{item.typeOfDevice}</TableCell>
                              <TableCell className="text-cyan-600">{item.nameOfDevice}</TableCell>
                              <TableCell className="text-foreground">{item.nameOfManufacturer}</TableCell>
                              <TableCell className="text-foreground">{item.nameOfAppliance || "-"}</TableCell>
                              <TableCell>
                                <div className="flex items-center justify-center">
                                  <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditDeviceOpen(true)}>
                                    <Edit className="h-[14px] w-[14px]" />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-6">
                    <span className="text-muted-foreground text-sm">
                      Showing {filteredData.length > 0 ? startIndex + 1 : 0} to {Math.min(endIndex, filteredData.length)} of {filteredData.length} entries
                    </span>

                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                      {getPageNumbers(totalPages, currentPage).map((page) => (
                        <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                      ))}
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages || totalPages === 0}>Next</Button>
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages || totalPages === 0}>Last</Button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* View Caleido Inventory Tab */}
            {activeTab === "view-inventory" && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-foreground">Caleido Inventory</h2>

                {/* Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-sm">Show</span>
                    <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                      <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white">
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
                    <Input
                      placeholder="Room no / Name of device"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-64 h-9 bg-muted/30 border-border/50 text-foreground"
                    />
                  </div>
                </div>

                {/* Table */}
                <div className="rounded-xl overflow-hidden border border-gray-200">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                        <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                        <TableHead className="text-gray-600 font-medium">Type Of Device</TableHead>
                        <TableHead className="text-gray-600 font-medium">Name of Device</TableHead>
                        <TableHead className="text-gray-600 font-medium">Name of Manufacturer</TableHead>
                        <TableHead className="text-gray-600 font-medium">Name of Appliance</TableHead>
                        <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginatedData.map((item, index) => (
                        <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}>
                          <TableCell className="text-foreground">{item.roomNo}</TableCell>
                          <TableCell className="text-foreground">{item.typeOfDevice}</TableCell>
                          <TableCell className="text-cyan-600">{item.nameOfDevice}</TableCell>
                          <TableCell className="text-foreground">{item.nameOfManufacturer}</TableCell>
                          <TableCell className="text-foreground">{item.nameOfAppliance || "-"}</TableCell>
                          <TableCell>
                            <div className="flex items-center justify-center">
                              <TooltipProvider delayDuration={100}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button size="sm" className="bg-[#ffc107] hover:bg-[#e0a800] text-[#333] h-8 w-8 p-0 rounded-[4px]" onClick={() => setDecommissionOpen(true)}>
                                      <Server className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent side="left" className="bg-black text-white text-xs border-0 pr-3 pl-3 py-2 -mr-1">
                                    Click here to change device status<br />to decommission
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground text-sm">
                    Showing {filteredData.length > 0 ? startIndex + 1 : 0} to {Math.min(endIndex, filteredData.length)} of {filteredData.length} entries
                  </span>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                    {getPageNumbers(totalPages, currentPage).map((page) => (
                      <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                    ))}
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages || totalPages === 0}>Next</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages || totalPages === 0}>Last</Button>
                  </div>
                </div>
              </div>
            )}

            {/* Network Alert Tracking Tab */}
            {activeTab === "network-alert" && (
              <div className="space-y-6">
                {/* Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-sm">Show</span>
                    <Select value={networkEntriesPerPage} onValueChange={setNetworkEntriesPerPage}>
                      <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white">
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
                    <Input
                      placeholder="Name of device, Device name, Mac"
                      value={networkSearch}
                      onChange={(e) => setNetworkSearch(e.target.value)}
                      className="w-72 h-9 bg-muted/30 border-border/50 text-foreground"
                    />
                  </div>
                </div>

                {/* Network Alert Table */}
                <div className="rounded-xl overflow-hidden border border-gray-200">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                        <TableHead className="text-gray-600 font-medium">Room No.</TableHead>
                        <TableHead className="text-gray-600 font-medium">Device ID</TableHead>
                        <TableHead className="text-gray-600 font-medium">Device Name</TableHead>
                        <TableHead className="text-gray-600 font-medium">Severity</TableHead>
                        <TableHead className="text-gray-600 font-medium">Alert</TableHead>
                        <TableHead className="text-gray-600 font-medium">Date & Time</TableHead>
                        <TableHead className="text-gray-600 font-medium">Status</TableHead>
                        <TableHead className="text-gray-600 font-medium">Assigned to</TableHead>
                        <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginatedNetworkAlerts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={9} className="text-center text-muted-foreground py-8">No alerts found</TableCell>
                        </TableRow>
                      ) : (
                        paginatedNetworkAlerts.map((item, index) => (
                          <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}>
                            <TableCell className="text-foreground">{item.roomNo}</TableCell>
                            <TableCell className="text-foreground">{item.deviceId}</TableCell>
                            <TableCell className="text-cyan-600">{item.deviceName}</TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs font-medium ${item.severity === "Critical" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                                {item.severity}
                              </span>
                            </TableCell>
                            <TableCell className="text-cyan-600">{item.alert}</TableCell>
                            <TableCell className="text-foreground">{item.dateTime}</TableCell>
                            <TableCell className="text-foreground">{item.status}</TableCell>
                            <TableCell className="text-foreground">{item.assignedTo}</TableCell>
                            <TableCell>
                              <div className="flex items-center justify-center">
                                <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditAlertOpen(true)}>
                                  <Edit className="h-[14px] w-[14px]" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground text-sm">
                    Showing {filteredNetworkAlerts.length > 0 ? networkStartIndex + 1 : 0} to {Math.min(networkEndIndex, filteredNetworkAlerts.length)} of 1,908,789 entries
                  </span>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(1)} disabled={networkCurrentPage === 1}>First</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(Math.max(1, networkCurrentPage - 1))} disabled={networkCurrentPage === 1}>Previous</Button>
                    {[1, 2, 3, 4, 5].map((page) => (
                      <Button key={page} variant={networkCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${networkCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setNetworkCurrentPage(page)}>{page}</Button>
                    ))}
                    <span className="text-muted-foreground mx-1">...</span>
                    <span className="text-muted-foreground text-sm">190,879</span>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(networkCurrentPage + 1)}>Next</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">Last</Button>
                  </div>
                </div>
              </div>
            )}

            {/* Maintenance Predictor Tab */}
            {activeTab === "maintenance" && (
              <div className="space-y-6">
                {/* Device Type Tabs */}
                <div className="bg-muted/30 p-1 rounded-xl w-fit">
                  <div className="flex gap-1">
                    {maintenanceDeviceTabs.map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => {
                          setMaintenanceDeviceType(tab.id as typeof maintenanceDeviceType);
                          setMaintenanceCurrentPage(1);
                        }}
                        className={`px-6 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${maintenanceDeviceType === tab.id
                          ? "bg-blue-600 text-white shadow-sm"
                          : "text-muted-foreground hover:text-foreground hover:bg-white/50"
                          }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-sm">Show</span>
                    <Select value={maintenanceEntriesPerPage} onValueChange={setMaintenanceEntriesPerPage}>
                      <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white">
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
                    <Input
                      placeholder="Room no"
                      value={maintenanceSearch}
                      onChange={(e) => setMaintenanceSearch(e.target.value)}
                      className="w-48 h-9 bg-muted/30 border-border/50 text-foreground"
                    />
                  </div>
                </div>

                {/* Table - Different columns based on device type */}
                <div className="rounded-xl overflow-hidden border border-gray-200">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                        <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                        <TableHead className="text-gray-600 font-medium">Device ID</TableHead>
                        <TableHead className="text-gray-600 font-medium">Installed Date</TableHead>
                        {maintenanceDeviceType === "kleio" ? (
                          <>
                            <TableHead className="text-gray-600 font-medium">Shaft Operations</TableHead>
                            <TableHead className="text-gray-600 font-medium">Expected Shaft Life (Days)</TableHead>
                            <TableHead className="text-gray-600 font-medium">Battery Status (%)</TableHead>
                            <TableHead className="text-gray-600 font-medium">Average Battery Life (Days)</TableHead>
                            <TableHead className="text-gray-600 font-medium">Expected Battery Life (Days)</TableHead>
                          </>
                        ) : (
                          <>
                            <TableHead className="text-gray-600 font-medium">Room Relay Operations</TableHead>
                            <TableHead className="text-gray-600 font-medium">Expected Relay Life (Days)</TableHead>
                          </>
                        )}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginatedMaintenanceData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={maintenanceDeviceType === "kleio" ? 8 : 5} className="text-center text-muted-foreground py-8">
                            No data found
                          </TableCell>
                        </TableRow>
                      ) : (
                        paginatedMaintenanceData.map((item, index) => (
                          <TableRow
                            key={item.id}
                            className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}
                          >
                            <TableCell className="text-foreground">{item.roomNo}</TableCell>
                            <TableCell className="text-foreground">{item.deviceId}</TableCell>
                            <TableCell className="text-cyan-600">{item.installedDate}</TableCell>
                            {maintenanceDeviceType === "kleio" ? (
                              <>
                                <TableCell className="text-cyan-600">{(item as typeof kleioMaintenanceData[0]).shaftOperations || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof kleioMaintenanceData[0]).expectedShaftLife || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof kleioMaintenanceData[0]).batteryStatus || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof kleioMaintenanceData[0]).avgBatteryLife || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof kleioMaintenanceData[0]).expectedBatteryLife || "-"}</TableCell>
                              </>
                            ) : (
                              <>
                                <TableCell className="text-cyan-600">{(item as typeof intellihubMaintenanceData[0]).roomRelayOperations || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof intellihubMaintenanceData[0]).expectedRelayLife || "-"}</TableCell>
                              </>
                            )}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground text-sm">
                    Showing {filteredMaintenanceData.length > 0 ? maintenanceStartIndex + 1 : 0} to {Math.min(maintenanceEndIndex, filteredMaintenanceData.length)} of {filteredMaintenanceData.length} entries
                  </span>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setMaintenanceCurrentPage(1)} disabled={maintenanceCurrentPage === 1}>First</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setMaintenanceCurrentPage(Math.max(1, maintenanceCurrentPage - 1))} disabled={maintenanceCurrentPage === 1}>Previous</Button>
                    {getPageNumbers(maintenanceTotalPages, maintenanceCurrentPage).map((page) => (
                      <Button key={page} variant={maintenanceCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${maintenanceCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setMaintenanceCurrentPage(page)}>{page}</Button>
                    ))}
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setMaintenanceCurrentPage(Math.min(maintenanceTotalPages, maintenanceCurrentPage + 1))} disabled={maintenanceCurrentPage === maintenanceTotalPages || maintenanceTotalPages === 0}>Next</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setMaintenanceCurrentPage(maintenanceTotalPages)} disabled={maintenanceCurrentPage === maintenanceTotalPages || maintenanceTotalPages === 0}>Last</Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Device Modal */}
        <Dialog open={editDeviceOpen} onOpenChange={setEditDeviceOpen}>
          <DialogContent className="max-w-[750px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
            <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
              <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Device Management</h2>
              <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditDeviceOpen(false)}>
                <X className="h-4 w-4 text-gray-500 stroke-[3]" />
              </Button>
            </div>
            <div className="p-8 px-12 space-y-7">
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Room No <span className="text-red-500">*</span></Label>
                <div className="relative">
                  <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                    <option>101</option>
                  </select>
                  <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Type of Device <span className="text-red-500">*</span></Label>
                <div className="relative">
                  <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                    <option>Mikos</option>
                  </select>
                  <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Name of Device <span className="text-red-500">*</span></Label>
                <input type="text" defaultValue="101MIKD1" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Name of Manufacturer <span className="text-red-500">*</span></Label>
                <input type="text" defaultValue="CXPL" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Name of Appliance</Label>
                <input type="text" placeholder="Enter Name of Appliance" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
              </div>
            </div>
            <div className="flex justify-center gap-4 pb-8 border-t border-gray-100 pt-6 mt-2">
              <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditDeviceOpen(false)}>Reset</Button>
              <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditDeviceOpen(false)}>Submit</Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Decommission Confirmation Modal */}
        <Dialog open={decommissionOpen} onOpenChange={setDecommissionOpen}>
          <DialogContent className="max-w-[400px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[8px]">
            <div className="p-10 flex flex-col items-center text-center space-y-4">
              <div className="h-[84px] w-[84px] rounded-full border-[4px] border-[#facea8] flex items-center justify-center">
                <div className="text-[#f8bb86] text-[56px] leading-none font-light mb-2">!</div>
              </div>
              <div className="space-y-2 mt-2">
                <h2 className="text-[26px] font-semibold text-[#545454]">Are you sure?</h2>
                <p className="text-[16px] text-[#545454]">This will decommission the device!</p>
              </div>

              <div className="flex gap-2.5 justify-center pt-2">
                <Button className="bg-[#3085d6] hover:bg-[#2b78c1] text-white text-[15px] font-medium px-4 py-2 rounded-[4px] h-[40px]" onClick={() => setDecommissionOpen(false)}>Yes, Decommission it!</Button>
                <Button className="bg-[#d33] hover:bg-[#bd2d2d] text-white text-[15px] font-medium px-4 py-2 rounded-[4px] h-[40px]" onClick={() => setDecommissionOpen(false)}>Cancel</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Edit Alert Status Modal */}
        <Dialog open={editAlertOpen} onOpenChange={setEditAlertOpen}>
          <DialogContent className="max-w-[500px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
            <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
              <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit alert status</h2>
              <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditAlertOpen(false)}>
                <X className="h-4 w-4 text-gray-500 stroke-[3]" />
              </Button>
            </div>
            <div className="p-8 px-10 space-y-7">
              <div className="grid grid-cols-[80px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Status <span className="text-red-500">*</span></Label>
                <div className="relative">
                  <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                    <option>Mark as unread</option>
                    <option>Mark as read</option>
                  </select>
                  <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>

            <div className="flex justify-center gap-4 pb-6 mt-1">
              <Button className="bg-[#3eb1c8] hover:bg-[#3296a9] text-white h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditAlertOpen(false)}>Update Status</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Firmware Management Page
  return (
    <div className="space-y-0 animate-fade-in">
      {/* Page Header */}
      <div className="mb-2">
        <h1 className="text-xl font-semibold text-white">Firmware Management</h1>
      </div>

      {/* Content Area */}
      <Card className="border-0 shadow-lg rounded-2xl bg-white rounded-t-none">
        <CardContent className="p-6 space-y-6">
          {/* Add Firmware Form */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Add New Firmware</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="deviceType">Device Type</Label>
                <Select>
                  <SelectTrigger className="bg-muted/30 border-border/50">
                    <SelectValue placeholder="Select device type" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="mikos-sensor">MIKOS Sensor</SelectItem>
                    <SelectItem value="mikos-controller">MIKOS Controller</SelectItem>
                    <SelectItem value="gateway">Gateway Hub</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="version">Firmware Version</Label>
                <Input id="version" placeholder="e.g., 2.4.2" className="bg-muted/30 border-border/50" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="crc">CRC Value</Label>
                <Input id="crc" placeholder="Enter CRC value" className="bg-muted/30 border-border/50" />
              </div>
              <div className="space-y-2 md:col-span-2 lg:col-span-3">
                <Label htmlFor="releaseNotes">Release Notes</Label>
                <Textarea id="releaseNotes" placeholder="Enter release notes..." rows={3} className="bg-muted/30 border-border/50" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="file">Firmware File</Label>
                <div className="flex gap-2">
                  <Input id="file" type="file" className="flex-1 bg-muted/30 border-border/50" />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
              <Button className="h-10 px-6 rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                <Upload className="h-4 w-4 mr-2" />
                Upload Firmware
              </Button>
            </div>
          </div>

          {/* Firmware List */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Firmware List</h2>
            <div className="rounded-xl overflow-hidden border border-gray-200">
              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                    <TableHead className="text-gray-600 font-medium">Device Type</TableHead>
                    <TableHead className="text-gray-600 font-medium">Firmware Version</TableHead>
                    <TableHead className="text-gray-600 font-medium">Uploaded On</TableHead>
                    <TableHead className="text-gray-600 font-medium">Uploaded By</TableHead>
                    <TableHead className="text-gray-600 font-medium">Running Devices</TableHead>
                    <TableHead className="text-gray-600 font-medium">Details</TableHead>
                    <TableHead className="text-gray-600 font-medium text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow className="bg-muted/30 hover:bg-background transition-colors">
                    <TableCell className="font-medium">MIKOS Sensor</TableCell>
                    <TableCell><span className="status-badge status-info px-2 py-1 rounded text-xs bg-cyan-500/20 text-cyan-400">v2.4.1</span></TableCell>
                    <TableCell>2024-01-10</TableCell>
                    <TableCell>Admin</TableCell>
                    <TableCell className="font-medium">156</TableCell>
                    <TableCell><Button variant="link" size="sm" className="h-auto p-0 text-cyan-500">View Details</Button></TableCell>
                    <TableCell>
                      <div className="flex gap-2 justify-center">
                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFirmwareOpen(true)}>
                          <Edit className="h-[14px] w-[14px]" />
                        </Button>
                        <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteFirmwareOpen(true)}>
                          <Trash2 className="h-[14px] w-[14px]" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  <TableRow className="bg-muted/20 hover:bg-background transition-colors">
                    <TableCell className="font-medium">MIKOS Controller</TableCell>
                    <TableCell><span className="status-badge status-info px-2 py-1 rounded text-xs bg-cyan-500/20 text-cyan-400">v3.1.0</span></TableCell>
                    <TableCell>2024-01-08</TableCell>
                    <TableCell>Admin</TableCell>
                    <TableCell className="font-medium">89</TableCell>
                    <TableCell><Button variant="link" size="sm" className="h-auto p-0 text-cyan-500">View Details</Button></TableCell>
                    <TableCell>
                      <div className="flex gap-2 justify-center">
                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFirmwareOpen(true)}>
                          <Edit className="h-[14px] w-[14px]" />
                        </Button>
                        <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteFirmwareOpen(true)}>
                          <Trash2 className="h-[14px] w-[14px]" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  <TableRow className="bg-muted/30 hover:bg-background transition-colors">
                    <TableCell className="font-medium">Gateway Hub</TableCell>
                    <TableCell><span className="status-badge status-info px-2 py-1 rounded text-xs bg-cyan-500/20 text-cyan-400">v1.2.3</span></TableCell>
                    <TableCell>2024-01-05</TableCell>
                    <TableCell>System</TableCell>
                    <TableCell className="font-medium">24</TableCell>
                    <TableCell><Button variant="link" size="sm" className="h-auto p-0 text-cyan-500">View Details</Button></TableCell>
                    <TableCell>
                      <div className="flex gap-2 justify-center">
                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFirmwareOpen(true)}>
                          <Edit className="h-[14px] w-[14px]" />
                        </Button>
                        <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteFirmwareOpen(true)}>
                          <Trash2 className="h-[14px] w-[14px]" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Firmware Update Section */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Push Firmware Update</h2>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Device Type</Label>
                <Select>
                  <SelectTrigger className="bg-muted/30 border-border/50">
                    <SelectValue placeholder="Select device type" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="mikos-sensor">MIKOS Sensor</SelectItem>
                    <SelectItem value="mikos-controller">MIKOS Controller</SelectItem>
                    <SelectItem value="gateway">Gateway Hub</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Latest Firmware Version</Label>
                <div className="flex items-center h-10 px-3 rounded-md bg-muted/30 border border-gray-200">
                  <span className="text-sm font-medium">v2.4.1</span>
                </div>
              </div>
              <div className="flex items-end">
                <Button className="bg-cyan-600 hover:bg-cyan-700">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Push Update
                </Button>
              </div>
            </div>

            {/* Device List for Update */}
            <div className="mt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-md font-semibold text-foreground">Device List</h3>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="Search devices..." className="pl-10 bg-muted/30 border-border/50" />
                </div>
              </div>
              <div className="rounded-xl overflow-hidden border border-gray-200">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                      <TableHead className="text-gray-600 font-medium w-12">
                        <Checkbox />
                      </TableHead>
                      <TableHead className="text-gray-600 font-medium">Device Name</TableHead>
                      <TableHead className="text-gray-600 font-medium">Current Version</TableHead>
                      <TableHead className="text-gray-600 font-medium">Expected Version</TableHead>
                      <TableHead className="text-gray-600 font-medium">Latest Version</TableHead>
                      <TableHead className="text-gray-600 font-medium">Released On</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow className="bg-muted/30 hover:bg-background transition-colors">
                      <TableCell><Checkbox /></TableCell>
                      <TableCell className="font-medium">MIKOS-301-A</TableCell>
                      <TableCell><span className="px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-400">v2.3.0</span></TableCell>
                      <TableCell>
                        <Select defaultValue="2.4.1">
                          <SelectTrigger className="w-28 h-8 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                          <SelectContent className="bg-white">
                            <SelectItem value="2.4.1">v2.4.1</SelectItem>
                            <SelectItem value="2.4.0">v2.4.0</SelectItem>
                            <SelectItem value="2.3.0">v2.3.0</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell><span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400">v2.4.1</span></TableCell>
                      <TableCell className="text-muted-foreground">2024-01-10</TableCell>
                    </TableRow>
                    <TableRow className="bg-muted/20 hover:bg-background transition-colors">
                      <TableCell><Checkbox /></TableCell>
                      <TableCell className="font-medium">MIKOS-301-B</TableCell>
                      <TableCell><span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400">v2.4.1</span></TableCell>
                      <TableCell>
                        <Select defaultValue="2.4.1">
                          <SelectTrigger className="w-28 h-8 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                          <SelectContent className="bg-white">
                            <SelectItem value="2.4.1">v2.4.1</SelectItem>
                            <SelectItem value="2.4.0">v2.4.0</SelectItem>
                            <SelectItem value="2.3.0">v2.3.0</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell><span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400">v2.4.1</span></TableCell>
                      <TableCell className="text-muted-foreground">2024-01-10</TableCell>
                    </TableRow>
                    <TableRow className="bg-muted/30 hover:bg-background transition-colors">
                      <TableCell><Checkbox /></TableCell>
                      <TableCell className="font-medium">MIKOS-205-A</TableCell>
                      <TableCell><span className="px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-400">v2.2.0</span></TableCell>
                      <TableCell>
                        <Select defaultValue="2.4.1">
                          <SelectTrigger className="w-28 h-8 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                          <SelectContent className="bg-white">
                            <SelectItem value="2.4.1">v2.4.1</SelectItem>
                            <SelectItem value="2.4.0">v2.4.0</SelectItem>
                            <SelectItem value="2.3.0">v2.3.0</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell><span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400">v2.4.1</span></TableCell>
                      <TableCell className="text-muted-foreground">2024-01-10</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Firmware Update Modal */}
      <Dialog open={editFirmwareOpen} onOpenChange={setEditFirmwareOpen}>
        <DialogContent className="max-w-[750px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
          <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
            <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Firmware Update</h2>
            <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditFirmwareOpen(false)}>
              <X className="h-4 w-4 text-gray-500 stroke-[3]" />
            </Button>
          </div>
          <div className="p-8 px-12 space-y-7">
            <div className="grid grid-cols-[160px_1fr] items-center gap-4">
              <Label className="text-sm font-medium text-gray-800">Device Type <span className="text-red-500">*</span></Label>
              <div className="relative">
                <select className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm appearance-none outline-none rounded-sm">
                  <option>AirQ</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
              </div>
            </div>
            <div className="grid grid-cols-[160px_1fr] items-center gap-4">
              <Label className="text-sm font-medium text-gray-800">Firmware Version <span className="text-red-500">*</span></Label>
              <input type="text" defaultValue="1.1.5" className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm outline-none rounded-sm" />
            </div>
            <div className="grid grid-cols-[160px_1fr] items-center gap-4">
              <Label className="text-sm font-medium text-gray-800">Release Notes <span className="text-red-500">*</span></Label>
              <textarea className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none resize-none pt-4" rows={2}></textarea>
            </div>
            <div className="grid grid-cols-[160px_1fr] items-center gap-4 mt-2">
              <Label className="text-sm font-medium text-gray-800">CRC Value <span className="text-red-500">*</span></Label>
              <input type="text" defaultValue="N/A" className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm outline-none rounded-sm" />
            </div>
          </div>
          <div className="flex justify-center gap-4 pb-8 border-t border-gray-100 pt-6 mt-2">
            <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditFirmwareOpen(false)}>Close</Button>
            <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditFirmwareOpen(false)}>Submit</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Firmware Delete Modal */}
      <Dialog open={deleteFirmwareOpen} onOpenChange={setDeleteFirmwareOpen}>
        <DialogContent className="max-w-[750px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
          <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
            <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Firmware Delete</h2>
            <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setDeleteFirmwareOpen(false)}>
              <X className="h-4 w-4 text-gray-500 stroke-[3]" />
            </Button>
          </div>
          <div className="p-8 px-12 space-y-7">
            <div className="grid grid-cols-[160px_1fr] items-center gap-4">
              <Label className="text-sm font-medium text-gray-800">Reason for Deletion <span className="text-red-500">*</span></Label>
              <input type="text" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
            </div>
          </div>
          <div className="flex justify-center gap-4 pb-8 border-t border-gray-100 pt-6 mt-2">
            <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setDeleteFirmwareOpen(false)}>Close</Button>
            <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setDeleteFirmwareOpen(false)}>Update</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DeviceManagement;






