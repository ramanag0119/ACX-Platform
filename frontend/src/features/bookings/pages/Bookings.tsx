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
  X,
  ArrowLeft,
  LogIn,
} from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import { toast } from "@/hooks/use-toast";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useRooms, useStays, useUsers } from "@/lib/api/hooks";
import { describeApiError } from "@/lib/api/client";
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

type BookingData = {
  id: string;
  name: string;
  mobileNumber: string;
  email: string;
  occupants: number;
  roomNo: string;
  roomType: string;
  noOfRooms: number;
  checkIn: string;
  extendCheckOut: boolean;
  bookingDate: string;
  documentsApproval: boolean;
  /** `stay.status`: pending | active | checkout ... | checked out | cancelled. */
  status: string;
  isCheckedIn: boolean;
  isCheckedOut: boolean;
  expectedCheckout: string;
  stayRef: string;
};

/**
 * Bookings, connected to GET /stays.
 *
 * THERE IS NO /bookings ENDPOINT AND NO booking TABLE. Phase 2.8 established
 * that a reservation is a `stay`, so that is what this screen lists -- no
 * parallel booking API was invented for it.
 *
 * Field mapping (all real `stay` columns):
 *   name          -> booker.name        (the UserRef; there is no guest table)
 *   occupants     -> no_of_guests
 *   noOfRooms     -> no_of_rooms
 *   checkIn       -> actual_checkin_time
 *   bookingDate   -> created_on
 *   docsApproval  -> document_approval_status
 *
 * NOT AVAILABLE on the stay projection, shown as "-": guest mobile number,
 * guest email and the allocated room number. `UserRef` is deliberately just
 * (id, name, emp_id), and rooms come from
 * GET /stays/{id}/room-allocations one stay at a time.
 *
 * Creating a booking, checking in and extending a checkout are write flows
 * with no endpoint; those controls are disabled.
 */

type ViewMode = "list" | "add" | "edit";

const Bookings = () => {
  // --- Live data -----------------------------------------------------------
  const staysQuery = useStays({ page: 1, page_size: MAX_PAGE_SIZE });

  const mockBookings: BookingData[] = (staysQuery.data?.items ?? []).map((stay) => ({
    id: stay.id,
    name: stay.booker?.name ?? "-",
    // The stay projection carries no guest contact details.
    mobileNumber: "-",
    email: "-",
    occupants: stay.no_of_guests,
    // Allocated rooms need GET /stays/{id}/room-allocations.
    roomNo: "",
    roomType: "-",
    noOfRooms: stay.no_of_rooms ?? 0,
    checkIn: stay.actual_checkin_time
      ? new Date(stay.actual_checkin_time).toLocaleString()
      : "",
    extendCheckOut: false,
    bookingDate: new Date(stay.created_on).toLocaleDateString(),
    documentsApproval: stay.document_approval_status === "approved",
    // --- Live workflow state, straight from `stay`.
    status: stay.status ?? "-",
    isCheckedIn: stay.is_checked_in,
    isCheckedOut: Boolean(stay.actual_checkout_time),
    expectedCheckout: stay.expected_checkout_time,
    stayRef: stay.internal_stay_ref_number,
  }));

  // --- Mutations. Each refetches /stays and /occupancy, so the table and the
  // Occupancy screen agree with the database immediately afterwards.
  const { canWrite } = useAuth();
  const mayWrite = canWrite("bookings");
  const checkIn = useCheckInStay();
  const checkOut = useCheckOutStay();
  const extend = useExtendStay();
  const cancel = useCancelStay();
  const approveDocs = useSetStayDocumentApproval();
  const createStay = useCreateStay();
  const updateStay = useUpdateStay();
  // A booking needs a booker, and a guest IS an `app_user` with is_staff = 0.
  const createGuest = useCreateUser({ success: "Guest record created" });

  // Rooms to allocate with the booking; `room_ids` are handled in the same
  // transaction as the stay, so each becomes Allotted immediately.
  const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
  const guestsQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 0 });

  /**
   * Rooms the backend will actually accept for allocation. `amenity_status`
   * "Available" is the only state POST /stays can allot; Occupied, Allotted and
   * Unavailable rooms are refused with 409, so offering them would only produce
   * an avoidable error. The real `status_name` decides -- nothing is hardcoded.
   */
  const allocatableRooms = (roomsQuery.data?.items ?? []).filter(
    (room) => room.status_name === "Available",
  );

  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [editingBooking, setEditingBooking] = useState<BookingData | null>(null);

  // Modal states
  const [checkInModalOpen, setCheckInModalOpen] = useState(false);
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [extendUntil, setExtendUntil] = useState("");
  const [selectedBooking, setSelectedBooking] = useState<BookingData | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    countryCode: "",
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
    bookingReference: "",
    comments: "",
  });

  const totalEntries = 13;
  const totalPages = Math.ceil(totalEntries / parseInt(entriesPerPage));

  const filteredBookings = mockBookings.filter((booking) => {
    const query = searchQuery.toLowerCase();
    return (
      booking.name.toLowerCase().includes(query) ||
      booking.mobileNumber.toLowerCase().includes(query) ||
      booking.email.toLowerCase().includes(query) ||
      booking.roomType.toLowerCase().includes(query)
    );
  });

  const handleFormChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const resetForm = () => {
    setViewMode("list");
    setEditingBooking(null);
    setFormData({
      firstName: "",
      lastName: "",
      email: "",
      countryCode: "",
      mobileNumber: "",
      gender: "",
      city: "",
      nationality: "",
      arrival: "",
      depart: "",
      guestRoom: "yes",
      roomId: "",
      subPackages: "",
      noOfPersons: "",
      numberOfRooms: "",
      gst: "",
      bookingReference: "",
      comments: "",
    });
  };

  /**
   * Create or update a real reservation.
   *
   * Add mode is two steps, because that is how the schema is shaped: a booking
   * needs a booker, and a guest is an `app_user` row with is_staff = 0. So the
   * guest is created first (POST /users), then the stay referencing them
   * (POST /stays) -- which also allocates any rooms chosen, in one transaction.
   *
   * Edit mode PATCHes the stay. Guest identity fields are not re-sent, because
   * editing a booking must not silently rewrite the guest's record.
   */
  const handleSubmit = () => {
    const checkin = formData.arrival ? new Date(formData.arrival) : null;
    const checkout = formData.depart ? new Date(formData.depart) : null;

    if (viewMode === "edit" && editingBooking) {
      updateStay.mutate(
        {
          id: editingBooking.id,
          body: {
            ...(checkin ? { expected_checkin_time: checkin.toISOString() } : {}),
            ...(checkout ? { expected_checkout_time: checkout.toISOString() } : {}),
            ...(formData.noOfPersons ? { no_of_guests: Number(formData.noOfPersons) } : {}),
            ...(formData.gst ? { gst: formData.gst } : {}),
            ...(formData.comments ? { comments: formData.comments } : {}),
            ...(formData.bookingReference
              ? { external_stay_ref_number: formData.bookingReference }
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
        description: "A stay stores both as NOT NULL timestamps.",
        variant: "destructive",
      });
      return;
    }

    createGuest.mutate(
      {
        first_name: formData.firstName,
        last_name: formData.lastName || null,
        email: formData.email || null,
        phone_number: `${formData.countryCode || "+91"}${formData.mobileNumber}`,
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
              ...(formData.bookingReference
                ? { external_stay_ref_number: formData.bookingReference }
                : {}),
              // A real `amenity.id`, straight from GET /rooms.
              ...(formData.roomId ? { room_ids: [formData.roomId] } : {}),
            },
            { onSuccess: resetForm },
          );
        },
      },
    );
  };

  const handleEdit = (booking: BookingData) => {
    setEditingBooking(booking);
    const nameParts = booking.name.split(" ");
    setFormData({
      firstName: nameParts[0] || "",
      lastName: nameParts.slice(1).join(" ") || "",
      email: booking.email,
      countryCode: booking.mobileNumber.split(" ")[0] || "+91",
      mobileNumber: booking.mobileNumber.split(" ")[1] || "",
      gender: "",
      city: "",
      nationality: "",
      arrival: booking.checkIn,
      depart: "",
      guestRoom: "yes",
      // Left empty on purpose: the row carries a room TYPE NAME, not an
      // `amenity.id`, and the edit branch of handleSubmit sends no `room_ids`
      // anyway -- reallocating a room is a separate operation
      // (PATCH /room-allocations/{id}).
      roomId: "",
      subPackages: "",
      noOfPersons: booking.occupants.toString(),
      numberOfRooms: booking.noOfRooms.toString(),
      gst: "",
      bookingReference: "",
      comments: "",
    });
    setViewMode("edit");
  };

  /**
   * Cancel, not delete.
   *
   * `stay` is referenced by `invoice`, `service_request` and `room_allocation`,
   * so the row is kept and its status moves to 'cancelled', which also releases
   * the rooms it held. The backend refuses this with 409 once a guest has
   * checked in -- they must be checked out instead.
   */
  const handleDelete = (bookingId: string) => {
    cancel.mutate(bookingId);
  };


  /**
   * Bulk upload has no endpoint. `import_job` holds the seeded rows for this
   * feature but no router exposes it, and there is no multipart upload path
   * anywhere in the API. The dialog previously logged the filename and then
   * closed itself, which was indistinguishable from a successful import.
   */
  const handleBulkUpload = () => {
    toast({
      title: "Bulk upload is not connected yet",
      description:
        "Imports are tracked in `import_job`, which no API endpoint exposes, " +
        "and the API has no file-upload route. Nothing was uploaded.",
      variant: "destructive",
    });
  };

  const handleCheckInClick = (booking: BookingData) => {
    setSelectedBooking(booking);
    setCheckInModalOpen(true);
  };

  /** Seeds the picker with the current expected check-out, in local time. */
  const toDateTimeLocal = (iso: string) => {
    const date = new Date(iso);
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
      date.getHours(),
    )}:${pad(date.getMinutes())}`;
  };

  const handleExtendClick = (booking: BookingData) => {
    setExtendUntil(booking.expectedCheckout ? toDateTimeLocal(booking.expectedCheckout) : "");
    setSelectedBooking(booking);
    setExtendModalOpen(true);
  };

  // Add Booking Form View
  if (viewMode === "add" || viewMode === "edit") {
    return (
      <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-muted"
              onClick={() => setViewMode("list")}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <h1 className="text-2xl font-semibold text-foreground">
              {viewMode === "edit" ? "Edit Booking" : "Add New Booking"}
            </h1>
          </div>
          <Button
            variant="ghost"
            className="text-red-500 hover:text-red-600 hover:bg-red-50"
            onClick={() => setViewMode("list")}
          >
            Cancel
          </Button>
        </div>

        {/* Form */}
        <Card className="border-0 shadow-lg rounded-2xl bg-white">
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
                      <SelectItem value="+91">+91 (India)</SelectItem>
                      <SelectItem value="+1">+1 (USA)</SelectItem>
                      <SelectItem value="+44">+44 (UK)</SelectItem>
                      <SelectItem value="+971">+971 (UAE)</SelectItem>
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
              <div className="space-y-2">
                <Label className="text-sm font-medium text-primary">
                  Guest Room <span className="text-red-500">*</span>
                </Label>
                <RadioGroup
                  value={formData.guestRoom}
                  onValueChange={(value) => handleFormChange("guestRoom", value)}
                  className="flex gap-6"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="yes" id="guest-yes" />
                    <Label htmlFor="guest-yes" className="cursor-pointer">Yes</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="no" id="guest-no" />
                    <Label htmlFor="guest-no" className="cursor-pointer">No</Label>
                  </div>
                </RadioGroup>
              </div>

              {/* Row 7: Room Preference, Sub Packages */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Room <span className="text-red-500">*</span>
                  </Label>
                  {/* The value submitted as `room_ids` MUST be the room's
                      `amenity.id`. This select used to offer package-name slugs
                      ("golden", "delux", ...), which are neither rooms nor UUIDs,
                      so POST /stays answered
                      422 room_ids: Input should be a valid UUID.
                      The label shows the human-readable room name; the value is
                      the UUID from GET /rooms. */}
                  <Select
                    value={formData.roomId}
                    onValueChange={(value) => handleFormChange("roomId", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select room to allocate" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      {roomsQuery.isLoading && (
                        <div className="px-3 py-2 text-sm text-muted-foreground">
                          Loading rooms...
                        </div>
                      )}
                      {roomsQuery.error && (
                        <div className="px-3 py-2 text-sm text-muted-foreground">
                          {describeApiError(roomsQuery.error)}
                        </div>
                      )}
                      {allocatableRooms.map((room) => (
                        <SelectItem key={room.id} value={room.id}>
                          {room.name}
                          {room.amenity_type_name ? ` - ${room.amenity_type_name}` : ""}
                        </SelectItem>
                      ))}
                      {!roomsQuery.isLoading &&
                        !roomsQuery.error &&
                        allocatableRooms.length === 0 && (
                          <div className="px-3 py-2 text-sm text-muted-foreground">
                            No room is currently Available
                          </div>
                        )}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Sub Packages</Label>
                  <Select
                    value={formData.subPackages}
                    onValueChange={(value) => handleFormChange("subPackages", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select sub packages" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      <SelectItem value="breakfast">Breakfast Included</SelectItem>
                      <SelectItem value="fullboard">Full Board</SelectItem>
                      <SelectItem value="halfboard">Half Board</SelectItem>
                      <SelectItem value="roomonly">Room Only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 8: No of Persons, Number of Rooms */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">No of Persons</Label>
                  <Select
                    value={formData.noOfPersons}
                    onValueChange={(value) => handleFormChange("noOfPersons", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select number" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                        <SelectItem key={num} value={num.toString()}>
                          {num}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Number of Rooms <span className="text-red-500">*</span>
                  </Label>
                  <Select
                    value={formData.numberOfRooms}
                    onValueChange={(value) => handleFormChange("numberOfRooms", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select number of rooms" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      {[1, 2, 3, 4, 5].map((num) => (
                        <SelectItem key={num} value={num.toString()}>
                          {num}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 9: GST, Booking Reference */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">GST</Label>
                  <Input
                    placeholder="Enter GST"
                    value={formData.gst}
                    onChange={(e) => handleFormChange("gst", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-primary">
                    Booking Reference <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    placeholder="Enter Booking Reference"
                    value={formData.bookingReference}
                    onChange={(e) => handleFormChange("bookingReference", e.target.value)}
                    className="h-12 bg-muted/30 border-border/50 focus:border-primary"
                  />
                </div>
              </div>

              {/* Row 10: Comments */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Comments</Label>
                <Textarea
                  placeholder="Enter comments"
                  value={formData.comments}
                  onChange={(e) => handleFormChange("comments", e.target.value)}
                  className="min-h-[100px] bg-muted/30 border-border/50 focus:border-primary resize-none"
                />
              </div>

              {/* Row 11: ID Proof Documents */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-primary">ID Proof Documents</Label>
                <div className="flex items-center gap-4">
                  <Button
                    variant="outline"
                    className="h-12 px-6 border-dashed border-2 hover:border-primary"
                    onClick={() => document.getElementById("id-proof-upload")?.click()}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Choose Files
                  </Button>
                  <span className="text-muted-foreground text-sm">No file chosen</span>
                  <input
                    id="id-proof-upload"
                    type="file"
                    multiple
                    className="hidden"
                    accept="image/*,.pdf"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-center pt-6">
                <Button
                  onClick={handleSubmit}
                  className="h-12 px-12 bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all"
                >
                  {viewMode === "edit" ? "Update Booking" : "Submit"}
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
    <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Booking Management</h1>
        <div className="flex items-center gap-3">
          <Button
            onClick={() => setViewMode("add")}
            className="bg-cyan-600 hover:bg-cyan-700 text-white font-medium px-5 h-10 rounded-lg shadow-md hover:shadow-lg transition-all"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Bookings
          </Button>
          <Button
            onClick={() => setBulkUploadOpen(true)}
            className="bg-amber-500 hover:bg-amber-600 text-white font-medium px-5 h-10 rounded-lg shadow-md hover:shadow-lg transition-all"
          >
            <Upload className="h-4 w-4 mr-2" />
            Bulk Upload
          </Button>
        </div>
      </div>

      {/* Table Container */}
      <Card className="border-0 shadow-lg rounded-2xl bg-white">
        <CardContent className="p-6">
          {/* Controls */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Show</span>
              <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
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
                  placeholder="Mobile number, Room Type, Guest name, Email"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-80 h-9 bg-muted/30 border-border/50"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[150px]">Name</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[170px]">Mobile Number</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[280px] text-center">Email</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[120px] text-center">Occupants</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[100px] text-center">Room No</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[140px]">Room Type</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[120px] text-center">No. of Rooms</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[100px] text-center">Check In</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[150px] text-center">Extend Checkout</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[130px]">Booking Date</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[170px] text-center">Documents Approval</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[100px] text-center">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(staysQuery.isLoading || staysQuery.error || filteredBookings.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={13} className="py-2">
                      <DataState
                        isLoading={staysQuery.isLoading}
                        error={staysQuery.error}
                        isEmpty
                        emptyTitle="No stays found"
                        loader={<TableLoading columns={11} />}
                      >
                        <span />
                      </DataState>
                    </TableCell>
                  </TableRow>
                )}
                {filteredBookings.map((booking, index) => (
                  <TableRow
                    key={booking.id}
                    className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"
                      } hover:bg-muted/40 transition-colors`}
                  >
                    <TableCell className="font-medium text-primary">{booking.name}</TableCell>
                    <TableCell className="text-muted-foreground">{booking.mobileNumber}</TableCell>
                    <TableCell className="text-primary text-center px-4">{booking.email || "-"}</TableCell>
                    <TableCell className="text-center">{booking.occupants}</TableCell>
                    <TableCell className="text-center">{booking.roomNo || "-"}</TableCell>
                    <TableCell>{booking.roomType}</TableCell>
                    <TableCell className="text-center">{booking.noOfRooms}</TableCell>
                    <TableCell className="text-center">
                      {/* One button, two verbs -- driven by `stay.is_checked_in`. */}
                      <Button
                        size="sm"
                        className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 px-2 rounded-md text-xs"
                        onClick={() => handleCheckInClick(booking)}
                        disabled={
                          !mayWrite ||
                          booking.isCheckedOut ||
                          booking.status === "cancelled"
                        }
                        title={
                          booking.isCheckedOut
                            ? "Already checked out"
                            : booking.isCheckedIn
                              ? "Check out"
                              : "Check in"
                        }
                      >
                        <LogIn className="h-4 w-4 mr-1" />
                        {booking.isCheckedIn ? "Out" : "In"}
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 w-8 p-0 rounded-md"
                        onClick={() => handleExtendClick(booking)}
                        disabled={!mayWrite || booking.isCheckedOut}
                        title="Extend the expected check-out"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell>{booking.bookingDate}</TableCell>
                    <TableCell className="text-center">
                      {/* `stay.document_approval_status`: pending <-> approved. */}
                      <button
                        type="button"
                        disabled={!mayWrite || approveDocs.isPending}
                        onClick={() =>
                          approveDocs.mutate({
                            id: booking.id,
                            approved: !booking.documentsApproval,
                          })
                        }
                        title={
                          booking.documentsApproval
                            ? "Approved -- click to reset to pending"
                            : "Pending -- click to approve"
                        }
                      >
                        <Badge
                          className={`${booking.documentsApproval
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
                          className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 w-8 p-0 rounded-md"
                          onClick={() => handleEdit(booking)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          className="bg-red-500 hover:bg-red-600 text-white h-8 w-8 p-0 rounded-md"
                          onClick={() => handleDelete(booking.id)}
                          disabled={
                            !mayWrite ||
                            booking.isCheckedIn ||
                            booking.status === "cancelled" ||
                            cancel.isPending
                          }
                          title={
                            booking.isCheckedIn
                              ? "Checked in -- check the guest out instead"
                              : booking.status === "cancelled"
                                ? "Already cancelled"
                                : "Cancel this booking and release its rooms"
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
          <div className="flex items-center justify-between mt-6">
            <span className="text-muted-foreground text-sm">
              Showing 1 to {Math.min(parseInt(entriesPerPage), filteredBookings.length)} of{" "}
              {totalEntries} entries
            </span>

            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
              >
                First
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              {[1, 2].map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "ghost"}
                  size="sm"
                  className={`w-9 h-9 p-0 ${currentPage === page
                    ? "bg-primary text-white"
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
                className="text-muted-foreground hover:text-foreground"
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-foreground"
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
            <DialogTitle className="text-xl font-semibold">Bulk Upload</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="flex items-center gap-4">
              <Button
                className="bg-amber-500 hover:bg-amber-600 text-white font-medium px-5 h-10 rounded-lg"
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
              to download the report of the last uploaded bookings.
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
                className="h-10 px-6 bg-cyan-600 hover:bg-cyan-700 text-white"
              >
                Submit
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Check In Modal */}
      <Dialog open={checkInModalOpen} onOpenChange={setCheckInModalOpen}>
        <DialogContent className="max-w-3xl bg-white text-foreground border-border">
          <DialogHeader className="border-b border-border pb-4">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl font-semibold">Booking Confirmation</DialogTitle>

            </div>
          </DialogHeader>
          <div className="py-6 space-y-8">
            <div className="grid grid-cols-2 gap-x-12 gap-y-8 px-6">
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Name :</span>
                <span className="font-medium text-lg">{selectedBooking?.name}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Room Category :</span>
                <span className="font-medium text-lg">{selectedBooking?.roomType}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Checkin Date :</span>
                <span className="font-medium text-lg">
                  {selectedBooking?.checkIn || "Not checked in"}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Expected Checkout :</span>
                <span className="font-medium text-lg">
                  {selectedBooking?.expectedCheckout
                    ? new Date(selectedBooking.expectedCheckout).toLocaleString()
                    : "-"}
                </span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Stay Reference :</span>
                <span className="font-medium text-lg">{selectedBooking?.stayRef ?? "-"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Status :</span>
                <span className="font-medium text-lg">{selectedBooking?.status ?? "-"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">No Of Occupants :</span>
                <span className="font-medium text-lg">{selectedBooking?.occupants}</span>
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
              disabled={!selectedBooking || checkIn.isPending || checkOut.isPending}
              onClick={() => {
                if (!selectedBooking) return;
                // Room state follows: Occupied on check-in, Available on check-out.
                const action = selectedBooking.isCheckedIn ? checkOut : checkIn;
                action.mutate(
                  { id: selectedBooking.id },
                  { onSuccess: () => setCheckInModalOpen(false) },
                );
              }}
            >
              {selectedBooking?.isCheckedIn ? "Check Out" : "Check In"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Extend Check Out Modal */}
      <Dialog open={extendModalOpen} onOpenChange={setExtendModalOpen}>
        <DialogContent className="max-w-2xl bg-white text-foreground border-border">
          <DialogHeader className="border-b border-border pb-4">
            <DialogTitle className="text-xl font-semibold">Extend Checkout Date & Time</DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-6 px-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-4">
              <Label className="text-foreground">Check out date & time <span className="text-red-500">*</span></Label>
              <Input
                value={
                  selectedBooking?.expectedCheckout
                    ? new Date(selectedBooking.expectedCheckout).toLocaleString()
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
              {/* One datetime-local field: `expected_checkout_time` is a single
                  timestamptz column, so splitting it into date + HH + MM + AM
                  controls could only reassemble the same value. */}
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

          <div className="flex justify-center gap-4 pt-6">
            <Button
              variant="outline"
              onClick={() => setExtendUntil("")}
              className="border-amber-500 text-amber-500 hover:bg-amber-50 hover:text-amber-500"
            >
              Reset
            </Button>
            <Button
              className="bg-transparent border border-cyan-500 text-cyan-500 hover:bg-cyan-50"
              disabled={!selectedBooking || !extendUntil || extend.isPending}
              onClick={() => {
                if (!selectedBooking || !extendUntil) return;
                extend.mutate(
                  {
                    id: selectedBooking.id,
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

export default Bookings;
