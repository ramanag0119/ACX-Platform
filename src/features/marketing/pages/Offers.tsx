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
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Pencil, Trash2, Hourglass } from "lucide-react";

// Sample Offers Data
const offersData = [
    { id: "1", offerName: "Pooja Offer", applicableTo: "101, 102, 103, 104, 105...", couponCode: "pooja45", couponDescription: "test", offerBy: "abc", validityFrom: "06-10-2024", validityTo: "17-10-2024", image: "-" },
    { id: "2", offerName: "Oct 2", applicableTo: "101, 102, 103, 104, 105...", couponCode: "20 on 2", couponDescription: "Test", offerBy: "aaa", validityFrom: "01-10-2024", validityTo: "02-10-2024", image: "-" },
    { id: "3", offerName: "test", applicableTo: "101, 102, 103, 104, 105...", couponCode: "25", couponDescription: "discount", offerBy: "test", validityFrom: "30-09-2024", validityTo: "02-10-2024", image: "-" },
    { id: "4", offerName: "ROLEX offer", applicableTo: "101, 102, 103, 104, 105...", couponCode: "ROLEX", couponDescription: "Mr. Test", offerBy: "Mr.test", validityFrom: "27-09-2024", validityTo: "31-10-2024", image: "-" },
    { id: "5", offerName: "3rd Anniversary Offer", applicableTo: "101, 102, 103, 104, 105...", couponCode: "0101", couponDescription: "", offerBy: "-", validityFrom: "25-09-2024", validityTo: "25-09-2024", image: "-" },
    { id: "6", offerName: "Test", applicableTo: "101, 102, 103, 104, 105...", couponCode: "10001", couponDescription: "", offerBy: "-", validityFrom: "25-09-2024", validityTo: "28-09-2024", image: "-" },
    { id: "7", offerName: "Sunday Offer", applicableTo: "101, 102, 103, 104, 105...", couponCode: "050505", couponDescription: "", offerBy: "-", validityFrom: "25-09-2024", validityTo: "29-09-2024", image: "-" },
    { id: "8", offerName: "Diwali Offer", applicableTo: "101, 102, 103, 104, 105...", couponCode: "DIWALI2024", couponDescription: "Diwali Offer", offerBy: "-", validityFrom: "24-09-2024", validityTo: "30-11-2024", image: "Click here for image" },
    { id: "9", offerName: "test", applicableTo: "401", couponCode: "123", couponDescription: "Test", offerBy: "test", validityFrom: "18-09-2024", validityTo: "18-09-2024", image: "Click here for image" },
    { id: "10", offerName: "New year offer", applicableTo: "103", couponCode: "NEWYEAR2002", couponDescription: "", offerBy: "-", validityFrom: "18-05-2023", validityTo: "18-05-2023", image: "-" },
];

const roomTypes = ["All", "Golden Package", "Delux Package", "Premium Suite", "Standard Room"];

const Offers = () => {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    // Form state
    const [offerName, setOfferName] = useState("");
    const [selectedRooms, setSelectedRooms] = useState<string[]>([]);
    type OfferItem = typeof offersData[number];
    const [selectedItemToDelete, setSelectedItemToDelete] = useState<OfferItem | null>(null);
    const [selectedItemToEdit, setSelectedItemToEdit] = useState<OfferItem | null>(null);

    const filteredData = offersData.filter(item =>
        item.offerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.couponCode.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, startIndex + parseInt(entriesPerPage));

    const handleRoomToggle = (roomId: string) => {
        setSelectedRooms(prev => prev.includes(roomId) ? prev.filter(id => id !== roomId) : [...prev, roomId]);
    };

    const handleWithdrawClick = (item: OfferItem) => {
        setSelectedItemToDelete(item);
        setIsDeleteModalOpen(true);
    };

    const handleEditClick = (item: OfferItem) => {
        setSelectedItemToEdit(item);
        setIsEditModalOpen(true);
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Offers Management</h1>
                <Button onClick={() => setIsModalOpen(true)} className="h-10 px-6 rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Add Offers</Button>
            </div>

            {/* Table Section */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
                <CardContent className="p-5">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-xs font-medium">Show</span>
                            <Select value={entriesPerPage} onValueChange={(val) => { setEntriesPerPage(val); setCurrentPage(1); }}>
                                <SelectTrigger className="w-18 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md"><SelectValue /></SelectTrigger>
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
                            <Input placeholder="Offer name, Coupon code" value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }} className="w-64 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60" />
                        </div>
                    </div>

                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Offer Name</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Applicable To</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Coupon Code</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Coupon Description</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Offer By</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Validity From</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Validity To</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap text-center">Offer Withdrawal</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap text-center">Image</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.length > 0 ? (
                                    paginatedData.map((item, index) => (
                                        <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                            <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 whitespace-nowrap font-medium">{item.offerName}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.applicableTo}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90 font-mono">{item.couponCode}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.couponDescription}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.offerBy}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.validityFrom}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.validityTo}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <div className="flex justify-center">
                                                    <Button size="sm" className="h-7 w-7 p-0 bg-brand-teal hover:bg-brand-teal/90 rounded-md" onClick={() => handleWithdrawClick(item)}>
                                                        <Hourglass className="h-3.5 w-3.5 text-white" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                            <TableCell className="whitespace-nowrap text-center py-3 px-4 text-xs">
                                                {item.image !== "-" ? <span className="text-cyan-600 dark:text-cyan-400 hover:underline cursor-pointer">{item.image}</span> : "-"}
                                            </TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <div className="flex gap-2 justify-center">
                                                    <Button size="sm" className="h-7 w-7 p-0 bg-[#f2716b] hover:bg-[#f2716b]/90 rounded-md" onClick={() => handleEditClick(item)}>
                                                        <Pencil className="h-3.5 w-3.5 text-white" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow>
                                        <TableCell colSpan={10} className="text-center py-6 text-muted-foreground text-xs">
                                            No offers found {searchQuery ? `matching "${searchQuery}"` : ""}
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
                        <span className="text-muted-foreground text-xs">Showing {filteredData.length > 0 ? startIndex + 1 : 0} to {Math.min(startIndex + parseInt(entriesPerPage), filteredData.length)} of {filteredData.length} entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Add Offer Modal */}
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader><DialogTitle>Add New Offer</DialogTitle></DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Offer Name<span className="text-red-500">*</span></Label>
                                <Input placeholder="Enter offer name" value={offerName} onChange={(e) => setOfferName(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                            <div className="space-y-2">
                                <Label>Coupon Code<span className="text-red-500">*</span></Label>
                                <Input placeholder="Enter coupon code" className="bg-muted/30 border-border/50" />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Applicable Rooms</Label>
                            <div className="grid grid-cols-3 gap-2">
                                {roomTypes.map((room) => (
                                    <div key={room} className="flex items-center space-x-2">
                                        <Checkbox id={room} checked={selectedRooms.includes(room)} onCheckedChange={() => handleRoomToggle(room)} />
                                        <label htmlFor={room} className="text-sm">{room}</label>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Validity From<span className="text-red-500">*</span></Label>
                                <Input type="date" className="bg-muted/30 border-border/50" />
                            </div>
                            <div className="space-y-2">
                                <Label>Validity To<span className="text-red-500">*</span></Label>
                                <Input type="date" className="bg-muted/30 border-border/50" />
                            </div>
                        </div>
                        <div className="flex justify-center gap-4 pt-4">
                            <Button variant="outline" onClick={() => setIsModalOpen(false)} className="px-8">Reset</Button>
                            <Button onClick={() => setIsModalOpen(false)} className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">Submit</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Withdraw Modal */}
            <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
                <DialogContent className="max-w-[400px] bg-white border-0 shadow-lg [&>button]:hidden sm:rounded-md p-8">
                    <div className="flex flex-col items-center text-center space-y-4">
                        <div className="w-16 h-16 rounded-full border-[3px] border-[#f8bb86] text-[#f8bb86] flex items-center justify-center text-5xl font-light font-serif">
                            !
                        </div>
                        <h2 className="text-2xl font-semibold text-[#545454]">Are you sure?</h2>
                        <p className="text-[#545454] text-[15px]">You won't be able to revert this!</p>

                        <div className="flex gap-4 pt-4 w-full justify-center">
                            <Button className="bg-[#3085d6] hover:bg-[#3085d6]/90 text-white px-5 rounded-md text-base shadow-md h-11" onClick={() => setIsDeleteModalOpen(false)}>
                                Yes, delete it!
                            </Button>
                            <Button className="bg-brand-danger hover:bg-brand-danger/90 text-white px-5 rounded-md text-base shadow-md h-11" onClick={() => setIsDeleteModalOpen(false)}>
                                Cancel
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Action Modal */}
            <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
                <DialogContent className="max-w-[1000px] w-[90vw] bg-white text-foreground border-gray-200 p-0 overflow-hidden flex flex-col hide-close-button shadow-lg [&>button]:hidden">
                    <div className="flex justify-between items-center p-3 px-6 bg-gray-50 border-b border-gray-200">
                        <h2 className="text-base font-medium text-foreground">Offers Management</h2>
                        <Button variant="destructive" className="bg-[#f2716b] hover:bg-red-500 h-8 px-6 font-normal rounded-md" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
                    </div>

                    <div className="px-10 py-8 space-y-6 overflow-y-auto max-h-[85vh]">
                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Offer Name <span className="text-red-500">*</span></Label>
                            <div className="text-sm font-medium text-gray-900 border-b border-gray-300 pb-1 w-full max-w-2xl h-8 pt-1.5">Pooja Offer</div>
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Applicable To <span className="text-red-500">*</span></Label>
                            <div className="border border-gray-300 rounded-sm p-1.5 flex flex-wrap gap-2 items-center bg-white min-h-[36px] max-w-2xl">
                                {[101, 102, 103].map(room => (
                                    <div key={room} className="bg-brand-teal text-white text-xs px-2 py-0.5 rounded-sm flex items-center">
                                        {room} <span className="ml-1 cursor-pointer hover:text-white/80">×</span>
                                    </div>
                                ))}
                                <div className="text-xs text-gray-500 ml-auto">+36</div>
                                <div className="border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[6px] border-t-gray-400 ml-1"></div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Coupon Code <span className="text-red-500">*</span></Label>
                            <Input value="pooja45" readOnly className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium" />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Coupon Description</Label>
                            <Input value="test" readOnly className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium" />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Offer By</Label>
                            <Input value="abc" readOnly className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium" />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-4">
                            <Label className="text-sm font-medium text-gray-700">Validity From <span className="text-red-500">*</span></Label>
                            <Input type="text" value="06-10-2024" readOnly className="bg-white text-foreground border border-gray-300 rounded-sm h-9 max-w-[calc(100%-400px)] px-3 font-medium" />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Validity To <span className="text-red-500">*</span></Label>
                            <Input type="text" value="17-10-2024" readOnly className="bg-white text-foreground border border-gray-300 rounded-sm h-9 max-w-[calc(100%-400px)] px-3 font-medium" />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-4">
                            <Label className="text-sm font-medium text-gray-700">Image</Label>
                            <div className="flex items-center gap-2 border-b border-gray-300 pb-1 w-full max-w-2xl">
                                <Button size="sm" variant="outline" className="h-7 bg-white text-foreground hover:bg-gray-50 rounded-sm text-xs px-3 font-medium border-gray-300">Choose file</Button>
                                <span className="text-xs text-gray-500">No file chosen</span>
                            </div>
                        </div>

                        <div className="flex justify-center mt-10 gap-4">
                            <Button variant="outline" className="bg-white hover:bg-gray-50 text-gray-600 border-gray-300 h-9 px-8 rounded-sm font-medium transition-colors">Reset</Button>
                            <Button className="bg-cyan-600 hover:bg-cyan-700 text-white border-transparent h-9 px-8 rounded-sm font-medium transition-colors">Update</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Offers;
