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
                <SelectContent className="bg-white">
                  <SelectItem value="101">Room 101</SelectItem>
                  <SelectItem value="102">Room 102</SelectItem>
                  <SelectItem value="103">Room 103</SelectItem>
                  <SelectItem value="104">Room 104</SelectItem>
                  <SelectItem value="105">Room 105</SelectItem>
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
                  <SelectContent className="bg-white">
                    <SelectItem value="mkds1">MKDS 1</SelectItem>
                    <SelectItem value="mkds2">MKDS 2</SelectItem>
                    <SelectItem value="mkds3">MKDS 3</SelectItem>
                    <SelectItem value="mkds4">MKDS 4</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-center pt-4">
              <Button className="h-11 px-8 min-w-[160px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                <Download className="h-4 w-4 mr-2" />
                Generate Report
              </Button>
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

          <Button className="h-11 px-8 min-w-[160px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
            <Download className="h-4 w-4 mr-2" />
            Generate Report
          </Button>
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
