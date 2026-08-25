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
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Search, ChevronLeft, ChevronRight, Eye, Edit, Check, X, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/core/contexts/AuthContext";
import { DataState, TableLoading } from "@/core/components/DataState";
import { describeApiError } from "@/lib/api/client";
import {
    useDepartments,
    useMaintenanceRequests,
    useRooms,
    useServiceCategories,
    useServiceTypes,
    useUsers,
} from "@/lib/api/hooks";
import {
    useCreateMaintenanceRequest,
    useRemoveMaintenanceRequest,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { MaintenanceRequestWrite } from "@/lib/api/writes";

type TabType = "scheduled" | "maintenance" | "disinfection";

/**
 * Services Planning, connected to the maintenance APIs.
 *
 *   GET    /maintenance-requests?request_type=  the tab's rows
 *   POST   /maintenance-requests               create (rooms + staff + rule)
 *   DELETE /maintenance-requests/{id}          soft delete (status = 0)
 *
 * The three tabs are the `maintenance_request_type` enum -- `scheduled`,
 * `planned` and `disinfection` -- one table, not three. Rooms come from
 * `maintenance_request_amenity`, assignees from `maintenance_request_assignee`
 * and the weekly rule from `maintenance_request_recurrence`.
 *
 * "Services Type" is NOT stored on the request: the schema reaches it through
 * `category_id` -> `service_category.service_type`, so the picker filters the
 * Facility Services list rather than being submitted.
 */

const ServicePlanning = () => {
    // --- Live data. Every picker below is populated from a real endpoint, and
    // every option's VALUE is the row's UUID; only the label is human-readable.
    const { canWrite } = useAuth();
    const mayWrite = canWrite("service_planning");

    const categoriesQuery = useServiceCategories({ page: 1, page_size: MAX_PAGE_SIZE });
    const serviceTypesQuery = useServiceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const departmentsQuery = useDepartments({ page: 1, page_size: MAX_PAGE_SIZE });
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
    // Assignment is to STAFF -- the backend refuses a guest.
    const staffQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 });

    const createPlan = useCreateMaintenanceRequest();
    const removePlan = useRemoveMaintenanceRequest();

    const [activeTab, setActiveTab] = useState<TabType>("scheduled");
    // The tab's own rows, filtered BY THE BACKEND on request_type.
    const plansQuery = useMaintenanceRequests({
        page: 1,
        page_size: MAX_PAGE_SIZE,
        request_type:
            activeTab === "scheduled"
                ? "scheduled"
                : activeTab === "maintenance"
                  ? "planned"
                  : "disinfection",
    });
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [editModalOpen, setEditModalOpen] = useState(false);

    // Form states for Scheduled Services
    const [scheduledForm, setScheduledForm] = useState({
        facilityServices: "",
        serviceType: "",
        department: "",
        assignTo: "",
        startTime: "",
        endTime: "",
        rooms: "rooms",
        roomNo: "",
        frequency: [] as string[],
        repeatWeekly: false,
    });

    // Form states for Plan Maintenance
    const [maintenanceForm, setMaintenanceForm] = useState({
        facilityServices: "",
        serviceType: "",
        department: "",
        assignTo: "",
        fromDate: "",
        toDate: "",
        startTime: "",
        endTime: "",
        rooms: "rooms",
        roomNo: "",
        underMaintenance: false,
    });

    // Form states for Disinfection
    const [disinfectionForm, setDisinfectionForm] = useState({
        sanitizerServices: "",
        serviceType: "",
        department: "",
        assignTo: "",
        startTime: "",
        endTime: "",
        rooms: "rooms",
        roomNo: "",
        frequency: [] as string[],
        repeatWeekly: false,
    });

    const tabs = [
        { id: "scheduled" as TabType, label: "Scheduled Services" },
        { id: "maintenance" as TabType, label: "Plan Maintenance" },
        { id: "disinfection" as TabType, label: "Disinfection Schedule" },
    ];

    const todayIso = new Date().toISOString().slice(0, 10);

    /** The service type chosen on whichever tab is in view. */
    const currentFormServiceType = () =>
        activeTab === "scheduled"
            ? scheduledForm.serviceType
            : activeTab === "maintenance"
              ? maintenanceForm.serviceType
              : disinfectionForm.serviceType;

    // --- Option lists, straight from the APIs. `id` is what gets submitted.
    type Option = { id: string; label: string };

    const serviceTypeOptions: Option[] = (serviceTypesQuery.data?.items ?? []).map((row) => ({
        id: String(row.id),
        label: row.name,
    }));

    /**
     * `maintenance_request` has NO service-type column -- the link is
     * `category_id` -> `service_category.service_type`. So "Services Type" is
     * not submitted; it narrows the Facility Services list through that real FK.
     */
    const selectedServiceType = currentFormServiceType();
    const categoryOptions: Option[] = (categoriesQuery.data?.items ?? [])
        .filter(
            (row) =>
                !selectedServiceType || String(row.service_type) === selectedServiceType,
        )
        .map((row) => ({
            id: row.id,
            label: [row.category_name ?? "-", row.service_type_name]
                .filter(Boolean)
                .join(" - "),
        }));
    const departmentOptions: Option[] = (departmentsQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        label: row.department_name,
    }));
    const staffOptions: Option[] = (staffQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        label: [row.first_name, row.last_name].filter(Boolean).join(" ") || row.user_name || "-",
    }));
    const roomOptions: Option[] = (roomsQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        label: row.amenity_type_name ? `${row.name} - ${row.amenity_type_name}` : row.name,
    }));

    /** Format a stored timestamptz as the HH:mm the table columns show. */
    const asTime = (value: string | null) =>
        value ? new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "-";

    /**
     * The tab's rows, mapped onto the existing column keys so the table markup
     * is untouched. Rooms and assignees are joined for display; the row keeps
     * its `id` so Remove can act on the real record.
     */
    const planRows = (plansQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        facilityServices: row.category_name ?? "-",
        sanitizerServices: row.category_name ?? "-",
        serviceType: row.service_type_name ?? "-",
        department: row.department_name ?? "-",
        assignTo: row.assignees.map((person) => person.name).join(", ") || "-",
        date: row.maintenance_start_date ?? "-",
        fromDate: row.maintenance_start_date ?? "-",
        toDate: row.maintenance_end_date ?? "-",
        startTime: asTime(row.maintenance_start_time),
        endTime: asTime(row.maintenance_end_time),
        roomNo: row.rooms.map((room) => room.room_name).filter(Boolean).join(", ")
            || row.non_room_comments
            || "-",
        underMaintenance: row.under_maintenance ? "Yes" : "No",
        status: row.status_name ?? "-",
    }));

    /** One table row, derived from the live payload rather than declared twice. */
    type PlanRow = (typeof planRows)[number];

    // --- Search and pagination, both driven by the rows actually fetched.
    // The whole tab is fetched in one page (`MAX_PAGE_SIZE` above), so the
    // Search box and the "Show N entries" picker narrow that list here instead
    // of re-querying. Previously neither control did anything and the footer
    // printed fixed numbers, which made the table look paginated when it was not.
    const searchTerm = searchQuery.trim().toLowerCase();
    const filteredRows = searchTerm
        ? planRows.filter((row) =>
              [row.facilityServices, row.serviceType, row.roomNo].some((field) =>
                  field.toLowerCase().includes(searchTerm),
              ),
          )
        : planRows;

    const pageSize = Math.max(1, parseInt(entriesPerPage, 10) || 10);
    const totalRows = filteredRows.length;
    const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
    // A tab switch, a search or a smaller page size can leave `currentPage`
    // past the end; clamp on render so the table never shows a blank page.
    const activePage = Math.min(currentPage, totalPages);
    const startIndex = (activePage - 1) * pageSize;
    const paginatedRows = filteredRows.slice(startIndex, startIndex + pageSize);

    /** Up to five page buttons, centred on the current page. */
    const pageNumbers = (() => {
        const span = Math.min(5, totalPages);
        const first = Math.max(1, Math.min(activePage - Math.floor(span / 2), totalPages - span + 1));
        return Array.from({ length: span }, (_, offset) => first + offset);
    })();

    /** Render a picker's options, with honest loading/error/empty states. */
    const renderOptions = (
        options: Option[],
        query: { isLoading: boolean; error: unknown },
        emptyLabel: string,
    ) => {
        if (query.isLoading) {
            return (
                <div className="px-3 py-2 text-sm text-muted-foreground">Loading...</div>
            );
        }
        if (query.error) {
            return (
                <div className="px-3 py-2 text-sm text-muted-foreground">
                    {describeApiError(query.error)}
                </div>
            );
        }
        if (options.length === 0) {
            return (
                <div className="px-3 py-2 text-sm text-muted-foreground">{emptyLabel}</div>
            );
        }
        return options.map((option) => (
            <SelectItem key={option.id} value={option.id}>
                {option.label}
            </SelectItem>
        ));
    };

    const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    /** The tab IS the `maintenance_request_type` enum value. */
    const REQUEST_TYPE: Record<TabType, MaintenanceRequestWrite["maintenance_request_type"]> = {
        scheduled: "scheduled",
        maintenance: "planned",
        disinfection: "disinfection",
    };

    /** The form for whichever tab is in view. */
    const currentForm =
        activeTab === "scheduled"
            ? scheduledForm
            : activeTab === "maintenance"
              ? maintenanceForm
              : disinfectionForm;

    /**
     * Combine a date with the form's `HH:mm` into an ISO timestamp.
     * `maintenance_start_time` is a real timestamptz, not a VARCHAR.
     */
    const toTimestamp = (day: string, time: string) =>
        day && time ? new Date(`${day}T${time}`).toISOString() : null;

    /**
     * Create the planned service.
     *
     * Every id sent is a real UUID chosen from the pickers above -- the
     * category, the department, the assignee and the room. The recurrence rule
     * goes as `day_labels`, which the backend encodes into the stored bitmask.
     */
    const handleSubmit = () => {
        const form = currentForm as typeof scheduledForm & typeof maintenanceForm &
            typeof disinfectionForm;
        const categoryId = (form.facilityServices || form.sanitizerServices || "").trim();
        // Plan Maintenance has its own from/to; the other tabs are single-day.
        const startDay = (form.fromDate || "").trim() || todayIso;
        const endDay = (form.toDate || "").trim() || startDay;

        if (!categoryId) {
            toast({
                title: "Facility service is required",
                description: "Pick the service category this plan covers.",
                variant: "destructive",
            });
            return;
        }
        const roomIds = form.roomNo ? [form.roomNo] : [];
        if (form.rooms === "rooms" && roomIds.length === 0) {
            toast({
                title: "Select a room",
                description:
                    "A room plan needs at least one room, or switch to Non Rooms " +
                    "and describe the area instead.",
                variant: "destructive",
            });
            return;
        }

        const body: MaintenanceRequestWrite = {
            maintenance_request_type: REQUEST_TYPE[activeTab],
            maintenance_start_date: startDay,
            maintenance_end_date: endDay,
            maintenance_start_time: toTimestamp(startDay, form.startTime),
            maintenance_end_time: toTimestamp(endDay, form.endTime),
            department_id: form.department || null,
            category_id: categoryId,
            amenity_ids: roomIds,
            assignee_ids: form.assignTo ? [form.assignTo] : [],
            ...(form.rooms === "rooms"
                ? {}
                  // The form has no free-text field for a non-room area, so the
                  // area is recorded from the chosen mode. `non_room_comments`
                  // is the only column the schema offers for it.
                  : { non_room_comments: "Non-room area" }),
            ...(activeTab === "maintenance"
                ? { under_maintenance: Boolean(form.underMaintenance) }
                : {}),
            // `is_recurring` is derived server-side from the rule's presence.
            ...(form.repeatWeekly && form.frequency?.length
                ? {
                      recurrence: {
                          recurrence_type: "weekly" as const,
                          day_labels: form.frequency,
                      },
                  }
                : {}),
        };

        createPlan.mutate(body, { onSuccess: handleReset });
    };

    /** Retire a plan -- the project's soft delete (`status = 0`). */
    const handleRemove = (id: string) => {
        removePlan.mutate({ id, comments: "Removed from Service Planning" });
    };

    const handleReset = () => {
        if (activeTab === "scheduled") {
            setScheduledForm({
                facilityServices: "",
                serviceType: "",
                department: "",
                assignTo: "",
                startTime: "",
                endTime: "",
                rooms: "rooms",
                roomNo: "",
                frequency: [],
                repeatWeekly: false,
            });
        } else if (activeTab === "maintenance") {
            setMaintenanceForm({
                facilityServices: "",
                serviceType: "",
                department: "",
                assignTo: "",
                fromDate: "",
                toDate: "",
                startTime: "",
                endTime: "",
                rooms: "rooms",
                roomNo: "",
                underMaintenance: false,
            });
        } else {
            setDisinfectionForm({
                sanitizerServices: "",
                serviceType: "",
                department: "",
                assignTo: "",
                startTime: "",
                endTime: "",
                rooms: "rooms",
                roomNo: "",
                frequency: [],
                repeatWeekly: false,
            });
        }
    };

    const toggleFrequency = (day: string, formType: "scheduled" | "disinfection") => {
        if (formType === "scheduled") {
            setScheduledForm((prev) => ({
                ...prev,
                frequency: prev.frequency.includes(day)
                    ? prev.frequency.filter((d) => d !== day)
                    : [...prev.frequency, day],
            }));
        } else {
            setDisinfectionForm((prev) => ({
                ...prev,
                frequency: prev.frequency.includes(day)
                    ? prev.frequency.filter((d) => d !== day)
                    : [...prev.frequency, day],
            }));
        }
    };

    const renderScheduledServicesForm = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Facility Services <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={scheduledForm.facilityServices}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, facilityServices: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Facility Services" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(categoryOptions, categoriesQuery, "No service category")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Services Type <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={scheduledForm.serviceType}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, serviceType: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Service Type" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(serviceTypeOptions, serviceTypesQuery, "No service type")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Department</Label>
                    <Select
                        value={scheduledForm.department}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, department: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Department" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(departmentOptions, departmentsQuery, "No department")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Assign To</Label>
                    <Select
                        value={scheduledForm.assignTo}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, assignTo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Employee" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(staffOptions, staffQuery, "No staff on record")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Start Time <span className="text-red-500">*</span>
                    </Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={23}
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={59}
                        />
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
                            AM
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">End Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={23}
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                            min={0}
                            max={59}
                        />
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
                            AM
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Rooms</Label>
                    <RadioGroup
                        value={scheduledForm.rooms}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, rooms: v })}
                        className="flex gap-4"
                    >
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="rooms" id="rooms" />
                            <Label htmlFor="rooms" className="cursor-pointer">Rooms</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="non-rooms" id="non-rooms" />
                            <Label htmlFor="non-rooms" className="cursor-pointer">Non-Rooms</Label>
                        </div>
                    </RadioGroup>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Room No</Label>
                    <Select
                        value={scheduledForm.roomNo}
                        onValueChange={(v) => setScheduledForm({ ...scheduledForm, roomNo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Room" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(roomOptions, roomsQuery, "No room")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Frequency</Label>
                    <div className="flex flex-wrap gap-2">
                        {weekDays.map((day) => (
                            <Button
                                key={day}
                                variant={scheduledForm.frequency.includes(day) ? "default" : "outline"}
                                size="sm"
                                className={`w-12 ${scheduledForm.frequency.includes(day)
                                    ? "bg-cyan-600 text-white"
                                    : "bg-muted/30 border-border/50"
                                    }`}
                                onClick={() => toggleFrequency(day, "scheduled")}
                            >
                                {day}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium">Repeat Weekly</Label>
                    <Switch
                        checked={scheduledForm.repeatWeekly}
                        onCheckedChange={(v) => setScheduledForm({ ...scheduledForm, repeatWeekly: v })}
                    />
                </div>
            </div>
        </div>
    );

    const renderPlanMaintenanceForm = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Facility Services</Label>
                    <Select
                        value={maintenanceForm.facilityServices}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, facilityServices: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Facility Services" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(categoryOptions, categoriesQuery, "No service category")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Service Type <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={maintenanceForm.serviceType}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, serviceType: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Service Type" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(serviceTypeOptions, serviceTypesQuery, "No service type")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Department <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={maintenanceForm.department}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, department: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Department" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(departmentOptions, departmentsQuery, "No department")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Assign To</Label>
                    <Select
                        value={maintenanceForm.assignTo}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, assignTo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Employee" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(staffOptions, staffQuery, "No staff on record")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        From Date <span className="text-red-500">*</span>
                    </Label>
                    <Input
                        type="date"
                        className="h-10 bg-muted/30 border-border/50"
                        value={maintenanceForm.fromDate}
                        onChange={(e) => setMaintenanceForm({ ...maintenanceForm, fromDate: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">To Date</Label>
                    <Input
                        type="date"
                        className="h-10 bg-muted/30 border-border/50"
                        value={maintenanceForm.toDate}
                        onChange={(e) => setMaintenanceForm({ ...maintenanceForm, toDate: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Start Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
                            AM
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">End Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
                            AM
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Rooms</Label>
                    <RadioGroup
                        value={maintenanceForm.rooms}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, rooms: v })}
                        className="flex gap-4"
                    >
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="rooms" id="maint-rooms" />
                            <Label htmlFor="maint-rooms" className="cursor-pointer">Rooms</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="non-rooms" id="maint-non-rooms" />
                            <Label htmlFor="maint-non-rooms" className="cursor-pointer">Non-Rooms</Label>
                        </div>
                    </RadioGroup>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Room No</Label>
                    <Select
                        value={maintenanceForm.roomNo}
                        onValueChange={(v) => setMaintenanceForm({ ...maintenanceForm, roomNo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Room" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(roomOptions, roomsQuery, "No room")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium">Under Maintenance</Label>
                    <Switch
                        checked={maintenanceForm.underMaintenance}
                        onCheckedChange={(v) => setMaintenanceForm({ ...maintenanceForm, underMaintenance: v })}
                    />
                </div>
            </div>
        </div>
    );

    const renderDisinfectionForm = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Sanitizer Services <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={disinfectionForm.sanitizerServices}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, sanitizerServices: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Sanitizer Services" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(categoryOptions, categoriesQuery, "No service category")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Service Type <span className="text-red-500">*</span>
                    </Label>
                    <Select
                        value={disinfectionForm.serviceType}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, serviceType: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Service Type" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(serviceTypeOptions, serviceTypesQuery, "No service type")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Department</Label>
                    <Select
                        value={disinfectionForm.department}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, department: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Department" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(departmentOptions, departmentsQuery, "No department")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Assign To</Label>
                    <Select
                        value={disinfectionForm.assignTo}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, assignTo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Employee" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(staffOptions, staffQuery, "No staff on record")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-primary text-sm font-medium">
                        Start Time <span className="text-red-500">*</span>
                    </Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
                            AM
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">End Time</Label>
                    <div className="flex items-center gap-2">
                        <Input
                            type="number"
                            placeholder="HH"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <span>:</span>
                        <Input
                            type="number"
                            placeholder="MM"
                            className="w-16 h-10 bg-muted/30 border-border/50 text-center"
                        />
                        <Button variant="outline" size="sm" className="bg-cyan-600 text-white border-0">
                            AM
                        </Button>
                    </div>
                </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label className="text-sm font-medium">Rooms</Label>
                    <RadioGroup
                        value={disinfectionForm.rooms}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, rooms: v })}
                        className="flex gap-4"
                    >
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="rooms" id="dis-rooms" />
                            <Label htmlFor="dis-rooms" className="cursor-pointer">Rooms</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <RadioGroupItem value="non-rooms" id="dis-non-rooms" />
                            <Label htmlFor="dis-non-rooms" className="cursor-pointer">Non-Rooms</Label>
                        </div>
                    </RadioGroup>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Room No</Label>
                    <Select
                        value={disinfectionForm.roomNo}
                        onValueChange={(v) => setDisinfectionForm({ ...disinfectionForm, roomNo: v })}
                    >
                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                            <SelectValue placeholder="Select Room" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover">
                            {renderOptions(roomOptions, roomsQuery, "No room")}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-sm font-medium">Frequency</Label>
                    <div className="flex flex-wrap gap-2">
                        {weekDays.map((day) => (
                            <Button
                                key={day}
                                variant={disinfectionForm.frequency.includes(day) ? "default" : "outline"}
                                size="sm"
                                className={`w-12 ${disinfectionForm.frequency.includes(day)
                                    ? "bg-cyan-600 text-white"
                                    : "bg-muted/30 border-border/50"
                                    }`}
                                onClick={() => toggleFrequency(day, "disinfection")}
                            >
                                {day}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <Label className="text-sm font-medium">Repeat Weekly</Label>
                    <Switch
                        checked={disinfectionForm.repeatWeekly}
                        onCheckedChange={(v) => setDisinfectionForm({ ...disinfectionForm, repeatWeekly: v })}
                    />
                </div>
            </div>
        </div>
    );

    const renderTable = () => {
        // Every tab renders the same rows; only the column set differs, because
        // all three are one `maintenance_request` table filtered by request_type.
        const data: PlanRow[] = paginatedRows;
        let columns: { key: keyof PlanRow; label: string }[] = [];

        if (activeTab === "scheduled") {
            columns = [
                { key: "facilityServices", label: "Facility Services" },
                { key: "serviceType", label: "Service Type" },
                { key: "department", label: "Department" },
                { key: "assignTo", label: "Assign To" },
                { key: "date", label: "Date" },
                { key: "startTime", label: "Start Time" },
                { key: "endTime", label: "End Time" },
                { key: "roomNo", label: "Room No" },
            ];
        } else if (activeTab === "maintenance") {
            columns = [
                { key: "facilityServices", label: "Facility Services" },
                { key: "serviceType", label: "Service Type" },
                { key: "department", label: "Department" },
                { key: "assignTo", label: "Assign To" },
                { key: "fromDate", label: "From Date" },
                { key: "toDate", label: "To Date" },
                { key: "startTime", label: "Start Time" },
                { key: "endTime", label: "End Time" },
                { key: "roomNo", label: "Room No" },
                { key: "underMaintenance", label: "Under Maintenance" },
            ];
        } else {
            columns = [
                { key: "sanitizerServices", label: "Sanitizer Services" },
                { key: "serviceType", label: "Service Type" },
                { key: "department", label: "Department" },
                { key: "assignTo", label: "Assign To" },
                { key: "date", label: "Date" },
                { key: "startTime", label: "Start Time" },
                { key: "endTime", label: "End Time" },
                { key: "roomNo", label: "Room No" },
            ];
        }

        return (
            <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                            {columns.map((col) => (
                                <TableHead key={col.key} className="text-gray-600 font-medium">
                                    {col.label}
                                </TableHead>
                            ))}
                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {/* One shared loading / error / empty state, so a failing
                            list never renders as an empty table. */}
                        {plansQuery.isLoading || plansQuery.error || data.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={columns.length + 1} className="py-2">
                                    <DataState
                                        isLoading={plansQuery.isLoading}
                                        error={plansQuery.error}
                                        isEmpty
                                        emptyTitle={
                                            searchTerm
                                                ? "No planned services match that search"
                                                : "No planned services yet"
                                        }
                                        emptyDescription={
                                            searchTerm
                                                ? "Clear the search box to see the whole list."
                                                : "Create one with the form above."
                                        }
                                        loader={<TableLoading columns={columns.length + 1} />}
                                    >
                                        <span />
                                    </DataState>
                                </TableCell>
                            </TableRow>
                        ) : (
                        data.map((row, index) => (
                            <TableRow
                                key={row.id}
                                className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"
                                    } hover:bg-muted/40 transition-colors`}
                            >
                                {columns.map((col) => (
                                    <TableCell key={col.key}>
                                        {col.key === "assignTo" || col.key === "roomNo" ? (
                                            <span className="text-cyan-400 cursor-pointer hover:underline">
                                                {row[col.key]}
                                            </span>
                                        ) : col.key === "underMaintenance" ? (
                                            <Badge
                                                className={
                                                    row[col.key] === "Yes"
                                                        ? "bg-green-500/20 text-green-500"
                                                        : "bg-gray-500/20 text-gray-400"
                                                }
                                            >
                                                {row[col.key]}
                                            </Badge>
                                        ) : (
                                            row[col.key]
                                        )}
                                    </TableCell>
                                ))}
                                <TableCell>
                                    <div className="flex items-center justify-center gap-2">
                                        <Button
                                            size="sm"
                                            className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]"
                                            onClick={() => setEditModalOpen(true)}
                                        >
                                            <Edit className="h-[14px] w-[14px]" />
                                        </Button>
                                        {/* Soft delete -- DELETE sets status = 0 and
                                            retires the room/assignee links with it. */}
                                        <Button
                                            size="sm"
                                            className="bg-[#d33] hover:bg-[#bd2d2d] text-white h-7 w-7 p-0 rounded-[3px]"
                                            disabled={!mayWrite || removePlan.isPending}
                                            title={
                                                mayWrite
                                                    ? "Remove this planned service"
                                                    : "Your role cannot change service planning"
                                            }
                                            onClick={() => handleRemove(row.id)}
                                        >
                                            <X className="h-[14px] w-[14px]" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        )))}
                    </TableBody>
                </Table>
            </div>
        );
    };

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Services Planning</h1>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 border-b border-gray-200">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => {
                            setActiveTab(tab.id);
                            // Each tab is its own query; page 3 of one tab is
                            // meaningless in the next.
                            setCurrentPage(1);
                        }}
                        className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === tab.id
                            ? "text-foreground"
                            : "text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {tab.label}
                        {activeTab === tab.id && (
                            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-600 rounded-t-full" />
                        )}
                    </button>
                ))}
            </div>

            {/* Form Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {activeTab === "scheduled" && renderScheduledServicesForm()}
                    {activeTab === "maintenance" && renderPlanMaintenanceForm()}
                    {activeTab === "disinfection" && renderDisinfectionForm()}

                    {/* Action Buttons */}
                    <div className="flex justify-center gap-4 pt-4 border-t border-border/30">
                        <Button
                            onClick={handleReset}
                            variant="outline"
                            className="h-10 px-8 bg-cyan-600 text-white border-0 hover:bg-cyan-700"
                        >
                            Reset
                        </Button>
                        <Button
                            onClick={handleSubmit}
                            disabled={!mayWrite || createPlan.isPending}
                            title={
                                mayWrite
                                    ? "Create this planned service"
                                    : "Your role cannot change service planning"
                            }
                            className="h-10 px-8 min-w-[120px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                        >
                            {createPlan.isPending ? "Saving..." : "Submit"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Data Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {/* Controls */}
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select
                                value={entriesPerPage}
                                onValueChange={(value) => {
                                    setEntriesPerPage(value);
                                    setCurrentPage(1);
                                }}
                            >
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    <SelectItem value="10">10</SelectItem>
                                    <SelectItem value="25">25</SelectItem>
                                    <SelectItem value="50">50</SelectItem>
                                    <SelectItem value="100">100</SelectItem>
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Facility services, Service type, Room No"
                                    value={searchQuery}
                                    onChange={(e) => {
                                        setSearchQuery(e.target.value);
                                        setCurrentPage(1);
                                    }}
                                    className="pl-10 w-80 h-9 bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Table */}
                    {renderTable()}

                    {/* Footer */}
                    <div className="flex items-center justify-between mt-6">
                        {/* Counts come from the rows actually fetched, so the
                            footer cannot disagree with the table above it. */}
                        <span className="text-muted-foreground text-sm">
                            Showing {totalRows === 0 ? 0 : startIndex + 1} to{" "}
                            {Math.min(startIndex + pageSize, totalRows)} of {totalRows} entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(1)}
                                disabled={activePage === 1}
                            >
                                First
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(Math.max(1, activePage - 1))}
                                disabled={activePage === 1}
                            >
                                <ChevronLeft className="h-4 w-4 mr-1" />
                                Previous
                            </Button>
                            {pageNumbers.map((page) => (
                                <Button
                                    key={page}
                                    variant={activePage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`w-9 h-9 p-0 ${activePage === page
                                        ? "bg-primary text-white"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    onClick={() => setCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            {pageNumbers[pageNumbers.length - 1] < totalPages && (
                                <span className="text-muted-foreground px-2">...</span>
                            )}
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(Math.min(totalPages, activePage + 1))}
                                disabled={activePage >= totalPages}
                            >
                                Next
                                <ChevronRight className="h-4 w-4 ml-1" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setCurrentPage(totalPages)}
                                disabled={activePage >= totalPages}
                            >
                                Last
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Edit Service Planning Modal */}
            <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
                <DialogContent className="max-w-[650px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-none">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Service Planning</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditModalOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>

                    <div className="px-12 py-10 space-y-6">
                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Sanitation Services <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-gray-100 border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-3 py-2 text-sm appearance-none outline-none rounded-t-[2px]">
                                    <option>Sanitation</option>
                                </select>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Services Type <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                    <option>Guest Room sanitation</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Department <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                    <option>Admin</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Assign To <span className="text-red-500">*</span></Label>
                            <div className="relative bg-gray-500 border border-gray-500 rounded-[2px] p-[2px] pr-8 flex items-center gap-1 h-[34px]">
                                <div className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-[2px] flex items-center gap-1">
                                    System User <X className="h-3 w-3 cursor-pointer hover:opacity-80" />
                                </div>
                                <div className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-[2px] flex items-center gap-1">
                                    Namas s <X className="h-3 w-3 cursor-pointer hover:opacity-80" />
                                </div>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-300 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-start">
                            <Label className="text-sm font-medium text-gray-800 text-left pt-6">Start Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="11" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <span className="text-xl font-bold pb-6">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="00" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <div className="pb-6">
                                    <div className="border border-[#3eb1c8] text-[#3eb1c8] rounded-[2px] px-3 py-[2px] text-[13px] font-medium cursor-pointer">AM</div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-start">
                            <Label className="text-sm font-medium text-gray-800 text-left pt-6">End Time <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-4">
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="12" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <span className="text-xl font-bold pb-6">:</span>
                                <div className="flex flex-col items-center">
                                    <ChevronUp className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                    <input type="text" value="00" readOnly className="w-12 text-center bg-transparent border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-0 pb-1 text-base outline-none cursor-default" />
                                    <ChevronDown className="h-5 w-5 text-[#3eb1c8] cursor-pointer" />
                                </div>
                                <div className="pb-6">
                                    <div className="border border-[#3eb1c8] text-[#3eb1c8] rounded-[2px] px-3 py-[2px] text-[13px] font-medium cursor-pointer">AM</div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Rooms <span className="text-red-500">*</span></Label>
                            <RadioGroup defaultValue="rooms" className="flex flex-col gap-2">
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="rooms" id="edit-rooms" className="text-[#3eb1c8] border-[#3eb1c8]" />
                                    <Label htmlFor="edit-rooms" className="cursor-pointer text-gray-900 font-normal">Rooms</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="non-rooms" id="edit-non-rooms" className="text-[#3eb1c8] border-gray-300" />
                                    <Label htmlFor="edit-non-rooms" className="cursor-pointer text-gray-900 font-normal">Non Rooms</Label>
                                </div>
                            </RadioGroup>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Room No <span className="text-red-500">*</span></Label>
                            <div className="relative border border-gray-500 rounded-[2px] p-[2px] pr-8 flex items-center gap-1 h-[34px]">
                                <div className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-[2px] flex items-center gap-1">
                                    211 <X className="h-3 w-3 cursor-pointer hover:opacity-80" />
                                </div>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Frequency <span className="text-red-500">*</span></Label>
                            <div className="flex bg-transparent border border-[#3eb1c8] rounded-[2px] w-fit overflow-hidden">
                                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day, idx) => (
                                    <div key={day} className={`px-3 py-1 text-xs font-medium cursor-pointer border-r border-[#3eb1c8] last:border-r-0 ${idx === 6 ? "bg-[#3eb1c8] text-white" : "text-gray-800 hover:bg-gray-100"}`}>
                                        {day}
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-800 text-left">Repeat Weekly <span className="text-red-500">*</span></Label>
                            <div className="flex items-center gap-2">
                                <Switch checked={true} className="data-[state=checked]:bg-[#4ad970]" />
                            </div>
                        </div>

                        <div className="flex justify-center gap-4 pt-4">
                            <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditModalOpen(false)}>Reset</Button>
                            <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditModalOpen(false)}>Submit</Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default ServicePlanning;




