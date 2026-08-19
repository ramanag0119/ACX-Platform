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
import { Pencil, Printer, Trash2 } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog,
    DialogContent,
} from "@/components/ui/dialog";

// Sample Job Orders Data
const jobOrdersData = [
    { id: "241", description: "211 room setup 2025", workPurchaseOrder: "211 config", roomsDevices: "View rooms & devices", typeOfWork: "Replacement", workCommence: "16-10-2025", estimateCompleteDate: "16-10-2025" },
    { id: "242", description: "211 room setup 2025", workPurchaseOrder: "211 config", roomsDevices: "View rooms & devices", typeOfWork: "Replacement", workCommence: "16-10-2025", estimateCompleteDate: "16-10-2025" },
    { id: "243", description: "211 2025 setup", workPurchaseOrder: "211 config", roomsDevices: "View rooms & devices", typeOfWork: "Replacement", workCommence: "16-10-2025", estimateCompleteDate: "16-10-2025" },
    { id: "240", description: "Mikos installation", workPurchaseOrder: "mikos installation", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "06-12-2024", estimateCompleteDate: "06-12-2024" },
    { id: "239", description: "111 hub,Mikos,Airq,Kleio", workPurchaseOrder: "111 Configuration", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "23-11-2024", estimateCompleteDate: "23-11-2024" },
    { id: "238", description: "Hub install for 3001", workPurchaseOrder: "installation", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "21-11-2024", estimateCompleteDate: "21-11-2024" },
    { id: "237", description: "install", workPurchaseOrder: "5001hub", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "13-11-2024", estimateCompleteDate: "13-11-2024" },
    { id: "236", description: "installation", workPurchaseOrder: "kleio installation", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "12-11-2024", estimateCompleteDate: "12-11-2024" },
    { id: "235", description: "Demo box installation", workPurchaseOrder: "installation", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "05-11-2024", estimateCompleteDate: "06-11-2024" },
    { id: "234", description: "Install", workPurchaseOrder: "412Mikos", roomsDevices: "View rooms & devices", typeOfWork: "Installation", workCommence: "28-10-2024", estimateCompleteDate: "28-10-2024" },
];

// Room options
const roomOptions = [
    { id: "101", name: "Room 101" },
    { id: "102", name: "Room 102" },
    { id: "103", name: "Room 103" },
    { id: "104", name: "Room 104" },
    { id: "105", name: "Room 105" },
    { id: "201", name: "Room 201" },
    { id: "202", name: "Room 202" },
    { id: "301", name: "Room 301" },
];

// Caleido Network options
const caleidoNetworkOptions = [
    { id: "1", name: "Hub" },
    { id: "2", name: "Mikos" },
    { id: "3", name: "Airq" },
    { id: "4", name: "Kleio" },
    { id: "5", name: "Tab" },
    { id: "6", name: "Gateway" },
];

type TabType = "create-job" | "job-orders";

const JobOrder = () => {
    const [activeTab, setActiveTab] = useState<TabType>("create-job");

    // Create Job form state
    const [workPurchaseRef, setWorkPurchaseRef] = useState("");
    const [typeOfWork, setTypeOfWork] = useState("fresh-installation");
    const [jobDescription, setJobDescription] = useState("");
    const [workCommence, setWorkCommence] = useState("");
    const [estimateCompleteDate, setEstimateCompleteDate] = useState("");
    const [selectedRoom, setSelectedRoom] = useState("");
    const [selectedCaleidoNetwork, setSelectedCaleidoNetwork] = useState("");
    const [addedRooms, setAddedRooms] = useState<{ room: string; network: string }[]>([]);

    // Job Orders table state
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    type JobOrderItem = typeof jobOrdersData[number];
    const [selectedJob, setSelectedJob] = useState<JobOrderItem | null>(null);

    const handleEditClick = (job: JobOrderItem) => {
        setSelectedJob(job);
        setIsEditModalOpen(true);
    };

    // Filter job orders
    const filteredJobOrders = jobOrdersData.filter(item =>
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.workPurchaseOrder.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(filteredJobOrders.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const endIndex = startIndex + parseInt(entriesPerPage);
    const paginatedJobOrders = filteredJobOrders.slice(startIndex, endIndex);

    const handleAddRoom = () => {
        if (selectedRoom && selectedCaleidoNetwork) {
            setAddedRooms([...addedRooms, { room: selectedRoom, network: selectedCaleidoNetwork }]);
            setSelectedRoom("");
            setSelectedCaleidoNetwork("");
        }
    };

    const handleRemoveRoom = (index: number) => {
        setAddedRooms(addedRooms.filter((_, i) => i !== index));
    };

    const handleSubmit = () => {
        console.log("Job Order Submit:", {
            workPurchaseRef,
            typeOfWork,
            jobDescription,
            workCommence,
            estimateCompleteDate,
            addedRooms
        });
    };

    const tabs = [
        { id: "create-job" as TabType, label: "Create Job" },
        { id: "job-orders" as TabType, label: "Job Orders" },
    ];

    const renderCreateJobTab = () => (
        <div className="space-y-6">
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                <CardContent className="p-6">
                    <div className="space-y-6">
                        {/* Work/Purchase Order Reference */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Work/Purchase Order Reference</Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Work/Purchase Order Reference"
                                    value={workPurchaseRef}
                                    onChange={(e) => setWorkPurchaseRef(e.target.value)}
                                    className="bg-muted/20 border-border dark:border-slate-700/80"
                                />
                            </div>
                        </div>

                        {/* Type Of Work */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Type Of Work<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <RadioGroup value={typeOfWork} onValueChange={setTypeOfWork} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="fresh-installation" id="fresh-installation" />
                                        <Label htmlFor="fresh-installation" className="text-cyan-600 cursor-pointer">Fresh Installation</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="replacement" id="replacement" />
                                        <Label htmlFor="replacement" className="cursor-pointer">Replacement</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Job Description */}
                        <div className="grid grid-cols-3 gap-4 items-start">
                            <Label className="text-sm font-medium text-right pt-2">Job Description<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Textarea
                                    placeholder="Enter Job Description"
                                    value={jobDescription}
                                    onChange={(e) => setJobDescription(e.target.value)}
                                    className="bg-muted/20 border-border dark:border-slate-700/80 min-h-[80px]"
                                />
                            </div>
                        </div>

                        {/* Work Commence */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Work Commence<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    type="date"
                                    value={workCommence}
                                    onChange={(e) => setWorkCommence(e.target.value)}
                                    className="bg-muted/20 border-border dark:border-slate-700/80"
                                />
                            </div>
                        </div>

                        {/* Estimate Complete Date */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Estimate Complete Date<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    type="date"
                                    value={estimateCompleteDate}
                                    onChange={(e) => setEstimateCompleteDate(e.target.value)}
                                    className="bg-muted/20 border-border dark:border-slate-700/80"
                                />
                            </div>
                        </div>

                        {/* Rooms */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Rooms<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={selectedRoom} onValueChange={setSelectedRoom}>
                                    <SelectTrigger className="bg-muted/20 border-border dark:border-slate-700/80">
                                        <SelectValue placeholder="Select Rooms" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover text-popover-foreground border-border">
                                        {roomOptions.map(room => (
                                            <SelectItem key={room.id} value={room.name}>{room.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Caleido Network */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Caleido Network<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={selectedCaleidoNetwork} onValueChange={setSelectedCaleidoNetwork}>
                                    <SelectTrigger className="bg-muted/20 border-border dark:border-slate-700/80">
                                        <SelectValue placeholder="Select Caleido Network" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover text-popover-foreground border-border">
                                        {caleidoNetworkOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            caleidoNetworkOptions.map(network => (
                                                <SelectItem key={network.id} value={network.name}>{network.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Add Button */}
                        <div className="flex justify-center">
                            <Button onClick={handleAddRoom} className="h-10 px-8 min-w-[120px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                                Add
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Added Rooms Table */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                <CardContent className="p-6">
                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Rooms</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Caleido Network</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {addedRooms.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center text-muted-foreground text-xs py-6">
                                            No rooms added yet. Select a room and network above.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    addedRooms.map((item, index) => (
                                        <TableRow key={index} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.room}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.network}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <Button size="sm" onClick={() => handleRemoveRoom(index)} className="bg-red-500 hover:bg-red-600 h-7 w-7 p-0 rounded-md">
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Submit Button */}
                    <div className="flex justify-center mt-6">
                        <Button onClick={handleSubmit} className="h-10 px-12 min-w-[140px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderJobOrdersTab = () => (
        <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
            <CardContent className="p-5">
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
                            </SelectContent>
                        </Select>
                        <span className="text-muted-foreground text-xs font-medium">entries</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-muted-foreground text-xs font-medium">Search:</span>
                        <Input
                            placeholder="Job ID, Work/Purchase order, Room no"
                            value={searchQuery}
                            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                            className="w-72 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                        />
                    </div>
                </div>

                <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Job ID</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Job Description</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Work/Purchase Order</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Rooms & devices</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Type of Work</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Work Commence</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Estimate Completion Date</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Printout</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedJobOrders.length > 0 ? (
                                paginatedJobOrders.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                        <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 font-medium whitespace-nowrap">{item.id}</TableCell>
                                        <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 hover:underline cursor-pointer whitespace-nowrap">{item.description}</TableCell>
                                        <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.workPurchaseOrder}</TableCell>
                                        <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 hover:underline cursor-pointer whitespace-nowrap">{item.roomsDevices}</TableCell>
                                        <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.typeOfWork}</TableCell>
                                        <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.workCommence}</TableCell>
                                        <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.estimateCompleteDate}</TableCell>
                                        <TableCell className="text-center py-3 px-4">
                                            <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700 h-7 w-7 p-0 rounded-md" onClick={() => handleEditClick(item)}>
                                                <Pencil className="h-3.5 w-3.5 text-white" />
                                            </Button>
                                        </TableCell>
                                        <TableCell className="text-center py-3 px-4">
                                            <Button size="sm" className="bg-amber-500 hover:bg-amber-600 h-7 w-7 p-0 rounded-md">
                                                <Printer className="h-3.5 w-3.5 text-white" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={9} className="text-center py-6 text-muted-foreground text-xs">
                                        No job orders found {searchQuery ? `matching "${searchQuery}"` : ""}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
                    <span className="text-muted-foreground text-xs">
                        Showing {filteredJobOrders.length > 0 ? startIndex + 1 : 0} to {Math.min(endIndex, filteredJobOrders.length)} of {filteredJobOrders.length} entries
                    </span>
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                        <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                            <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                        ))}
                        <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                        <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Job Order Management</h1>
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

            {/* Content */}
            {activeTab === "create-job" && renderCreateJobTab()}
            {activeTab === "job-orders" && renderJobOrdersTab()}

            <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
                <DialogContent className="max-w-[1000px] w-[90vw] bg-white text-foreground border-gray-200 p-0 overflow-hidden flex flex-col hide-close-button shadow-lg [&>button]:hidden">
                    <div className="flex justify-between items-center p-3 px-6 bg-gray-50 border-b border-gray-200">
                        <h2 className="text-base font-medium">Job Order Management</h2>
                        <Button variant="destructive" className="bg-[#f2716b] hover:bg-red-500 h-8 px-6 font-normal" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
                    </div>

                    <div className="px-10 py-8 space-y-6 overflow-y-auto max-h-[85vh]">
                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Work/Purchase Order Reference <span className="text-red-500">*</span></Label>
                            <Input placeholder="Enter Work/Purchase Order Reference" className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl" />
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Type Of Work <span className="text-red-500">*</span></Label>
                            <RadioGroup defaultValue="fresh-installation" className="flex gap-4">
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="fresh-installation" id="modal-fresh" className="border-gray-400 text-cyan-600 h-3 w-3" />
                                    <Label htmlFor="modal-fresh" className="text-foreground font-medium text-sm cursor-pointer">Fresh Installation</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="replacement" id="modal-repl" className="border-gray-400 text-gray-400 h-3 w-3" />
                                    <Label htmlFor="modal-repl" className="text-foreground font-medium text-sm cursor-pointer">Replacement</Label>
                                </div>
                            </RadioGroup>
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Job Description <span className="text-red-500">*</span></Label>
                            <Input placeholder="Enter Job Description" className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8" />
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center pt-8">
                            <Label className="text-sm font-medium text-gray-700">Work Commence <span className="text-red-500">*</span></Label>
                            <Input type="text" placeholder="dd-mm-yyyy" className="bg-white border border-gray-300 text-foreground rounded-sm h-8 max-w-2xl px-3" />
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Estimate Complete Date <span className="text-red-500">*</span></Label>
                            <Input type="text" placeholder="dd-mm-yyyy" className="bg-white border border-gray-300 text-foreground rounded-sm h-8 max-w-2xl px-3" />
                        </div>

                        <div className="border border-gray-200 rounded-md px-6 py-8 mt-6">
                            <div className="space-y-6">
                                <div className="grid grid-cols-[212px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-700">Rooms <span className="text-red-500">*</span></Label>
                                    <Select>
                                        <SelectTrigger className="bg-white border-gray-300 text-foreground w-full h-8 rounded-sm text-xs">
                                            <SelectValue placeholder="" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="101">Room 101</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="grid grid-cols-[212px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-700">Caleido Network <span className="text-red-500">*</span></Label>
                                    <Select>
                                        <SelectTrigger className="bg-white border-gray-300 text-foreground w-full h-8 rounded-sm text-xs">
                                            <SelectValue placeholder="Select Caleido Network" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="hub">Hub</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="flex justify-center pt-4">
                                    <Button className="h-9 px-6 rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-xs shadow-md hover:shadow-lg transition-all border-0">Add Job</Button>
                                </div>
                            </div>
                        </div>

                        <div className="mt-8 border border-gray-200 rounded-t-lg overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow className="border-b border-gray-200 bg-gray-50 hover:bg-gray-50">
                                        <TableHead className="text-gray-700 text-center font-bold text-xs h-10">S.No</TableHead>
                                        <TableHead className="text-gray-700 text-center font-bold text-xs h-10">Rooms</TableHead>
                                        <TableHead className="text-gray-700 text-center font-bold text-xs h-10">Caleido Network</TableHead>
                                        <TableHead className="text-gray-700 text-center font-bold text-xs h-10">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    <TableRow className="border-0 hover:bg-transparent">
                                        <TableCell colSpan={4} className="h-8"></TableCell>
                                    </TableRow>
                                </TableBody>
                            </Table>
                        </div>

                        <div className="flex justify-center mt-2 pb-4">
                            <Button className="h-10 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all border-0">Update</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default JobOrder;




