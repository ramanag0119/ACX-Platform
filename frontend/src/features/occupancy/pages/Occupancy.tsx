import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
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
import { ArrowRight, Clock, Minus } from "lucide-react";
import { RoomDetailsModal } from "../components/RoomDetailsModal";
import { ConditionBadge } from "../components/ConditionBadge";
import { conditionLabel } from "../lib/roomStatus";
import { STATUS_QUERY_PARAM } from "../lib/occupancyLinks";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { ReallocateRoomDialog } from "../components/ReallocateRoomDialog";
import { RoomConditionsDialog } from "../components/RoomConditionsDialog";
import { CheckOutConfirmDialog } from "../components/CheckOutConfirmDialog";
import {
  useAllOccupancy,
  useBuildings,
  useFloors,
} from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { OccupancyRead } from "@/lib/api/types";
import { PageHeader } from "@/components/layout/PageHeader";

/**
 * The Occupancy Dashboard: live occupancy from GET /occupancy.
 *
 * DRILL-DOWN. Building -> Floor -> Status -> room list. Building and Floor are
 * server side filters the endpoint already accepts (`building_id` and
 * `floor_id` resolve through `property_chain`). Both default to the FIRST row
 * of their lookup rather than "All", so the screen opens on one floor.
 *
 * ONE SCROLLABLE LIST. There is no page size, pager or search box: every row
 * for the selected building / floor is loaded (useAllOccupancy walks the
 * endpoint's pages) and the browser's own scroll and Ctrl+F do the rest.
 *
 * Status is filtered in the browser, over that full list, on the housekeeping
 * conditions the table's Status column draws, and its options are the
 * conditions actually present in it. The select can only ever offer a value
 * that is visible in the grid and will show rows.
 *
 * Building / Floor options are real lookups:
 *   Building -> GET /buildings
 *   Floor    -> GET /floors?building_id=...   (narrowed by the selection)
 *
 * Deliberately NOT here: Available / Occupied / Allotted / Unavailable summary
 * cards.
 *
 * Guest name. The mock's flat `guestName` string is now
 * `current_stay.booker`, the backend's UserRef. A room with no in-house stay
 * shows "-" instead of a fabricated name.
 *
 * Guest / Non Guest are the real `amenity_category` values: the Guest tab is
 * category "room"; Non Guest is everything else. The API filters one category
 * at a time, so the Non Guest tab merges "restaurant" and "others".
 */

type RoomRow = {
  amenityId: string;
  roomNo: string;
  roomType: string;
  buildingName: string;
  floorName: string;
  guestName: string;
  statusName: string;
  conditions: string[];
  /** Present only while a stay is in house -- drives Check-Out. */
  stayId: string | null;
  checkedIn: boolean;
  /** The stay's realized check-in; null until the guest is in house. */
  checkInTime: string | null;
  /** The stay's EXPECTED checkout -- the only checkout the projection holds. */
  checkOutTime: string | null;
  conditionIds: number[];
};

const toRow = (item: OccupancyRead): RoomRow => ({
  amenityId: item.amenity_id,
  roomNo: item.room_name,
  roomType: item.amenity_type_name ?? "-",
  buildingName: item.building_name ?? "-",
  floorName: item.floor_name ?? "-",
  guestName: item.current_stay?.booker?.name ?? "-",
  statusName: item.status_name ?? "-",
  // Display label only -- `conditionIds` below still carries the stored ids,
  // so filtering and saving keep working on the backend vocabulary.
  conditions: item.conditions.map((condition) => conditionLabel(condition.name)),
  stayId: item.current_stay?.stay_id ?? null,
  // `actual_checkin_time` is what makes a stay in-house.
  checkedIn: Boolean(item.current_stay?.actual_checkin_time),
  checkInTime: item.current_stay?.actual_checkin_time ?? null,
  checkOutTime: item.current_stay?.expected_checkout_time ?? null,
  conditionIds: item.conditions.map((condition) => condition.id),
});

/**
 * An empty table value, drawn as a muted em dash. Display only: the row keeps
 * its "-" (the mapping above is unchanged).
 */
const EmptyDash = () => (
  <>
    <span className="badge hms-muted" aria-hidden="true">
      —
    </span>
    <span className="sr-only">Not set</span>
  </>
);

const cellValue = (value: string) => (value === "-" ? <EmptyDash /> : value);

/** A cell's hover text: the full value, or none for an empty one. */
const cellTitle = (value: string) => (value === "-" ? undefined : value);

/**
 * Relative column widths, in table order: Room No, Room Type, Building, Floor,
 * Guest name, Check-In, Check-Out, Generate, Status, Reassign, Invoice.
 * Percentages rather than pixels so the fixed layout scales with the container
 * instead of reintroducing a horizontal scroll.
 */
const COLUMN_WIDTHS = [
  "6.3%", "5.3%", "8.2%", "7.2%", "11.6%", "11.6%", "13%", "9.2%", "14.5%", "5.8%", "7.3%",
];

/**
 * Check-In / Check-Out for the table cell: two tight lines, the date over the
 * time, so the row keeps the table's fixed height. An overdue checkout turns
 * the date red and tucks a micro "Overdue" tag beside the time rather than on
 * a third line.
 *
 * Colours live in index.css (`hms-*`). A global sweep there repaints every
 * span in `main` pure black / white with !important; `badge` is that sweep's
 * own opt-out (it carries no styles), so these spans keep their muted / red
 * colour. EmptyDash and "No stay" use it for the same reason.
 */
const DateTimeStack = ({ value, overdue = false }: { value: string | null; overdue?: boolean }) => {
  if (!value) return <EmptyDash />;
  const date = new Date(value);
  return (
    <span className="flex flex-col leading-tight">
      <span className={`whitespace-nowrap text-[11px] ${overdue ? "badge hms-overdue-text font-medium" : ""}`}>
        {date.toLocaleDateString()}
      </span>
      <span className="flex items-center gap-1 whitespace-nowrap">
        <span className="badge hms-muted text-[10px]">
          {date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
        </span>
        {overdue && (
          <span
            className="badge hms-overdue-tag"
            title="Expected check-out has passed but the stay is still checked in"
          >
            <Clock className="h-2 w-2" /> Overdue
          </span>
        )}
      </span>
    </span>
  );
};

/**
 * Room Type, shortened for the table cell only.
 *
 * The stored `amenity_type.name` ("Guest Room", "Suite") is untouched: the row
 * still carries it and the cell keeps it in its `title`, so the meaning is
 * never lost. The initial is taken FROM that name
 * rather than from a map of known types, so a type added to `amenity_type`
 * later shortens itself without a change here.
 */
const shortRoomType = (roomType: string) =>
  roomType && roomType !== "-" ? roomType.trim().charAt(0).toUpperCase() : "-";

/**
 * A stay that is still in house after its expected checkout has passed.
 *
 * Both halves are values the API already returns -- `actual_checkin_time` (via
 * `checkedIn`) and `expected_checkout_time`. No date is hardcoded, and the
 * room's stored status is NOT rewritten: a room the database says is Occupied
 * still reports Occupied. What this does is stop the table showing a past
 * checkout as if it were unremarkable, which is the inconsistency -- an
 * overdue departure is a real operational state, not a normal occupancy.
 */
const isOverdueCheckout = (room: RoomRow) =>
  room.checkedIn &&
  room.checkOutTime !== null &&
  new Date(room.checkOutTime).getTime() < Date.now();

/**
 * The "no filter applied" sentinel shared by the status, building and floor
 * selects. Every select, default and param check has to agree on it exactly or
 * a select silently stops clearing its filter, so the literal is named once.
 * It must never collide with a real option: a building / floor id or an
 * `amenity_condition` label.
 */
const ALL_FILTER_VALUE = "all";

const Occupancy = () => {
  const [activeTab, setActiveTab] = useState<"guest" | "nonGuest">("guest");
  /**
   * The status filter, seeded from `?status=` so the Occupancy Statistics donut
   * can drill through to it. Clicking Available there lands here already
   * filtered to Available rather than on the unfiltered list.
   *
   * Read once, as the initial value only: this is a starting point, not a bound
   * parameter, so changing the select afterwards does not fight the URL and the
   * user is free to widen the filter on the screen they just landed on.
   *
   * The value is compared, exactly, with the condition labels in the Status
   * column. The donut sends an `amenity_status_name` (Available, ...), which is
   * not a condition, so today that link falls back to Show All.
   */
  const [searchParams] = useSearchParams();
  const [filterBy, setFilterBy] = useState(
    () => searchParams.get(STATUS_QUERY_PARAM) || ALL_FILTER_VALUE,
  );
  /**
   * The user's Building / Floor pick, or null while they have not made one.
   * Null means "the first row of the lookup" (resolved below), so the default
   * follows the data instead of being a hardcoded name, and it is known as
   * soon as the lookup answers -- no effect, no unfiltered first fetch.
   */
  const [buildingChoice, setBuildingChoice] = useState<string | null>(null);
  const [floorChoice, setFloorChoice] = useState<string | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<RoomRow | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reallocateRoom, setReallocateRoom] = useState<RoomRow | null>(null);
  const [conditionsRoom, setConditionsRoom] = useState<RoomRow | null>(null);
  /**
   * The row whose Check-Out awaits confirmation; the dialog sends the request.
   * Kept apart from the open flag (as with Room Details) so the dialog still
   * names the room while it fades out, instead of flashing "Room ".
   */
  const [checkOutRoom, setCheckOutRoom] = useState<RoomRow | null>(null);
  const [isCheckOutOpen, setIsCheckOutOpen] = useState(false);

  // Write actions live in the dialogs below; each mutation refetches
  // occupancy, so the table shows the database's state, not a patched row.
  const { canRead, canWrite } = useAuth();
  const mayWriteOccupancy = canWrite("occupancy");
  const mayWriteBookings = canWrite("bookings");

  // Building / Floor options. /buildings and /floors are gated on
  // `facility_management`, which is not the `occupancy` grant that opens this
  // screen, so they are requested only when the role holds it -- asking
  // anyway would answer 403 and leave the selects broken rather than absent.
  // `enabled` is what actually stops the request -- conditional params alone
  // would still fire an unfiltered one and take the 403 this avoids.
  const mayReadFacility = canRead("facility_management");
  const buildingsQuery = useBuildings(
    mayReadFacility ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    { enabled: mayReadFacility },
  );
  const buildings = buildingsQuery.data?.items ?? [];
  // No pick yet -> the first building in the list, not "All Buildings".
  const buildingFilter = buildingChoice ?? buildings[0]?.id ?? ALL_FILTER_VALUE;

  const floorsQuery = useFloors(
    mayReadFacility
      ? {
          page: 1,
          page_size: MAX_PAGE_SIZE,
          // Floors follow the chosen building; the endpoint owns the join.
          ...(buildingFilter !== ALL_FILTER_VALUE ? { building_id: buildingFilter } : {}),
        }
      : undefined,
    { enabled: mayReadFacility },
  );
  const floors = floorsQuery.data?.items ?? [];
  // No pick yet -> the building's first floor. Under "All Buildings" there is
  // no meaningful "first floor", so the floor stays unfiltered there.
  const floorFilter =
    floorChoice ??
    (buildingFilter !== ALL_FILTER_VALUE ? floors[0]?.id : undefined) ??
    ALL_FILTER_VALUE;

  // Hold the occupancy fetch until the defaults above are known; otherwise the
  // first request goes out unfiltered and the table flashes every room. A
  // failed lookup still counts as settled -- it just leaves that level on All.
  const settled = (query: { isSuccess: boolean; isError: boolean }) =>
    query.isSuccess || query.isError;
  const scopeReady =
    !mayReadFacility ||
    (settled(buildingsQuery) && (buildingFilter === ALL_FILTER_VALUE || settled(floorsQuery)));

  /** The drill-down, as the endpoint's own query parameters. */
  const scopeParams = {
    ...(buildingFilter !== ALL_FILTER_VALUE ? { building_id: buildingFilter } : {}),
    ...(floorFilter !== ALL_FILTER_VALUE ? { floor_id: floorFilter } : {}),
  };

  const isGuest = activeTab === "guest";
  const guestQuery = useAllOccupancy(
    { ...scopeParams, amenity_category: "room" },
    { enabled: scopeReady && isGuest },
  );
  // Two calls, because `amenity_category` takes a single value.
  const restaurantQuery = useAllOccupancy(
    { ...scopeParams, amenity_category: "restaurant" },
    { enabled: scopeReady && !isGuest },
  );
  const othersQuery = useAllOccupancy(
    { ...scopeParams, amenity_category: "others" },
    { enabled: scopeReady && !isGuest },
  );

  const isLoading =
    !scopeReady ||
    (isGuest ? guestQuery.isLoading : restaurantQuery.isLoading || othersQuery.isLoading);
  const error = isGuest
    ? guestQuery.error
    : restaurantQuery.error ?? othersQuery.error;

  const rows = useMemo(() => {
    if (isGuest) return (guestQuery.data ?? []).map(toRow);
    return [...(restaurantQuery.data ?? []), ...(othersQuery.data ?? [])]
      .map(toRow)
      .sort((a, b) => a.roomNo.localeCompare(b.roomNo));
  }, [isGuest, guestQuery.data, restaurantQuery.data, othersQuery.data]);

  // Status options are the condition labels the table's Status column draws
  // (`room.conditions`, the pills) -- not `statusName`, which no column shows.
  // Taken from the loaded rows, so the select only offers values on screen.
  // A room with no condition ("-") is listed under Show All only.
  const statusOptions = useMemo(
    () =>
      [...new Set(rows.flatMap((room) => room.conditions))]
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b)),
    [rows],
  );
  // A selection this building / floor has no rooms in (e.g. one carried over
  // from ?status= or from the previous floor) falls back to Show All rather
  // than leaving the trigger blank over an empty table.
  const statusFilter = statusOptions.includes(filterBy) ? filterBy : ALL_FILTER_VALUE;

  const filteredRooms =
    statusFilter === ALL_FILTER_VALUE
      ? rows
      : // Exact string match; a room can carry several conditions, so it is
        // shown when any one of its pills is the selected value.
        rows.filter((room) => room.conditions.some((condition) => condition === statusFilter));

  /**
   * Choosing a building clears the floor pick, so the floor falls back to the
   * new building's first floor: a floor id from the previous building would be
   * sent alongside the new selection and match nothing.
   */
  const changeBuilding = (value: string) => {
    setBuildingChoice(value);
    setFloorChoice(null);
  };

  const handleDetailsClick = (room: RoomRow) => {
    setSelectedRoom(room);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-5 animate-fade-in text-foreground">
      <PageHeader title="Occupancy Dashboard" />

      {/* Tabs */}
      <div className="flex gap-6 border-b border-border dark:border-slate-800">
        <button
          onClick={() => setActiveTab("guest")}
          className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === "guest"
            ? "text-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Guest
          {activeTab === "guest" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-t-full" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("nonGuest")}
          className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === "nonGuest"
            ? "text-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Non Guest
          {activeTab === "nonGuest" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-t-full" />
          )}
        </button>
      </div>

      {/* Table Container */}
      <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
        <CardContent className="p-5">
          {/* Controls. No page size or search: the table is one scrollable
              list and the browser's Ctrl+F covers finding a row. */}
          <div className="flex flex-wrap items-center justify-end gap-4 mb-5">
            {/* Building -> Floor -> Status drill-down. Building and Floor are
                database rows; Status is the statuses present in the list. */}
            {mayReadFacility && (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-sm">Building</span>
                  <Select value={buildingFilter} onValueChange={changeBuilding}>
                    <SelectTrigger className="w-36 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                      <SelectItem value={ALL_FILTER_VALUE}>All Buildings</SelectItem>
                      {buildings.map((building) => (
                        <SelectItem key={building.id} value={building.id}>
                          {building.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-sm">Floor</span>
                  <Select value={floorFilter} onValueChange={setFloorChoice}>
                    <SelectTrigger className="w-36 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                      <SelectItem value={ALL_FILTER_VALUE}>All Floors</SelectItem>
                      {floors.map((floor) => (
                        <SelectItem key={floor.id} value={floor.id}>
                          {floor.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Status</span>
              <Select value={statusFilter} onValueChange={setFilterBy}>
                <SelectTrigger className="w-36 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                  <SelectItem value={ALL_FILTER_VALUE}>Show All</SelectItem>
                  {statusOptions.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-slate-800">
            <DataState
              isLoading={isLoading}
              error={error}
              isEmpty={filteredRooms.length === 0}
              emptyTitle="No Rooms match this view"
              loader={<TableLoading columns={COLUMN_WIDTHS.length} />}
            >
              {/* `min-w-0` drops the shared Table's `min-w-max` and
                  `table-fixed` applies COLUMN_WIDTHS, so the columns share the
                  container width instead of scrolling. `hms-occupancy-table`
                  sets the row height and compacts cells, buttons and badges
                  (index.css). */}
              <Table className="hms-occupancy-table table-fixed min-w-0">
                <colgroup>
                  {COLUMN_WIDTHS.map((width, index) => (
                    <col key={index} style={{ width }} />
                  ))}
                </colgroup>
                <TableHeader>
                  <TableRow className="bg-gray-50/80 dark:bg-slate-800/60 hover:bg-gray-50 dark:hover:bg-slate-800/60 border-b border-gray-200 dark:border-slate-800">
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Room No</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Room Type</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Building</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Floor</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Guest name</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Check-In</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Check-Out</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Generate <span className="text-gray-400 dark:text-slate-500">↓</span></TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Status</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Reassign</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Invoice <span className="text-gray-400 dark:text-slate-500">↓</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRooms.map((room, index) => (
                    <TableRow
                      key={room.amenityId}
                      className={`${index % 2 === 0 ? "bg-card dark:bg-slate-900/60" : "bg-muted/20 dark:bg-slate-800/40"} hover:bg-muted/40 dark:hover:bg-slate-800/80 border-b border-border/40 dark:border-slate-800/50`}
                    >
                      <TableCell className="font-medium text-foreground">
                        {/* The room number opens the same dialog as Details. */}
                        <button
                          type="button"
                          className="font-medium text-foreground hover:text-primary hover:underline"
                          onClick={() => handleDetailsClick(room)}
                          title={`Open details for room ${room.roomNo}`}
                        >
                          {room.roomNo}
                        </button>
                      </TableCell>
                      {/* Shortened for width; the full type is on the title. */}
                      <TableCell className="text-foreground" title={cellTitle(room.roomType)}>
                        {cellValue(shortRoomType(room.roomType))}
                      </TableCell>
                      {/* Single-line cells: a long name truncates with an
                          ellipsis instead of growing the row; the full value
                          is on the title. */}
                      <TableCell className="hms-truncate text-foreground" title={cellTitle(room.buildingName)}>
                        {cellValue(room.buildingName)}
                      </TableCell>
                      <TableCell className="hms-truncate text-foreground" title={cellTitle(room.floorName)}>
                        {cellValue(room.floorName)}
                      </TableCell>
                      <TableCell className="hms-truncate text-foreground" title={cellTitle(room.guestName)}>
                        {cellValue(room.guestName)}
                      </TableCell>
                      <TableCell className="text-foreground">
                        <DateTimeStack value={room.checkInTime} />
                      </TableCell>
                      <TableCell className="text-foreground">
                        <DateTimeStack value={room.checkOutTime} overdue={isOverdueCheckout(room)} />
                      </TableCell>
                      <TableCell className="text-center">
                        {/* Check-Out for an in-house stay, "No stay" otherwise.
                            The API sends `current_stay` only while a stay is
                            checked in and not out, so a stay id here always
                            means a guest in house -- there is no pre-arrival
                            Check-In state to show (that lives in Bookings). A
                            room whose stored status says Occupied without an
                            in-house stay has nothing to check out. */}
                        {room.stayId ? (
                          <Button
                            size="sm"
                            // Light purple box, purple text: the actionable
                            // state, against the muted "No stay". index.css
                            // repaints `bg-purple-*` pills in table cells (both
                            // themes, hover included) to this same tint.
                            className="rounded-full border border-purple-200 bg-purple-50 text-purple-700 text-xs font-semibold px-3"
                            disabled={!mayWriteBookings}
                            // Step one only: opens the confirmation, which is
                            // the sole place the check-out request is sent.
                            onClick={() => {
                              setCheckOutRoom(room);
                              setIsCheckOutOpen(true);
                            }}
                            title={
                              mayWriteBookings
                                ? "Check this stay out and release the Room"
                                : "Your role cannot change bookings"
                            }
                          >
                            Check-Out
                          </Button>
                        ) : (
                          <span className="badge hms-muted text-[11px]">No stay</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {/* A div, not a button: the condition pills inside are
                            interactive-looking elements and a button may not
                            nest one. `disabled` does not exist on a div, so the
                            read-only state is carried by aria-disabled and the
                            cursor class rather than a `disabled:` variant that
                            would never match. */}
                        <div
                          role="button"
                          aria-disabled={!mayWriteOccupancy}
                          tabIndex={mayWriteOccupancy ? 0 : -1}
                          // `hms-cell-trigger`: a layout wrapper around the
                          // condition pills, not a button, so it opts out of
                          // the boxed table-action chrome in index.css. The
                          // role is for keyboard activation only.
                          className={`hms-cell-trigger flex w-full flex-wrap items-center justify-center gap-1.5 ${
                            mayWriteOccupancy ? "cursor-pointer" : "cursor-not-allowed"
                          }`}
                          onClick={() => mayWriteOccupancy && setConditionsRoom(room)}
                          onKeyDown={(event) => {
                            if ((event.key === "Enter" || event.key === " ") && mayWriteOccupancy) {
                              event.preventDefault();
                              setConditionsRoom(room);
                            }
                          }}
                          title={
                            mayWriteOccupancy
                              ? "Edit housekeeping conditions"
                              : "Your role cannot change occupancy"
                          }
                        >
                          {room.conditions.length > 0
                            ? room.conditions.map((condition) => <ConditionBadge key={condition} condition={condition} />)
                            : <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-gray-50 text-gray-400 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400 text-xs font-semibold">
                                <Minus className="h-3.5 w-3.5" /> -
                              </span>}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          size="sm"
                          // `bg-brand` is the Submit-button colour (#5865f2, see
                          // tailwind.config.ts), so the row's actions share one
                          // token instead of each carrying its own accent.
                          //
                          // Never raw `bg-cyan-600` here -- that is caught by
                          // the pagination rule in index.css and repainted
                          // anyway (see Bookings' actions).
                          className="hms-action-on-fill bg-brand hover:bg-brand-hover text-white w-8 h-8 p-0"
                          disabled={!mayWriteBookings || !room.stayId}
                          onClick={() => setReallocateRoom(room)}
                          title={
                            !room.stayId
                              ? "No stay holds this Room"
                              : mayWriteBookings
                                ? "Move this stay to another Room"
                                : "Your role cannot change bookings"
                          }
                        >
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-cyan-500 text-cyan-600 hover:bg-cyan-50 dark:text-cyan-400 dark:hover:bg-cyan-950/50 text-xs px-3"
                          disabled
                          title={
                            "Invoice generation needs amounts the schema does not hold: " +
                            "`package` has no price and there is no tariff or tax rate " +
                            "(OPEN DECISION #10)."
                          }
                        >
                          Invoice
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </DataState>
          </div>

          {/* Row count only: every row is on screen, so there is no pager. */}
          <div className="mt-6">
            <span className="text-muted-foreground text-sm">
              Showing {filteredRooms.length} {filteredRooms.length === 1 ? "entry" : "entries"}
            </span>
          </div>
        </CardContent>
      </Card>

      <ReallocateRoomDialog
        open={Boolean(reallocateRoom)}
        onClose={() => setReallocateRoom(null)}
        stayId={reallocateRoom?.stayId ?? null}
        currentRoomName={reallocateRoom?.roomNo ?? ""}
      />

      <CheckOutConfirmDialog
        open={isCheckOutOpen}
        onClose={() => setIsCheckOutOpen(false)}
        stayId={checkOutRoom?.stayId ?? null}
        roomName={checkOutRoom?.roomNo ?? ""}
        guestName={checkOutRoom?.guestName ?? "-"}
      />

      <RoomConditionsDialog
        open={Boolean(conditionsRoom)}
        onClose={() => setConditionsRoom(null)}
        amenityId={conditionsRoom?.amenityId ?? null}
        roomName={conditionsRoom?.roomNo ?? ""}
        selectedIds={conditionsRoom?.conditionIds ?? []}
      />

      <RoomDetailsModal
        amenityId={selectedRoom?.amenityId ?? null}
        roomNo={selectedRoom?.roomNo ?? null}
        roomType={selectedRoom?.roomType}
        guestName={selectedRoom?.guestName}
        status={selectedRoom?.statusName}
        conditions={selectedRoom?.conditions}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};

export default Occupancy;
