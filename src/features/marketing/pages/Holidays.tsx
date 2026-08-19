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
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Holidays Management</h1>
            </div>

            {/* Add Form */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                <CardContent className="p-6">
                    <h2 className="text-base font-semibold mb-6 text-foreground">Add Holidays</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
                        <div className="space-y-2">
                            <Label>Start Date<span className="text-red-500">*</span></Label>
                            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-muted/20 border-border dark:border-slate-700/80" />
                            {errors.startDate && <p className="text-red-500 text-xs">{errors.startDate}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label>End Date<span className="text-red-500">*</span></Label>
                            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-muted/20 border-border dark:border-slate-700/80" />
                            {errors.endDate && <p className="text-red-500 text-xs">{errors.endDate}</p>}
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>Lock message<span className="text-red-500">*</span></Label>
                            <Input value={lockMessage} onChange={(e) => setLockMessage(e.target.value)} placeholder="This message will be shown on the lock screen" className="bg-muted/20 border-border dark:border-slate-700/80" />
                            {errors.lockMessage && <p className="text-red-500 text-xs">{errors.lockMessage}</p>}
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>Description<span className="text-red-500">*</span></Label>
                            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Enter description" className="bg-muted/20 border-border dark:border-slate-700/80 min-h-[100px]" />
                            {errors.description && <p className="text-red-500 text-xs">{errors.description}</p>}
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 mt-6">
                        <Button variant="outline" onClick={handleReset} className="px-8 border-border hover:bg-muted">Reset</Button>
                        <Button onClick={handleSubmit} className="bg-[#5865F2] hover:bg-[#4752c4] text-white px-8 rounded-xl font-semibold shadow-md">{editingId ? "Update" : "Submit"}</Button>
                    </div>
                </CardContent>
            </Card>

            {/* Table */}
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
                            <Input placeholder="Lock message, description" value={search} onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }} className="w-64 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60" />
                        </div>
                    </div>

                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Start Date</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">End Date</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Lock message</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Description</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.length > 0 ? (
                                    paginatedData.map((item, index) => (
                                        <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.startDate}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.endDate}</TableCell>
                                            <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 font-medium">{item.lockMessage}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.description}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <div className="flex gap-2 justify-center">
                                                    <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-md" onClick={() => setEditModalOpen(true)}>
                                                        <Edit className="h-3.5 w-3.5" />
                                                    </Button>
                                                    <Button size="sm" className="bg-[#d33] hover:bg-[#bd2d2d] text-white h-7 w-7 p-0 rounded-md" onClick={() => setDeleteModalOpen(true)}>
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center py-6 text-muted-foreground text-xs">
                                            No holidays found {search ? `matching "${search}"` : ""}
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
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
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
