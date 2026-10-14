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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Plus,
  Upload,
  Search,
  Edit,
  Trash2,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  ArrowLeft,
  LogIn,
  Wallet,
} from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import { toast } from "@/hooks/use-toast";
import { MAX_PAGE_SIZE, ROOM_STATUS } from "@/lib/api/types";
import { useRooms, useStays } from "@/lib/api/hooks";
import {
  useCancelStay,
  useCreateUser,
  useUpdateStay,
  useCheckInStay,
  useCheckOutStay,
  useCreateStay,
  useExtendStay,
  useSetStayDocumentApproval,
} from "@/lib/api/mutations";
import { useAuth } from "@/core/contexts/AuthContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";

export type ReservationData = {
  id: string;
  name: string;
  mobileNumber: string;
  email: string;
  occupants: number;
  roomNo: string;
  roomType: string;
  noOfRooms: number;
  checkIn: string;
  /** Scheduled checkout, shown in the check in and extend dialogs. */
  checkOut: string;
  extendCheckOut: boolean;
  reservationDate: string;
  documentsApproval: boolean;
  /** `stay.status`: pending | active | checkout ... | checked out | cancelled. */
  status: string;
  isCheckedIn: boolean;
  isCheckedOut: boolean;
  expectedCheckout: string;
  stayRef: string;
};

type ViewMode = "list" | "add" | "edit";

const COUNTRY_CODES = [
  { code: "+91", label: "+91 (India)" },
  { code: "+1", label: "+1 (USA)" },
  { code: "+44", label: "+44 (UK)" },
  { code: "+971", label: "+971 (UAE)" },
] as const;

const DEFAULT_COUNTRY_CODE: string = COUNTRY_CODES[0].code;

const EMPTY_FORM = {
  firstName: "",
  lastName: "",
  email: "",
  countryCode: DEFAULT_COUNTRY_CODE,
  mobileNumber: "",
  gender: "",
  city: "",
  nationality: "",
  arrival: "",
  depart: "",
  guestRoom: "yes",
  /** An `amenity.id` (UUID) -- what POST /stays wants in `room_ids`. */
  roomId: "",
  subPackages: "",
  noOfPersons: "",
  numberOfRooms: "",
  gst: "",
  reservationReference: "",
  comments: "",
  eWallet: "disabled",
};

export const Reservations = () => {
  // --- Live data -----------------------------------------------------------
  const staysQuery = useStays({ page: 1, page_size: MAX_PAGE_SIZE });

  const reservations: ReservationData[] = (staysQuery.data?.items ?? []).map((stay) => ({
    id: stay.id,
    name: stay.booker?.name ?? "-",
    mobileNumber: "-",
    email: "-",
    occupants: stay.no_of_guests,
    roomNo: "",
    roomType: "-",
    noOfRooms: stay.no_of_rooms ?? 0,
    checkIn: stay.actual_checkin_time
      ? new Date(stay.actual_checkin_time).toLocaleString()
      : "",
    checkOut: stay.actual_checkout_time
      ? new Date(stay.actual_checkout_time).toLocaleString()
      : "",
    extendCheckOut: false,
    reservationDate: new Date(stay.created_on).toLocaleDateString(),
    documentsApproval: stay.document_approval_status === "approved",
    status: stay.status ?? "-",
    isCheckedIn: stay.is_checked_in,
    isCheckedOut: Boolean(stay.actual_checkout_time),
    expectedCheckout: stay.expected_checkout_time,
    stayRef: stay.internal_stay_ref_number,
  }));

  const { canWrite } = useAuth();
  const mayWrite = canWrite("bookings");
  const checkIn = useCheckInStay();
  const checkOut = useCheckOutStay();
  const extend = useExtendStay();
  const cancel = useCancelStay();
  const approveDocs = useSetStayDocumentApproval();
  const createStay = useCreateStay();
  const updateStay = useUpdateStay();
  const createGuest = useCreateUser({ success: "Guest record created" });

  const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
  const allocatableRooms = (roomsQuery.data?.items ?? []).filter(
    (room) => room.status_name === ROOM_STATUS.AVAILABLE,
  );

  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  useScrollToTop(currentPage);

  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [editingReservation, setEditingReservation] = useState<ReservationData | null>(null);

  // Modal states
  const [checkInModalOpen, setCheckInModalOpen] = useState(false);
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [extendUntil, setExtendUntil] = useState("");
  const [selectedReservation, setSelectedReservation] = useState<ReservationData | null>(null);

  // Form state
  const [formData, setFormData] = useState(EMPTY_FORM);

  const matchesSearch = (reservation: ReservationData) => {
    const query = searchQuery.toLowerCase();
    return (
      reservation.name.toLowerCase().includes(query) ||
      reservation.mobileNumber.toLowerCase().includes(query) ||
      reservation.email.toLowerCase().includes(query) ||
      reservation.roomType.toLowerCase().includes(query)
    );
  };

  const filteredReservations = reservations.filter(matchesSearch);
  const totalEntries = filteredReservations.length;
  const pageSize = parseInt(entriesPerPage) || 10;
  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalEntries);
  const paginatedReservations = filteredReservations.slice(startIndex, endIndex);

  const handleFormChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const resetForm = () => {
    setViewMode("list");
    setEditingReservation(null);
    setFormData(EMPTY_FORM);
  };

  const handleSubmit = () => {
    const checkin = formData.arrival ? new Date(formData.arrival) : null;
    const checkout = formData.depart ? new Date(formData.depart) : null;

    if (viewMode === "edit" && editingReservation) {
      updateStay.mutate(
        {
          id: editingReservation.id,
          body: {
            ...(checkin ? { expected_checkin_time: checkin.toISOString() } : {}),
            ...(checkout ? { expected_checkout_time: checkout.toISOString() } : {}),
            ...(formData.noOfPersons ? { no_of_guests: Number(formData.noOfPersons) } : {}),
            ...(formData.gst ? { gst: formData.gst } : {}),
            ...(formData.comments ? { comments: formData.comments } : {}),
            ...(formData.reservationReference
              ? { external_stay_ref_number: formData.reservationReference }
              : {}),
          },
        },
        { onSuccess: resetForm },
      );
      return;
    }

    if (!checkin || !checkout) {
      toast({
        title: "Arrival and departure are required",
        description: "A reservation stores both as NOT NULL timestamps.",
        variant: "destructive",
      });
      return;
    }

    createGuest.mutate(
      {
        first_name: formData.firstName,
        last_name: formData.lastName || null,
        email: formData.email || null,
        phone_number: `${formData.countryCode || DEFAULT_COUNTRY_CODE}${formData.mobileNumber}`,
        gender: (formData.gender || null) as "male" | "female" | "other" | null,
        address: formData.city || null,
        is_staff: 0,
      },
      {
        onSuccess: (guest) => {
          createStay.mutate(
            {
              booking_user_id: (guest as { id: string }).id,
              expected_checkin_time: checkin.toISOString(),
              expected_checkout_time: checkout.toISOString(),
              no_of_guests: Number(formData.noOfPersons) || 1,
              ...(formData.gst ? { gst: formData.gst } : {}),
              ...(formData.comments ? { comments: formData.comments } : {}),
              ...(formData.reservationReference
                ? { external_stay_ref_number: formData.reservationReference }
                : {}),
              ...(formData.roomId ? { room_ids: [formData.roomId] } : {}),
            },
            { onSuccess: resetForm },
          );
        },
      },
    );
  };

  const handleEdit = (reservation: ReservationData) => {
    setEditingReservation(reservation);
    const nameParts = reservation.name.split(" ");
    setFormData({
      ...EMPTY_FORM,
      firstName: nameParts[0] || "",
      lastName: nameParts.slice(1).join(" ") || "",
      email: reservation.email,
      countryCode: reservation.mobileNumber.split(" ")[0] || DEFAULT_COUNTRY_CODE,
      mobileNumber: reservation.mobileNumber.split(" ")[1] || "",
      arrival: reservation.checkIn,
      noOfPersons: reservation.occupants.toString(),
      numberOfRooms: reservation.noOfRooms.toString(),
    });
    setViewMode("edit");
  };

  const handleDelete = (reservationId: string) => {
    cancel.mutate(reservationId);
  };

  const handleBulkUpload = () => {
    toast({
      title: "Bulk upload is not connected yet",
      description:
        "Imports are tracked in `import_job`, which no API endpoint exposes, " +
        "and the API has no file-upload route. Nothing was uploaded.",
      variant: "destructive",
    });
  };

  const handleCheckInClick = (reservation: ReservationData) => {
    setSelectedReservation(reservation);
    setCheckInModalOpen(true);
  };

  const toDateTimeLocal = (iso: string) => {
    const date = new Date(iso);
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
      date.getHours(),
    )}:${pad(date.getMinutes())}`;
  };

  const handleExtendClick = (reservation: ReservationData) => {
    setExtendUntil(reservation.expectedCheckout ? toDateTimeLocal(reservation.expectedCheckout) : "");
    setSelectedReservation(reservation);
    setExtendModalOpen(true);
  };

  // Add / Edit Reservation Form View
  if (viewMode === "add" || viewMode === "edit") {
    return (
      <div className="space-y-6 animate-fade-in text-foreground">
        <PageHeader
          title={viewMode === "edit" ? "Edit Reservation" : "Add New Reservation"}
          leading={
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-muted"
              onClick={resetForm}
              aria-label="Back to reservation list"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          }
          actions={
            <Button
              variant="ghost"
              className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
              onClick={resetForm}
            >
              Cancel
            </Button>
          }
        />

        {/* Form */}
        <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
          <CardContent className="p-8">
            <div className="grid gap-6">
              {/* Row 1: First Name, Last Name */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    First Name <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    placeholder="Enter First Name"
                    value={formData.firstName}
                    onChange={(e) => handleFormChange("firstName", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Last Name <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    placeholder="Enter Last Name"
                    value={formData.lastName}
                    onChange={(e) => handleFormChange("lastName", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
              </div>

              {/* Row 2: Email, Country Code */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Email</Label>
                  <Input
                    type="email"
                    placeholder="Enter Email"
                    value={formData.email}
                    onChange={(e) => handleFormChange("email", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Country Code <span className="text-red-500">*</span>
                  </Label>
                  <Select
                    value={formData.countryCode}
                    onValueChange={(value) => handleFormChange("countryCode", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select country code" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      {COUNTRY_CODES.map(({ code, label }) => (
                        <SelectItem key={code} value={code}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 3: Mobile Number, Gender */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Mobile Number <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    placeholder="Enter Mobile Number"
                    value={formData.mobileNumber}
                    onChange={(e) => handleFormChange("mobileNumber", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Gender</Label>
                  <Select
                    value={formData.gender}
                    onValueChange={(value) => handleFormChange("gender", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select Gender" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 4: City, Nationality */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">City</Label>
                  <Input
                    placeholder="Enter City"
                    value={formData.city}
                    onChange={(e) => handleFormChange("city", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Nationality</Label>
                  <Select
                    value={formData.nationality}
                    onValueChange={(value) => handleFormChange("nationality", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select nationality" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      <SelectItem value="indian">Indian</SelectItem>
                      <SelectItem value="american">American</SelectItem>
                      <SelectItem value="british">British</SelectItem>
                      <SelectItem value="australian">Australian</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 5: Arrival, Depart */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Arrival <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    type="date"
                    value={formData.arrival}
                    onChange={(e) => handleFormChange("arrival", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Depart <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    type="date"
                    value={formData.depart}
                    onChange={(e) => handleFormChange("depart", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
              </div>

              {/* Row 6: Guest Room */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Guest Room</Label>
                <RadioGroup
                  value={formData.guestRoom}
                  onValueChange={(value) => handleFormChange("guestRoom", value)}
                  className="flex gap-6"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="yes" id="room-yes" className="text-primary border-primary" />
                    <Label htmlFor="room-yes" className="font-normal cursor-pointer">Yes</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="no" id="room-no" className="text-primary border-primary" />
                    <Label htmlFor="room-no" className="font-normal cursor-pointer">No</Label>
                  </div>
                </RadioGroup>
              </div>

              {/* Row 7: Room Allocation, Sub Packages */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Allocate Room</Label>
                  <Select
                    value={formData.roomId}
                    onValueChange={(value) => handleFormChange("roomId", value)}
                    disabled={viewMode === "edit"}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue
                        placeholder={
                          viewMode === "edit"
                            ? "Rooms are changed via room allocations"
                            : allocatableRooms.length === 0
                              ? "No available rooms to allocate"
                              : "Select an available room"
                        }
                      />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      {allocatableRooms.map((room) => (
                        <SelectItem key={room.amenity_id} value={room.amenity_id}>
                          {room.room_name} ({room.amenity_type_name ?? "Room"})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Sub Packages</Label>
                  <Input
                    placeholder="Enter Sub Packages"
                    value={formData.subPackages}
                    onChange={(e) => handleFormChange("subPackages", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
              </div>

              {/* Row 8: Persons, Rooms */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    No. of Persons <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    type="number"
                    min="1"
                    placeholder="Enter No. of Persons"
                    value={formData.noOfPersons}
                    onChange={(e) => handleFormChange("noOfPersons", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Number of Rooms <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    type="number"
                    min="1"
                    placeholder="Enter Number of Rooms"
                    value={formData.numberOfRooms}
                    onChange={(e) => handleFormChange("numberOfRooms", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
              </div>

              {/* Row 9: GST, Reference */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">GST / Tax Number</Label>
                  <Input
                    placeholder="Enter GST"
                    value={formData.gst}
                    onChange={(e) => handleFormChange("gst", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">External Reference</Label>
                  <Input
                    placeholder="OTA / external reference"
                    value={formData.reservationReference}
                    onChange={(e) => handleFormChange("reservationReference", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
              </div>

              {/* Row 10: Comments */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Comments</Label>
                <Textarea
                  placeholder="Additional notes"
                  value={formData.comments}
                  onChange={(e) => handleFormChange("comments", e.target.value)}
                  rows={3}
                  className="bg-muted/30 border-border/50 focus:border-primary resize-none"
                />
              </div>

              {/* Row 11: E-Wallet */}
              <div className="space-y-3 pt-2">
                <Label className="text-sm font-medium flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-muted-foreground" />
                  E-Wallet
                </Label>
                <RadioGroup
                  value={formData.eWallet}
                  onValueChange={(value) => handleFormChange("eWallet", value)}
                  className="flex gap-6"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="enabled" id="ewallet-enabled" className="text-primary border-primary" />
                    <Label htmlFor="ewallet-enabled" className="font-normal cursor-pointer">Enabled</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="disabled" id="ewallet-disabled" className="text-primary border-primary" />
                    <Label htmlFor="ewallet-disabled" className="font-normal cursor-pointer">Disabled</Label>
                  </div>
                </RadioGroup>
              </div>

              {/* Form Buttons */}
              <div className="flex justify-center gap-4 pt-6 border-t border-border/50">
                <Button
                  variant="outline"
                  onClick={resetForm}
                  className="h-12 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={createStay.isPending || updateStay.isPending || createGuest.isPending}
                  className="h-12 px-8 min-w-[120px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                >
                  {createStay.isPending || updateStay.isPending || createGuest.isPending
                    ? "Saving..."
                    : "Submit"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // List View
  return (
    <div className="space-y-6 animate-fade-in text-foreground">
      <PageHeader
        title="Reservation Management"
        actions={
          <>
            <Button
              onClick={() => { setEditingReservation(null); setFormData(EMPTY_FORM); setViewMode("add"); }}
              className="bg-brand hover:bg-brand-hover text-white font-semibold px-5 rounded-xl shadow-md hover:shadow-lg transition-all"
            >
              <Plus className="h-4 w-4 mr-2 stroke-[2.5]" />
              Add Reservation
            </Button>
            <Button
              onClick={() => setBulkUploadOpen(true)}
              className="bg-brand hover:bg-brand-hover text-white font-semibold px-5 rounded-xl shadow-md hover:shadow-lg transition-all"
            >
              <Upload className="h-4 w-4 mr-2 stroke-[2.5]" />
              Bulk Upload
            </Button>
          </>
        }
      />

      {/* Table Container */}
      <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
        <CardContent className="p-5">
          {/* Controls */}
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
                  placeholder="Search reservations..."
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
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
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[150px]">Name</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[170px]">Mobile Number</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[240px] text-center">Email</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[100px] text-center">Occupants</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[90px] text-center">Room No</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[130px]">Room Type</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[110px] text-center">No. of Rooms</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[100px] text-center">Check In</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[130px] text-center">Extend Checkout</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[120px]">Reservation Date</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[150px] text-center">Documents Approval</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap min-w-[90px] text-center">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(staysQuery.isLoading || staysQuery.error || paginatedReservations.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={13} className="py-2">
                      <DataState
                        isLoading={staysQuery.isLoading}
                        error={staysQuery.error}
                        isEmpty
                        emptyTitle="No reservations found"
                        loader={<TableLoading columns={11} />}
                      >
                        <span />
                      </DataState>
                    </TableCell>
                  </TableRow>
                )}
                {paginatedReservations.map((reservation) => (
                  <TableRow
                    key={reservation.id}
                    className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                  >
                    <TableCell className="font-medium text-primary">{reservation.name}</TableCell>
                    <TableCell className="text-muted-foreground">{reservation.mobileNumber}</TableCell>
                    <TableCell className="text-primary text-center px-4">{reservation.email || "-"}</TableCell>
                    <TableCell className="text-center">{reservation.occupants}</TableCell>
                    <TableCell className="text-center">{reservation.roomNo || "-"}</TableCell>
                    <TableCell>{reservation.roomType}</TableCell>
                    <TableCell className="text-center">{reservation.noOfRooms}</TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 px-2 rounded-md text-xs"
                        onClick={() => handleCheckInClick(reservation)}
                        disabled={
                          !mayWrite ||
                          reservation.isCheckedOut ||
                          reservation.status === "cancelled"
                        }
                        title={
                          reservation.isCheckedOut
                            ? "Already checked out"
                            : reservation.isCheckedIn
                              ? "Check out"
                              : "Check in"
                        }
                      >
                        <LogIn className="h-4 w-4 mr-1" />
                        {reservation.isCheckedIn ? "Out" : "In"}
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="hms-action-on-fill bg-brand hover:bg-brand-hover text-white h-8 w-8 p-0 rounded-md"
                        onClick={() => handleExtendClick(reservation)}
                        disabled={!mayWrite || reservation.isCheckedOut}
                        title="Extend the expected check-out"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell>{reservation.reservationDate}</TableCell>
                    <TableCell className="text-center">
                      <button
                        type="button"
                        className="hms-cell-trigger"
                        disabled={!mayWrite || approveDocs.isPending}
                        onClick={() =>
                          approveDocs.mutate({
                            id: reservation.id,
                            approved: !reservation.documentsApproval,
                          })
                        }
                        title={
                          reservation.documentsApproval
                            ? "Approved -- click to reset to pending"
                            : "Pending -- click to approve"
                        }
                      >
                        <Badge
                          className={`${reservation.documentsApproval
                            ? "bg-green-500/20 text-green-600 hover:bg-green-500/30"
                            : "bg-amber-500/20 text-amber-600 hover:bg-amber-500/30"
                            }`}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Badge>
                      </button>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          size="sm"
                          className="h-8 w-8 p-0 rounded-md"
                          onClick={() => handleEdit(reservation)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          className="hms-action-on-fill bg-brand-danger hover:bg-brand-danger-hover text-white h-8 w-8 p-0 rounded-md"
                          onClick={() => handleDelete(reservation.id)}
                          disabled={
                            !mayWrite ||
                            reservation.isCheckedIn ||
                            reservation.status === "cancelled" ||
                            cancel.isPending
                          }
                          title={
                            reservation.isCheckedIn
                              ? "Checked in -- check the guest out instead"
                              : reservation.status === "cancelled"
                                ? "Already cancelled"
                                : "Cancel this reservation and release its rooms"
                          }
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
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
                  className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page
                    ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                    }`}
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

      {/* Bulk Upload Modal */}
      <Dialog open={bulkUploadOpen} onOpenChange={setBulkUploadOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold">Bulk Upload Reservations</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="flex items-center gap-4">
              <Button
                className="bg-brand hover:bg-brand-hover text-white font-medium px-5 h-10 rounded-xl shadow-sm"
              >
                <Download className="h-4 w-4 mr-2" />
                Sample Template
              </Button>
              <div className="flex-1">
                <Button
                  variant="outline"
                  className="h-10 px-4 border-dashed border-2"
                  onClick={() => document.getElementById("bulk-file-upload")?.click()}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Choose File
                </Button>
                <span className="ml-3 text-sm text-muted-foreground">
                  {selectedFile ? selectedFile.name : "No file chosen"}
                </span>
                <input
                  id="bulk-file-upload"
                  type="file"
                  className="hidden"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                />
              </div>
            </div>

            <p className="text-sm text-muted-foreground">
              <a href="#" className="text-primary hover:underline">
                Click here
              </a>{" "}
              to download the report of the last uploaded reservations.
            </p>

            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setBulkUploadOpen(false);
                  setSelectedFile(null);
                }}
                className="h-10 px-6"
              >
                Close
              </Button>
              <Button
                onClick={handleBulkUpload}
                disabled={!selectedFile}
                className="h-10 px-6 bg-brand hover:bg-brand-hover text-white font-semibold rounded-lg"
              >
                Submit
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Check In Modal */}
      <Dialog open={checkInModalOpen} onOpenChange={setCheckInModalOpen}>
        <DialogContent className="max-w-3xl bg-white dark:bg-card text-foreground border-border">
          <DialogHeader className="border-b border-border pb-4">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl font-semibold">Reservation Check-In Confirmation</DialogTitle>
            </div>
          </DialogHeader>
          <div className="py-6 space-y-8">
            <div className="grid grid-cols-2 gap-x-12 gap-y-8 px-6">
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Name :</span>
                <span className="font-medium text-lg">{selectedReservation?.name}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Room Category :</span>
                <span className="font-medium text-lg">{selectedReservation?.roomType}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Checkin Date :</span>
                <span className="font-medium text-lg">
                  {selectedReservation?.checkIn || "Not checked in"}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Expected Checkout :</span>
                <span className="font-medium text-lg">
                  {selectedReservation?.expectedCheckout
                    ? new Date(selectedReservation.expectedCheckout).toLocaleString()
                    : "-"}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Stay Reference :</span>
                <span className="font-medium text-lg">{selectedReservation?.stayRef ?? "-"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Status :</span>
                <span className="font-medium text-lg">{selectedReservation?.status ?? "-"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">No Of Occupants :</span>
                <span className="font-medium text-lg">{selectedReservation?.occupants}</span>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button
              variant="ghost"
              onClick={() => setCheckInModalOpen(false)}
              className="text-muted-foreground hover:bg-muted/10 hover:text-foreground"
            >
              Close
            </Button>
            <Button
              className="bg-cyan-600 hover:bg-cyan-700 text-white px-6"
              disabled={!selectedReservation || checkIn.isPending || checkOut.isPending}
              onClick={() => {
                if (!selectedReservation) return;
                const action = selectedReservation.isCheckedIn ? checkOut : checkIn;
                action.mutate(
                  { id: selectedReservation.id },
                  { onSuccess: () => setCheckInModalOpen(false) },
                );
              }}
            >
              {selectedReservation?.isCheckedIn ? "Check Out" : "Check In"}
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
              <Label className="text-foreground">Check out date & time <span className="text-red-500">*</span></Label>
              <Input
                value={
                  selectedReservation?.expectedCheckout
                    ? new Date(selectedReservation.expectedCheckout).toLocaleString()
                    : "-"
                }
                readOnly
                className="bg-transparent border-none text-foreground focus-visible:ring-0 px-0 shadow-none font-medium"
              />
            </div>

            <div className="border-t border-border my-2"></div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-4">
              <Label className="text-foreground">
                New check out <span className="text-red-500">*</span>
              </Label>
              <Input
                type="datetime-local"
                value={extendUntil}
                onChange={(event) => setExtendUntil(event.target.value)}
                className="bg-white border-gray-200 text-foreground"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              The new time must be later than the current expected check-out; the
              backend rejects anything earlier.
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
              disabled={!selectedReservation || !extendUntil || extend.isPending}
              onClick={() => {
                if (!selectedReservation || !extendUntil) return;
                extend.mutate(
                  {
                    id: selectedReservation.id,
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

export default Reservations;
