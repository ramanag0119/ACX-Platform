import { useState } from "react";
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
import { Pencil, Trash2, X, Edit } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";

// Sample holidays data
const initialHolidaysData = [
    { id: "1", startDate: "28-10-2024", endDate: "05-11-2024", lockMessage: "Diwali Holiday", description: "test test test" },
    { id: "2", startDate: "15-08-2024", endDate: "18-08-2024", lockMessage: "test1", description: "test1" },
    { id: "3", startDate: "01-08-2024", endDate: "07-08-2024", lockMessage: "test", description: "test" },
    { id: "4", startDate: "11-05-2023", endDate: "28-05-2023", lockMessage: "Happy Holidays", description: "Vacation leave" },
    { id: "5", startDate: "20-04-2023", endDate: "30-04-2023", lockMessage: "holidays", description: "holiday" },
    { id: "6", startDate: "15-02-2023", endDate: "16-02-2023", lockMessage: "we are closed", description: "testing" },
];

const Holidays = () => {
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [lockMessage, setLockMessage] = useState("");
    const [description, setDescription] = useState("");
    const [editingId, setEditingId] = useState<string | null>(null);
    const [errors, setErrors] = useState<{ startDate?: string; endDate?: string; lockMessage?: string; description?: string; }>({});
    const [holidaysData, setHolidaysData] = useState(initialHolidaysData);
    const [search, setSearch] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    const [editModalOpen, setEditModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);

    const validateForm = () => {
        const newErrors: typeof errors = {};
        if (!startDate) newErrors.startDate = "Start Date is required";
        if (!endDate) newErrors.endDate = "End Date is required";
        if (!lockMessage.trim()) newErrors.lockMessage = "Lock message is required";
        if (!description.trim()) newErrors.description = "Description is required";
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const formatDate = (dateString: string) => {
        if (!dateString) return "";
        const date = new Date(dateString);
        return `${String(date.getDate()).padStart(2, '0')}-${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`;
    };

    const handleSubmit = () => {
        if (!validateForm()) return;
        if (editingId) {
            setHolidaysData(prev => prev.map(item => item.id === editingId ? { ...item, startDate: formatDate(startDate), endDate: formatDate(endDate), lockMessage, description } : item));
            setEditingId(null);
        } else {
            setHolidaysData(prev => [{ id: String(Date.now()), startDate: formatDate(startDate), endDate: formatDate(endDate), lockMessage, description }, ...prev]);
        }
        handleReset();
    };

    const handleReset = () => { setStartDate(""); setEndDate(""); setLockMessage(""); setDescription(""); setErrors({}); setEditingId(null); };

    const handleEdit = (item: typeof initialHolidaysData[0]) => {
        setEditingId(item.id);
        const [d, m, y] = item.startDate.split('-');
        setStartDate(`${y}-${m}-${d}`);
        const [ed, em, ey] = item.endDate.split('-');
        setEndDate(`${ey}-${em}-${ed}`);
        setLockMessage(item.lockMessage);
        setDescription(item.description);
    };

    const handleDelete = (id: string) => { setHolidaysData(prev => prev.filter(item => item.id !== id)); };

    const filteredData = holidaysData.filter(item => item.lockMessage.toLowerCase().includes(search.toLowerCase()) || item.description.toLowerCase().includes(search.toLowerCase()));
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, startIndex + parseInt(entriesPerPage));

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Holidays Management</h1>
            </div>

            {/* Add Form */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <h2 className="text-lg font-semibold mb-6">Add Holidays</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
                        <div className="space-y-2">
                            <Label>Start Date<span className="text-red-500">*</span></Label>
                            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-muted/30 border-border/50" />
                            {errors.startDate && <p className="text-red-500 text-xs">{errors.startDate}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label>End Date<span className="text-red-500">*</span></Label>
                            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-muted/30 border-border/50" />
                            {errors.endDate && <p className="text-red-500 text-xs">{errors.endDate}</p>}
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>Lock message<span className="text-red-500">*</span></Label>
                            <Input value={lockMessage} onChange={(e) => setLockMessage(e.target.value)} placeholder="This message will be shown on the lock screen" className="bg-muted/30 border-border/50" />
                            {errors.lockMessage && <p className="text-red-500 text-xs">{errors.lockMessage}</p>}
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>Description<span className="text-red-500">*</span></Label>
                            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Enter description" className="bg-muted/30 border-border/50 min-h-[100px]" />
                            {errors.description && <p className="text-red-500 text-xs">{errors.description}</p>}
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 mt-6">
                        <Button variant="outline" onClick={handleReset} className="px-8">Reset</Button>
                        <Button onClick={handleSubmit} className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">{editingId ? "Update" : "Submit"}</Button>
                    </div>
                </CardContent>
            </Card>

            {/* Table */}
            <Card className="border-0 shadow-xl">
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
                            <Input placeholder="lock message" value={search} onChange={(e) => setSearch(e.target.value)} className="w-64 h-9 bg-muted/30 border-border/50" />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Start Date</TableHead>
                                    <TableHead className="text-gray-600 font-medium">End Date</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Lock message</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                        <TableCell>{item.startDate}</TableCell>
                                        <TableCell>{item.endDate}</TableCell>
                                        <TableCell className="text-cyan-600">{item.lockMessage}</TableCell>
                                        <TableCell>{item.description}</TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex gap-2 justify-center">
                                                <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditModalOpen(true)}>
                                                    <Edit className="h-[14px] w-[14px]" />
                                                </Button>
                                                <Button size="sm" className="bg-[#d33] hover:bg-[#bd2d2d] text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setDeleteModalOpen(true)}>
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
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Edit Holiday Modal */}
            <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
                <DialogContent className="max-w-[600px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Holiday</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditModalOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-6">
                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Start Date <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="29-10-2024"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">End Date <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="05-11-2024"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Lock message <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="Diwali Holiday"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-start gap-4 h-24 pt-2">
                            <Label className="text-sm font-medium text-gray-800 pt-1">Description <span className="text-red-500">*</span></Label>
                            <textarea
                                defaultValue="test test test"
                                className="w-full h-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 text-sm outline-none resize-none pt-1"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Reset</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Modal */}
            <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
                <DialogContent className="max-w-[400px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[8px]">
                    <div className="p-10 flex flex-col items-center text-center space-y-5">
                        <div className="h-[84px] w-[84px] rounded-full border-[4px] border-[#facea8] flex items-center justify-center">
                            <div className="text-[#f8bb86] text-[56px] leading-none font-light mb-2">!</div>
                        </div>
                        <div className="space-y-2 mt-2">
                            <h2 className="text-[26px] font-semibold text-[#545454]">Are you sure?</h2>
                            <p className="text-[16px] text-[#545454]">You won't be able to revert this!</p>
                        </div>

                        <div className="flex gap-2.5 justify-center pt-2">
                            <Button className="bg-[#3085d6] hover:bg-[#2b78c1] text-white text-[15px] font-medium px-4 py-2 rounded-[4px] h-[40px]" onClick={() => setDeleteModalOpen(false)}>Yes, delete it!</Button>
                            <Button className="bg-[#d33] hover:bg-[#bd2d2d] text-white text-[15px] font-medium px-4 py-2 rounded-[4px] h-[40px]" onClick={() => setDeleteModalOpen(false)}>Cancel</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Holidays;
