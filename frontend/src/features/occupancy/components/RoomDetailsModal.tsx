import type { ReactNode } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CheckCircle, XCircle } from "lucide-react";
import { DataState } from "@/core/components/DataState";
import { useDevices, useOccupancyDetail, useServiceRequests } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { conditionLabel, roomStatusBadgeClass } from "../lib/roomStatus";
import { ConditionBadge } from "./ConditionBadge";
import { serviceStatusBadgeClass } from "../lib/serviceStatus";
import { DETAIL_GRID, EMPTY_VALUE, Field } from "./DetailField";
import { RoomPowerEnergy } from "./RoomPowerEnergy";

interface RoomDetailsModalProps {
    /** `amenity.id` -- everything in this dialog is fetched with it. */
    amenityId: string | null;
    roomNo: string | null;
    isOpen: boolean;
    onClose: () => void;
    roomType?: string;
    guestName?: string;
    status?: string;
    /**
     * The row's housekeeping conditions, already display-labelled -- what the
     * table's Status column showed. Used until the detail read lands.
     */
    conditions?: string[];
}

/**
 * The heading above each section, written once.
 *
 * The same five classes were repeated verbatim on all five section <h3>s.
 * Splitting the sections across tabs moved every one of them, so they are named
 * here rather than carried to a new home five times over.
 */
const SECTION_HEADING =
    "text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4";

/**
 * Column heading styling for the one table left in this dialog.
 *
 * The same string was pasted onto all seven <TableHead>s (and onto the eight of
 * the service-request table before it became cards). Named once so a change to
 * the header treatment cannot land on six columns and miss the seventh.
 * Alignment stays per-column: append `text-center` or `text-right`.
 */
const TABLE_HEAD =
    "text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3";

/**
 * One tab in the bar under the title.
 *
 * An underline rather than the shadcn default, which is a filled pill on a
 * `bg-muted` track -- that reads as a segmented control and fights the flat
 * slate surfaces this dialog is built from. The active tab brightens to
 * `text-foreground` and takes a `border-primary` rule; the inactive ones stay
 * on `text-muted-foreground`, which is the same muted slate the section
 * headings and field labels already use, so they remain legible rather than
 * greyed out. Typography matches SECTION_HEADING for the same reason.
 */
const TAB_TRIGGER = [
    "relative rounded-none border-b-2 border-transparent bg-transparent",
    "px-4 py-3 text-xs font-semibold uppercase tracking-wider",
    "text-muted-foreground shadow-none transition-colors",
    "hover:text-foreground",
    "data-[state=active]:border-primary data-[state=active]:bg-transparent",
    "data-[state=active]:text-foreground data-[state=active]:shadow-none",
    "focus-visible:ring-offset-0",
].join(" ");

/**
 * The scrolling body of one tab.
 *
 * `max-h-[70vh]` with `overflow-y-auto` is what keeps the dialog on screen:
 * DialogContent is capped at 90vh and no longer pinned to it, so a short tab
 * now makes a short modal instead of 90vh of dead space below the content.
 *
 * This replaced a Radix ScrollArea, and with it a workaround the old markup
 * needed. ScrollArea's viewport wraps its children in a `display: table` div,
 * which shrink-wraps to the WIDEST child; the device table is wider than the
 * modal, so that wrapper outgrew the viewport and the `overflow-x-auto`
 * container inside had nothing left to scroll. A plain block element takes its
 * parent's width, so that table scrolls sideways in its own container without
 * the `[&>[data-radix-scroll-area-viewport]>div]:!block` override that used to
 * force it. `scrollbar-thin` is the same scrollbar utility it already uses.
 */
const TabPanel = ({ value, children }: { value: string; children: ReactNode }) => (
    <TabsContent
        value={value}
        className="mt-0 focus-visible:ring-0 focus-visible:ring-offset-0"
    >
        <div className="max-h-[70vh] overflow-y-auto scrollbar-thin px-6">
            <div className="pt-6 pb-8 space-y-8">{children}</div>
        </div>
    </TabsContent>
);

const formatDate = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleDateString() : EMPTY_VALUE;

const formatDateTime = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString() : EMPTY_VALUE;

/**
 * Room detail dialog, fully backend-driven.
 *
 * The five sections are split across three tabs, because stacked end to end
 * they made a dialog an operator had to scroll through to reach anything:
 *
 *   Details                 room attributes + occupants
 *   Environment & Utilities device inventory + its power/energy readings
 *   Service Requests        the request log
 *
 * The title and status badge sit above the bar and stay fixed, so the room
 * being looked at is never in doubt. See TabPanel for how each tab is capped
 * and scrolled.
 *
 * Two deliberate changes to the mock's columns, because the data does not
 * exist and must not be invented:
 *
 *   - "MAC Address" is now "Device UID". Phase 2.6 established that `device`
 *     stores no MAC or IP address.
 *   - The maintenance table now shows the room's SERVICE REQUESTS with their
 *     real columns. `maintenance_request` exists in the schema but no Phase
 *     2.x endpoint exposes it, so its own columns (from/to date, start/stop
 *     time) have no source.
 *
 * Guest contact details, ID proof, nationality and pax are likewise absent:
 * the occupancy projection returns only `UserRef` (id, name, emp_id).
 *
 * The Power & Energy section is where the retired Power View and Energy View
 * live now. It reuses their reads, narrowed to this room's amenity id -- see
 * `RoomPowerEnergy` for the parameters, units and permission handling.
 */
export function RoomDetailsModal({
    amenityId,
    roomNo,
    isOpen,
    onClose,
    roomType = EMPTY_VALUE,
    guestName = EMPTY_VALUE,
    status = EMPTY_VALUE,
    conditions: rowConditions = [],
}: RoomDetailsModalProps) {
    const enabled = isOpen ? amenityId : null;
    const occupancyQuery = useOccupancyDetail(enabled);
    const devicesQuery = useDevices(
        enabled ? { amenity_id: enabled, page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    );
    const requestsQuery = useServiceRequests(
        enabled ? { amenity_id: enabled, page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    );

    if (!roomNo) return null;

    const occupancy = occupancyQuery.data;
    const stay = occupancy?.current_stay;
    const devices = devicesQuery.data?.items ?? [];
    const requests = requestsQuery.data?.items ?? [];
    // The detail read is live, so a condition edited while the dialog is open
    // shows here; the row's copy only covers the moment before it arrives.
    const conditions =
        occupancy?.conditions.map((condition) => conditionLabel(condition.name)) ?? rowConditions;

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col overflow-hidden p-0 bg-background text-foreground border-border">
                <DialogHeader className="shrink-0 p-6 pb-4">
                    <div className="flex items-center justify-between">
                        <DialogTitle className="text-xl font-semibold">
                            Room No: {roomNo}
                        </DialogTitle>
                        {/* The same pills as the table's Status column, which
                            shows housekeeping CONDITIONS (Sanitation, Under
                            maintenance...), not `amenity_status`. This badge used
                            to show `amenity_status` alone, so a room the table
                            marked Sanitation opened reading "Available" -- true
                            of the room flag, but not what the operator had just
                            clicked. With no condition set, the room status is
                            the most useful thing left to show. */}
                        {conditions.length > 0 ? (
                            <div className="mr-8 flex flex-wrap items-center justify-end gap-1.5">
                                {conditions.map((condition) => (
                                    <ConditionBadge key={condition} condition={condition} />
                                ))}
                            </div>
                        ) : (
                            <Badge
                                variant="outline"
                                className={`mr-8 ${roomStatusBadgeClass(occupancy?.status_name ?? status)}`}
                            >
                                {occupancy?.status_name ?? status}
                            </Badge>
                        )}
                    </div>
                </DialogHeader>

                {/* Three tabs, in the order an operator reads the room:
                    who and what it is, then how it is behaving, then what has
                    been asked of it. The title and status badge above stay put
                    -- they identify the room whichever tab is open.

                    Inactive panels unmount, which is Radix's default and the
                    one behavioural consequence of tabbing this dialog up: the
                    three queries in this component still run the moment the
                    dialog opens, but RoomPowerEnergy owns its own reads and so
                    does not issue them until its tab is first shown. React
                    Query serves the cache on every later visit. Add
                    `forceMount` to the panels to restore eager fetching. */}
                <Tabs defaultValue="details" className="flex min-h-0 flex-1 flex-col">
                    <TabsList className="h-auto w-full shrink-0 justify-start gap-2 rounded-none border-b border-border bg-transparent p-0 px-6 dark:border-slate-800">
                        <TabsTrigger value="details" className={TAB_TRIGGER}>
                            Details
                        </TabsTrigger>
                        <TabsTrigger value="environment" className={TAB_TRIGGER}>
                            Environment &amp; Utilities
                        </TabsTrigger>
                        <TabsTrigger value="requests" className={TAB_TRIGGER}>
                            Service Requests
                        </TabsTrigger>
                    </TabsList>

                    {/* Tab 1 -- the room itself and who is in it. */}
                    <TabPanel value="details">
                        {/* Room Details Section.
                            The rule underneath is the only section divider in
                            the dialog, and it earns its place here: this tab is
                            the one that stacks two label/value grids of the same
                            typography, so without it the eye cannot tell where
                            the room's own fields stop and the occupants' begin.
                            `pb-6` holds the line clear of the last row; the
                            wrapper's `space-y-8` then sets the next heading
                            32px below it. */}
                        <section className="border-b border-border dark:border-slate-800 pb-6">
                            <h3 className={SECTION_HEADING}>
                                Room Details
                            </h3>
                            <DataState isLoading={occupancyQuery.isLoading} error={occupancyQuery.error}>
                                <div className={DETAIL_GRID}>
                                    {/* Row 1. "Room Allotted" is gone: the room
                                        number is already the dialog's title.
                                        "Room Status" is gone too -- the header
                                        badge top-right carries the same value. */}
                                    <Field
                                        label="Category"
                                        value={occupancy?.amenity_type_name ?? roomType}
                                    />
                                    {/* Building and floor are separate columns on
                                        the occupancy projection, so they are shown
                                        separately rather than concatenated. */}
                                    <Field
                                        label="Tower / Building"
                                        value={occupancy?.building_name ?? EMPTY_VALUE}
                                    />
                                    <Field label="Floor" value={occupancy?.floor_name ?? EMPTY_VALUE} />
                                    <Field
                                        label="Room Allocations"
                                        value={occupancy?.allocation_count ?? EMPTY_VALUE}
                                    />

                                    {/* Row 2 -- the four dates, in one row. */}
                                    <Field
                                        label="Expected Check-In"
                                        value={formatDateTime(stay?.expected_checkin_time)}
                                    />
                                    <Field
                                        label="Actual Check-In"
                                        value={formatDateTime(stay?.actual_checkin_time)}
                                    />
                                    <Field
                                        label="Expected Check-Out"
                                        value={formatDateTime(stay?.expected_checkout_time)}
                                    />
                                    {/* ACTUAL CHECK-OUT IS STRUCTURALLY ALWAYS "-" HERE.
                                        Not an oversight and not fixable in this file.

                                        `current_stay` is selected by the IN_HOUSE
                                        predicate in services/occupancy.py --
                                        `actual_checkin_time IS NOT NULL AND
                                        actual_checkout_time IS NULL`. A stay that
                                        satisfies it has BY DEFINITION not checked
                                        out, so the column is null for every stay
                                        this dialog can ever display, and
                                        CurrentStayRef does not project it at all.

                                        Rendered because the brief asks for the
                                        four-column row, and shown as "-" rather
                                        than invented. The tooltip is what stops an
                                        operator reading the dash as missing data.
                                        Filling it needs the projection widened,
                                        which is a backend change this task forbids. */}
                                    <Field
                                        label="Actual Check-Out"
                                        value={EMPTY_VALUE}
                                        title="This room's stay is still in house, so it has no actual check-out time yet."
                                    />
                                </div>
                            </DataState>
                        </section>

                        {/* Occupants Details Section */}
                        <section>
                            <h3 className={SECTION_HEADING}>
                                Occupants Details
                            </h3>
                            {/* `isEmpty={!stay}`: every field in this section is
                                stay-derived now that the occupant name list is
                                gone, so "no stay" is exactly what makes it empty.
                                The old `&& occupants.length === 0` could not
                                change the result either way -- the backend only
                                populates occupants when a current stay exists, so
                                that term was always true here. */}
                            <DataState
                                isLoading={occupancyQuery.isLoading}
                                error={occupancyQuery.error}
                                isEmpty={!stay}
                                emptyTitle="No active occupants recorded for this room."
                            >
                                {/* No card. This section sits straight on the
                                    dialog background like Room Details above, so
                                    the two grids start at the same x and their
                                    columns line up exactly. */}
                                <div className={DETAIL_GRID}>
                                    {/* The "Occupants" name list is gone: it
                                        restated the same party that "Guests"
                                        already counts. The four primary fields
                                        sit on one row, on the same four columns
                                        as Room Details above. */}
                                    <Field
                                        label="Primary Guest"
                                        value={stay?.booker?.name ?? guestName}
                                    />
                                    <Field
                                        label="Stay Reference"
                                        value={stay?.internal_stay_ref_number ?? EMPTY_VALUE}
                                    />
                                    <Field label="Stay Status" value={stay?.status ?? EMPTY_VALUE} />
                                    <Field label="Guests" value={stay?.no_of_guests ?? EMPTY_VALUE} />
                                </div>
                            </DataState>
                        </section>

                    </TabPanel>

                    {/* Tab 2 -- the hardware in the room and what it is drawing.
                        The device inventory sits above the readings those same
                        devices produce. */}
                    <TabPanel value="environment">
                        {/* Device Details Section */}
                        <section>
                            <h3 className={SECTION_HEADING}>
                                Device Details
                            </h3>
                            <div className="rounded-lg overflow-hidden overflow-x-auto scrollbar-thin border border-border/80 dark:border-slate-800">
                                <DataState
                                    isLoading={devicesQuery.isLoading}
                                    error={devicesQuery.error}
                                    isEmpty={devices.length === 0}
                                    emptyTitle="No devices installed in this room"
                                >
                                    <Table>
                                        <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                                            <TableRow>
                                                <TableHead className={TABLE_HEAD}>Device Type</TableHead>
                                                <TableHead className={TABLE_HEAD}>
                                                    Occupancy No
                                                </TableHead>
                                                <TableHead className={TABLE_HEAD}>Device UID</TableHead>
                                                <TableHead className={TABLE_HEAD}>Config Status</TableHead>
                                                <TableHead className={`${TABLE_HEAD} text-center`}>
                                                    Health
                                                </TableHead>
                                                <TableHead className={`${TABLE_HEAD} text-right`}>
                                                    Installed On
                                                </TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {devices.map((device) => (
                                                <TableRow key={device.id} className="hover:bg-muted/5">
                                                    <TableCell>{device.device_type_name ?? EMPTY_VALUE}</TableCell>
                                                    <TableCell>{device.amenity_name ?? roomNo}</TableCell>
                                                    <TableCell className="font-mono text-xs">
                                                        {device.device_uid || EMPTY_VALUE}
                                                    </TableCell>
                                                    <TableCell>
                                                        <span
                                                            className={
                                                                // The enum label is lower-case; "Commissioned"
                                                                // never matched, so this always read as muted.
                                                                device.device_config_status === "commissioned"
                                                                    ? "text-green-600"
                                                                    : "text-muted-foreground"
                                                            }
                                                        >
                                                            {device.device_config_status ?? EMPTY_VALUE}
                                                        </span>
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {device.health_status === "Active" ? (
                                                            <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                                                        ) : (
                                                            <XCircle className="h-4 w-4 text-red-500 mx-auto" />
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        {formatDate(device.installed_on)}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </DataState>
                            </div>
                        </section>

                        {/* Power & Energy Section -- what the retired Power View
                            and Energy View used to show, narrowed to this room.
                            See RoomPowerEnergy for the parameters and units. */}
                        <section>
                            <h3 className={SECTION_HEADING}>
                                Power &amp; Energy
                            </h3>
                            <RoomPowerEnergy amenityId={enabled} />
                        </section>

                    </TabPanel>

                    {/* Tab 3 -- what has been asked of this room. */}
                    <TabPanel value="requests">
                        {/* Service Requests Section (see the file header: the
                            maintenance_request table has no endpoint).

                            One card per request rather than a row in a table
                            eight columns wide. That table could not fit the
                            dialog, so it carried its own horizontal scrollbar
                            and half the fields sat off-screen -- on a tab whose
                            whole job is to show them. Reading a single request
                            meant scrolling right and then tracking back along
                            the row.

                            The card reuses `Field` and `DETAIL_GRID`, so a
                            request's fields are laid out on exactly the same
                            four columns, gaps and label/value typography as the
                            Details tab. Nothing here is styled independently:
                            restyle those two and this follows. */}
                        <section>
                            <h3 className={SECTION_HEADING}>
                                Service Requests
                            </h3>
                            <DataState
                                isLoading={requestsQuery.isLoading}
                                error={requestsQuery.error}
                                isEmpty={requests.length === 0}
                                emptyTitle="No service requests recorded for this room"
                            >
                                <div className="space-y-4">
                                    {requests.map((item) => (
                                        <div
                                            key={item.id}
                                            className="rounded-lg border border-border/80 bg-muted/30 p-4 dark:border-slate-800 dark:bg-slate-800/30"
                                        >
                                            {/* Status is the one field the brief's
                                                list leaves out, and it was a column
                                                in the table this replaces. Dropping
                                                it would lose real data, so it keeps
                                                its badge and moves to the corner of
                                                the card it describes -- the shape the
                                                dialog header already uses for the
                                                room's own status. As a badge it reads
                                                as the state of the whole request,
                                                which a label in the grid would not. */}
                                            <div className="mb-4 flex justify-end">
                                                <Badge
                                                    variant="secondary"
                                                    className={`shrink-0 ${serviceStatusBadgeClass(item.status_name)}`}
                                                >
                                                    {item.status_name ?? EMPTY_VALUE}
                                                </Badge>
                                            </div>

                                            <div className={DETAIL_GRID}>
                                                <Field
                                                    label="Service Category"
                                                    value={item.category_name ?? EMPTY_VALUE}
                                                />
                                                <Field
                                                    label="Services Type"
                                                    value={item.service_type_name ?? EMPTY_VALUE}
                                                />
                                                <Field
                                                    label="Requested On"
                                                    value={formatDate(item.created_on)}
                                                />
                                                <Field
                                                    label="Expected"
                                                    value={formatDate(item.expected_date)}
                                                />
                                                <Field
                                                    label="Completed"
                                                    value={formatDate(item.completed_on)}
                                                />
                                                <Field
                                                    label="Department"
                                                    value={item.department_name ?? EMPTY_VALUE}
                                                />
                                                <Field
                                                    label="Emp ID/Name"
                                                    value={
                                                        item.assignee
                                                            ? [item.assignee.emp_id, item.assignee.name]
                                                                  .filter(Boolean)
                                                                  .join(" / ")
                                                            : EMPTY_VALUE
                                                    }
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </DataState>
                        </section>
                    </TabPanel>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}
