import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Download, FileText } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataState, TableLoading } from "@/core/components/DataState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDevices, useEnergyStats, useRooms } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Reports.
 *
 * THERE IS NO REPORT-GENERATION OR EXPORT ENDPOINT. Every "Generate Report"
 * button is therefore disabled: producing a file is a backend capability that
 * Phase 2.x does not deliver, and a client-side approximation would not be the
 * same report.
 *
 * What IS connected:
 *   - The Room No and device pickers list real rooms (GET /rooms) and devices
 *     (GET /devices) instead of hardcoded numbers.
 *   - The Energy Report shows the real `energy_stat` rows for the chosen date
 *     range via GET /energy-stats. Values carry NO UNIT, because the table
 *     stores none, and nothing is costed or carbon-weighted.
 */

const reportTabs = [
  { id: "occupancy", label: "Occupancy Report" },
  { id: "employee", label: "Employee Report" },
  { id: "room-status", label: "Room Status Report" },
  { id: "booking", label: "Booking Report" },
  { id: "ticket", label: "Ticket Report" },
  { id: "housekeeping", label: "Housekeeping Report" },
  { id: "sanitization", label: "Sanitization Report" },
  { id: "alert", label: "Alert Report" },
  { id: "energy", label: "Energy Report" },
];

// Energy Report Component
const EnergyReportContent = () => {
  const [mainTab, setMainTab] = useState("room-based");
  const [subTab, setSubTab] = useState("guest-rooms");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [roomNo, setRoomNo] = useState("");
  const [mkds, setMkds] = useState("");

  // --- Live data -----------------------------------------------------------
  const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
  const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE });
  const energyQuery = useEnergyStats({
    page: 1,
    page_size: MAX_PAGE_SIZE,
    ...(roomNo ? { amenity_id: roomNo } : {}),
    ...(mkds ? { device_name: mkds } : {}),
    ...(dateFrom ? { timestamp_from: new Date(`${dateFrom}T00:00:00Z`).toISOString() } : {}),
    ...(dateTo ? { timestamp_to: new Date(`${dateTo}T23:59:59Z`).toISOString() } : {}),
  });
  const energyRows = energyQuery.data?.items ?? [];

  const mainTabs = [
    { id: "room-based", label: "Room Based" },
    { id: "device-based", label: "Device Based" },
    { id: "multiple-room-based", label: "Multiple Room Based" },
  ];

  const subTabs = [
    { id: "guest-rooms", label: "Guest Rooms" },
    { id: "non-guest-rooms", label: "Non Guest Rooms" },
    { id: "multiple-device-based", label: "Multiple Device Based" },
  ];

  // Determine which fields to show based on tab selection
  const showMkdsField = mainTab === "device-based" ||
    (mainTab === "multiple-room-based" && subTab === "multiple-device-based");

  return (
    <Card className="border-0 shadow-lg">
      <CardContent className="p-8">
        {/* Report Title */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-blue-50 rounded-lg">
            <FileText className="h-5 w-5 text-blue-600" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">Energy Report</h2>
        </div>

        {/* Main Tabs */}
        <div className="bg-muted/30 p-1 rounded-xl w-fit mb-4">
          <div className="flex gap-1">
            {mainTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setMainTab(tab.id);
                  if (tab.id === "multiple-room-based") {
                    setSubTab("guest-rooms");
                  }
                }}
                className={`px-4 py-2.5 text-sm font-medium transition-all duration-200 rounded-lg ${mainTab === tab.id
                  ? "bg-white text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/50"
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sub Tabs (only for Multiple Room Based) */}
        {mainTab === "multiple-room-based" && (
          <div className="bg-muted/20 p-1 rounded-lg w-fit mb-6 ml-2">
            <div className="flex gap-1">
              {subTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSubTab(tab.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${subTab === tab.id
                    ? "bg-[#5865F2] text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/50"
                    }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Form Fields */}
        <div className="max-w-2xl">
          <div className="space-y-4">
            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  Date From
                </Label>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  placeholder="dd / mm / yyyy"
                  className="h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  Date To
                </Label>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  placeholder="dd / mm / yyyy"
                  className="h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]"
                />
              </div>
            </div>

            {/* Room No */}
            <div className="flex items-center gap-4">
              <Label className="text-sm font-medium text-foreground w-32 text-right">
                Room No
              </Label>
              <Select value={roomNo} onValueChange={setRoomNo}>
                <SelectTrigger className="flex-1 h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]">
                  <SelectValue placeholder="Select Room No" />
                </SelectTrigger>
                <SelectContent className="bg-popover text-popover-foreground border-border">
                  {(roomsQuery.data?.items ?? []).map((room) => (
                    <SelectItem key={room.id} value={room.id}>{room.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* MKDS (Conditional) */}
            {showMkdsField && (
              <div className="flex items-center gap-4">
                <Label className="text-sm font-medium text-foreground w-32 text-right">
                  MKDS
                </Label>
                <Select value={mkds} onValueChange={setMkds}>
                  <SelectTrigger className="flex-1 h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]">
                    <SelectValue placeholder="Select MKDS" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {(devicesQuery.data?.items ?? [])
                      .filter((device) => device.device_name)
                      .map((device) => (
                        <SelectItem key={device.id} value={device.device_name as string}>
                          {device.device_name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Export needs a backend report endpoint, which does not exist.
                The stored rows are listed below instead. */}
            <div className="flex flex-col items-center gap-2 pt-4">
              <Button
                className="h-11 px-8 min-w-[160px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                disabled
                title="No report export endpoint exists"
              >
                <Download className="h-4 w-4 mr-2" />
                Generate Report
              </Button>
              <p className="text-xs text-muted-foreground">
                File export is not available: the API exposes no report-generation
                endpoint. The stored readings are shown below.
              </p>
            </div>

            {/* Live energy_stat rows for the current filters. */}
            <div className="rounded-xl border border-gray-200 overflow-hidden">
              <DataState
                isLoading={energyQuery.isLoading}
                error={energyQuery.error}
                isEmpty={energyRows.length === 0}
                emptyTitle="No energy readings for this selection"
                loader={<TableLoading columns={5} />}
              >
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead>Room</TableHead>
                      <TableHead>Device</TableHead>
                      <TableHead>Hour (UTC)</TableHead>
                      <TableHead className="text-right">Energy consumed</TableHead>
                      <TableHead>Unit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {energyRows.slice(0, 50).map((row) => (
                      <TableRow key={`${row.device_name}-${row.amenity_id}-${row.hour}`}>
                        <TableCell>{row.amenity_name ?? "-"}</TableCell>
                        <TableCell>{row.device_name}</TableCell>
                        <TableCell>{new Date(row.hour_timestamp).toLocaleString()}</TableCell>
                        <TableCell className="text-right">{row.energy_consumed}</TableCell>
                        {/* Always null: energy_stat stores no unit. */}
                        <TableCell className="text-muted-foreground">
                          {row.energy_unit ?? "not recorded"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </DataState>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Standard Report Content Component
const StandardReportContent = ({ reportName, singleDateOnly = false }: { reportName: string; singleDateOnly?: boolean }) => {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [singleDate, setSingleDate] = useState("");

  return (
    <Card className="border-0 shadow-lg">
      <CardContent className="p-8">
        {/* Report Title */}
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 bg-[#5865F2]/10 rounded-lg">
            <FileText className="h-5 w-5 text-[#5865F2]" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">{reportName}</h2>
        </div>

        {/* Date Filters and Generate Button */}
        <div className="flex flex-wrap items-end gap-6">
          {singleDateOnly ? (
            /* Single Date Only - for Housekeeping and Sanitization Reports */
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                Date
              </Label>
              <Input
                type="date"
                value={singleDate}
                onChange={(e) => setSingleDate(e.target.value)}
                placeholder="dd / mm / yyyy"
                className="w-56 h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]"
              />
            </div>
          ) : (
            /* Date Range - From Date and To Date */
            <>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  From Date
                </Label>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  placeholder="dd / mm / yyyy"
                  className="w-56 h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  To Date
                </Label>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  placeholder="dd / mm / yyyy"
                  className="w-56 h-11 bg-white border-gray-200 rounded-lg focus:border-[#5865F2] focus:ring-[#5865F2]"
                />
              </div>
            </>
          )}

          <div className="flex flex-col gap-1">
            <Button
              className="h-11 px-8 min-w-[160px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
              disabled
              title="No report export endpoint exists"
            >
              <Download className="h-4 w-4 mr-2" />
              Generate Report
            </Button>
            <p className="text-xs text-muted-foreground max-w-xs">
              Report generation is a backend capability the API does not expose.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const Reports = () => {
  const [activeTab, setActiveTab] = useState("occupancy");

  const activeReport = reportTabs.find((tab) => tab.id === activeTab);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Reports</h1>
        <p className="text-muted-foreground mt-1">
          Generate and download various operational reports
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-6 min-w-max pb-px">
          {reportTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-2 pb-3.5 text-sm font-medium transition-all duration-200 whitespace-nowrap ${activeTab === tab.id
                ? "text-foreground font-semibold"
                : "text-muted-foreground hover:text-foreground"
                }`}
            >
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-[#5865F2] rounded-t-full shadow-sm" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Report Content */}
      {activeTab === "energy" ? (
        <EnergyReportContent />
      ) : (
        <StandardReportContent
          reportName={activeReport?.label || ""}
          singleDateOnly={activeTab === "housekeeping" || activeTab === "sanitization"}
        />
      )}
    </div>
  );
};

export default Reports;
