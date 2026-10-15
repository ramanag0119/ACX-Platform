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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  LogIn,
  LogOut,
  UserCheck,
  Clock,
  Building,
} from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useCount, useStays } from "@/lib/api/hooks";
import {
  useCheckInStay,
  useCheckOutStay,
  useExtendStay,
  useSetStayDocumentApproval,
} from "@/lib/api/mutations";
import { useAuth } from "@/core/contexts/AuthContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";
import { cn } from "@/lib/utils";

export type CheckInData = {
  id: string;
  name: string;
  mobileNumber: string;
  email: string;
  occupants: number;
  roomNo: string;
  roomType: string;
  noOfRooms: number;
  actualCheckIn: string;
  expectedCheckIn: string;
  actualCheckOut: string;
  expectedCheckOut: string;
  bookingDate: string;
  documentsApproval: boolean;
  status: string;
  isCheckedIn: boolean;
  isCheckedOut: boolean;
  isInHouse: boolean;
  displayStatus: string;
  stayRef: string;
};

type CheckInTab = "in-room" | "all-checkins" | "pending-arrivals";

const renderTabCount = (query: { total: number | null; isError: boolean }) => {
  if (query.total !== null) {
    return query.total;
  }
  if (query.isError) {
    return "-";
  }
  return <Skeleton className="h-2.5 w-3 rounded bg-current opacity-40 animate-pulse" />;
};

export const CheckIn = () => {
  const staysQuery = useStays({ page: 1, page_size: MAX_PAGE_SIZE });

  const allRecords: CheckInData[] = (staysQuery.data?.items ?? []).map((stay) => {
    const isCheckedIn = stay.is_checked_in;
    const isCheckedOut = Boolean(stay.actual_checkout_time);
    const isInHouse = isCheckedIn && !isCheckedOut;

    return {
      id: stay.id,
      name: stay.booker?.name ?? "-",
      mobileNumber: "-",
      email: "-",
      occupants: stay.no_of_guests,
      roomNo: "",
      roomType: "-",
      noOfRooms: stay.no_of_rooms ?? 0,
      actualCheckIn: stay.actual_checkin_time
        ? new Date(stay.actual_checkin_time).toLocaleString()
        : "",
      expectedCheckIn: stay.expected_checkin_time
        ? new Date(stay.expected_checkin_time).toLocaleString()
        : "",
      actualCheckOut: stay.actual_checkout_time
        ? new Date(stay.actual_checkout_time).toLocaleString()
        : "",
      expectedCheckOut: stay.expected_checkout_time
        ? new Date(stay.expected_checkout_time).toLocaleString()
        : "",
      bookingDate: new Date(stay.created_on).toLocaleDateString(),
      documentsApproval: stay.document_approval_status === "approved",
      status: stay.status ?? "-",
      isCheckedIn,
      isCheckedOut,
      isInHouse,
      displayStatus: stay.display_status ?? (isInHouse ? "In-Room" : isCheckedOut ? "Checked Out" : "Pending"),
      stayRef: stay.internal_stay_ref_number,
    };
  });

  const { canWrite } = useAuth();
  const mayWrite = canWrite("bookings");
  const checkIn = useCheckInStay();
  const checkOut = useCheckOutStay();
  const extend = useExtendStay();
  const approveDocs = useSetStayDocumentApproval();

  // Active Tab: In-Room, All Check-ins, or Pending Arrivals
  const [activeTab, setActiveTab] = useState<CheckInTab>("in-room");
  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  useScrollToTop(currentPage);

  // Modal states
  const [checkInModalOpen, setCheckInModalOpen] = useState(false);
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [extendUntil, setExtendUntil] = useState("");
  const [selectedRecord, setSelectedRecord] = useState<CheckInData | null>(null);

  // Exact database KPI counts from list endpoint's COUNT(*)
  const inRoomCountQuery = useCount("stays", { is_in_house: true });
  const allCheckinsCountQuery = useCount("stays", { is_checked_in: true });
  const pendingArrivalsCountQuery = useCount("stays", { status: "pending" });

  // Filter records by selected tab
  const tabFilteredRecords = allRecords.filter((record) => {
    if (activeTab === "in-room") {
      return record.isInHouse;
    }
    if (activeTab === "all-checkins") {
      return record.isCheckedIn;
    }
    if (activeTab === "pending-arrivals") {
      return record.status === "pending";
    }
    return true;
  });

  // Filter records by search query
  const matchesSearch = (record: CheckInData) => {
    const query = searchQuery.toLowerCase();
    return (
      record.name.toLowerCase().includes(query) ||
      record.mobileNumber.toLowerCase().includes(query) ||
      record.email.toLowerCase().includes(query) ||
      record.roomType.toLowerCase().includes(query) ||
      record.stayRef.toLowerCase().includes(query)
    );
  };

  const filteredRecords = tabFilteredRecords.filter(matchesSearch);
  const totalEntries = filteredRecords.length;
  const pageSize = parseInt(entriesPerPage) || 10;
  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalEntries);
  const paginatedRecords = filteredRecords.slice(startIndex, endIndex);

  const handleActionClick = (record: CheckInData) => {
    setSelectedRecord(record);
    setCheckInModalOpen(true);
  };

  const toDateTimeLocal = (iso: string) => {
    const date = new Date(iso);
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
      date.getHours(),
    )}:${pad(date.getMinutes())}`;
  };

  const handleExtendClick = (record: CheckInData) => {
    setExtendUntil(record.expectedCheckOut ? toDateTimeLocal(record.expectedCheckOut) : "");
    setSelectedRecord(record);
    setExtendModalOpen(true);
  };

  return (
    <div className="space-y-6 animate-fade-in text-foreground">
      <PageHeader
        title="Check-in Management"
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground mr-1">
              In-Room Stays:
            </span>
            <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold px-3 py-1 text-xs border border-emerald-500/30 inline-flex items-center min-w-[5.5rem] justify-center">
              <UserCheck className="w-3.5 h-3.5 mr-1 shrink-0" />
              {inRoomCountQuery.total !== null ? (
                <span>{inRoomCountQuery.total} In-Room</span>
              ) : inRoomCountQuery.isError ? (
                <span title="Count unavailable">- In-Room</span>
              ) : (
                <span className="inline-flex items-center gap-1">
                  <Skeleton className="h-3 w-4 rounded bg-emerald-600/30 dark:bg-emerald-400/30 animate-pulse" />
                  <span>In-Room</span>
                </span>
              )}
            </Badge>
          </div>
        }
      />

      {/* Check-in Tab Filters */}
      <div className="flex items-center gap-2 border-b border-border/80 dark:border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => { setActiveTab("in-room"); setCurrentPage(1); }}
          className={cn(
            "flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-all",
            activeTab === "in-room"
              ? "bg-brand text-white shadow-sm"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          )}
        >
          <UserCheck className="w-4 h-4" />
          <span>In-Room</span>
          <span className={cn(
            "text-[11px] px-1.5 py-0.5 rounded-full font-bold min-w-[1.25rem] inline-flex items-center justify-center",
            activeTab === "in-room" ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
          )}>
            {renderTabCount(inRoomCountQuery)}
          </span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab("all-checkins"); setCurrentPage(1); }}
          className={cn(
            "flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-all",
            activeTab === "all-checkins"
              ? "bg-brand text-white shadow-sm"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          )}
        >
          <Building className="w-4 h-4" />
          <span>All Check-ins</span>
          <span className={cn(
            "text-[11px] px-1.5 py-0.5 rounded-full font-bold min-w-[1.25rem] inline-flex items-center justify-center",
            activeTab === "all-checkins" ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
          )}>
            {renderTabCount(allCheckinsCountQuery)}
          </span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab("pending-arrivals"); setCurrentPage(1); }}
          className={cn(
            "flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-all",
            activeTab === "pending-arrivals"
              ? "bg-brand text-white shadow-sm"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          )}
        >
          <Clock className="w-4 h-4" />
          <span>Pending Arrivals</span>
          <span className={cn(
            "text-[11px] px-1.5 py-0.5 rounded-full font-bold min-w-[1.25rem] inline-flex items-center justify-center",
            activeTab === "pending-arrivals" ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
          )}>
            {renderTabCount(pendingArrivalsCountQuery)}
          </span>
        </button>
      </div>

      {/* Table Container */}
      <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
        <CardContent className="p-5">
          {/* Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-xs font-medium">Show</span>
              <Select
                value={entriesPerPage}
                onValueChange={(val) => {
                  setEntriesPerPage(val);
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger className="w-18 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
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

            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-xs font-medium">Search:</span>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                <Input
                  placeholder="Search check-ins..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="pl-9 w-64 md:w-72 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[150px]">Guest Name</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[150px]">Mobile Number</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[100px] text-center">Room No</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[130px]">Room Type</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[100px] text-center">Occupants</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[150px] text-center">Check-in Time</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[150px] text-center">Expected Checkout</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[120px] text-center">Status</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[110px] text-center">Action</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[130px] text-center">Extend</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[140px] text-center">Documents</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(staysQuery.isLoading || staysQuery.error || paginatedRecords.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={11} className="py-2">
                      <DataState
                        isLoading={staysQuery.isLoading}
                        error={staysQuery.error}
                        isEmpty
                        emptyTitle="No check-in records found"
                        loader={<TableLoading columns={11} />}
                      >
                        <span />
                      </DataState>
                    </TableCell>
                  </TableRow>
                )}
                {paginatedRecords.map((record) => (
                  <TableRow
                    key={record.id}
                    className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                  >
                    <TableCell className="font-medium text-primary">{record.name}</TableCell>
                    <TableCell className="text-muted-foreground">{record.mobileNumber}</TableCell>
                    <TableCell className="text-center">{record.roomNo || "-"}</TableCell>
                    <TableCell>{record.roomType}</TableCell>
                    <TableCell className="text-center">{record.occupants}</TableCell>
                    <TableCell className="text-center text-xs">
                      {record.actualCheckIn ? (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                          {record.actualCheckIn}
                        </span>
                      ) : (
                        <span className="text-amber-500 italic">Pending Check-in</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center text-xs">
                      {record.expectedCheckOut || "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        className={cn(
                          "text-[11px] font-semibold border",
                          record.displayStatus === "In-Room"
                            ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                            : record.displayStatus === "Checked Out"
                              ? "bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-500/30"
                              : record.displayStatus === "Cancelled"
                                ? "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30"
                                : "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30"
                        )}
                      >
                        {record.displayStatus}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className={cn(
                          "h-8 px-2.5 rounded-md text-xs font-semibold text-white transition-all",
                          record.isCheckedOut
                            ? "bg-slate-400 cursor-not-allowed"
                            : record.isCheckedIn
                              ? "bg-rose-600 hover:bg-rose-700 shadow-xs"
                              : "bg-cyan-600 hover:bg-cyan-700 shadow-xs"
                        )}
                        onClick={() => handleActionClick(record)}
                        disabled={
                          !mayWrite ||
                          record.isCheckedOut ||
                          record.status === "cancelled"
                        }
                        title={
                          record.isCheckedOut
                            ? "Already checked out"
                            : record.isCheckedIn
                              ? "Check out guest"
                              : "Check in guest"
                        }
                      >
                        {record.isCheckedIn ? (
                          <>
                            <LogOut className="h-3.5 w-3.5 mr-1" />
                            Out
                          </>
                        ) : (
                          <>
                            <LogIn className="h-3.5 w-3.5 mr-1" />
                            In
                          </>
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="hms-action-on-fill bg-brand hover:bg-brand-hover text-white h-8 w-8 p-0 rounded-md"
                        onClick={() => handleExtendClick(record)}
                        disabled={!mayWrite || record.isCheckedOut || !record.isCheckedIn}
                        title={
                          !record.isCheckedIn
                            ? "Guest has not checked in yet"
                            : record.isCheckedOut
                              ? "Guest already checked out"
                              : "Extend the expected check-out"
                        }
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <button
                        type="button"
                        className="hms-cell-trigger"
                        disabled={!mayWrite || approveDocs.isPending}
                        onClick={() =>
                          approveDocs.mutate({
                            id: record.id,
                            approved: !record.documentsApproval,
                          })
                        }
                        title={
                          record.documentsApproval
                            ? "Approved -- click to reset to pending"
                            : "Pending -- click to approve"
                        }
                      >
                        <Badge
                          className={cn(
                            "cursor-pointer text-xs",
                            record.documentsApproval
                              ? "bg-green-500/20 text-green-600 hover:bg-green-500/30"
                              : "bg-amber-500/20 text-amber-600 hover:bg-amber-500/30"
                          )}
                        >
                          <CheckCircle className="h-4 w-4 mr-1 inline" />
                          {record.documentsApproval ? "Approved" : "Pending"}
                        </Badge>
                      </button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Footer */}
          <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
            <span className="text-muted-foreground text-xs">
              Showing {totalEntries > 0 ? startIndex + 1 : 0} to {endIndex} of {totalEntries} entries
            </span>

            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
              >
                First
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                Previous
              </Button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "ghost"}
                  size="sm"
                  className={cn(
                    "h-8 w-8 p-0 text-xs rounded-xl",
                    currentPage === page
                      ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              ))}
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
              >
                Next
                <ChevronRight className="h-3.5 w-3.5 ml-1" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
              >
                Last
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Check In / Out Modal */}
      <Dialog open={checkInModalOpen} onOpenChange={setCheckInModalOpen}>
        <DialogContent className="max-w-2xl bg-white dark:bg-card text-foreground border-border">
          <DialogHeader className="border-b border-border pb-4">
            <DialogTitle className="text-xl font-semibold flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-primary" />
              {selectedRecord?.isCheckedIn ? "Guest Checkout Confirmation" : "Guest Check-in Confirmation"}
            </DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-6 px-4">
            <div className="grid grid-cols-2 gap-x-8 gap-y-4">
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs uppercase font-medium">Guest Name</span>
                <span className="font-semibold text-base block">{selectedRecord?.name}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs uppercase font-medium">Stay Reference</span>
                <span className="font-semibold text-base block">{selectedRecord?.stayRef ?? "-"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs uppercase font-medium">Room Category</span>
                <span className="font-semibold text-base block">{selectedRecord?.roomType}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs uppercase font-medium">No. of Occupants</span>
                <span className="font-semibold text-base block">{selectedRecord?.occupants}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs uppercase font-medium">Actual Check-in</span>
                <span className="font-semibold text-base block">
                  {selectedRecord?.actualCheckIn || "Not checked in yet"}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs uppercase font-medium">Expected Checkout</span>
                <span className="font-semibold text-base block">
                  {selectedRecord?.expectedCheckOut || "-"}
                </span>
              </div>
            </div>

            <div className="p-3 bg-muted/40 rounded-lg text-xs text-muted-foreground">
              {selectedRecord?.isCheckedIn
                ? "Checking out will update the guest stay to 'checked out' and release the assigned room back to available status."
                : "Checking in will register the guest stay as in-room and record the actual arrival timestamp."}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button
              variant="ghost"
              onClick={() => setCheckInModalOpen(false)}
              className="text-muted-foreground hover:bg-muted/10 hover:text-foreground"
            >
              Cancel
            </Button>
            <Button
              className={cn(
                "text-white px-6 font-semibold",
                selectedRecord?.isCheckedIn ? "bg-rose-600 hover:bg-rose-700" : "bg-cyan-600 hover:bg-cyan-700"
              )}
              disabled={!selectedRecord || checkIn.isPending || checkOut.isPending}
              onClick={() => {
                if (!selectedRecord) return;
                const action = selectedRecord.isCheckedIn ? checkOut : checkIn;
                action.mutate(
                  { id: selectedRecord.id },
                  { onSuccess: () => setCheckInModalOpen(false) },
                );
              }}
            >
              {checkIn.isPending || checkOut.isPending
                ? "Processing..."
                : selectedRecord?.isCheckedIn
                  ? "Confirm Check Out"
                  : "Confirm Check In"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Extend Check Out Modal */}
      <Dialog open={extendModalOpen} onOpenChange={setExtendModalOpen}>
        <DialogContent className="max-w-2xl bg-white dark:bg-card text-foreground border-border">
          <DialogHeader className="border-b border-border pb-4">
            <DialogTitle className="text-xl font-semibold">Extend Checkout Date & Time</DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-6 px-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-4">
              <Label className="text-foreground">Current Checkout <span className="text-red-500">*</span></Label>
              <Input
                value={selectedRecord?.expectedCheckOut || "-"}
                readOnly
                className="bg-transparent border-none text-foreground focus-visible:ring-0 px-0 shadow-none font-medium"
              />
            </div>

            <div className="border-t border-border my-2"></div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-4">
              <Label className="text-foreground">
                New Checkout <span className="text-red-500">*</span>
              </Label>
              <Input
                type="datetime-local"
                value={extendUntil}
                onChange={(event) => setExtendUntil(event.target.value)}
                className="bg-background border-border text-foreground"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              The new time must be later than the current expected check-out time.
            </p>
          </div>

          <div className="flex justify-center gap-4 pt-6 border-t border-border/30">
            <Button
              variant="outline"
              onClick={() => setExtendUntil("")}
              className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
            >
              Reset
            </Button>
            <Button
              className="h-10 px-8 min-w-[110px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
              disabled={!selectedRecord || !extendUntil || extend.isPending}
              onClick={() => {
                if (!selectedRecord || !extendUntil) return;
                extend.mutate(
                  {
                    id: selectedRecord.id,
                    until: new Date(extendUntil).toISOString(),
                  },
                  {
                    onSuccess: () => {
                      setExtendModalOpen(false);
                      setExtendUntil("");
                    },
                  },
                );
              }}
            >
              {extend.isPending ? "Extending..." : "Check & Extend"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CheckIn;
