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
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Search, ChevronLeft, ChevronRight, ChevronDown, Eye, Edit, Trash2, Upload, X, ChevronUp } from "lucide-react";

type TabType = "facility" | "amenity" | "roomAmenities" | "packages" | "roomSetup";

// Facility Setup Data
const facilitySetupData = [
    {
        id: "1",
        organizationName: "Country Retreat",
        hospitalityName: "CRPL",
        guestRooms: 500,
        hotelImage: "View",
        city: "Hyderabad",
        state: "Hyderabad",
        pinCode: "500001",
        email: "sarumugan@inspirionics.net",
        additionalEmail: "ganesanK@caleidoltenia.com,sikodevelop/inspirionics.net",
        googleMap: "View",
        connectToCaleido: "dcyncounty.db.connect",
    },
];

// Amenity Type Data
const amenityTypeData = [
    { id: "1", amenityType: "Banquet Hall", icon: "Click Here" },
    { id: "2", amenityType: "Business Center", icon: "Click Here" },
    { id: "3", amenityType: "Car Parking", icon: "-" },
    { id: "4", amenityType: "Champagne Bar", icon: "Click Here" },
    { id: "5", amenityType: "Diamond Epicure Kitchen", icon: "Click Here" },
    { id: "6", amenityType: "Divine Linens Turndown", icon: "Click Here" },
    { id: "7", amenityType: "Gaming Arena", icon: "Click Here" },
    { id: "8", amenityType: "Guest Room", icon: "-" },
    { id: "9", amenityType: "Gym", icon: "Click Here" },
    { id: "10", amenityType: "High-Tea Service Area", icon: "Click Here" },
];

// Room Amenities Data
const roomAmenitiesData = [
    { id: "1", amenity: "Ample Wall Outlets" },
    { id: "2", amenity: "Business Facilities" },
    { id: "3", amenity: "Caleido - Air Quality Control" },
    { id: "4", amenity: "Caleido Smart Lock" },
    { id: "5", amenity: "Champagne Bar" },
    { id: "6", amenity: "Complimentary Electronics Chargers" },
    { id: "7", amenity: "Complimentary Luggage storage" },
    { id: "8", amenity: "Curated Experiences" },
    { id: "9", amenity: "Doctor On Call" },
    { id: "10", amenity: "Electronic Safe / Locker" },
];

// Packages Data
const packagesData = [
    {
        id: "1",
        packageName: "breakfast",
        amenityType: "Continental old",
        subPackages: "-",
        features: "coffee(unlimited), fresh juice(1 glass), poached fish, club sandwich...",
        image: "-",
    },
    {
        id: "2",
        packageName: "Business class Exclusive",
        amenityType: "Business Center",
        subPackages: "-",
        features: "Iron + ironing board, air freshener, Charging points, desk & chair, mood lights...",
        image: "-",
    },
    {
        id: "3",
        packageName: "Caleido Package",
        amenityType: "Guest Room",
        subPackages: "Amenities",
        features: "Elite Geyser, Blackout Curtain, Lamp, Wardrobe, air condition, Pet Friendly...",
        image: "-",
    },
    {
        id: "4",
        packageName: "Pool",
        amenityType: "Swimming",
        subPackages: "Pool package",
        features: "Expert-Mix, Resort-Pool, Rooftop-Refreshing Oasis, outdoor pool, infinity outdoor...",
        image: "-",
    },
    {
        id: "5",
        packageName: "Honeymoon Bundle",
        amenityType: "Honey Moon",
        subPackages: "-",
        features: "Romantic Spa, Candlelit Dinner, Champagne upon arrival, Rose Petal Bed...",
        image: "-",
    },
];

// Room Setup Data
const roomSetupData = [
    { id: "1", amenityType: "Busy Room", package: "Black Room", roomNo: "101", smoking: "NO", poolFacing: "NO" },
    { id: "2", amenityType: "Restaurant", package: "South Indian Restaurant", roomNo: "102", smoking: "NO", poolFacing: "NO" },
    { id: "3", amenityType: "Cross Room", package: "None", roomNo: "103", smoking: "NO", poolFacing: "NO" },
    { id: "4", amenityType: "Restaurant", package: "South Indian Restaurant", roomNo: "104", smoking: "NO", poolFacing: "NO" },
    { id: "5", amenityType: "Restaurant", package: "South Indian Restaurant", roomNo: "105", smoking: "NO", poolFacing: "NO" },
    { id: "6", amenityType: "Guest Room", package: "Delux Package", roomNo: "106", smoking: "NO", poolFacing: "NO" },
    { id: "7", amenityType: "Guest Room", package: "Delux Package", roomNo: "107", smoking: "YES", poolFacing: "YES" },
    { id: "8", amenityType: "Car Parking", package: "None", roomNo: "108", smoking: "YES", poolFacing: "YES" },
    { id: "9", amenityType: "Lavish Room", package: "Golden Package", roomNo: "111", smoking: "YES", poolFacing: "YES" },
    { id: "10", amenityType: "Lavish Room", package: "Golden Package", roomNo: "114", smoking: "YES", poolFacing: "YES" },
];

// Selected Amenities for Room Amenities Tab
const selectedAmenities = [
    "Ample Wall Outlets", "Business Facilities", "Caleido - Air Quality Control", "Caleido Smart Lock",
    "Champagne Bar", "Complimentary Electronics Chargers", "Complimentary Luggage storage",
    "Curated Experiences", "Doctor On Call", "Electronic Safe / Locker",
    "Exercise Facilities and Accessories", "Fancy Bathrobes", "Flat Screen TV", "Hair dryer",
    "High Speed Wireless Internet", "Iron", "Ironing Board", "Kid Friendly Room and Products",
    "Letter Head with Pen", "Mini Bar / Mini Fridge", "Mood lighting", "Newspaper",
    "Non-Smoking Rooms", "Parking", "Pet Friendly", "Premium Bedding", "Smoking Lounge",
    "Stain Remover Wipes", "Tea / Coffee Maker", "Work Desk"
];

const FacilityManagement = () => {
    const [activeTab, setActiveTab] = useState<TabType>("facility");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    const [editFacilityOpen, setEditFacilityOpen] = useState(false);
    const [editAmenityOpen, setEditAmenityOpen] = useState(false);
    const [editPackageOpen, setEditPackageOpen] = useState(false);
    const [editRoomOpen, setEditRoomOpen] = useState(false);

    // Form states
    const [amenityForm, setAmenityForm] = useState({
        amenityType: "",
        amenitiesIcon: null as File | null,
    });

    const [packageForm, setPackageForm] = useState({
        packages: "",
        roomType: "",
        amenityType: "",
        features: "",
        subPackages: "",
        packageImage: "",
    });

    const [roomSetupForm, setRoomSetupForm] = useState({
        amenityType: "",
        package: "",
        facilityStructure: [] as string[],
        room: "",
        smoking: "no",
        poolFacing: "no",
    });

    // Packages sub-tab state
    const [packagesSubTab, setPackagesSubTab] = useState<"parent" | "sub">("parent");

    // Sub Packages form state
    const [subPackageForm, setSubPackageForm] = useState({
        parentPackage: "",
        packageName: "",
        amenityType: "",
        features: "",
        subPackages: "",
        packageImage: "",
    });

    // Sub Packages Data
    const subPackagesData = [
        {
            id: "1",
            sNo: 1,
            packageName: "Luxuryking",
            amenityType: "undefined",
            features: "Mini bar, 24 inch LCD tv, cable sports HD/netflix, light dimmer bedroom...",
            image: "-",
        },
        {
            id: "2",
            sNo: 2,
            packageName: "Sunrise",
            amenityType: "Champagne Bar",
            features: "Complete Dining Club, Champagne Bar, Cooking Demo...",
            image: "-",
        },
    ];

    const handleSubPackageReset = () => {
        setSubPackageForm({
            parentPackage: "",
            packageName: "",
            amenityType: "",
            features: "",
            subPackages: "",
            packageImage: "",
        });
    };

    const tabs = [
        { id: "facility" as TabType, label: "Facility Setup" },
        { id: "amenity" as TabType, label: "Amenity Type" },
        { id: "roomAmenities" as TabType, label: "Room Amenities" },
        { id: "packages" as TabType, label: "Packages" },
        { id: "roomSetup" as TabType, label: "Room Setup" },
    ];

    const handleReset = () => {
        if (activeTab === "amenity") {
            setAmenityForm({ amenityType: "", amenitiesIcon: null });
        } else if (activeTab === "packages") {
            setPackageForm({ packages: "", roomType: "", amenityType: "", features: "", subPackages: "", packageImage: "" });
        } else if (activeTab === "roomSetup") {
            setRoomSetupForm({ amenityType: "", package: "", facilityStructure: [], room: "", smoking: "no", poolFacing: "no" });
        }
    };

    const handleSubmit = () => {
        console.log("Submitting form for tab:", activeTab);
    };

    // Facility Setup Tab
    const renderFacilitySetup = () => (
        <Card className="border-0 shadow-lg rounded-2xl bg-white">
            <CardContent className="p-6">
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
                            </SelectContent>
                        </Select>
                        <span className="text-muted-foreground text-sm">entries</span>
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="text-muted-foreground text-sm">Search:</span>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Organization name, Hotel name"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-10 w-64 h-9 bg-muted/30 border-border/50"
                            />
                        </div>
                    </div>
                </div>

                <div className="rounded-xl overflow-hidden border border-gray-200">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium">Organization Name</TableHead>
                                <TableHead className="text-gray-600 font-medium">Hospitality Name</TableHead>
                                <TableHead className="text-gray-600 font-medium">Guest Rooms</TableHead>
                                <TableHead className="text-gray-600 font-medium">Hotel Image</TableHead>
                                <TableHead className="text-gray-600 font-medium">City</TableHead>
                                <TableHead className="text-gray-600 font-medium">State</TableHead>
                                <TableHead className="text-gray-600 font-medium">PIN Code</TableHead>
                                <TableHead className="text-gray-600 font-medium">Email</TableHead>
                                <TableHead className="text-gray-600 font-medium">Google Map</TableHead>
                                <TableHead className="text-gray-600 font-medium">Connect to Caleido</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {facilitySetupData.map((row, index) => (
                                <TableRow
                                    key={row.id}
                                    className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}
                                >
                                    <TableCell>{row.organizationName}</TableCell>
                                    <TableCell>{row.hospitalityName}</TableCell>
                                    <TableCell>{row.guestRooms}</TableCell>
                                    <TableCell>
                                        <span className="text-cyan-400 cursor-pointer hover:underline">{row.hotelImage}</span>
                                    </TableCell>
                                    <TableCell>{row.city}</TableCell>
                                    <TableCell>{row.state}</TableCell>
                                    <TableCell>{row.pinCode}</TableCell>
                                    <TableCell className="max-w-[150px] truncate">{row.email}</TableCell>
                                    <TableCell>
                                        <span className="text-cyan-400 cursor-pointer hover:underline">{row.googleMap}</span>
                                    </TableCell>
                                    <TableCell>{row.connectToCaleido}</TableCell>
                                    <TableCell>
                                        <div className="flex items-center justify-center">
                                            <Button size="sm" className="bg-brand-teal hover:bg-brand-teal/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFacilityOpen(true)}>
                                                <Edit className="h-[14px] w-[14px]" />
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>

                <div className="flex items-center justify-between mt-6">
                    <span className="text-muted-foreground text-sm">Showing 1 to 1 of 1 entries</span>
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
                        <Button variant="default" size="sm" className="w-9 h-9 p-0 bg-primary text-white">1</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );

    // Amenity Type Tab
    const renderAmenityType = () => (
        <>
            <Card className="border-0 shadow-lg rounded-2xl bg-white mb-6">
                <CardContent className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Amenity Type</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label className="text-primary text-sm font-medium">
                                Amenity Type <span className="text-red-500">*</span>
                            </Label>
                            <Input
                                placeholder="Enter Amenity Type"
                                value={amenityForm.amenityType}
                                onChange={(e) => setAmenityForm({ ...amenityForm, amenityType: e.target.value })}
                                className="h-10 bg-muted/30 border-border/50"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Amenities Icon</Label>
                            <div className="flex items-center gap-2">
                                <Button variant="outline" className="bg-muted/30 border-border/50">
                                    <Upload className="h-4 w-4 mr-2" />
                                    Choose File
                                </Button>
                                <span className="text-muted-foreground text-sm">No file chosen</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pt-6 mt-6 border-t border-border/30">
                        <Button onClick={handleReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">
                            Reset
                        </Button>
                        <Button onClick={handleSubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
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
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input
                                placeholder="Amenity type"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-48 h-9 bg-muted/30 border-border/50"
                            />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium text-center">Amenity Type</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Icon</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {amenityTypeData.map((row, index) => (
                                    <TableRow
                                        key={row.id}
                                        className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}
                                    >
                                        <TableCell className="text-center">{row.amenityType}</TableCell>
                                        <TableCell className="text-center">
                                            {row.icon === "-" ? (
                                                <span>-</span>
                                            ) : (
                                                <span className="text-cyan-400 cursor-pointer hover:underline">{row.icon}</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center justify-center gap-2">
                                                <Button size="sm" className="bg-brand-teal hover:bg-brand-teal/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditAmenityOpen(true)}>
                                                    <Edit className="h-[14px] w-[14px]" />
                                                </Button>
                                                <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]">
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
                        <span className="text-muted-foreground text-sm">Showing 1 to 10 of 21 entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
                            <Button variant="default" size="sm" className="w-9 h-9 p-0 bg-primary text-white">1</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">2</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">3</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </>
    );

    // Room Amenities Tab
    const renderRoomAmenities = () => (
        <>
            <Card className="border-0 shadow-lg rounded-2xl bg-white mb-6">
                <CardContent className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Room Amenities</h3>

                    <div className="p-4 border border-gray-200 rounded-lg bg-muted/20 mb-6">
                        <div className="flex flex-wrap gap-2.5">
                            {selectedAmenities.map((amenity) => (
                                <Badge
                                    key={amenity}
                                    className="bg-brand/15 text-brand dark:bg-brand/25 dark:text-[#c7d2fe] border border-brand/35 px-3.5 py-1.5 rounded-full flex items-center gap-2 font-medium text-xs shadow-sm hover:bg-brand/25 transition-all"
                                >
                                    {amenity}
                                    <X className="h-3.5 w-3.5 cursor-pointer hover:text-red-500 hover:scale-110 transition-all opacity-70 hover:opacity-100" />
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div className="flex justify-center pt-6 mt-6 border-t border-border/30">
                        <Button onClick={handleSubmit} className="h-11 px-12 min-w-[140px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
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
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input
                                placeholder="Room amenities"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-48 h-9 bg-muted/30 border-border/50"
                            />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium text-center">Room Amenities</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {roomAmenitiesData.map((row, index) => (
                                    <TableRow
                                        key={row.id}
                                        className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}
                                    >
                                        <TableCell className="text-center">{row.amenity}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing 1 to 10 of 30 entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
                            <Button variant="default" size="sm" className="w-9 h-9 p-0 bg-primary text-white">1</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">2</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">3</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </>
    );

    // Packages Tab
    const renderPackages = () => (
        <>
            <Card className="border-0 shadow-lg rounded-2xl bg-white mb-6">
                <CardContent className="p-6">
                    {packagesSubTab === "parent" ? (
                        // Parent Packages Form
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Packages</Label>
                                    <Input
                                        placeholder="Enter Package Name"
                                        value={packageForm.packages}
                                        onChange={(e) => setPackageForm({ ...packageForm, packages: e.target.value })}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-primary text-sm font-medium">
                                        Room Type <span className="text-red-500">*</span>
                                    </Label>
                                    <Select
                                        value={packageForm.roomType}
                                        onValueChange={(v) => setPackageForm({ ...packageForm, roomType: v })}
                                    >
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Room Type" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-popover">
                                            <SelectItem value="guest">Guest Room</SelectItem>
                                            <SelectItem value="deluxe">Deluxe Room</SelectItem>
                                            <SelectItem value="suite">Suite</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-primary text-sm font-medium">
                                        Amenity Type <span className="text-red-500">*</span>
                                    </Label>
                                    <Select
                                        value={packageForm.amenityType}
                                        onValueChange={(v) => setPackageForm({ ...packageForm, amenityType: v })}
                                    >
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Amenity Type" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-popover">
                                            <SelectItem value="continental">Continental old</SelectItem>
                                            <SelectItem value="business">Business Center</SelectItem>
                                            <SelectItem value="guest-room">Guest Room</SelectItem>
                                            <SelectItem value="swimming">Swimming</SelectItem>
                                            <SelectItem value="honeymoon">Honey Moon</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Features</Label>
                                    <Input
                                        placeholder="Enter Features"
                                        value={packageForm.features}
                                        onChange={(e) => setPackageForm({ ...packageForm, features: e.target.value })}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Sub Packages</Label>
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={packageForm.subPackages}
                                            onValueChange={(v) => setPackageForm({ ...packageForm, subPackages: v })}
                                        >
                                            <SelectTrigger className="h-10 bg-muted/30 border-border/50 flex-1">
                                                <SelectValue placeholder="Select Sub Package" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-popover">
                                                <SelectItem value="amenities">Amenities</SelectItem>
                                                <SelectItem value="pool">Pool package</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <Button size="icon" className="bg-cyan-600 hover:bg-cyan-700 h-10 w-10">
                                            +
                                        </Button>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Package Image</Label>
                                    <div className="flex items-center gap-2">
                                        <Button variant="outline" className="bg-muted/30 border-border/50">
                                            <Upload className="h-4 w-4 mr-2" />
                                            Choose file
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        // Sub Packages Form
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Packages</Label>
                                    <Select
                                        value={subPackageForm.parentPackage}
                                        onValueChange={(v) => setSubPackageForm({ ...subPackageForm, parentPackage: v })}
                                    >
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Room Number" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-popover">
                                            <SelectItem value="breakfast">Breakfast</SelectItem>
                                            <SelectItem value="caleido">Caleido Package</SelectItem>
                                            <SelectItem value="pool">Pool</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Package Name</Label>
                                    <Input
                                        placeholder="Enter Package Name"
                                        value={subPackageForm.packageName}
                                        onChange={(e) => setSubPackageForm({ ...subPackageForm, packageName: e.target.value })}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Amenity Type</Label>
                                    <Select
                                        value={subPackageForm.amenityType}
                                        onValueChange={(v) => setSubPackageForm({ ...subPackageForm, amenityType: v })}
                                    >
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Amenity Type" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-popover">
                                            <SelectItem value="continental">Continental old</SelectItem>
                                            <SelectItem value="business">Business Center</SelectItem>
                                            <SelectItem value="champagne">Champagne Bar</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Features</Label>
                                    <Input
                                        placeholder="Enter Features"
                                        value={subPackageForm.features}
                                        onChange={(e) => setSubPackageForm({ ...subPackageForm, features: e.target.value })}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Sub Packages</Label>
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={subPackageForm.subPackages}
                                            onValueChange={(v) => setSubPackageForm({ ...subPackageForm, subPackages: v })}
                                        >
                                            <SelectTrigger className="h-10 bg-muted/30 border-border/50 flex-1">
                                                <SelectValue placeholder="Select Sub Package" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-popover">
                                                <SelectItem value="amenities">Amenities</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <Button size="icon" className="bg-cyan-600 hover:bg-cyan-700 h-10 w-10">
                                            +
                                        </Button>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Package Image</Label>
                                    <div className="flex items-center gap-2">
                                        <Button variant="outline" className="bg-muted/30 border-border/50">
                                            <Upload className="h-4 w-4 mr-2" />
                                            Choose file
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="flex justify-center gap-4 pt-6 mt-6 border-t border-border/30">
                        <Button
                            onClick={packagesSubTab === "parent" ? handleReset : handleSubPackageReset}
                            variant="outline"
                            className="h-10 px-8 bg-cyan-600 text-white border-0 hover:bg-cyan-700"
                        >
                            Reset
                        </Button>
                        <Button onClick={handleSubmit} className="h-10 px-8 bg-amber-500 hover:bg-amber-600 text-white">
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Sub Tabs for Parent/Sub Packages */}
            <div className="flex gap-1 bg-muted/30 p-1 rounded-xl w-fit mb-6">
                <button
                    onClick={() => setPackagesSubTab("parent")}
                    className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${packagesSubTab === "parent"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                        }`}
                >
                    Parent Packages
                </button>
                <button
                    onClick={() => setPackagesSubTab("sub")}
                    className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${packagesSubTab === "sub"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                        }`}
                >
                    Sub Packages
                </button>
            </div>

            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
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
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input
                                placeholder="Package Name"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-48 h-9 bg-muted/30 border-border/50"
                            />
                        </div>
                    </div>

                    {packagesSubTab === "parent" ? (
                        // Parent Packages Table
                        <div className="rounded-xl overflow-hidden border border-gray-200">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                        <TableHead className="text-primary font-semibold">Package Name</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Amenity Type</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Sub Packages</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Features</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Image</TableHead>
                                        <TableHead className="text-red-400 font-semibold text-center">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {packagesData.map((row, index) => (
                                        <TableRow
                                            key={row.id}
                                            className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}
                                        >
                                            <TableCell className="text-primary">{row.packageName}</TableCell>
                                            <TableCell className="text-primary">{row.amenityType}</TableCell>
                                            <TableCell>
                                                {row.subPackages === "-" ? "-" : (
                                                    <span className="text-primary">{row.subPackages}</span>
                                                )}
                                            </TableCell>
                                            <TableCell className="max-w-[300px] truncate">{row.features}</TableCell>
                                            <TableCell>{row.image}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center justify-center gap-2">
                                                    <Button size="sm" className="bg-brand-teal hover:bg-brand-teal/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditPackageOpen(true)}>
                                                        <Edit className="h-[14px] w-[14px]" />
                                                    </Button>
                                                    <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]">
                                                        <Trash2 className="h-[14px] w-[14px]" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    ) : (
                        // Sub Packages Table
                        <div className="rounded-xl overflow-hidden border border-gray-200">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                        <TableHead className="text-gray-600 font-medium">S No</TableHead>
                                        <TableHead className="text-primary font-semibold">Package Name</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Amenity Type</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Features</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Image</TableHead>
                                        <TableHead className="text-red-400 font-semibold text-center">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {subPackagesData.map((row, index) => (
                                        <TableRow
                                            key={row.id}
                                            className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}
                                        >
                                            <TableCell>{row.sNo}</TableCell>
                                            <TableCell className="text-primary">{row.packageName}</TableCell>
                                            <TableCell className="text-primary">{row.amenityType}</TableCell>
                                            <TableCell className="max-w-[300px] truncate">{row.features}</TableCell>
                                            <TableCell>{row.image}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center justify-center gap-2">
                                                    <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700 text-white h-8 w-8 p-0 rounded-full">
                                                        <Edit className="h-4 w-4" />
                                                    </Button>
                                                    <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white h-8 w-8 p-0 rounded-full">
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    )}

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing 1 to {packagesSubTab === "parent" ? packagesData.length : subPackagesData.length} of {packagesSubTab === "parent" ? "12" : "2"} entries
                        </span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
                            <Button variant="default" size="sm" className="w-9 h-9 p-0 bg-primary text-white rounded-full">1</Button>
                            {packagesSubTab === "parent" && (
                                <Button variant="ghost" size="sm" className="text-muted-foreground">2</Button>
                            )}
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </>
    );

    // Room Setup Tab
    const renderRoomSetup = () => (
        <>
            <Card className="border-0 shadow-lg rounded-2xl bg-white mb-6">
                <CardContent className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Room Setup</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Amenity Type</Label>
                                <Select
                                    value={roomSetupForm.amenityType}
                                    onValueChange={(v) => setRoomSetupForm({ ...roomSetupForm, amenityType: v })}
                                >
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select an amenity" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        <SelectItem value="guest-room">Guest Room</SelectItem>
                                        <SelectItem value="restaurant">Restaurant</SelectItem>
                                        <SelectItem value="car-parking">Car Parking</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Package</Label>
                                <Select
                                    value={roomSetupForm.package}
                                    onValueChange={(v) => setRoomSetupForm({ ...roomSetupForm, package: v })}
                                >
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select room package" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        <SelectItem value="delux">Delux Package</SelectItem>
                                        <SelectItem value="golden">Golden Package</SelectItem>
                                        <SelectItem value="none">None</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Facility Structure</Label>
                                <div className="p-2 border border-gray-200 rounded-lg bg-white max-h-64 overflow-y-auto">
                                    <div className="space-y-0">
                                        {/* CXPL Root */}
                                        <Collapsible defaultOpen>
                                            <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                                <span className="text-sm">CXPL</span>
                                            </CollapsibleTrigger>
                                            <CollapsibleContent className="ml-4">
                                                {/* Building A */}
                                                <Collapsible>
                                                    <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                        <span className="text-sm">Building A</span>
                                                    </CollapsibleTrigger>
                                                    <CollapsibleContent className="ml-4 pl-2 border-l border-border/30">
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor 1</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor 2</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor 3</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor 4</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor 5</div>
                                                    </CollapsibleContent>
                                                </Collapsible>

                                                {/* Demo Box */}
                                                <Collapsible>
                                                    <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                        <span className="text-sm">Demo Box</span>
                                                    </CollapsibleTrigger>
                                                    <CollapsibleContent className="ml-4 pl-2 border-l border-border/30">
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">US demo</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Demo</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Senthil MDU room</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Senthil USA</div>
                                                    </CollapsibleContent>
                                                </Collapsible>

                                                {/* Dev & Testing */}
                                                <Collapsible>
                                                    <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                        <span className="text-sm">Dev & Testing</span>
                                                    </CollapsibleTrigger>
                                                    <CollapsibleContent className="ml-4 pl-2 border-l border-border/30">
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor1</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Testing</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">FW_Dev Devices</div>
                                                    </CollapsibleContent>
                                                </Collapsible>

                                                {/* Building D PILOT */}
                                                <Collapsible>
                                                    <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                        <span className="text-sm">Building D PILOT</span>
                                                    </CollapsibleTrigger>
                                                    <CollapsibleContent className="ml-4 pl-2 border-l border-border/30">
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Ground Floor</div>
                                                        <div className="py-1 px-2 text-sm hover:bg-muted/20 rounded cursor-pointer">Floor 1</div>
                                                    </CollapsibleContent>
                                                </Collapsible>
                                            </CollapsibleContent>
                                        </Collapsible>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Room</Label>
                                <Input
                                    placeholder="101,102,103,104"
                                    value={roomSetupForm.room}
                                    onChange={(e) => setRoomSetupForm({ ...roomSetupForm, room: e.target.value })}
                                    className="h-10 bg-muted/30 border-border/50"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Smoking</Label>
                                <RadioGroup
                                    value={roomSetupForm.smoking}
                                    onValueChange={(v) => setRoomSetupForm({ ...roomSetupForm, smoking: v })}
                                    className="flex gap-4"
                                >
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="yes" id="smoking-yes" />
                                        <Label htmlFor="smoking-yes" className="cursor-pointer">Yes</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="no" id="smoking-no" />
                                        <Label htmlFor="smoking-no" className="cursor-pointer">No</Label>
                                    </div>
                                </RadioGroup>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Pool Facing</Label>
                                <RadioGroup
                                    value={roomSetupForm.poolFacing}
                                    onValueChange={(v) => setRoomSetupForm({ ...roomSetupForm, poolFacing: v })}
                                    className="flex gap-4"
                                >
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="yes" id="pool-yes" />
                                        <Label htmlFor="pool-yes" className="cursor-pointer">Yes</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="no" id="pool-no" />
                                        <Label htmlFor="pool-no" className="cursor-pointer">No</Label>
                                    </div>
                                </RadioGroup>
                            </div>

                            {/* Room Image Preview */}
                            <div className="w-16 h-32 bg-muted/30 border border-gray-200 rounded-lg flex items-center justify-center">
                                <div className="w-8 h-24 bg-muted/50 rounded" />
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pt-6 mt-6 border-t border-border/30">
                        <Button onClick={handleReset} variant="outline" className="h-10 px-8 bg-cyan-600 text-white border-0 hover:bg-cyan-700">
                            Reset
                        </Button>
                        <Button onClick={handleSubmit} className="h-10 px-8 bg-amber-500 hover:bg-amber-600 text-white">
                            Submit
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
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
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input
                                placeholder="Room No"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-48 h-9 bg-muted/30 border-border/50"
                            />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Amenity Type</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Package</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Smoking</TableHead>
                                    <TableHead className="text-gray-600 font-medium">Pool Facing</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {roomSetupData.map((row, index) => (
                                    <TableRow
                                        key={row.id}
                                        className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}
                                    >
                                        <TableCell>
                                            {row.amenityType === "Busy Room" || row.amenityType === "Guest Room" ? (
                                                <span className="text-amber-400">{row.amenityType}</span>
                                            ) : (
                                                row.amenityType
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {row.package === "Delux Package" || row.package === "Golden Package" ? (
                                                <span className="text-amber-400">{row.package}</span>
                                            ) : (
                                                row.package
                                            )}
                                        </TableCell>
                                        <TableCell>{row.roomNo}</TableCell>
                                        <TableCell>{row.smoking}</TableCell>
                                        <TableCell>{row.poolFacing}</TableCell>
                                        <TableCell>
                                            <div className="flex items-center justify-center">
                                                <Button size="sm" className="bg-brand-teal hover:bg-brand-teal/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditRoomOpen(true)}>
                                                    <Edit className="h-[14px] w-[14px]" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing 1 to 10 of 14 entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
                            <Button variant="default" size="sm" className="w-9 h-9 p-0 bg-primary text-white">1</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">2</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">3</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">...</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">8</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </>
    );

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Facility Management</h1>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 border-b border-border dark:border-slate-800">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
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
            {activeTab === "facility" && renderFacilitySetup()}
            {activeTab === "amenity" && renderAmenityType()}
            {activeTab === "roomAmenities" && renderRoomAmenities()}
            {activeTab === "packages" && renderPackages()}
            {activeTab === "roomSetup" && renderRoomSetup()}

            {/* Edit Facility Setup Modal */}
            <Dialog open={editFacilityOpen} onOpenChange={setEditFacilityOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Facility Setup</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditFacilityOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-6 px-10 max-h-[75vh] overflow-y-auto space-y-6">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Organization Name <span className="text-red-500">*</span></Label>
                            <input type="text" value="County Retreat" readOnly className="w-full bg-gray-100 border-0 border-b border-gray-300 text-gray-900 focus:ring-0 px-3 py-2 text-sm outline-none rounded-t-[2px]" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Hospitality Name <span className="text-red-500">*</span></Label>
                            <input type="text" value="CXPL" readOnly className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">No. of guest Rooms <span className="text-red-500">*</span></Label>
                            <input type="text" value="500" readOnly className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Edit Facility OutLayer <span className="text-red-500">*</span></Label>
                            <div className="bg-transparent border-0 border-b border-gray-300 pb-2 text-sm">
                                <div className="flex items-center text-gray-800 font-medium"><ChevronDown className="h-4 w-4 mr-1 text-gray-500" /> CXPL</div>
                                <div className="ml-5 mt-1">
                                    <div className="flex items-center text-gray-800 font-medium"><ChevronDown className="h-4 w-4 mr-1 text-gray-500" /> Building</div>
                                    <div className="ml-5 mt-1 flex items-center text-gray-800 opacity-80"><ChevronRight className="h-4 w-4 mr-1 text-gray-500" /> Floor</div>
                                </div>
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Facility Structure <span className="text-red-500">*</span></Label>
                            <div className="bg-transparent border-0 border-b border-gray-300 pb-2 text-sm max-h-[150px] overflow-y-auto custom-scrollbar">
                                <div className="flex items-center text-gray-800 font-medium"><ChevronDown className="h-4 w-4 mr-1 text-gray-500" /> CXPL</div>
                                <div className="ml-5 mt-1">
                                    <div className="flex items-center text-gray-800 font-medium"><ChevronDown className="h-4 w-4 mr-1 text-gray-500" /> Building A</div>
                                    <div className="ml-5 mt-1 space-y-1">
                                        <div className="flex items-center text-gray-800 before:content-['•'] before:mr-2 before:text-gray-400">Floor 1</div>
                                        <div className="flex items-center text-gray-800 before:content-['•'] before:mr-2 before:text-gray-400">Floor 2</div>
                                        <div className="flex items-center text-gray-800 before:content-['•'] before:mr-2 before:text-gray-400">Floor 3</div>
                                        <div className="flex items-center text-gray-800 before:content-['•'] before:mr-2 before:text-gray-400">Floor 4</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Hotel Image</Label>
                            <div className="border-0 border-b border-gray-300 pb-2">
                                <div className="flex items-center gap-2">
                                    <button className="bg-gray-100 text-gray-800 border border-gray-300 text-xs px-2 py-1 rounded-[2px] shadow-sm hover:bg-gray-200">Choose file</button>
                                    <span className="text-[13px] text-gray-500">No file chosen</span>
                                </div>
                                <div className="text-brand-teal text-xs mt-1 hover:underline cursor-pointer">Click here to preview image</div>
                            </div>
                        </div>
                        {[
                            { label: "City *", value: "Hyderabad" },
                            { label: "State *", value: "Hyderabad" },
                            { label: "PIN Code *", value: "500001" },
                            { label: "Email *", value: "sarumugam@inspirionics.net" },
                            { label: "Additional Email", value: "genesanIc@caleidoxenia.com, skodevallo@inspirionics.net" },
                            { label: "Google Map *", value: "https://goo.gl/maps/HnTVuzYriD2KuXjS27" },
                            { label: "Connect to Caleido *", value: "deyoncounty.db.connect" },
                        ].map((field, i) => (
                            <div key={i} className="grid grid-cols-[160px_1fr] items-center gap-4">
                                <Label className="text-sm font-medium text-gray-800">
                                    {field.label.replace(' *', '')} {field.label.includes('*') && <span className="text-red-500">*</span>}
                                </Label>
                                <input type="text" value={field.value} readOnly className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-center p-4 border-t border-gray-200">
                        <Button className="bg-transparent text-brand-teal border border-brand-teal hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFacilityOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Hotel Amenities Modal */}
            <Dialog open={editAmenityOpen} onOpenChange={setEditAmenityOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Hotel Amenities</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditAmenityOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-8">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Hotel Amenities <span className="text-red-500">*</span></Label>
                            <input type="text" value="Banquet Hall" readOnly className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-1">Amenities Icon</Label>
                            <div className="border-0 border-b border-gray-300 pb-2">
                                <div className="flex items-center gap-2">
                                    <button className="bg-gray-100 text-gray-800 border border-gray-300 text-xs px-2 py-1 rounded-[2px] shadow-sm hover:bg-gray-200">Choose file</button>
                                    <span className="text-[13px] text-gray-500">No file chosen</span>
                                </div>
                                <div className="text-brand-teal text-xs mt-1 hover:underline cursor-pointer">Click here to preview image</div>
                            </div>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditAmenityOpen(false)}>Reset</Button>
                        <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditAmenityOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Parent Packages Modal */}
            <Dialog open={editPackageOpen} onOpenChange={setEditPackageOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Parent Packages</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditPackageOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-6">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Package Name <span className="text-red-500">*</span></Label>
                            <input type="text" value="Beverage" readOnly className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-1 text-sm outline-none cursor-default" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Amenity Type <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-500 text-gray-700 focus:ring-0 px-0 pb-2 text-sm appearance-none outline-none">
                                    <option>Champagne Bar</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Features <span className="text-red-500">*</span></Label>
                            <div className="relative border border-gray-300 rounded-[4px] p-2 pr-8 flex flex-wrap gap-2 min-h-[120px] bg-transparent">
                                {[
                                    "Flat Screen TV", "Work Desk", "Letter Head with Pen",
                                    "High Speed Wireless Internet", "Electronic Safe / Locker",
                                    "Mini Bar / Mini Fridge", "Tea / Coffee Maker", "Ironing Board", "Iron",
                                    "Hair dryer", "Newspaper", "Mood lighting",
                                    "Caleido - Air Quality Control", "Caleido Smart Lock",
                                    "Non-Smoking Rooms", "Smoking Lounge", "Pet Friendly",
                                    "Doctor On Call", "Parking", "Ample Wall Outlets",
                                    "Complimentary Electronics Chargers", "Business Facilities",
                                    "Exercise Facilities and Accessories", "Complimentary Luggage storage",
                                    "Curated Experiences", "Fancy Bathrobes",
                                    "Kid-friendly Rooms and Products", "Premium Bedding",
                                    "Stain Remover Wipes", "Champagne Bar"
                                ].map((tag, i) => (
                                    <div key={i} className="bg-brand-teal text-white text-[12px] px-2 py-0.5 rounded-[2px] flex items-center gap-1 hover:bg-brand-teal/90 cursor-default shadow-sm border border-brand-teal">
                                        {tag} <X className="h-[10px] w-[10px] cursor-pointer hover:opacity-80 stroke-[3]" />
                                    </div>
                                ))}
                                <ChevronDown className="absolute right-2 top-2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">SubPackages</Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border border-gray-400 text-gray-700 focus:ring-0 px-3 py-1.5 text-sm appearance-none outline-none rounded-[4px]">
                                    <option>Select Sub Packages</option>
                                </select>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-1">Package Icon</Label>
                            <div className="border-0 border-b border-gray-300 pb-2">
                                <div className="flex items-center gap-2">
                                    <button className="bg-gray-100 text-gray-800 border border-gray-400 text-xs font-medium px-3 py-1 rounded-[2px] shadow-sm hover:bg-gray-200">Choose file</button>
                                    <span className="text-[13px] text-gray-500">No file chosen</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="flex justify-center p-4">
                        <Button className="bg-brand-teal hover:bg-brand-teal/90 text-white h-[34px] px-8 rounded-[3px] font-medium" onClick={() => setEditPackageOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Room Modal */}
            <Dialog open={editRoomOpen} onOpenChange={setEditRoomOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Room</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditRoomOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 max-h-[75vh] overflow-y-auto space-y-6">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Amenity Type <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-gray-100 border-0 border-b border-gray-300 text-gray-600 focus:ring-0 px-3 py-1.5 text-sm appearance-none outline-none rounded-t-[2px]">
                                    <option>Guest Room</option>
                                </select>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Package <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Delux Package</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Facility Structure <span className="text-red-500">*</span></Label>
                            <div className="bg-transparent border-0 border-b border-gray-300 pb-4 text-sm max-h-[200px] overflow-y-auto custom-scrollbar">
                                <div className="flex items-center text-gray-800 font-medium"><ChevronDown className="h-4 w-4 mr-1 text-gray-500" /> CXPL</div>
                                <div className="ml-5 mt-2">
                                    <div className="flex items-center text-gray-800 font-medium"><ChevronDown className="h-4 w-4 mr-1 text-gray-500" /> Building A</div>
                                    <div className="ml-5 mt-2 space-y-2">
                                        <div className="flex items-center text-red-500 font-medium before:content-['•'] before:mr-2 before:text-gray-400 border-b border-red-500 inline-block">Floor 1</div>
                                        <div className="flex items-center text-gray-800 font-medium before:content-['•'] before:mr-2 before:text-gray-400">Floor 2</div>
                                        <div className="flex items-center text-gray-800 font-medium before:content-['•'] before:mr-2 before:text-gray-400">Floor 3</div>
                                        <div className="flex items-center text-gray-800 font-medium before:content-['•'] before:mr-2 before:text-gray-400">Floor 4</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Room <span className="text-red-500">*</span></Label>
                            <input type="text" value="106" readOnly className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-1 text-sm outline-none cursor-default" />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4 mt-2">
                            <Label className="text-sm font-medium text-gray-800">Smoking <span className="text-red-500">*</span></Label>
                            <RadioGroup defaultValue="yes" className="flex flex-col gap-2">
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="yes" id="room-smoke-yes" className="text-gray-800 border-gray-400" />
                                    <Label htmlFor="room-smoke-yes" className="cursor-pointer text-gray-800 font-medium">Yes</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="no" id="room-smoke-no" className="border-brand-teal text-brand-teal" />
                                    <Label htmlFor="room-smoke-no" className="cursor-pointer text-brand-teal font-medium">No</Label>
                                </div>
                            </RadioGroup>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4 mt-2">
                            <Label className="text-sm font-medium text-gray-800">Front Facing <span className="text-red-500">*</span></Label>
                            <RadioGroup defaultValue="yes" className="flex flex-col gap-2">
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="yes" id="room-front-yes" className="text-gray-800 border-gray-400" />
                                    <Label htmlFor="room-front-yes" className="cursor-pointer text-gray-800 font-medium">Yes</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="no" id="room-front-no" className="border-brand-teal text-brand-teal" />
                                    <Label htmlFor="room-front-no" className="cursor-pointer text-brand-teal font-medium">No</Label>
                                </div>
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8 border-t border-transparent pt-4">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditRoomOpen(false)}>Reset</Button>
                        <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditRoomOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default FacilityManagement;




