import { useEffect, useState } from "react";
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
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { CalendarX2, X, Edit, ChevronUp, ChevronDown } from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { useEvents } from "@/lib/api/hooks";
import { useCreateEvent, useUpdateEvent } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";

// Sample Events Data
interface EventRow {
    id: string;
    eventName: string;
    description: string;
    venue: string;
    chiefGuests: string;
    startDateTime: string;
    endDateTime: string;
    attendees: number;
    interestedGuests: number;
    image: string;
}

/**
 * Events, connected to GET/POST/PATCH /events (`facility_event`).
 *
 * `interested_attendees` is read-only here: it is a guest-app counter, not an
 * operator field, so the API refuses to accept it.
 */

const Events = () => {
    const eventsQuery = useEvents({ page: 1, page_size: MAX_PAGE_SIZE });
    const { canWrite } = useAuth();
    const mayWrite = canWrite("events");
    const createEvent = useCreateEvent();
    const updateEvent = useUpdateEvent();

    const eventsData: EventRow[] = (eventsQuery.data?.items ?? []).map((event) => ({
        id: event.id,
        eventName: event.name,
        description: event.description ?? "",
        venue: event.venue ?? "-",
        chiefGuests: event.chief_guests ?? "-",
        startDateTime: event.start_date_time
            ? new Date(event.start_date_time).toLocaleString()
            : "-",
        endDateTime: event.end_date_time ? new Date(event.end_date_time).toLocaleString() : "-",
        attendees: event.expected_attendees ?? 0,
        interestedGuests: event.interested_attendees ?? 0,
        image: "-",
    }));
    const [isAddEventOpen, setIsAddEventOpen] = useState(false);
    const [editingEventId, setEditingEventId] = useState<string | null>(null);
    const [cancellingEventId, setCancellingEventId] = useState<string | null>(null);
    const [cancelReason, setCancelReason] = useState("");
    /** The four details, editable while cancelling. Seeded from the event. */
    const [cancelForm, setCancelForm] = useState({
        name: "",
        venue: "",
        startDateTime: "",
        endDateTime: "",
    });
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);
    // Pagination sits at the bottom of the table; without this the new
    // page kept the old scroll offset and the sticky header stayed
    // above the fold. See use-scroll-to-top.
    useScrollToTop(currentPage);

    // Modal States
    const [editEventOpen, setEditEventOpen] = useState(false);
    const [cancelEventOpen, setCancelEventOpen] = useState(false);

    /** The Add Event form; every field maps to a `facility_event` column. */
    const [eventName, setEventName] = useState("");
    const [venue, setVenue] = useState("");
    const [chiefGuests, setChiefGuests] = useState("");
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [attendees, setAttendees] = useState("");
    const [description, setDescription] = useState("");

    const filteredData = eventsData.filter(item => item.eventName.toLowerCase().includes(searchQuery.toLowerCase()) || item.venue.toLowerCase().includes(searchQuery.toLowerCase()));
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, startIndex + parseInt(entriesPerPage));

    const handleReset = () => { setEventName(""); setVenue(""); setChiefGuests(""); setStartDate(""); setEndDate(""); setAttendees(""); setDescription(""); };

    /**
     * The row each dialog is acting on.
     *
     * Resolved from `eventsData` rather than copied into state when the button
     * is clicked: a dialog then shows whatever the table currently holds, so a
     * refetch between opening and submitting cannot leave stale details on
     * screen beside a live id.
     */
    const editingEvent = eventsData.find((event) => event.id === editingEventId);
    const cancellingEvent = eventsData.find((event) => event.id === cancellingEventId);

    /**
     * Closing has to clear the reason as well as the target. Leaving it behind
     * pre-filled the next cancellation with the previous event's reason, which
     * the required-field check would then happily accept.
     */
    /** `datetime-local` wants LOCAL `YYYY-MM-DDTHH:mm`. `toISOString()` would
     *  shift every event by the timezone offset, so the parts are read locally. */
    const toLocalInput = (iso: string | null | undefined) => {
        if (!iso) return "";
        const d = new Date(iso);
        const pad = (n: number) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    /* Seeded from the RAW row: the table's strings are toLocaleString() output,
       which a datetime-local input cannot take and the API cannot parse back. */
    const cancellingRaw = (eventsQuery.data?.items ?? []).find(
        (event) => event.id === cancellingEventId,
    );

    useEffect(() => {
        if (!cancellingRaw) return;
        setCancelForm({
            name: cancellingRaw.name ?? "",
            venue: cancellingRaw.venue ?? "",
            startDateTime: toLocalInput(cancellingRaw.start_date_time),
            endDateTime: toLocalInput(cancellingRaw.end_date_time),
        });
        // Keyed on the id alone: seed once per targeted event, so a background
        // refetch cannot overwrite what the operator has typed.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [cancellingEventId]);

    const closeCancelDialog = () => {
        setCancelEventOpen(false);
        setCancellingEventId(null);
        setCancelReason("");
        setCancelForm({ name: "", venue: "", startDateTime: "", endDateTime: "" });
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            <PageHeader
                title="Events Management"
                actions={
                    <Button onClick={() => setIsAddEventOpen(true)} className="px-6 rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Add Events</Button>
                }
            />


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
                            <Input placeholder="Event name, Venue" value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }} className="w-64 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60" />
                        </div>
                    </div>

                    {/* Loading and error are handled here, not by the empty row
                        below: without this a failed GET /events left `items` at
                        [] and the table said "No events found", which reads as
                        "this facility has no events" rather than "the request
                        failed". `isEmpty` is deliberately not passed -- the row
                        below states whether a search term is filtering it. */}
                    <DataState
                        isLoading={eventsQuery.isLoading}
                        error={eventsQuery.error}
                        loader={<TableLoading columns={12} />}
                    >
                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Event Name</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">#</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Description</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Venue</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">#</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Chief Guests</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Start date and time</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">End date and time</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Attendees</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Interested Guests</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4">Image</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.length > 0 ? (
                                    paginatedData.map((item, index) => (
                                        <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                            <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 whitespace-nowrap font-medium">{item.eventName}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.id}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-muted-foreground">{item.description || "-"}</TableCell>
                                            <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 whitespace-nowrap">{item.venue}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.id}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.chiefGuests}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.startDateTime}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.endDateTime}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.attendees}</TableCell>
                                            <TableCell className="text-xs py-3 px-4 text-foreground/90">{item.interestedGuests}</TableCell>
                                            <TableCell className="text-cyan-600 dark:text-cyan-400 text-xs py-3 px-4 cursor-pointer hover:underline">{item.image}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <div className="flex gap-2 justify-center">
                                                    <Button size="sm" className="h-7 w-7 p-0 rounded-md" onClick={() => { setEditingEventId(item.id); setEditEventOpen(true); }}>
                                                        <Edit className="h-3.5 w-3.5" />
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-md"
                                                        disabled={!mayWrite}
                                                        aria-label={`Cancel event ${item.eventName}`}
                                                        title="Cancel this event. The event is kept and marked cancelled -- it is never deleted."
                                                        onClick={() => { setCancellingEventId(item.id); setCancelEventOpen(true); }}
                                                    >
                                                        {/* Deliberately NOT a trash icon. This action is a cancellation:
                                                            it PATCHes `facility_event.status` to 0 and the row stays in
                                                            the table. There is no delete path for an event anywhere in
                                                            the client, and none should be added. */}
                                                        <CalendarX2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow>
                                        <TableCell colSpan={12} className="text-center py-6 text-muted-foreground text-xs">
                                            No events found {searchQuery ? `matching "${searchQuery}"` : ""}
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>
                    </DataState>

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

            {/* Add Event Modal */}
            <Dialog open={isAddEventOpen} onOpenChange={setIsAddEventOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader><DialogTitle>Add New Event</DialogTitle></DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Event Name</Label>
                                <Input placeholder="Enter Event Name" value={eventName} onChange={(e) => setEventName(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                            <div className="space-y-2">
                                <Label>Venue<span className="text-red-500">*</span></Label>
                                <Input placeholder="Enter Venue" value={venue} onChange={(e) => setVenue(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Chief Guests<span className="text-red-500">*</span></Label>
                                <Input placeholder="Enter Chief Guest" value={chiefGuests} onChange={(e) => setChiefGuests(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                            <div className="space-y-2">
                                <Label>Attendees<span className="text-red-500">*</span></Label>
                                <Input placeholder="Enter Total Number Of Attendees" value={attendees} onChange={(e) => setAttendees(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Start Date<span className="text-red-500">*</span></Label>
                                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                            <div className="space-y-2">
                                <Label>End Date<span className="text-red-500">*</span></Label>
                                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-muted/30 border-border/50" />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Description</Label>
                            <Textarea placeholder="Enter Description" value={description} onChange={(e) => setDescription(e.target.value)} className="bg-muted/30 border-border/50 min-h-[100px]" />
                        </div>
                        <div className="space-y-2">
                            <Label>Image</Label>
                            <Input type="file" className="bg-muted/30 border-border/50" />
                        </div>
                        <div className="flex justify-center gap-4 pt-4">
                            <Button variant="outline" onClick={handleReset} className="px-8">Reset</Button>
                            <Button
                                className="h-10 px-8 min-w-[160px] rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                                /* Reads the state the inputs above actually bind to.
                                   This previously read an `eventForm` object that
                                   nothing ever populated, so the button was
                                   permanently disabled and the form could not be
                                   submitted at all. */
                                disabled={!mayWrite || !eventName.trim() || createEvent.isPending}
                                onClick={() =>
                                    createEvent.mutate(
                                        {
                                            name: eventName.trim(),
                                            venue: venue.trim() || null,
                                            chief_guests: chiefGuests.trim() || null,
                                            description: description.trim() || null,
                                            expected_attendees: attendees.trim()
                                                ? Number(attendees)
                                                : null,
                                            start_date_time: startDate
                                                ? new Date(startDate).toISOString()
                                                : null,
                                            end_date_time: endDate
                                                ? new Date(endDate).toISOString()
                                                : null,
                                        },
                                        {
                                            onSuccess: () => {
                                                handleReset();
                                                setIsAddEventOpen(false);
                                            },
                                        },
                                    )
                                }
                            >
                                {createEvent.isPending ? "Saving..." : "Submit"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Event Modal */}
            <Dialog open={editEventOpen} onOpenChange={setEditEventOpen}>
                <DialogContent className="max-w-[750px] bg-card text-card-foreground border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-card border-b border-border">
                        <h2 className="text-[17px] font-semibold text-foreground tracking-wide">Events Management</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-border rounded-[2px] hover:bg-muted" onClick={() => { setEditEventOpen(false); setEditingEventId(null); }}>
                            <X className="h-4 w-4 text-muted-foreground stroke-[3]" />
                        </Button>
                    </div>
                    {/* Only the four details asked for. Chief Guests, Start/End
                        Time, Attendees, Description and Image were removed.

                        READ-ONLY, and that is not a downgrade: the fields here
                        were `defaultValue="Marriage"` / `"Venue 5"` / `"19-11-2024"`
                        hardcoded placeholders, the dialog never recorded which
                        row was clicked, and it has no submit button -- nothing
                        typed into it could ever be saved. These values now come
                        from the row that opened it. */}
                    <div className="p-8 px-12">
                        {editingEvent ? (
                            <dl className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-5">
                                <dt className="text-sm font-medium text-muted-foreground">Event Name</dt>
                                <dd className="text-sm font-medium text-foreground">{editingEvent.eventName}</dd>

                                <dt className="text-sm font-medium text-muted-foreground">Venue</dt>
                                <dd className="text-sm text-foreground">{editingEvent.venue}</dd>

                                <dt className="text-sm font-medium text-muted-foreground">Start Date</dt>
                                <dd className="text-sm text-foreground">{editingEvent.startDateTime}</dd>

                                <dt className="text-sm font-medium text-muted-foreground">End Date</dt>
                                <dd className="text-sm text-foreground">{editingEvent.endDateTime}</dd>
                            </dl>
                        ) : (
                            <p className="text-sm text-muted-foreground">No event selected.</p>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Cancel Event Modal */}
            <Dialog open={cancelEventOpen} onOpenChange={(open) => (open ? setCancelEventOpen(true) : closeCancelDialog())}>
                <DialogContent className="max-w-[500px] bg-card text-card-foreground border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-card border-b border-border">
                        <h2 className="text-[17px] font-semibold text-foreground tracking-wide">Cancel Events Menu</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-border rounded-[2px] hover:bg-muted" onClick={closeCancelDialog}>
                            <X className="h-4 w-4 text-muted-foreground stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-7">
                        {/* Which event is being cancelled. Read-only: this is a
                            confirmation surface, not an edit form -- the only
                            thing the operator supplies here is the reason.
                            Values come from the row that opened the dialog, so
                            they cannot disagree with the table behind it. */}
                        {cancellingEvent && (
                            <div className="space-y-5">
                                <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                                    <Label htmlFor="cancel-name" className="text-sm font-medium text-foreground">Event Name</Label>
                                    <input
                                        id="cancel-name"
                                        type="text"
                                        value={cancelForm.name}
                                        onChange={(e) => setCancelForm((f) => ({ ...f, name: e.target.value }))}
                                        className="w-full bg-transparent border-0 border-b border-border text-foreground focus:ring-0 px-0 pb-1 text-sm outline-none"
                                    />
                                </div>
                                <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                                    <Label htmlFor="cancel-venue" className="text-sm font-medium text-foreground">Venue</Label>
                                    <input
                                        id="cancel-venue"
                                        type="text"
                                        value={cancelForm.venue}
                                        onChange={(e) => setCancelForm((f) => ({ ...f, venue: e.target.value }))}
                                        className="w-full bg-transparent border-0 border-b border-border text-foreground focus:ring-0 px-0 pb-1 text-sm outline-none"
                                    />
                                </div>
                                {/* datetime-local, not text: the value must return to
                                    the API as ISO, and free-text dates cannot be parsed
                                    reliably. */}
                                <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                                    <Label htmlFor="cancel-start" className="text-sm font-medium text-foreground">Start Date</Label>
                                    <input
                                        id="cancel-start"
                                        type="datetime-local"
                                        value={cancelForm.startDateTime}
                                        onChange={(e) => setCancelForm((f) => ({ ...f, startDateTime: e.target.value }))}
                                        className="w-full bg-transparent border-0 border-b border-border text-foreground focus:ring-0 px-0 pb-1 text-sm outline-none"
                                    />
                                </div>
                                <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                                    <Label htmlFor="cancel-end" className="text-sm font-medium text-foreground">End Date</Label>
                                    <input
                                        id="cancel-end"
                                        type="datetime-local"
                                        value={cancelForm.endDateTime}
                                        onChange={(e) => setCancelForm((f) => ({ ...f, endDateTime: e.target.value }))}
                                        className="w-full bg-transparent border-0 border-b border-border text-foreground focus:ring-0 px-0 pb-1 text-sm outline-none"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label htmlFor="cancel-reason" className="text-sm font-medium text-foreground">Reason for Cancel <span className="text-red-500">*</span></Label>
                            <input
                                id="cancel-reason"
                                type="text"
                                value={cancelReason}
                                onChange={(e) => setCancelReason(e.target.value)}
                                className="w-full bg-transparent border-0 border-b border-border text-foreground focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button
                            className="bg-brand-teal hover:bg-cyan-600 text-white h-8 px-6 rounded-[3px] font-normal"
                            disabled={
                                !mayWrite ||
                                !cancellingEventId ||
                                !cancelReason.trim() ||
                                updateEvent.isPending
                            }
                            onClick={() =>
                                cancellingEventId &&
                                updateEvent.mutate(
                                    {
                                        id: cancellingEventId,
                                        body: {
                                            // `facility_event` stores the reason and a status flag.
                                            // The reason was previously collected and thrown away:
                                            // the field is marked required, so submitting without
                                            // it recorded a cancellation nobody could explain.
                                            status: 0,
                                            cancellation_reason: cancelReason.trim(),
                                            // The edited details go up with the cancellation.
                                            name: cancelForm.name.trim(),
                                            venue: cancelForm.venue.trim() || null,
                                            start_date_time: cancelForm.startDateTime
                                                ? new Date(cancelForm.startDateTime).toISOString()
                                                : null,
                                            end_date_time: cancelForm.endDateTime
                                                ? new Date(cancelForm.endDateTime).toISOString()
                                                : null,
                                        },
                                    },
                                    { onSuccess: () => closeCancelDialog() },
                                )
                            }
                        >
                            {updateEvent.isPending ? "Cancelling..." : "Submit"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Events;
