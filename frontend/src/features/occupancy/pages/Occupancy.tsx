import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Badge } from "@/components/ui/badge";
import { Info, ArrowRight, Wrench, ShieldCheck, BatteryLow, Star, UserCheck, Clock, Minus } from "lucide-react";
import { RoomDetailsModal } from "../components/RoomDetailsModal";
import { roomStatusBadgeClass } from "../lib/roomStatus";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { ReallocateRoomDialog } from "../components/ReallocateRoomDialog";
import { RoomConditionsDialog } from "../components/RoomConditionsDialog";
import {
  useCheckInStay,
  useCheckOutStay,
  useUpdateRoomState,
} from "@/lib/api/mutations";
import {
  useAmenityStatuses,
  useBuildings,
  useFloors,
  useOccupancy,
} from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { OccupancyRead } from "@/lib/api/types";

/**
 * The Occupancy Dashboard: live occupancy from GET /occupancy.
 *
 * DRILL-DOWN. Building -> Floor -> Status -> room list. All three are server
 * side filters the endpoint already accepts (`building_id` and `floor_id`
 * resolve through `property_chain`, `status` through `amenity_status`), so the
 * table, its `total` and its pagination all agree with the selection. Nothing
 * is filtered in the browser except the free-text search, which the endpoint
 * has no parameter for.
 *
 * Every option list is a real lookup:
 *   Building -> GET /buildings
 *   Floor    -> GET /floors?building_id=...   (narrowed by the selection)
 *   Status   -> GET /amenity-statuses         (the four rows, never hardcoded)
 *
 * Deliberately NOT here: Available / Occupied / Allotted / Unavailable summary
 * cards. The four statuses are drill-down options only.
 *
 * TWO MISMATCHES WITH THE ORIGINAL SCREEN, both resolved in favour of the
 * database:
 *
 *   1. Status. The mock had only "Available" | "Unavailable". The real
 *      `amenity_status` table has FOUR rows -- Available, Occupied,
 *      Unavailable, Allotted -- and every one of them is rendered. The
 *      "Filter By" select is populated from GET /amenity-statuses rather than
 *      being hardcoded, so it can never drift from the lookup table.
 *
 *   2. Guest name. The mock's flat `guestName` string is now
 *      `current_stay.booker`, the backend's UserRef. A room with no in-house
 *      stay shows "-" instead of a fabricated name.
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
  /** Present when a stay currently holds the room -- drives check-in/out. */
  stayId: string | null;
  stayStatus: string | null;
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
  conditions: item.conditions.map((condition) => condition.name),
  stayId: item.current_stay?.stay_id ?? null,
  stayStatus: item.current_stay?.status ?? null,
  // `actual_checkin_time` is what makes a stay in-house.
  checkedIn: Boolean(item.current_stay?.actual_checkin_time),
  checkInTime: item.current_stay?.actual_checkin_time ?? null,
  checkOutTime: item.current_stay?.expected_checkout_time ?? null,
  conditionIds: item.conditions.map((condition) => condition.id),
});

const formatDateTime = (value: string | null) =>
  value ? new Date(value).toLocaleString() : "-";

const Occupancy = () => {
  const [activeTab, setActiveTab] = useState<"guest" | "nonGuest">("guest");
  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterBy, setFilterBy] = useState("all");
  const [buildingFilter, setBuildingFilter] = useState("all");
  const [floorFilter, setFloorFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRoom, setSelectedRoom] = useState<RoomRow | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reallocateRoom, setReallocateRoom] = useState<RoomRow | null>(null);
  const [conditionsRoom, setConditionsRoom] = useState<RoomRow | null>(null);

  // --- Mutations. Each one refetches occupancy, so the table shows the
  // database's state rather than a locally patched row.
  const { canRead, canWrite } = useAuth();
  const mayWriteOccupancy = canWrite("occupancy");
  const mayWriteBookings = canWrite("bookings");
  const checkIn = useCheckInStay();
  const checkOut = useCheckOutStay();
  const roomState = useUpdateRoomState();

  const pageSize = Number(entriesPerPage);

  // Status filter options come from the lookup table, not from a literal.
  const statusesQuery = useAmenityStatuses({ page: 1, page_size: MAX_PAGE_SIZE });
  const statuses = statusesQuery.data?.items ?? [];
  const selectedStatusId =
    filterBy === "all"
      ? undefined
      : statuses.find((status) => status.amenity_status_name === filterBy)?.id;

  // Building / Floor options. /buildings and /floors are gated on
  // `facility_management`, which is not the `occupancy` grant that opens this
  // screen, so they are requested only when the role holds it -- asking
  // anyway would answer 403 and leave the selects broken rather than absent.
  const mayReadFacility = canRead("facility_management");
  const buildingsQuery = useBuildings(
    mayReadFacility ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
  );
  const floorsQuery = useFloors(
    mayReadFacility
      ? {
          page: 1,
          page_size: MAX_PAGE_SIZE,
          // Floors follow the chosen building; the endpoint owns the join.
          ...(buildingFilter !== "all" ? { building_id: buildingFilter } : {}),
        }
      : undefined,
  );
  const buildings = buildingsQuery.data?.items ?? [];
  const floors = floorsQuery.data?.items ?? [];

  /** The drill-down, as the endpoint's own query parameters. */
  const scopeParams = {
    ...(buildingFilter !== "all" ? { building_id: buildingFilter } : {}),
    ...(floorFilter !== "all" ? { floor_id: floorFilter } : {}),
    ...(selectedStatusId !== undefined ? { status: selectedStatusId } : {}),
  };

  const commonParams = {
    page: currentPage,
    page_size: pageSize,
    ...scopeParams,
  };

  const guestQuery = useOccupancy(
    activeTab === "guest" ? { ...commonParams, amenity_category: "room" } : undefined,
  );
  // Two calls, because `amenity_category` takes a single value.
  const restaurantQuery = useOccupancy(
    activeTab === "nonGuest"
      ? { page: 1, page_size: MAX_PAGE_SIZE, amenity_category: "restaurant", ...scopeParams }
      : undefined,
  );
  const othersQuery = useOccupancy(
    activeTab === "nonGuest"
      ? { page: 1, page_size: MAX_PAGE_SIZE, amenity_category: "others", ...scopeParams }
      : undefined,
  );

  const isGuest = activeTab === "guest";
  const isLoading = isGuest
    ? guestQuery.isLoading
    : restaurantQuery.isLoading || othersQuery.isLoading;
  const error = isGuest
    ? guestQuery.error
    : restaurantQuery.error ?? othersQuery.error;

  const { rows, totalEntries, serverPaged } = useMemo(() => {
    if (isGuest) {
      return {
        rows: (guestQuery.data?.items ?? []).map(toRow),
        totalEntries: guestQuery.data?.total ?? 0,
        serverPaged: true,
      };
    }
    const merged = [
      ...(restaurantQuery.data?.items ?? []),
      ...(othersQuery.data?.items ?? []),
    ]
      .map(toRow)
      .sort((a, b) => a.roomNo.localeCompare(b.roomNo));
    return {
      rows: merged,
      totalEntries: (restaurantQuery.data?.total ?? 0) + (othersQuery.data?.total ?? 0),
      serverPaged: false,
    };
  }, [isGuest, guestQuery.data, restaurantQuery.data, othersQuery.data]);

  // Search runs over the rows the API returned for this page. It is a client
  // convenience: /occupancy exposes no free-text search parameter.
  const searched = rows.filter((room) => {
    if (!searchQuery) return true;
    const needle = searchQuery.toLowerCase();
    return (
      room.roomNo.toLowerCase().includes(needle) ||
      room.roomType.toLowerCase().includes(needle) ||
      room.guestName.toLowerCase().includes(needle)
    );
  });

  const filteredRooms = serverPaged
    ? searched
    : searched.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const firstEntry = totalEntries === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const lastEntry = (currentPage - 1) * pageSize + filteredRooms.length;

  const switchTab = (tab: "guest" | "nonGuest") => {
    setActiveTab(tab);
    setCurrentPage(1);
  };

  /**
   * Choosing a building clears the floor below it: a floor id from the
   * previous building would be sent alongside the new selection and match
   * nothing. Any change returns to page 1, because the row count changes.
   */
  const changeBuilding = (value: string) => {
    setBuildingFilter(value);
    setFloorFilter("all");
    setCurrentPage(1);
  };

  const changeFloor = (value: string) => {
    setFloorFilter(value);
    setCurrentPage(1);
  };

  const getConditionBadge = (condition: string) => {
    const lowerCondition = condition.toLowerCase();
    if (lowerCondition.includes("maintenance")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/40 dark:bg-orange-950/60 dark:text-orange-400 text-[11.5px] font-medium">
          <Wrench className="h-3 w-3 text-orange-600 dark:text-orange-400" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("sanitation")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-950/60 dark:text-emerald-400 text-[11.5px] font-medium">
          <ShieldCheck className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("low battery")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-950/60 dark:text-rose-400 text-[11.5px] font-medium">
          <BatteryLow className="h-3 w-3 text-rose-600 dark:text-rose-400" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("vip")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-500/40 dark:bg-purple-950/60 dark:text-purple-300 text-[11.5px] font-medium">
          <Star className="h-3 w-3 text-purple-600 dark:text-purple-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("occupied")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/60 dark:text-amber-300 text-[11.5px] font-medium">
          <UserCheck className="h-3 w-3 text-amber-600 dark:text-amber-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("late checkout")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/60 dark:text-amber-400 text-[11.5px] font-medium">
          <Clock className="h-3 w-3 text-amber-600 dark:text-amber-400" />
          {condition}
        </span>
      );
    }
    return (
      <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700/60 dark:bg-slate-800/60 dark:text-slate-400 text-[11.5px] font-medium">
        <Minus className="h-3 w-3" />
        {condition}
      </span>
    );
  };

  const handleDetailsClick = (room: RoomRow) => {
    setSelectedRoom(room);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-5 animate-fade-in text-foreground">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-xl font-semibold text-foreground tracking-tight">Occupancy Dashboard</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-border dark:border-slate-800">
        <button
          onClick={() => switchTab("guest")}
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
          onClick={() => switchTab("nonGuest")}
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
          {/* Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Show</span>
              <Select
                value={entriesPerPage}
                onValueChange={(value) => {
                  setEntriesPerPage(value);
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-muted-foreground text-xs font-medium">entries</span>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              {/* Building -> Floor -> Status drill-down. Every option is a
                  database row; none of the three is hardcoded. */}
              {mayReadFacility && (
                <>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-sm">Building</span>
                    <Select value={buildingFilter} onValueChange={changeBuilding}>
                      <SelectTrigger className="w-36 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                        <SelectItem value="all">All Buildings</SelectItem>
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
                    <Select value={floorFilter} onValueChange={changeFloor}>
                      <SelectTrigger className="w-36 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                        <SelectItem value="all">All Floors</SelectItem>
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
                <Select
                  value={filterBy}
                  onValueChange={(value) => {
                    setFilterBy(value);
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="w-36 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                    <SelectItem value="all">Show All</SelectItem>
                    {statuses.map((status) => (
                      <SelectItem key={status.id} value={status.amenity_status_name}>
                        {status.amenity_status_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-xs font-medium">Search:</span>
                <Input
                  placeholder="Room no, Room type, Guest name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-56 md:w-64 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-slate-800">
            <DataState
              isLoading={isLoading}
              error={error}
              isEmpty={filteredRooms.length === 0}
              emptyTitle="No rooms match this view"
              loader={<TableLoading columns={13} />}
            >
              <Table>
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
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Condition</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Details</TableHead>
                    <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Reallocate</TableHead>
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
                      <TableCell className="text-foreground">{room.roomType}</TableCell>
                      <TableCell className="text-foreground">{room.buildingName}</TableCell>
                      <TableCell className="text-foreground">{room.floorName}</TableCell>
                      <TableCell className="text-foreground">{room.guestName}</TableCell>
                      <TableCell className="text-foreground whitespace-nowrap">
                        {formatDateTime(room.checkInTime)}
                      </TableCell>
                      <TableCell className="text-foreground whitespace-nowrap">
                        {formatDateTime(room.checkOutTime)}
                      </TableCell>
                      <TableCell className="text-center">
                        {/* Check-in / check-out: the real stay workflow. Room
                            state follows automatically (Occupied / Available). */}
                        {room.stayId && !room.checkedIn ? (
                          <Button
                            size="sm"
                            className="bg-teal-600 hover:bg-teal-700 text-white text-xs px-3"
                            disabled={!mayWriteBookings || checkIn.isPending}
                            onClick={() => checkIn.mutate({ id: room.stayId as string })}
                            title={
                              mayWriteBookings
                                ? "Check this stay in"
                                : "Your role cannot change bookings"
                            }
                          >
                            Check-In
                          </Button>
                        ) : room.stayId && room.checkedIn ? (
                          <Button
                            size="sm"
                            className="bg-purple-600 hover:bg-purple-700 text-white text-xs px-3"
                            disabled={!mayWriteBookings || checkOut.isPending}
                            onClick={() => checkOut.mutate({ id: room.stayId as string })}
                            title={
                              mayWriteBookings
                                ? "Check this stay out and release the room"
                                : "Your role cannot change bookings"
                            }
                          >
                            Check-Out
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground">No stay</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="outline" className={roomStatusBadgeClass(room.statusName)}>
                          {room.statusName}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <button
                          type="button"
                          className="flex flex-wrap gap-1 justify-center w-full disabled:cursor-not-allowed"
                          disabled={!mayWriteOccupancy}
                          onClick={() => setConditionsRoom(room)}
                          title={
                            mayWriteOccupancy
                              ? "Edit housekeeping conditions"
                              : "Your role cannot change occupancy"
                          }
                        >
                          {room.conditions.length > 0
                            ? room.conditions.map((condition) => getConditionBadge(condition))
                            : <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-gray-50 text-gray-400 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400 text-xs font-semibold">
                                <Minus className="h-3.5 w-3.5" /> -
                              </span>}
                        </button>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          size="sm"
                          className="bg-amber-500 hover:bg-amber-600 text-white w-8 h-8 p-0"
                          onClick={() => handleDetailsClick(room)}
                        >
                          <Info className="h-4 w-4" />
                        </Button>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          size="sm"
                          className="bg-cyan-600 hover:bg-cyan-700 text-white w-8 h-8 p-0"
                          disabled={!mayWriteBookings || !room.stayId}
                          onClick={() => setReallocateRoom(room)}
                          title={
                            !room.stayId
                              ? "No stay holds this room"
                              : mayWriteBookings
                                ? "Move this stay to another room"
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

          {/* Pagination -- driven by the API's `total`. */}
          <div className="flex items-center justify-between mt-6">
            <span className="text-muted-foreground text-sm">
              Showing {firstEntry} to {lastEntry} of {totalEntries} entries
            </span>

            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
              {Array.from({ length: Math.min(totalPages, 4) }, (_, index) => index + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "ghost"}
                  size="sm"
                  className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              ))}
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage >= totalPages}>Next</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage >= totalPages}>Last</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <ReallocateRoomDialog
        open={Boolean(reallocateRoom)}
        onClose={() => setReallocateRoom(null)}
        stayId={reallocateRoom?.stayId ?? null}
        currentRoomName={reallocateRoom?.roomNo ?? ""}
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
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};

export default Occupancy;
