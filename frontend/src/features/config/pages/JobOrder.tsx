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
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { useDeviceTypes, useDevices, useJobOrders, useRooms } from "@/lib/api/hooks";
import { useCreateJobOrder, useUpdateJobOrder } from "@/lib/api/mutations";
import { describeApiError } from "@/lib/api/client";
import { toast } from "@/hooks/use-toast";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { JobOrderRead, JobOrderTypeOfWork } from "@/lib/api/writes";

/**
 * Job Order Management, connected to the Phase 3.0 job-order API.
 *
 *   GET/POST/PATCH/DELETE /job-orders   -> `job_order`
 *                                          + `job_order_amenity` (rooms)
 *                                          + `job_order_device`  (devices)
 *
 * The two pickers on the create form are backed by the same real APIs they
 * always were -- rooms from GET /rooms, the Caleido Network list from GET
 * /device-types -- and their option VALUES are now the ids those APIs return,
 * so a UUID reaches the payload instead of a room number.
 *
 * WHY A THIRD QUERY: `job_order_device.device_id` is a FK to `device.id`, but
 * "Caleido Network" is a `device_type` (a small integer), not a device. GET
 * /devices resolves each (room, device type) pair the user adds into the actual
 * device rows installed in that room -- `device.amenity_id` + `device.device_type`.
 * No new endpoint and no new client: it is the existing useDevices hook.
 *
 * WHAT THE SCHEMA WILL NOT STORE: the form pairs one room with one network per
 * table row, but `job_order_amenity` and `job_order_device` are two independent
 * many-to-many tables. A job order therefore covers a SET of rooms and a SET of
 * devices; the pairing itself has nowhere to live and is not persisted. The
 * table below is the create-form draft, not a stored shape.
 */

/** Form radio value -> the real `job_order_type_of_work` enum. */
const TYPE_OF_WORK: Record<string, JobOrderTypeOfWork> = {
    "fresh-installation": "installation",
    replacement: "replacement",
};
/** Inverse, for prefilling the edit modal from a stored row. */
const RADIO_FOR_TYPE: Record<string, string> = {
    installation: "fresh-installation",
    replacement: "replacement",
    troubleshoot: "fresh-installation",
};

/** A room+network row on the create/edit draft table. */
interface DraftRow {
    amenityId: string;
    roomName: string;
    deviceTypeId: string;
    deviceTypeName: string;
    /** The real `device.id` values that pair resolved to. May be empty. */
    deviceIds: string[];
}

/** `<input type="date">` gives YYYY-MM-DD; the columns are timestamptz. */
const toIsoStart = (value: string) => `${value}T00:00:00Z`;
const toDateInput = (iso: string | null) => (iso ? iso.slice(0, 10) : "");

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
    const [addedRooms, setAddedRooms] = useState<DraftRow[]>([]);

    // The two pickers, from the real APIs. Option values are the ids these
    // endpoints return -- `amenity.id` and `device_type.id`.
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
    const roomOptions = (roomsQuery.data?.items ?? []).map((room) => ({
        id: room.id,
        name: room.name,
    }));
    const deviceTypesQuery = useDeviceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const caleidoNetworkOptions = (deviceTypesQuery.data?.items ?? [])
        .filter((type) => type.name)
        .map((type) => ({ id: String(type.id), name: type.name as string }));

    // Devices, so a (room, device type) pair can become real `device.id` values.
    const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE });
    const allDevices = devicesQuery.data?.items ?? [];

    const jobOrdersQuery = useJobOrders({ page: 1, page_size: MAX_PAGE_SIZE });
    const jobOrders = jobOrdersQuery.data?.items ?? [];

    const { canWrite } = useAuth();
    const mayWrite = canWrite("job_order");
    const createJobOrder = useCreateJobOrder();
    const updateJobOrder = useUpdateJobOrder();

    // Job Orders table state
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingJob, setEditingJob] = useState<JobOrderRead | null>(null);
    const [editForm, setEditForm] = useState({
        orderReference: "",
        typeOfWork: "fresh-installation",
        description: "",
        workCommence: "",
        estimateCompleteDate: "",
    });
    const [editRooms, setEditRooms] = useState<DraftRow[]>([]);
    const [editSelectedRoom, setEditSelectedRoom] = useState("");
    const [editSelectedNetwork, setEditSelectedNetwork] = useState("");

    /**
     * The devices of one type installed in one room -- `device.amenity_id` and
     * `device.device_type`, which is how a "Caleido Network" choice becomes the
     * `device.id` values `job_order_device` requires.
     */
    const devicesForPair = (amenityId: string, deviceTypeId: string) =>
        allDevices
            .filter(
                (device) =>
                    device.amenity_id === amenityId &&
                    String(device.device_type) === deviceTypeId,
            )
            .map((device) => device.id);

    /** Shared by the create form and the edit modal. */
    const buildDraftRow = (amenityId: string, deviceTypeId: string): DraftRow | null => {
        const room = roomOptions.find((option) => option.id === amenityId);
        const network = caleidoNetworkOptions.find((option) => option.id === deviceTypeId);
        if (!room || !network) return null;
        const deviceIds = devicesForPair(amenityId, deviceTypeId);
        if (deviceIds.length === 0) {
            // Said plainly rather than silently creating a job with no device
            // link. The row is still added: `job_order_device` is optional, and
            // the seeded JO-2026-0001 covers two rooms and no devices.
            toast({
                title: "No matching device in that room",
                description:
                    `Room ${room.name} has no ${network.name} device, so this row adds the ` +
                    "room but no device link.",
            });
        }
        return {
            amenityId,
            roomName: room.name,
            deviceTypeId,
            deviceTypeName: network.name,
            deviceIds,
        };
    };

    const handleAddRoom = () => {
        if (!selectedRoom || !selectedCaleidoNetwork) return;
        const duplicate = addedRooms.some(
            (row) =>
                row.amenityId === selectedRoom && row.deviceTypeId === selectedCaleidoNetwork,
        );
        if (duplicate) {
            toast({
                title: "Already added",
                description: "That room and network pair is already on the list.",
                variant: "destructive",
            });
            return;
        }
        const row = buildDraftRow(selectedRoom, selectedCaleidoNetwork);
        if (!row) return;
        setAddedRooms([...addedRooms, row]);
        setSelectedRoom("");
        setSelectedCaleidoNetwork("");
    };

    const handleRemoveRoom = (index: number) => {
        setAddedRooms(addedRooms.filter((_, i) => i !== index));
    };

    const handleReset = () => {
        setWorkPurchaseRef("");
        setTypeOfWork("fresh-installation");
        setJobDescription("");
        setWorkCommence("");
        setEstimateCompleteDate("");
        setSelectedRoom("");
        setSelectedCaleidoNetwork("");
        setAddedRooms([]);
    };

    /** The two link tables take SETS, so the draft rows are flattened and deduped. */
    const linkIdsFrom = (rows: DraftRow[]) => ({
        amenity_ids: [...new Set(rows.map((row) => row.amenityId))],
        device_ids: [...new Set(rows.flatMap((row) => row.deviceIds))],
    });

    /**
     * Create the `job_order` plus one `job_order_amenity` per room and one
     * `job_order_device` per resolved device, in a single backend transaction.
     * Required fields are checked here so the user gets one clear message
     * instead of a 422 field list; the backend validates them again.
     */
    const handleSubmit = () => {
        const missing: string[] = [];
        if (!jobDescription.trim()) missing.push("Job Description");
        if (!workCommence) missing.push("Work Commence");
        if (!estimateCompleteDate) missing.push("Estimate Complete Date");
        if (addedRooms.length === 0) missing.push("at least one room");
        if (missing.length) {
            toast({
                title: "Required fields are missing",
                description: `Please provide ${missing.join(", ")}.`,
                variant: "destructive",
            });
            return;
        }
        if (estimateCompleteDate < workCommence) {
            toast({
                title: "Dates are out of order",
                description: "Estimate Complete Date cannot be before Work Commence.",
                variant: "destructive",
            });
            return;
        }
        createJobOrder.mutate(
            {
                // Omitted, the server continues the seeded JO-YYYY-NNNN sequence.
                ...(workPurchaseRef.trim() ? { order_reference: workPurchaseRef.trim() } : {}),
                description: jobDescription.trim(),
                type_of_work: TYPE_OF_WORK[typeOfWork],
                work_commence: toIsoStart(workCommence),
                estimated_completion_date: toIsoStart(estimateCompleteDate),
                ...linkIdsFrom(addedRooms),
            },
            { onSuccess: handleReset },
        );
    };

    const handleEditClick = (job: JobOrderRead) => {
        setEditingJob(job);
        setEditForm({
            orderReference: job.order_reference,
            typeOfWork: RADIO_FOR_TYPE[job.type_of_work] ?? "fresh-installation",
            description: job.description ?? "",
            workCommence: toDateInput(job.work_commence),
            estimateCompleteDate: toDateInput(job.estimated_completion_date),
        });
        // The stored rooms and devices are two independent sets. They are shown
        // as one row per room, carrying that room's own devices.
        setEditRooms(
            job.rooms.map((room) => {
                const roomDevices = job.devices.filter(
                    (device) => device.amenity_id === room.amenity_id,
                );
                return {
                    amenityId: room.amenity_id,
                    roomName: room.room_name ?? "-",
                    deviceTypeId: roomDevices[0]?.device_type
                        ? String(roomDevices[0].device_type)
                        : "",
                    deviceTypeName:
                        roomDevices.map((device) => device.device_type_name ?? "-").join(", ") ||
                        "-",
                    deviceIds: roomDevices.map((device) => device.device_id),
                };
            }),
        );
        setEditSelectedRoom("");
        setEditSelectedNetwork("");
        setIsEditModalOpen(true);
    };

    const handleEditAddRoom = () => {
        if (!editSelectedRoom || !editSelectedNetwork) return;
        const duplicate = editRooms.some(
            (row) =>
                row.amenityId === editSelectedRoom && row.deviceTypeId === editSelectedNetwork,
        );
        if (duplicate) {
            toast({
                title: "Already added",
                description: "That room and network pair is already on the list.",
                variant: "destructive",
            });
            return;
        }
        const row = buildDraftRow(editSelectedRoom, editSelectedNetwork);
        if (!row) return;
        setEditRooms([...editRooms, row]);
        setEditSelectedRoom("");
        setEditSelectedNetwork("");
    };

    /** PATCH only what the modal can change. Sending both id lists REPLACES them. */
    const handleUpdate = () => {
        if (!editingJob) return;
        if (!editForm.description.trim() || !editForm.workCommence || !editForm.estimateCompleteDate) {
            toast({
                title: "Required fields are missing",
                description: "Job Description, Work Commence and Estimate Complete Date are required.",
                variant: "destructive",
            });
            return;
        }
        if (editForm.estimateCompleteDate < editForm.workCommence) {
            toast({
                title: "Dates are out of order",
                description: "Estimate Complete Date cannot be before Work Commence.",
                variant: "destructive",
            });
            return;
        }
        updateJobOrder.mutate(
            {
                id: editingJob.id,
                body: {
                    order_reference: editForm.orderReference.trim() || undefined,
                    description: editForm.description.trim(),
                    type_of_work: TYPE_OF_WORK[editForm.typeOfWork],
                    work_commence: toIsoStart(editForm.workCommence),
                    estimated_completion_date: toIsoStart(editForm.estimateCompleteDate),
                    ...linkIdsFrom(editRooms),
                },
            },
            {
                onSuccess: () => {
                    setIsEditModalOpen(false);
                    setEditingJob(null);
                },
            },
        );
    };

    // Filter job orders over the fetched page.
    const needle = searchQuery.trim().toLowerCase();
    const filteredJobOrders = jobOrders.filter((job) => {
        if (!needle) return true;
        return (
            job.order_reference.toLowerCase().includes(needle) ||
            (job.description ?? "").toLowerCase().includes(needle) ||
            job.rooms.some((room) => (room.room_name ?? "").toLowerCase().includes(needle))
        );
    });
    const perPage = parseInt(entriesPerPage);
    const totalPages = Math.max(1, Math.ceil(filteredJobOrders.length / perPage));
    const startIndex = (currentPage - 1) * perPage;
    const endIndex = startIndex + perPage;
    const paginatedJobOrders = filteredJobOrders.slice(startIndex, endIndex);

    const tabs = [
        { id: "create-job" as TabType, label: "Create Job" },
        { id: "job-orders" as TabType, label: "Job Orders" },
    ];

    const triggerClass = (compact: boolean) =>
        compact
            ? "bg-white border-gray-300 text-foreground w-full h-8 rounded-sm text-xs"
            : "bg-muted/30 border-border/50";

    /** The Rooms picker. Unchanged source (GET /rooms); the option VALUE is the
     *  `amenity.id` UUID that `job_order_amenity` needs, the label the room name. */
    const renderRoomSelect = (
        value: string, onChange: (next: string) => void, compact = false,
    ) => (
        <Select value={value} onValueChange={onChange}>
            <SelectTrigger className={triggerClass(compact)}>
                <SelectValue placeholder="Select Rooms No" />
            </SelectTrigger>
            <SelectContent className={compact ? "bg-white" : "bg-popover"}>
                {roomOptions.length === 0 ? (
                    <div className="py-3 px-4 text-muted-foreground text-sm">
                        {roomsQuery.isLoading
                            ? "Loading rooms..."
                            : roomsQuery.error
                                ? describeApiError(roomsQuery.error)
                                : "No data available"}
                    </div>
                ) : (
                    roomOptions.map(option => (
                        <SelectItem key={option.id} value={option.id}>{option.name}</SelectItem>
                    ))
                )}
            </SelectContent>
        </Select>
    );

    /** The Caleido Network picker. Unchanged source (GET /device-types); the value
     *  is `device_type.id`, which `devicesForPair` turns into real `device.id`s. */
    const renderNetworkSelect = (
        value: string, onChange: (next: string) => void, compact = false,
    ) => (
        <Select value={value} onValueChange={onChange}>
            <SelectTrigger className={triggerClass(compact)}>
                <SelectValue placeholder="Select Caleido Network" />
            </SelectTrigger>
            <SelectContent className={compact ? "bg-white" : "bg-popover"}>
                {caleidoNetworkOptions.length === 0 ? (
                    <div className="py-3 px-4 text-muted-foreground text-sm">
                        {deviceTypesQuery.isLoading
                            ? "Loading device types..."
                            : deviceTypesQuery.error
                                ? describeApiError(deviceTypesQuery.error)
                                : "No data available"}
                    </div>
                ) : (
                    caleidoNetworkOptions.map(option => (
                        <SelectItem key={option.id} value={option.id}>{option.name}</SelectItem>
                    ))
                )}
            </SelectContent>
        </Select>
    );

    const renderCreateJobTab = () => {
        return (
            <div className="space-y-6">
                <Card className="border-0 shadow-lg rounded-2xl bg-white">
                    <CardContent className="p-6">
                        <div className="space-y-6">
                            {/* Work/Purchase Order Reference */}
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Work/Purchase Order Reference</Label>
                                <div className="col-span-2">
                                    <Input
                                        placeholder="Leave blank to continue the JO-YYYY-NNNN sequence"
                                        value={workPurchaseRef}
                                        onChange={(e) => setWorkPurchaseRef(e.target.value)}
                                        maxLength={20}
                                        className="bg-muted/30 border-border/50"
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
                                        maxLength={200}
                                        className="bg-muted/30 border-border/50 min-h-[80px]"
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
                                        className="bg-amber-500 border-border/50 text-white"
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
                                        className="bg-amber-500 border-border/50 text-white"
                                    />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Rooms & Caleido Network Section */}
                <Card className="border-0 shadow-lg rounded-2xl bg-white">
                    <CardContent className="p-6">
                        <div className="space-y-6">
                            {/* Rooms */}
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Rooms<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    {renderRoomSelect(selectedRoom, setSelectedRoom)}
                                </div>
                            </div>

                            {/* Caleido Network */}
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Caleido Network<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    {renderNetworkSelect(selectedCaleidoNetwork, setSelectedCaleidoNetwork)}
                                </div>
                            </div>

                            {/* Add Button */}
                            <div className="flex justify-center">
                                <Button
                                    onClick={handleAddRoom}
                                    disabled={!selectedRoom || !selectedCaleidoNetwork}
                                    className="h-10 px-8 min-w-[160px] rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                                >
                                    Add
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Added Rooms Table */}
                <Card className="border-0 shadow-lg rounded-2xl bg-white">
                    <CardContent className="p-6">
                        <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                        <TableHead className="text-gray-600 font-medium">Rooms</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Caleido Network</TableHead>
                                        <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {addedRooms.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                                                No rooms added yet. Select a room and network above.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        addedRooms.map((item, index) => (
                                            <TableRow key={`${item.amenityId}-${item.deviceTypeId}`} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                                <TableCell>{item.roomName}</TableCell>
                                                <TableCell>
                                                    {item.deviceTypeName}
                                                    <span className="text-muted-foreground text-xs ml-2">
                                                        {item.deviceIds.length === 0
                                                            ? "(no device in this room)"
                                                            : `(${item.deviceIds.length} device${item.deviceIds.length > 1 ? "s" : ""})`}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    <Button size="sm" onClick={() => handleRemoveRoom(index)} className="bg-red-500 hover:bg-red-600 h-8 w-8 p-0">
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>

                        {/* Submit Button */}
                        <div className="flex justify-center gap-4 mt-6">
                            <Button
                                onClick={handleReset}
                                className="bg-gray-500 hover:bg-gray-600 text-white px-8"
                            >
                                Reset
                            </Button>
                            <Button
                                onClick={handleSubmit}
                                disabled={!mayWrite || createJobOrder.isPending}
                                title={mayWrite ? "Create this job order" : "Your role cannot create job orders"}
                                className="bg-cyan-600 hover:bg-cyan-700 text-white px-12"
                            >
                                {createJobOrder.isPending ? "Submitting..." : "Submit"}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    };

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
                            placeholder="Work/Purchase order, description, room no"
                            value={searchQuery}
                            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                            className="w-72 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                        />
                    </div>
                </div>

                <DataState
                    isLoading={jobOrdersQuery.isLoading}
                    error={jobOrdersQuery.error}
                    isEmpty={filteredJobOrders.length === 0}
                    emptyTitle="No job orders found"
                    emptyDescription={
                        jobOrders.length === 0
                            ? "Nothing in `job_order` yet. Create one from the Create Job tab."
                            : "No job order matches that search."
                    }
                    loader={<TableLoading rows={5} columns={9} />}
                >
                    <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Job ID</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Job Description</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Work/Purchase Order</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Rooms &amp; devices</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Type of Work</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Work Commence</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Estimate Completion Date</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Printout</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedJobOrders.map((job, index) => (
                                    <TableRow key={job.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                        {/* `job_order` has one human reference; the row's own id
                                            is a UUID, shortened here with the full value on hover. */}
                                        <TableCell className="text-cyan-600 whitespace-nowrap" title={job.id}>
                                            {job.id.slice(0, 8)}
                                        </TableCell>
                                        <TableCell className="whitespace-nowrap max-w-[260px] truncate" title={job.description ?? ""}>
                                            {job.description ?? "-"}
                                        </TableCell>
                                        <TableCell className="whitespace-nowrap">{job.order_reference}</TableCell>
                                        <TableCell
                                            className="whitespace-nowrap"
                                            title={[
                                                job.rooms.map((room) => room.room_name).join(", "),
                                                job.devices.map((device) => device.device_type_name ?? device.device_uid).join(", "),
                                            ].filter(Boolean).join(" | ")}
                                        >
                                            {job.room_count} room{job.room_count === 1 ? "" : "s"}
                                            {", "}
                                            {job.device_count} device{job.device_count === 1 ? "" : "s"}
                                        </TableCell>
                                        <TableCell className="whitespace-nowrap capitalize">{job.type_of_work}</TableCell>
                                        <TableCell className="whitespace-nowrap">{toDateInput(job.work_commence)}</TableCell>
                                        <TableCell className="whitespace-nowrap">{toDateInput(job.estimated_completion_date)}</TableCell>
                                        <TableCell className="text-center">
                                            <Button
                                                size="sm"
                                                className="bg-cyan-600 hover:bg-cyan-700 h-8 w-8 p-0"
                                                onClick={() => handleEditClick(job)}
                                                disabled={!mayWrite}
                                                title={mayWrite ? "Edit this job order" : "Your role cannot edit job orders"}
                                            >
                                                <Pencil className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <Button
                                                size="sm"
                                                className="bg-amber-500 hover:bg-amber-600 h-8 w-8 p-0"
                                                onClick={() => window.print()}
                                                title="Print this page"
                                            >
                                                <Printer className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing {startIndex + 1} to {Math.min(endIndex, filteredJobOrders.length)} of {filteredJobOrders.length} entries
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
                </DataState>
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
                            <Input
                                placeholder="Enter Work/Purchase Order Reference"
                                value={editForm.orderReference}
                                onChange={(e) => setEditForm({ ...editForm, orderReference: e.target.value })}
                                maxLength={20}
                                className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl"
                            />
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Type Of Work <span className="text-red-500">*</span></Label>
                            <RadioGroup
                                value={editForm.typeOfWork}
                                onValueChange={(value) => setEditForm({ ...editForm, typeOfWork: value })}
                                className="flex gap-4"
                            >
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
                            <Input
                                placeholder="Enter Job Description"
                                value={editForm.description}
                                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                                maxLength={200}
                                className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8"
                            />
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center pt-8">
                            <Label className="text-sm font-medium text-gray-700">Work Commence <span className="text-red-500">*</span></Label>
                            <Input
                                type="date"
                                value={editForm.workCommence}
                                onChange={(e) => setEditForm({ ...editForm, workCommence: e.target.value })}
                                className="bg-white border border-gray-300 text-foreground rounded-sm h-8 max-w-2xl px-3"
                            />
                        </div>

                        <div className="grid grid-cols-[260px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Estimate Complete Date <span className="text-red-500">*</span></Label>
                            <Input
                                type="date"
                                value={editForm.estimateCompleteDate}
                                onChange={(e) => setEditForm({ ...editForm, estimateCompleteDate: e.target.value })}
                                className="bg-white border border-gray-300 text-foreground rounded-sm h-8 max-w-2xl px-3"
                            />
                        </div>

                        <div className="border border-gray-200 rounded-md px-6 py-8 mt-6">
                            <div className="space-y-6">
                                <div className="grid grid-cols-[212px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-700">Rooms <span className="text-red-500">*</span></Label>
                                    {renderRoomSelect(editSelectedRoom, setEditSelectedRoom, true)}
                                </div>

                                <div className="grid grid-cols-[212px_1fr] gap-6 items-center">
                                    <Label className="text-sm font-medium text-gray-700">Caleido Network <span className="text-red-500">*</span></Label>
                                    {renderNetworkSelect(editSelectedNetwork, setEditSelectedNetwork, true)}
                                </div>

                                <div className="flex justify-center pt-4">
                                    <Button
                                        onClick={handleEditAddRoom}
                                        disabled={!editSelectedRoom || !editSelectedNetwork}
                                        className="bg-[#1f899e] hover:bg-[#1f899e]/90 text-white h-7 px-5 rounded-sm text-xs border border-[#1f899e]"
                                    >
                                        Add Job
                                    </Button>
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
                                    {editRooms.length === 0 ? (
                                        <TableRow className="border-0 hover:bg-transparent">
                                            <TableCell colSpan={4} className="h-8 text-center text-xs text-muted-foreground">
                                                No rooms on this job order.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        editRooms.map((row, index) => (
                                            <TableRow key={`${row.amenityId}-${row.deviceTypeId}`} className="border-b border-gray-100">
                                                <TableCell className="text-center text-xs">{index + 1}</TableCell>
                                                <TableCell className="text-center text-xs">{row.roomName}</TableCell>
                                                <TableCell className="text-center text-xs">{row.deviceTypeName}</TableCell>
                                                <TableCell className="text-center">
                                                    <Button
                                                        size="sm"
                                                        onClick={() => setEditRooms(editRooms.filter((_, i) => i !== index))}
                                                        className="bg-red-500 hover:bg-red-600 h-6 w-6 p-0"
                                                    >
                                                        <Trash2 className="h-3 w-3" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>

                        <div className="flex justify-center mt-2 pb-4">
                            <Button
                                onClick={handleUpdate}
                                disabled={!mayWrite || updateJobOrder.isPending}
                                className="bg-[#1f899e] hover:bg-[#1f899e]/90 text-white h-7 px-6 rounded-sm text-xs border border-[#1f899e]"
                            >
                                {updateJobOrder.isPending ? "Updating..." : "Update"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default JobOrder;
