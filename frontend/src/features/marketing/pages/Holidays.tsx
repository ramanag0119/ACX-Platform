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
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { useHolidays, useOccasionTypes } from "@/lib/api/hooks";
import { useCreateHoliday, useUpdateHoliday } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

// Sample holidays data
/**
 * Holidays, connected to GET/POST/PATCH /holidays (`occasion`).
 *
 * `occasion_type` is the seeded lookup (Birthday, Festival, Holiday, Marriage
 * anniversary). `month` and `day_of_month` are NOT NULL and are derived from the
 * start date by the backend, which is what makes a repeatable occasion recur --
 * so the form asks for the date once.
 */

const Holidays = () => {
    const holidaysQuery = useHolidays({ page: 1, page_size: MAX_PAGE_SIZE });
    const typesQuery = useOccasionTypes();
    const { canWrite } = useAuth();
    const mayWrite = canWrite("holidays");
    const createHoliday = useCreateHoliday();
    const updateHoliday = useUpdateHoliday();

    const initialHolidaysData = (holidaysQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        startDate: row.occasion_start_date,
        endDate: row.occasion_end_date ?? "-",
        lockMessage: row.occasion_name ?? row.occasion_type_name ?? "-",
        description: row.occasion_type_name ?? "-",
    }));
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [lockMessage, setLockMessage] = useState("");
    const [description, setDescription] = useState("");
    const [editingId, setEditingId] = useState<string | null>(null);
    const [errors, setErrors] = useState<{ startDate?: string; endDate?: string; lockMessage?: string; description?: string; }>({});
    // Rows come straight from the API; there is no local copy to drift.
    const holidaysData = initialHolidaysData;
    const [search, setSearch] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    const [editModalOpen, setEditModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    /** Which `occasion` the delete dialog is about to retire. */
    const [deletingId, setDeletingId] = useState<string | null>(null);

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

    /**
     * Create or update an `occasion`.
     *
     * The type comes from the `occasion_type` lookup -- the Description field is
     * that choice, so it is matched against the real type names. `month` and
     * `day_of_month` are derived server-side from the start date.
     */
    const handleSubmit = () => {
        if (!validateForm()) return;

        const types = typesQuery.data ?? [];
        const occasionType =
            types.find((type) => type.name.toLowerCase() === description.trim().toLowerCase())
            ?? types.find((type) => type.name === "Holiday")
            ?? types[0];
        if (!occasionType) return;

        const body = {
            occasion_type: occasionType.id,
            occasion_name: lockMessage.trim(),
            occasion_start_date: startDate,
            occasion_end_date: endDate || null,
        };

        if (editingId) {
            updateHoliday.mutate({ id: editingId, body }, { onSuccess: handleReset });
            return;
        }
        createHoliday.mutate(body, { onSuccess: handleReset });
    };

    const handleReset = () => { setStartDate(""); setEndDate(""); setLockMessage(""); setDescription(""); setErrors({}); setEditingId(null); };

    const handleEdit = (item: typeof initialHolidaysData[0]) => {
        setEditingId(item.id);
        // The API returns ISO dates, which is what the date inputs want.
        setStartDate(item.startDate);
        setEndDate(item.endDate === "-" ? "" : item.endDate);
        setLockMessage(item.lockMessage);
        setDescription(item.description);
    };

    /**
     * Deactivate rather than delete: `occasion` has a `status` column and no
     * delete endpoint, because a past occasion is a record, not a mistake.
     */
    const handleDelete = (id: string) => {
        updateHoliday.mutate({ id, body: { status: 0 } });
    };

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
                        <Button variant="outline" onClick={handleReset} className="px-8">Reset</Button>
                        <Button
                            onClick={handleSubmit}
                            disabled={!mayWrite || createHoliday.isPending || updateHoliday.isPending}
                            className="h-10 px-8 min-w-[160px] rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                        >
                            {createHoliday.isPending || updateHoliday.isPending
                                ? "Saving..."
                                : editingId
                                    ? "Update"
                                    : "Submit"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Table */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
                <CardContent className="p-5">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                                <SelectContent className="bg-popover text-popover-foreground border-border">
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
                                {paginatedData.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                        <TableCell>{item.startDate}</TableCell>
                                        <TableCell>{item.endDate}</TableCell>
                                        <TableCell className="text-cyan-600">{item.lockMessage}</TableCell>
                                        <TableCell>{item.description}</TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex gap-2 justify-center">
                                                <Button size="sm" className="bg-brand-teal hover:bg-brand-teal/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditModalOpen(true)}>
                                                    <Edit className="h-[14px] w-[14px]" />
                                                </Button>
                                                {/* Record WHICH occasion is being retired.
                                                    Previously the dialog opened without an id,
                                                    so the confirm button had nothing to act on. */}
                                                <Button
                                                    size="sm"
                                                    className="bg-[#d33] hover:bg-brand-danger-hover text-white h-7 w-7 p-0 rounded-[3px]"
                                                    disabled={!mayWrite}
                                                    onClick={() => {
                                                        setDeletingId(item.id);
                                                        setDeleteModalOpen(true);
                                                    }}
                                                >
                                                    <Trash2 className="h-[14px] w-[14px]" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
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
                        <Button className="bg-transparent text-brand-teal border border-brand-teal hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Submit</Button>
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
                            {/* Actually performs the retirement via PATCH status=0. */}
                            <Button
                                className="bg-[#3085d6] hover:bg-[#2b78c1] text-white text-[15px] font-medium px-4 py-2 rounded-[4px] h-[40px]"
                                disabled={!mayWrite || !deletingId || updateHoliday.isPending}
                                onClick={() => {
                                    if (!deletingId) return;
                                    handleDelete(deletingId);
                                    setDeletingId(null);
                                    setDeleteModalOpen(false);
                                }}
                            >
                                {updateHoliday.isPending ? "Removing..." : "Yes, delete it!"}
                            </Button>
                            <Button className="bg-[#d33] hover:bg-brand-danger-hover text-white text-[15px] font-medium px-4 py-2 rounded-[4px] h-[40px]" onClick={() => setDeleteModalOpen(false)}>Cancel</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Holidays;
