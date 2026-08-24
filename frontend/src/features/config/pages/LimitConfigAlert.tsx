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
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Pencil, Trash2 } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

// Parameter options
const parameterOptions = [
    { id: "1", name: "Voltage" },
    { id: "2", name: "Current" },
    { id: "3", name: "Power" },
    { id: "4", name: "Energy 5 mnts" },
    { id: "5", name: "Energy 24 hrs" },
];

// Device Name options
const deviceNameOptions = [
    { id: "1", name: "102MIK01 - Refridge" },
    { id: "2", name: "105MIK01" },
    { id: "3", name: "109MIK01" },
    { id: "4", name: "401MIK01" },
    { id: "5", name: "303MIK01" },
    { id: "6", name: "101MIK01" },
    { id: "7", name: "201HUB01" },
    { id: "8", name: "201MIK01" },
    { id: "9", name: "411HUB01" },
    { id: "10", name: "411MIK01" },
    { id: "11", name: "402MIK01 - CXPL" },
    { id: "12", name: "221HUB01" },
    { id: "13", name: "221MIK01" },
    { id: "14", name: "307MIK01" },
    { id: "15", name: "211HUB01 - Hub" },
    { id: "16", name: "211MIK01 - Mikos" },
    { id: "17", name: "3003MIK01 - Cxpl" },
];

// Sample data (empty initially)
const limitConfigData: any[] = [];

const LimitConfigAlert = () => {
    // Form state
    const [parameter, setParameter] = useState("");
    const [deviceName, setDeviceName] = useState("");
    const [limitCheck, setLimitCheck] = useState("yes");
    const [limitBy, setLimitBy] = useState("percentage");
    const [nominal, setNominal] = useState("");
    const [limitLow, setLimitLow] = useState("");
    const [limitHigh, setLimitHigh] = useState("");
    const [comments, setComments] = useState("");

    // Table state
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    // Filter data
    const filteredData = limitConfigData.filter(item =>
        item.deviceName?.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const endIndex = startIndex + parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, endIndex);

    const handleReset = () => {
        setParameter("");
        setDeviceName("");
        setLimitCheck("yes");
        setLimitBy("percentage");
        setNominal("");
        setLimitLow("");
        setLimitHigh("");
        setComments("");
    };

    const handleSubmit = () => {
        console.log("Limit Config Alert Submit:", {
            parameter,
            deviceName,
            limitCheck,
            limitBy,
            nominal,
            limitLow,
            limitHigh,
            comments
        });
    };

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Limit Config Alert</h1>
            </div>

            {/* Form Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="space-y-6">
                        {/* Parameter */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Parameter<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={parameter} onValueChange={setParameter}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Parameter" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {parameterOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            parameterOptions.map(param => (
                                                <SelectItem key={param.id} value={param.name}>{param.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Device Name */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Device Name<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={deviceName} onValueChange={setDeviceName}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Device Name" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {deviceNameOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            deviceNameOptions.map(device => (
                                                <SelectItem key={device.id} value={device.name}>{device.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Limit Check */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit Check</Label>
                            <div className="col-span-2">
                                <RadioGroup value={limitCheck} onValueChange={setLimitCheck} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="yes" id="limit-check-yes" />
                                        <Label htmlFor="limit-check-yes" className="cursor-pointer">Yes</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="no" id="limit-check-no" />
                                        <Label htmlFor="limit-check-no" className="cursor-pointer">No</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Limit By */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit By</Label>
                            <div className="col-span-2">
                                <RadioGroup value={limitBy} onValueChange={setLimitBy} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="percentage" id="limit-by-percentage" />
                                        <Label htmlFor="limit-by-percentage" className="cursor-pointer">Percentage</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="limit-value" id="limit-by-value" />
                                        <Label htmlFor="limit-by-value" className="cursor-pointer">Limit Value</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Nominal */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Nominal<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Nominal"
                                    value={nominal}
                                    onChange={(e) => setNominal(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Limit Low (%) */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit Low (%)<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Limit Low"
                                    value={limitLow}
                                    onChange={(e) => setLimitLow(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Limit High (%) */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit High (%)<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Limit High"
                                    value={limitHigh}
                                    onChange={(e) => setLimitHigh(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Comments/Remarks */}
                        <div className="grid grid-cols-3 gap-4 items-start">
                            <Label className="text-sm font-medium text-right pt-2">Comments/Remarks</Label>
                            <div className="col-span-2">
                                <Textarea
                                    placeholder="Enter Your Remarks"
                                    value={comments}
                                    onChange={(e) => setComments(e.target.value)}
                                    className="bg-muted/30 border-border/50 min-h-[80px]"
                                />
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex justify-center gap-4">
                            <Button onClick={handleReset} variant="outline" className="px-8 border-red-500 text-red-500 hover:bg-red-50">
                                Reset
                            </Button>
                            <Button onClick={handleSubmit} className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">
                                Submit
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
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
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input
                                placeholder="Device Name"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-64 h-9 bg-muted/30 border-border/50"
                            />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Parameter ◆</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Device Name ◆</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Limit Check</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Limit By</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Nominal</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Limit Low (%)</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Limit High (%)</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Limit Low Value</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Limit High Value</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                                            No data available in table
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    paginatedData.map((item, index) => (
                                        <TableRow key={index} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}>
                                            <TableCell className="whitespace-nowrap">{item.parameter}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.deviceName}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.limitCheck}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.limitBy}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.nominal}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.limitLow}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.limitHigh}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.limitLowValue}</TableCell>
                                            <TableCell className="whitespace-nowrap">{item.limitHighValue}</TableCell>
                                            <TableCell className="text-center">
                                                <div className="flex gap-2 justify-center">
                                                    <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700 h-8 w-8 p-0">
                                                        <Pencil className="h-4 w-4" />
                                                    </Button>
                                                    <Button size="sm" className="bg-red-500 hover:bg-red-600 h-8 w-8 p-0">
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing {startIndex} to {Math.min(endIndex, filteredData.length)} of {filteredData.length} entries
                        </span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${currentPage === page ? "bg-primary text-white" : "text-muted-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            {totalPages > 5 && <span className="text-muted-foreground px-2">...</span>}
                            {totalPages > 5 && (
                                <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)}>{totalPages}</Button>
                            )}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default LimitConfigAlert;




