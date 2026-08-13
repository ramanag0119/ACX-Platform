import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Pencil, Trash2, Upload, Edit, X } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";

// Sample firmware data
const firmwareData = [
    { id: "1", deviceType: "Intellihub", firmwareVersion: "v2.1.5", releaseNotes: "Bug fixes and improvements", crcValue: "A3B5C7D9", uploadDate: "2024-01-15" },
    { id: "2", deviceType: "AirQ", firmwareVersion: "v1.3.2", releaseNotes: "New features added", crcValue: "E4F6G8H0", uploadDate: "2024-01-10" },
    { id: "3", deviceType: "Mikos", firmwareVersion: "v3.0.1", releaseNotes: "Performance optimization", crcValue: "I1J2K3L4", uploadDate: "2024-01-05" },
    { id: "4", deviceType: "Kleio", firmwareVersion: "v4.2.0", releaseNotes: "Security patches", crcValue: "M5N6O7P8", uploadDate: "2024-01-01" },
];

// Sample devices for firmware update
const devicesList = [
    { id: "1", deviceName: "Room 101 Lock", currentVersion: "v2.0.0", expectedVersion: "v2.1.5", selected: false },
    { id: "2", deviceName: "Room 102 Lock", currentVersion: "v2.0.0", expectedVersion: "v2.1.5", selected: false },
    { id: "3", deviceName: "Lobby Switch", currentVersion: "v1.2.0", expectedVersion: "v1.3.2", selected: true },
    { id: "4", deviceName: "Room 201 Sensor", currentVersion: "v2.9.0", expectedVersion: "v3.0.1", selected: false },
    { id: "5", deviceName: "Main Gateway", currentVersion: "v4.1.0", expectedVersion: "v4.2.0", selected: true },
];

const FirmwareManagement = () => {
    const [activeTab, setActiveTab] = useState("add-firmware");
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    // Add Firmware form state
    const [deviceType, setDeviceType] = useState("");
    const [firmwareVersion, setFirmwareVersion] = useState("");
    const [releaseNotes, setReleaseNotes] = useState("");
    const [crcValue, setCrcValue] = useState("");

    // Firmware Update state
    const [selectedDeviceType, setSelectedDeviceType] = useState("");
    const [devices, setDevices] = useState(devicesList);

    // Modal states
    const [editFirmwareOpen, setEditFirmwareOpen] = useState(false);
    const [deleteFirmwareOpen, setDeleteFirmwareOpen] = useState(false);

    const filteredData = firmwareData.filter(item =>
        item.deviceType.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.firmwareVersion.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, startIndex + parseInt(entriesPerPage));

    const handleDeviceSelect = (deviceId: string) => {
        setDevices(prev => prev.map(d => d.id === deviceId ? { ...d, selected: !d.selected } : d));
    };

    const handleSelectAll = (checked: boolean) => {
        setDevices(prev => prev.map(d => ({ ...d, selected: checked })));
    };

    const handleReset = () => { setDeviceType(""); setFirmwareVersion(""); setReleaseNotes(""); setCrcValue(""); };

    return (
        <>
            <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
                {/* Header */}
                <div className="mb-2">
                    <h1 className="text-2xl font-semibold text-foreground">Firmware Management</h1>
                </div>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <div className="flex gap-6 border-b border-gray-200 mb-6">
                        <button
                            onClick={() => setActiveTab("add-firmware")}
                            className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === "add-firmware"
                                ? "text-foreground"
                                : "text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            Add Firmware
                            {activeTab === "add-firmware" && (
                                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-600 rounded-t-full" />
                            )}
                        </button>
                        <button
                            onClick={() => setActiveTab("firmware-update")}
                            className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === "firmware-update"
                                ? "text-foreground"
                                : "text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            Firmware Update
                            {activeTab === "firmware-update" && (
                                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-600 rounded-t-full" />
                            )}
                        </button>
                    </div>

                    <TabsContent value="add-firmware" className="space-y-6">
                        {/* Add Firmware Form */}
                        <Card className="border-0 shadow-lg rounded-2xl bg-white">
                            <CardContent className="p-6">
                                <h2 className="text-lg font-semibold mb-6">Add New Firmware</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
                                    <div className="space-y-2">
                                        <Label>Device Type<span className="text-red-500">*</span></Label>
                                        <Select value={deviceType} onValueChange={setDeviceType}>
                                            <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                                <SelectValue placeholder="Select device type" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-white">
                                                <SelectItem value="intellihub">Intellihub</SelectItem>
                                                <SelectItem value="airq">AirQ</SelectItem>
                                                <SelectItem value="mikos">Mikos</SelectItem>
                                                <SelectItem value="kleio">Kleio</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Firmware Version<span className="text-red-500">*</span></Label>
                                        <Input placeholder="e.g., v2.1.5" value={firmwareVersion} onChange={(e) => setFirmwareVersion(e.target.value)} className="h-10 bg-muted/30 border-border/50" />
                                    </div>
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Release Notes</Label>
                                        <Textarea placeholder="Enter release notes..." value={releaseNotes} onChange={(e) => setReleaseNotes(e.target.value)} className="bg-muted/30 border-border/50 min-h-[100px]" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>CRC Value</Label>
                                        <Input placeholder="Enter CRC value" value={crcValue} onChange={(e) => setCrcValue(e.target.value)} className="h-10 bg-muted/30 border-border/50" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Firmware File<span className="text-red-500">*</span></Label>
                                        <div className="flex gap-2">
                                            <Input type="file" className="bg-muted/30 border-border/50" />
                                            <Button className="bg-cyan-600 hover:bg-cyan-700 text-white"><Upload className="h-4 w-4" /></Button>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex justify-center gap-4 mt-6">
                                    <Button variant="outline" onClick={handleReset} className="px-8">Reset</Button>
                                    <Button className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">Submit</Button>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Firmware Table */}
                        <Card className="border-0 shadow-lg rounded-2xl bg-white">
                            <CardContent className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <div className="flex items-center gap-2">
                                        <span className="text-muted-foreground text-sm">Show</span>
                                        <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                                            <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                                            <SelectContent className="bg-white">
                                                <SelectItem value="10">10</SelectItem>
                                                <SelectItem value="25">25</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <span className="text-muted-foreground text-sm">entries</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-muted-foreground text-sm">Search:</span>
                                        <Input placeholder="Device type, version..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-64 h-9 bg-muted/30 border-border/50" />
                                    </div>
                                </div>

                                <div className="rounded-xl overflow-hidden border border-gray-200">
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                                <TableHead className="text-gray-600 font-medium">Device Type</TableHead>
                                                <TableHead className="text-gray-600 font-medium">Firmware Version</TableHead>
                                                <TableHead className="text-gray-600 font-medium">Release Notes</TableHead>
                                                <TableHead className="text-gray-600 font-medium">CRC Value</TableHead>
                                                <TableHead className="text-gray-600 font-medium">Upload Date</TableHead>
                                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {paginatedData.map((item, index) => (
                                                <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                                    <TableCell className="text-cyan-600 font-medium">{item.deviceType}</TableCell>
                                                    <TableCell>{item.firmwareVersion}</TableCell>
                                                    <TableCell>{item.releaseNotes}</TableCell>
                                                    <TableCell className="font-mono">{item.crcValue}</TableCell>
                                                    <TableCell>{item.uploadDate}</TableCell>
                                                    <TableCell className="text-center">
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
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>

                                <div className="flex items-center justify-between mt-6">
                                    <span className="text-muted-foreground text-sm">Showing {startIndex + 1} to {Math.min(startIndex + parseInt(entriesPerPage), filteredData.length)} of {filteredData.length} entries</span>
                                    <div className="flex items-center gap-1">
                                        <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
                                        <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
                                        <Button size="sm" className="w-9 h-9 p-0 bg-cyan-600 text-white">1</Button>
                                        <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
                                        <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="firmware-update" className="space-y-6">
                        <Card className="border-0 shadow-lg rounded-2xl bg-white">
                            <CardContent className="p-6">
                                <h2 className="text-lg font-semibold mb-6">Push Firmware Update</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mb-6">
                                    <div className="space-y-2">
                                        <Label>Select Device Type</Label>
                                        <Select value={selectedDeviceType} onValueChange={setSelectedDeviceType}>
                                            <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                                <SelectValue placeholder="Select device type" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-white">
                                                <SelectItem value="intellihub">Intellihub</SelectItem>
                                                <SelectItem value="airq">AirQ</SelectItem>
                                                <SelectItem value="mikos">Mikos</SelectItem>
                                                <SelectItem value="kleio">Kleio</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Latest Firmware Version</Label>
                                        <Input value="v2.1.5" readOnly className="h-10 bg-muted/30 border-border/50" />
                                    </div>
                                </div>

                                <div className="rounded-xl overflow-hidden border border-gray-200">
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                                <TableHead className="text-gray-600 font-medium w-12">
                                                    <Checkbox onCheckedChange={(checked) => handleSelectAll(checked as boolean)} />
                                                </TableHead>
                                                <TableHead className="text-gray-600 font-medium">Device Name</TableHead>
                                                <TableHead className="text-gray-600 font-medium">Current Version</TableHead>
                                                <TableHead className="text-gray-600 font-medium">Expected Version</TableHead>
                                                <TableHead className="text-gray-600 font-medium">Select Version</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {devices.map((device, index) => (
                                                <TableRow key={device.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                                    <TableCell>
                                                        <Checkbox checked={device.selected} onCheckedChange={() => handleDeviceSelect(device.id)} />
                                                    </TableCell>
                                                    <TableCell className="text-cyan-600 font-medium">{device.deviceName}</TableCell>
                                                    <TableCell>{device.currentVersion}</TableCell>
                                                    <TableCell>{device.expectedVersion}</TableCell>
                                                    <TableCell>
                                                        <Select defaultValue={device.expectedVersion}>
                                                            <SelectTrigger className="w-32 h-8 bg-muted/30 border-border/50">
                                                                <SelectValue />
                                                            </SelectTrigger>
                                                            <SelectContent className="bg-white">
                                                                <SelectItem value="v2.1.5">v2.1.5</SelectItem>
                                                                <SelectItem value="v2.1.4">v2.1.4</SelectItem>
                                                                <SelectItem value="v2.1.3">v2.1.3</SelectItem>
                                                            </SelectContent>
                                                        </Select>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>

                                <div className="flex justify-center gap-4 mt-6">
                                    <Button className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">Push Firmware Update</Button>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>

            {/* Firmware Update Modal */}
            <Dialog open={editFirmwareOpen} onOpenChange={setEditFirmwareOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col [&>button]:hidden shadow-2xl rounded-[4px]">
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
                                    <option>Intellihub</option>
                                    <option>AirQ</option>
                                    <option>Mikos</option>
                                    <option>Kleio</option>
                                </select>
                                <X className="absolute right-3 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400 pointer-events-none rotate-0" style={{ display: 'none' }} />
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Firmware Version <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="1.1.5" className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm outline-none rounded-sm" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-4">Release Notes <span className="text-red-500">*</span></Label>
                            <textarea rows={3} className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none resize-none"></textarea>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">CRC Value <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="N/A" className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm outline-none rounded-sm" />
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8 border-t border-gray-100 pt-6 mt-2">
                        <Button variant="outline" className="text-red-500 border-red-400 hover:bg-red-50 hover:text-red-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFirmwareOpen(false)}>Close</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFirmwareOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Firmware Delete Modal */}
            <Dialog open={deleteFirmwareOpen} onOpenChange={setDeleteFirmwareOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col [&>button]:hidden shadow-2xl rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Firmware Delete</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setDeleteFirmwareOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-12 space-y-7">
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Reason for Deletion <span className="text-red-500">*</span></Label>
                            <textarea rows={4} className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none resize-none"></textarea>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8 border-t border-gray-100 pt-6 mt-2">
                        <Button variant="outline" className="text-red-500 border-red-400 hover:bg-red-50 hover:text-red-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setDeleteFirmwareOpen(false)}>Close</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setDeleteFirmwareOpen(false)}>Update</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </>
    );
};

export default FirmwareManagement;
