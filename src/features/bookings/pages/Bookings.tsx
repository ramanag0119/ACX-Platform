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
};

const mockBookings: BookingData[] = [
  {
    id: "1",
    name: "Siva Subramanian N",
    mobileNumber: "+91 6381332167",
    email: "sivasubramaniannarayanan@gmail.com",
    occupants: 1,
    roomNo: "211",
    roomType: "Golden Package",
    noOfRooms: 1,
    checkIn: "27-12-2025 16:22",
    extendCheckOut: false,
    bookingDate: "27-12-2025",
    documentsApproval: true,
  },
  {
    id: "2",
    name: "Senra A",
    mobileNumber: "+91 7397003222",
    email: "",
    occupants: 1,
    roomNo: "",
    roomType: "Golden Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "16-10-2025",
    documentsApproval: true,
  },
  {
    id: "3",
    name: "cspi cspi",
    mobileNumber: "+91 8300275378",
    email: "senthikumaran@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Delux Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "19-11-2024",
    documentsApproval: true,
  },
  {
    id: "4",
    name: "Queen S",
    mobileNumber: "+91 9090441916",
    email: "squeenevangelin@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Golden Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "12-11-2024",
    documentsApproval: true,
  },
  {
    id: "5",
    name: "Caleido Pilot",
    mobileNumber: "+91 8300275377",
    email: "caleidopilot@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Delux Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "05-11-2024",
    documentsApproval: true,
  },
  {
    id: "6",
    name: "Ganesan K",
    mobileNumber: "+91 9894014096",
    email: "",
    occupants: 1,
    roomNo: "",
    roomType: "Golden Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "22-10-2024",
    documentsApproval: true,
  },
  {
    id: "7",
    name: "Yamuna devi",
    mobileNumber: "+91 9566842991",
    email: "yamunasakthi78@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Delux Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "01-07-2023",
    documentsApproval: true,
  },
  {
    id: "8",
    name: "John Lewis",
    mobileNumber: "+91 8529637410",
    email: "johnlll@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Delux Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "05-05-2023",
    documentsApproval: true,
  },
  {
    id: "9",
    name: "Dayawan Johnson",
    mobileNumber: "+1 4544732451",
    email: "dayawan@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Delux Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "05-05-2023",
    documentsApproval: true,
  },
  {
    id: "10",
    name: "Ananthi Vasan",
    mobileNumber: "+91 9876543213",
    email: "ananthi123@gmail.com",
    occupants: 1,
    roomNo: "",
    roomType: "Delux Package",
    noOfRooms: 1,
    checkIn: "",
    extendCheckOut: false,
    bookingDate: "14-03-2023",
    documentsApproval: true,
  },
];

type ViewMode = "list" | "add" | "edit";

const Bookings = () => {
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
    roomPreference: "",
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

  const handleSubmit = () => {
    console.log("Submitting form:", formData);
    // Here you would typically send the data to the backend
    setViewMode("list");
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
      roomPreference: "",
      subPackages: "",
      noOfPersons: "",
      numberOfRooms: "",
      gst: "",
      bookingReference: "",
      comments: "",
    });
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
      roomPreference: booking.roomType,
      subPackages: "",
      noOfPersons: booking.occupants.toString(),
      numberOfRooms: booking.noOfRooms.toString(),
      gst: "",
      bookingReference: "",
      comments: "",
    });
    setViewMode("edit");
  };

  const handleDelete = (bookingId: string) => {
    console.log("Deleting booking:", bookingId);
    // Here you would typically send delete request to backend
  };


  const handleBulkUpload = () => {
    if (selectedFile) {
      console.log("Uploading file:", selectedFile.name);
      // Here you would upload the file to backend
      setBulkUploadOpen(false);
      setSelectedFile(null);
    }
  };

  const handleCheckInClick = (booking: BookingData) => {
    setSelectedBooking(booking);
    setCheckInModalOpen(true);
  };

  const handleExtendClick = (booking: BookingData) => {
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
                    Room Preference <span className="text-red-500">*</span>
                  </Label>
                  <Select
                    value={formData.roomPreference}
                    onValueChange={(value) => handleFormChange("roomPreference", value)}
                  >
                    <SelectTrigger className="h-12 bg-muted/30 border-border/50">
                      <SelectValue placeholder="Select room preference" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      <SelectItem value="golden">Golden Package</SelectItem>
                      <SelectItem value="delux">Delux Package</SelectItem>
                      <SelectItem value="premium">Premium Suite</SelectItem>
                      <SelectItem value="standard">Standard Room</SelectItem>
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
            className="bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold px-5 h-10 rounded-xl shadow-md hover:shadow-lg transition-all"
          >
            <Plus className="h-4 w-4 mr-2 stroke-[2.5]" />
            Add Bookings
          </Button>
          <Button
            onClick={() => setBulkUploadOpen(true)}
            className="bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold px-5 h-10 rounded-xl shadow-md hover:shadow-lg transition-all"
          >
            <Upload className="h-4 w-4 mr-2 stroke-[2.5]" />
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

            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500 pointer-events-none stroke-[2]" />
              <Input
                placeholder="Search bookings..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 w-72 md:w-80 h-10 bg-slate-50/80 dark:bg-[#0c101d] border border-slate-200 dark:border-slate-800 rounded-xl text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus-visible:ring-1 focus-visible:ring-primary focus-visible:border-primary shadow-sm transition-all"
              />
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
                      <Button
                        size="sm"
                        className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 w-8 p-0 rounded-md"
                        onClick={() => handleCheckInClick(booking)}
                      >
                        <LogIn className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 w-8 p-0 rounded-md"
                        onClick={() => handleExtendClick(booking)}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell>{booking.bookingDate}</TableCell>
                    <TableCell className="text-center">
                      <Badge
                        className={`${booking.documentsApproval
                          ? "bg-green-500/20 text-green-600 hover:bg-green-500/30"
                          : "bg-amber-500/20 text-amber-600 hover:bg-amber-500/30"
                          }`}
                      >
                        <CheckCircle className="h-4 w-4" />
                      </Badge>
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
                  className={`w-9 h-9 p-0 rounded-xl ${currentPage === page
                    ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm"
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
                className="bg-[#5865F2] hover:bg-[#4752c4] text-white font-medium px-5 h-10 rounded-xl shadow-sm"
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
                className="h-10 px-6 bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold rounded-lg"
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
                {/* Using bookingDate or a default future date for demo since checkIn might be empty */}
                <span className="font-medium text-lg">{selectedBooking?.checkIn || "16-10-2025 11:00"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground text-sm block">Checkout Date :</span>
                <span className="font-medium text-lg">31-10-2025 13:00</span>
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
              onClick={() => setCheckInModalOpen(false)}
            >
              Check In
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
                value="31-10-2025 13:00"
                readOnly
                className="bg-transparent border-none text-foreground focus-visible:ring-0 px-0 shadow-none font-medium"
              />
            </div>

            <div className="border-t border-border my-2"></div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-4">
              <Label className="text-foreground">Extend check out Date <span className="text-red-500">*</span></Label>
              <Input
                placeholder="31-10-2025"
                className="bg-white border-gray-200 text-foreground placeholder:text-muted-foreground"
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-4">
              <Label className="text-foreground">Extend check out Time <span className="text-red-500">*</span></Label>
              <div className="flex items-center gap-4">
                <div className="flex flex-col items-center">
                  <Button variant="ghost" size="sm" className="h-6 text-cyan-500 hover:bg-cyan-50"><ChevronLeft className="h-4 w-4 rotate-90" /></Button>
                  <span className="text-muted-foreground text-sm">HH</span>
                  <Button variant="ghost" size="sm" className="h-6 text-cyan-500 hover:bg-cyan-50"><ChevronRight className="h-4 w-4 rotate-90" /></Button>
                </div>
                <span className="text-foreground font-medium">:</span>
                <div className="flex flex-col items-center">
                  <Button variant="ghost" size="sm" className="h-6 text-[#5865F2] hover:bg-[#5865F2]/10"><ChevronLeft className="h-4 w-4 rotate-90" /></Button>
                  <span className="text-muted-foreground text-sm">MM</span>
                  <Button variant="ghost" size="sm" className="h-6 text-[#5865F2] hover:bg-[#5865F2]/10"><ChevronRight className="h-4 w-4 rotate-90" /></Button>
                </div>
                <div className="flex items-center ml-2">
                  <button className="px-3.5 py-1 bg-[#5865F2] hover:bg-[#4752c4] text-white rounded-xl text-xs font-semibold shadow-sm transition-all">AM</button>
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-center gap-4 pt-6 border-t border-border/30">
            <Button
              variant="outline"
              onClick={() => { }}
              className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
            >
              Reset
            </Button>
            <Button
              className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
              onClick={() => setExtendModalOpen(false)}
            >
              Check & Extend
            </Button>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
};

export default Bookings;
