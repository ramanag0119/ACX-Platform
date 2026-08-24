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
import { DataState, TableLoading } from "@/core/components/DataState";
import { useDeviceTypes, useDevices, useIncidents, useRooms, useUsers } from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import { IncidentActionsDialog } from "../components/IncidentActionsDialog";
import {
  useCommissionDevice,
  useCreateDevice,
  useDecommissionDevice,
  useUpdateDevice,
  useUpdateIncident,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Caleido Network, connected to the Phase 2.6 / 2.7 APIs.
 *
 *   Devices tab       -> GET /devices        (+ /device-types, /rooms for the form)
 *   Network Alert tab -> GET /incidents
 *
 * The alert table is driven by INCIDENTS, not alerts, because the schema
 * separates the two: an alert carries a severity and nothing else, while the
 * lifecycle status and assignee live on the incident it belongs to. Using
 * /alerts would have left Status and Assigned To permanently blank.
 *
 * NOT AVAILABLE:
 *   - Maintenance Predictor. Shaft/relay operation counts and expected
 *     remaining life are IKANOS predictions that the 92-table schema does not
 *     store, and there is no bulk health endpoint -- /devices/{id}/health is
 *     per device. That tab shows a notice instead of sample rows.
 *   - `device.authentication_code` is never requested and cannot appear here.
 *
 * Phase 3.0 writes:
 *   Add Device tab     -> POST /devices (starts `configured`)
 *   Row edit           -> PATCH /devices/{id}
 *   Commission/decommission -> POST /devices/{id}/commission|decommission,
 *                          which set `device_config_status`; the row is never
 *                          deleted because telemetry references it
 *   Network Alert rows  -> PATCH /incidents/{id} (acknowledge / assign / resolve)
 *
 * `device.authentication_code` is neither sent nor displayed anywhere.
 */

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

  // --- Live data ---------------------------------------------------------
  const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE });
  const deviceTypesQuery = useDeviceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
  const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
  const incidentsQuery = useIncidents({ page: 1, page_size: MAX_PAGE_SIZE });
  const staffQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 });

  // --- Mutations
  const { canWrite } = useAuth();
  const mayWrite = canWrite("caleido_network");
  const createDeviceMutation = useCreateDevice();
  const updateDeviceMutation = useUpdateDevice();
  const commission = useCommissionDevice();
  const decommission = useDecommissionDevice();
  const updateIncidentMutation = useUpdateIncident();
  const [editingDevice, setEditingDevice] = useState<{ id: string; appliance: string } | null>(null);
  const [incidentTarget, setIncidentTarget] = useState<{
    id: string;
    subject: string;
    statusId: number | null;
    assignedToId: string | null;
  } | null>(null);

  const deviceTypes = (deviceTypesQuery.data?.items ?? []).map((type) => ({
    value: String(type.id),
    label: type.name ?? String(type.id),
  }));
  const roomNumbers = (roomsQuery.data?.items ?? []).map((room) => room.name);

  const devicesData = (devicesQuery.data?.items ?? []).map((device) => ({
    id: device.id,
    roomNo: device.amenity_name ?? "-",
    typeOfDevice: device.device_type_name ?? "-",
    nameOfDevice: device.device_name ?? device.device_uid ?? "-",
    nameOfManufacturer: device.manufacturer_name ?? "-",
    nameOfAppliance: device.appliance_name ?? "",
    configStatus: device.device_config_status ?? "-",
  }));

  const networkAlerts = (incidentsQuery.data?.items ?? []).map((incident) => ({
    id: incident.id,
    statusId: incident.current_incident_status ?? null,
    assignedToId: incident.assignee?.id ?? null,
    roomNo: incident.amenity_name ?? "-",
    deviceId: incident.device_uid ?? "-",
    deviceName: incident.device_name ?? "-",
    severity: incident.latest_alert_severity ?? "-",
    alert: incident.subject ?? incident.alert_type_name ?? "-",
    dateTime: new Date(incident.created_on).toLocaleString(),
    status: incident.status_name ?? "-",
    assignedTo: incident.assignee?.name ?? "-",
  }));
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

    const room = (roomsQuery.data?.items ?? []).find((item) => item.name === roomNo);
    if (!room) {
      setErrors({ typeOfDevice: "Select a room that exists" });
      return;
    }

    createDeviceMutation.mutate(
      {
        device_type: Number(typeOfDevice),
        amenity_id: room.id,
        device_name: nameOfDevice || null,
        manufacturer_name: nameOfManufacturer || null,
        appliance_name: nameOfAppliance || null,
        // `device.mfg_date` is NOT NULL; today is the honest default for a
        // device being registered now.
        mfg_date: new Date().toISOString(),
        installed_on: new Date().toISOString(),
      },
      { onSuccess: handleReset },
    );
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

  // Shaft/relay operation counts and expected remaining life are not stored
  // anywhere in the schema, so there is nothing to list.
  const maintenanceData: {
    id: string; roomNo: string; deviceId: string; installedDate: string;
    shaftOperations?: string; expectedShaftLife?: string; batteryStatus?: string;
    avgBatteryLife?: string; expectedBatteryLife?: string;
    roomRelayOperations?: string; expectedRelayLife?: string;
  }[] = [];
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
      <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
        {/* Page Header */}
        <div className="mb-2">
          <h1 className="text-2xl font-semibold text-foreground">Device Management</h1>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-6 border-b border-gray-200">
          <div className="flex gap-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
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
        </div>

        {/* Content Area */}
        <Card className="border-0 shadow-lg rounded-2xl bg-white">
          <CardContent className="p-6">
            {/* Add Device Tab */}
            {activeTab === "add-device" && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-foreground">Add Devices</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
                  {/* Room No */}
                  <div className="space-y-2">
                    <Label className="text-foreground">
                      Room No<span className="text-red-500">*</span>
                    </Label>
                    <Select value={roomNo} onValueChange={setRoomNo}>
                      <SelectTrigger className="bg-muted/30 border-border/50 text-foreground">
                        <SelectValue placeholder="Select Room Number" />
                      </SelectTrigger>
                      <SelectContent className="bg-white max-h-60">
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
                        className="bg-amber-500 hover:bg-amber-600 text-white"
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
                <div className="flex justify-center gap-4 mt-6">
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    className="bg-muted/30 border-border/50 text-foreground hover:bg-muted/50 px-8"
                  >
                    Reset
                  </Button>
                  <Button
                    onClick={handleSubmit}
                    className="bg-cyan-600 hover:bg-cyan-700 text-white px-8"
                  >
                    Submit
                  </Button>
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
                        {devicesQuery.isLoading || devicesQuery.error || paginatedData.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={6} className="py-2">
                              <DataState
                                isLoading={devicesQuery.isLoading}
                                error={devicesQuery.error}
                                isEmpty
                                emptyTitle="No devices found"
                                loader={<TableLoading columns={6} />}
                              >
                                <span />
                              </DataState>
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
                                  <Button
                                    size="sm"
                                    className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]"
                                    disabled={!mayWrite}
                                    onClick={() => {
                                      setEditingDevice({ id: item.id, appliance: item.nameOfAppliance });
                                      setEditDeviceOpen(true);
                                    }}
                                  >
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
                        <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${currentPage === page ? "bg-cyan-600 text-white" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
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
                                    <Button
                                      size="sm"
                                      className="bg-[#ffc107] hover:bg-[#e0a800] text-[#333] h-8 w-8 p-0 rounded-[4px]"
                                      disabled={!mayWrite || commission.isPending || decommission.isPending}
                                      onClick={() =>
                                        item.configStatus === "decommissioned"
                                          ? commission.mutate(item.id)
                                          : decommission.mutate({ id: item.id })
                                      }
                                    >
                                      <Server className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent side="left" className="bg-black text-white text-xs border-0 pr-3 pl-3 py-2 -mr-1">
                                    {item.configStatus === "decommissioned" ? (
                                      <>Currently decommissioned.<br />Click to commission it again.</>
                                    ) : (
                                      <>Currently {item.configStatus}.<br />Click to decommission.</>
                                    )}
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
                      <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${currentPage === page ? "bg-cyan-600 text-white" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
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
                      {incidentsQuery.isLoading || incidentsQuery.error || paginatedNetworkAlerts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={9} className="py-2">
                            <DataState
                              isLoading={incidentsQuery.isLoading}
                              error={incidentsQuery.error}
                              isEmpty
                              emptyTitle="No alerts found"
                              loader={<TableLoading columns={9} />}
                            >
                              <span />
                            </DataState>
                          </TableCell>
                        </TableRow>
                      ) : (
                        paginatedNetworkAlerts.map((item, index) => (
                          <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}>
                            <TableCell className="text-foreground">{item.roomNo}</TableCell>
                            <TableCell className="text-foreground">{item.deviceId}</TableCell>
                            <TableCell className="text-cyan-600">{item.deviceName}</TableCell>
                            <TableCell>
                              {/* `alert_severity` labels are lower-case: warning | critical.
                                  Comparing against "Critical" never matched, so critical
                                  incidents were rendered in the warning colour. */}
                              <span className={`px-2 py-1 rounded text-xs font-medium ${item.severity === "critical" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                                {item.severity}
                              </span>
                            </TableCell>
                            <TableCell className="text-cyan-600">{item.alert}</TableCell>
                            <TableCell className="text-foreground">{item.dateTime}</TableCell>
                            <TableCell className="text-foreground">{item.status}</TableCell>
                            <TableCell className="text-foreground">{item.assignedTo}</TableCell>
                            <TableCell>
                              <div className="flex items-center justify-center">
                                <Button
                                  size="sm"
                                  className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]"
                                  disabled={!mayWrite}
                                  onClick={() =>
                                    setIncidentTarget({
                                      id: item.id,
                                      subject: item.alert,
                                      statusId: item.statusId,
                                      assignedToId: item.assignedToId,
                                    })
                                  }
                                  title={
                                    mayWrite
                                      ? "Acknowledge, assign or resolve"
                                      : "Your role cannot change the device network"
                                  }
                                >
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
                    Showing {filteredNetworkAlerts.length > 0 ? networkStartIndex + 1 : 0} to {Math.min(networkEndIndex, filteredNetworkAlerts.length)} of {filteredNetworkAlerts.length} entries
                  </span>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(1)} disabled={networkCurrentPage === 1}>First</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(Math.max(1, networkCurrentPage - 1))} disabled={networkCurrentPage === 1}>Previous</Button>
                    {getPageNumbers(networkTotalPages, networkCurrentPage).map((page) => (
                      <Button key={page} variant={networkCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${networkCurrentPage === page ? "bg-cyan-600 text-white" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setNetworkCurrentPage(page)}>{page}</Button>
                    ))}
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(Math.min(networkTotalPages, networkCurrentPage + 1))} disabled={networkCurrentPage === networkTotalPages || networkTotalPages === 0}>Next</Button>
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setNetworkCurrentPage(networkTotalPages)} disabled={networkCurrentPage === networkTotalPages || networkTotalPages === 0}>Last</Button>
                  </div>
                </div>
              </div>
            )}

            {/* Maintenance Predictor Tab */}
            {activeTab === "maintenance" && (
              <div className="space-y-6">
                <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  Maintenance prediction is not available. Shaft and relay operation
                  counts and expected remaining life are not stored in the database,
                  and device health is only exposed one device at a time
                  (<span className="font-mono">GET /devices/&#123;id&#125;/health</span>).
                  No predicted figures are shown rather than estimated ones.
                </p>
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
                                <TableCell className="text-cyan-600">{(item as typeof maintenanceData[0]).shaftOperations || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof maintenanceData[0]).expectedShaftLife || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof maintenanceData[0]).batteryStatus || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof maintenanceData[0]).avgBatteryLife || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof maintenanceData[0]).expectedBatteryLife || "-"}</TableCell>
                              </>
                            ) : (
                              <>
                                <TableCell className="text-cyan-600">{(item as typeof maintenanceData[0]).roomRelayOperations || "-"}</TableCell>
                                <TableCell className="text-foreground">{(item as typeof maintenanceData[0]).expectedRelayLife || "-"}</TableCell>
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
                      <Button key={page} variant={maintenanceCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${maintenanceCurrentPage === page ? "bg-cyan-600 text-white" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setMaintenanceCurrentPage(page)}>{page}</Button>
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
                  <select
                    className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none"
                    disabled
                  >
                    <option>
                      {devicesData.find((row) => row.id === editingDevice?.id)?.roomNo ?? "-"}
                    </option>
                  </select>
                  <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Type of Device <span className="text-red-500">*</span></Label>
                <div className="relative">
                  <select
                    className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none"
                    disabled
                  >
                    <option>
                      {devicesData.find((row) => row.id === editingDevice?.id)?.typeOfDevice ?? "-"}
                    </option>
                  </select>
                  <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Name of Device <span className="text-red-500">*</span></Label>
                <input
                  type="text"
                  readOnly
                  value={devicesData.find((row) => row.id === editingDevice?.id)?.nameOfDevice ?? ""}
                  className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                />
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Name of Manufacturer <span className="text-red-500">*</span></Label>
                <input
                  type="text"
                  readOnly
                  value={
                    devicesData.find((row) => row.id === editingDevice?.id)?.nameOfManufacturer ?? ""
                  }
                  className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                />
              </div>
              <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                <Label className="text-sm font-medium text-gray-800">Name of Appliance</Label>
                <input
                  type="text"
                  placeholder="Enter Name of Appliance"
                  value={editingDevice?.appliance ?? ""}
                  onChange={(event) =>
                    setEditingDevice((current) =>
                      current ? { ...current, appliance: event.target.value } : current,
                    )
                  }
                  className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-700 focus:ring-0 px-0 pb-1 text-sm outline-none"
                />
              </div>
              <p className="text-xs text-gray-500">
                Room, device type, name and manufacturer identify the device and are
                set when it is registered.
              </p>
            </div>
            <div className="flex justify-center gap-4 pb-8 border-t border-gray-100 pt-6 mt-2">
              <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditDeviceOpen(false)}>Reset</Button>
              <Button
                className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal"
                disabled={!editingDevice || updateDeviceMutation.isPending}
                onClick={() =>
                  editingDevice &&
                  updateDeviceMutation.mutate(
                    { id: editingDevice.id, body: { appliance_name: editingDevice.appliance || null } },
                    { onSuccess: () => setEditDeviceOpen(false) },
                  )
                }
              >
                {updateDeviceMutation.isPending ? "Saving..." : "Submit"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* The decommission confirmation dialog was removed: the row button is a
            single action whose tooltip states the device's current
            device_config_status and what clicking will change it to. */}

        {/* The old "Edit alert status" dialog was removed: an ALERT is a fact a
            device reported and has no status column. The lifecycle belongs to the
            INCIDENT, which IncidentActionsDialog edits (and which records an
            incident_history row for every transition). */}
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
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" className="bg-muted/30 border-border/50">Reset</Button>
              <Button className="bg-cyan-600 hover:bg-cyan-700">
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
                        <Button size="sm" className="bg-[#d33] hover:bg-[#bd2d2d] text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteFirmwareOpen(true)}>
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
                        <Button size="sm" className="bg-[#d33] hover:bg-[#bd2d2d] text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteFirmwareOpen(true)}>
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
                        <Button size="sm" className="bg-[#d33] hover:bg-[#bd2d2d] text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteFirmwareOpen(true)}>
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
            <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFirmwareOpen(false)}>Close</Button>
            <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFirmwareOpen(false)}>Submit</Button>
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
            <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setDeleteFirmwareOpen(false)}>Close</Button>
            <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setDeleteFirmwareOpen(false)}>Update</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Network Alert Tracking -> acknowledge / assign / resolve an incident.
          The row action already set `incidentTarget`, but this dialog was
          imported and never rendered, so the button appeared to do nothing.
          It writes through PATCH /incidents/{id}. */}
      <IncidentActionsDialog
        open={incidentTarget !== null}
        target={incidentTarget}
        canWrite={mayWrite}
        onClose={() => setIncidentTarget(null)}
      />
    </div>
  );
};

export default DeviceManagement;






