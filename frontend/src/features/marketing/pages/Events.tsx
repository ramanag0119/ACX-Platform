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
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Pencil, Trash2, X, Edit, ChevronUp, ChevronDown } from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { useEvents } from "@/lib/api/hooks";
import { useCreateEvent, useUpdateEvent } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

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
    const [cancellingEventId, setCancellingEventId] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

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

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Events Management</h1>
                <Button onClick={() => setIsAddEventOpen(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white">Add Events</Button>
            </div>


            {/* Table Section */}
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
                            <Input placeholder="Event name, Venue" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-64 h-9 bg-muted/30 border-border/50" />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Event Name</TableHead>
                                    <TableHead className="text-gray-600 font-medium">#</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Venue</TableHead>
                                    <TableHead className="text-gray-600 font-medium">#</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Chief Guests</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Start date and time ↓</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">End date and time</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Attendees</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Interested Guests</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Image</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                        <TableCell className="text-cyan-600 whitespace-nowrap">{item.eventName}</TableCell>
                                        <TableCell>{item.id}</TableCell>
                                        <TableCell>{item.description || "-"}</TableCell>
                                        <TableCell className="text-cyan-600 whitespace-nowrap">{item.venue}</TableCell>
                                        <TableCell>{item.id}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.chiefGuests}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.startDateTime}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.endDateTime}</TableCell>
                                        <TableCell>{item.attendees}</TableCell>
                                        <TableCell>{item.interestedGuests}</TableCell>
                                        <TableCell className="text-cyan-600 cursor-pointer hover:underline">{item.image}</TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex gap-2 justify-center">
                                                <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditEventOpen(true)}>
                                                    <Edit className="h-[14px] w-[14px]" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]"
                                                    disabled={!mayWrite}
                                                    title="Cancel this event"
                                                    onClick={() => { setCancellingEventId(item.id); setCancelEventOpen(true); }}
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

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing {startIndex + 1} to {Math.min(startIndex + parseInt(entriesPerPage), filteredData.length)} of {filteredData.length} entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(3, totalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${currentPage === page ? "bg-cyan-600 text-white" : ""}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
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
                                className="bg-cyan-600 hover:bg-cyan-700 text-white px-8"
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
                <DialogContent className="max-w-[750px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Events Management</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditEventOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-12 space-y-7 max-h-[75vh] overflow-y-auto custom-scrollbar">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Event Name <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="Marriage" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Venue <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="Venue 5" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Chief Guests <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="Brindha" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Start Date <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="19-11-2024" className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">End Date <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="19-11-2024" className="w-full bg-gray-100 border border-gray-200 text-gray-600 focus:ring-0 px-3 py-2 text-sm outline-none" />
                        </div>

                        {/* Start Time */}
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Start Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-4 w-4 text-cyan-600 cursor-pointer" />
                                    <span className="text-gray-600 text-sm mt-1 border-b border-gray-300 pb-1 px-2">01</span>
                                    <ChevronDown className="h-4 w-4 text-cyan-600 cursor-pointer mt-1" />
                                </div>
                                <span className="text-gray-800 font-medium pb-2">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-4 w-4 text-cyan-600 cursor-pointer" />
                                    <span className="text-gray-600 text-sm mt-1 border-b border-gray-300 pb-1 px-2">31</span>
                                    <ChevronDown className="h-4 w-4 text-cyan-600 cursor-pointer mt-1" />
                                </div>
                                <div className="ml-2 border border-[#3eb1c8] text-[#3eb1c8] rounded px-3 py-1 text-sm font-medium">PM</div>
                            </div>
                        </div>

                        {/* End Time */}
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">End Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-4 w-4 text-cyan-600 cursor-pointer" />
                                    <span className="text-gray-600 text-sm mt-1 border-b border-gray-300 pb-1 px-2">09</span>
                                    <ChevronDown className="h-4 w-4 text-cyan-600 cursor-pointer mt-1" />
                                </div>
                                <span className="text-gray-800 font-medium pb-2">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-4 w-4 text-cyan-600 cursor-pointer" />
                                    <span className="text-gray-600 text-sm mt-1 border-b border-gray-300 pb-1 px-2">00</span>
                                    <ChevronDown className="h-4 w-4 text-cyan-600 cursor-pointer mt-1" />
                                </div>
                                <div className="ml-2 border border-[#3eb1c8] text-[#3eb1c8] rounded px-3 py-1 text-sm font-medium">PM</div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Attendees <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="500" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Description</Label>
                            <input type="text" placeholder="Enter Description" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4 pt-2">
                            <Label className="text-sm font-medium text-gray-800 text-left">Image</Label>
                            <div className="space-y-3">
                                <div className="flex items-center border-b border-gray-300 pb-1">
                                    <Button variant="outline" className="h-7 px-3 bg-gray-100 text-gray-700 text-xs border border-gray-300 rounded-[2px] font-normal">Choose file</Button>
                                    <span className="ml-3 text-xs text-gray-400">No file chosen</span>
                                </div>
                                <div className="text-[#3eb1c8] text-xs cursor-pointer hover:underline">Click here to preview image</div>
                            </div>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Cancel Event Modal */}
            <Dialog open={cancelEventOpen} onOpenChange={setCancelEventOpen}>
                <DialogContent className="max-w-[500px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Cancel Events Menu</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setCancelEventOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-7">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Reason for Cancel <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button
                            className="bg-[#3eb1c8] hover:bg-cyan-600 text-white h-8 px-6 rounded-[3px] font-normal"
                            disabled={!mayWrite || !cancellingEventId || updateEvent.isPending}
                            onClick={() =>
                                cancellingEventId &&
                                updateEvent.mutate(
                                    {
                                        id: cancellingEventId,
                                        body: {
                                            // `facility_event` stores the reason and a status flag.
                                            status: 0,
                                        },
                                    },
                                    { onSuccess: () => setCancelEventOpen(false) },
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
