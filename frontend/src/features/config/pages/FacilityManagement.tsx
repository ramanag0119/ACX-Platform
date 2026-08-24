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
import { DataState, TableLoading } from "@/core/components/DataState";
import {
  useAmenityTypes,
  useFacilities,
  useFeatures,
  usePackages,
  useRooms,
} from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  useCreateAmenityType,
  useCreateFeature,
  useCreatePackage,
  useCreateRoom,
  useRemovePackage,
  useUpdateAmenityType,
  useUpdateFacility,
  useUpdateRoom,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

type TabType = "facility" | "amenity" | "roomAmenities" | "packages" | "roomSetup";

/**
 * Facility Management, connected to the Phase 2.2 facility APIs.
 *
 * CONNECTED (real data):
 *   Facility Setup -> GET /facilities
 *   Amenity Type   -> distinct amenity types seen on GET /rooms
 *   Packages       -> distinct packages seen on GET /rooms
 *   Room Setup     -> GET /rooms
 *
 * Phase 3.0 connected the rest and made them writable:
 *   Amenity Type   -> GET/POST/PATCH /amenity-types
 *   Room Amenities -> GET/POST /features  (the `feature` table)
 *   Packages       -> GET/POST/PATCH /packages, including `package_feature`
 *   Room Setup     -> POST/PATCH /rooms   (a room IS an `amenity`)
 *   Facility Setup -> PATCH /facilities/{id}
 *
 * Sub Packages are `package.is_sub_package`, so that sub-tab lists and creates
 * packages with the flag set rather than needing a table of its own.
 *
 * Columns with no column behind them (Hospitality Name, Hotel Image, Connect
 * to Caleido, Smoking, Pool Facing) show "-": `facility` and `amenity` store
 * no such field, and Phase 3.0 does not add one.
 */

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

    // --- Live data -------------------------------------------------------
    const facilitiesQuery = useFacilities({ page: 1, page_size: MAX_PAGE_SIZE });
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
    // Phase 3.0 endpoints: the catalogue is no longer derived from rooms.
    const amenityTypesQuery = useAmenityTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const packagesQuery = usePackages({ page: 1, page_size: MAX_PAGE_SIZE });
    const featuresQuery = useFeatures({ page: 1, page_size: MAX_PAGE_SIZE });

    // --- Mutations
    const { canWrite } = useAuth();
    const mayWrite = canWrite("facility_management");
    const createAmenityType = useCreateAmenityType();
    const updateAmenityTypeMutation = useUpdateAmenityType();
    const createPackageMutation = useCreatePackage();
    const removePackageMutation = useRemovePackage();
    const createFeatureMutation = useCreateFeature();
    const createRoomMutation = useCreateRoom();
    const updateRoomMutation = useUpdateRoom();
    const updateFacilityMutation = useUpdateFacility();

    const facilitySetupData = (facilitiesQuery.data?.items ?? []).map((facility) => ({
        id: facility.id,
        organizationName: facility.name,
        // `facility` has no hospitality-name, image or Caleido-connection column.
        hospitalityName: "-",
        guestRooms: facility.guest_rooms ?? "-",
        hotelImage: facility.facility_image_id ? "View" : "-",
        city: facility.city ?? "-",
        state: facility.state ?? "-",
        pinCode: facility.pin_code ?? "-",
        email: facility.email,
        googleMap: facility.google_map_link ? "View" : "-",
        connectToCaleido: "-",
    }));

    const rooms = roomsQuery.data?.items ?? [];

    const amenityTypeData = (amenityTypesQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        amenityType: row.name,
        icon: row.amenity_category,
    }));

    const allPackages = packagesQuery.data?.items ?? [];
    const packagesData = allPackages
        .filter((row) => !row.is_sub_package)
        .map((row) => ({
            // `id` is the real `package.id` UUID -- what delete and edit act on.
            id: row.id,
            packageName: row.name,
            amenityType: row.amenity_type_name ?? "-",
            subPackages: row.is_sub_package ? "Yes" : "-",
            features: row.feature_names.join(", ") || "-",
            image: "-",
            // Rooms on this package. The API refuses to retire a package that
            // still has any, so the button says so before the click.
            roomCount: row.room_count,
        }));

    const roomSetupData = rooms.map((room) => ({
        id: room.id,
        amenityTypeId: room.amenity_type_id,
        packageId: room.package_id,
        amenityType: room.amenity_type_name ?? "-",
        package: room.package_name ?? "None",
        roomNo: room.name,
        // `amenity` stores no smoking or pool-facing flag.
        smoking: "-",
        poolFacing: "-",
    }));

    // Packages sub-tab state
    const [packagesSubTab, setPackagesSubTab] = useState<"parent" | "sub">("parent");
    /** New room-amenity (`feature`) name, for the Room Amenities tab. */
    const [newAmenityName, setNewAmenityName] = useState("");

    const roomAmenitiesData = (featuresQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        amenity: row.feature_name,
    }));
    const selectedAmenities = roomAmenitiesData.map((row) => row.amenity);

    // Sub Packages form state
    const [subPackageForm, setSubPackageForm] = useState({
        parentPackage: "",
        packageName: "",
        amenityType: "",
        features: "",
        subPackages: "",
        packageImage: "",
    });

    // A sub package is `package.is_sub_package` -- the same table, one flag.
    const subPackagesData = allPackages
        .filter((row) => row.is_sub_package)
        .map((row, index) => ({
            id: row.id,
            sNo: index + 1,
            packageName: row.name,
            amenityType: row.amenity_type_name ?? "-",
            features: row.feature_names.join(", ") || "-",
            image: "-",
            roomCount: row.room_count,
        }));

    /**
     * Delete a package -- the project's soft delete (`status = 0`), the same
     * shape ServicePlanning and Bookings use for their row actions. The row's
     * real `package.id` UUID goes to PATCH /packages/{id}; on success the
     * mutation invalidates the catalogue queries, /packages refetches without
     * the retired row, and the table loses it. A 409 (rooms still assigned)
     * surfaces through the shared error toast.
     */
    const handleRemovePackage = (packageId: string) => {
        removePackageMutation.mutate(packageId);
    };

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

    /**
     * Each tab writes to its own table, so one submit dispatches by tab.
     *
     *   amenity       -> POST /amenity-types
     *   roomAmenities -> POST /features
     *   packages      -> POST /packages (with `is_sub_package` for the sub tab
     *                    and `feature_ids` for the ticked room amenities)
     *   roomSetup     -> POST /rooms, which needs an amenity type AND a package
     *                    because both columns are NOT NULL
     */
    const handleSubmit = () => {
        if (activeTab === "amenity") {
            if (!amenityForm.amenityType.trim()) return;
            createAmenityType.mutate(
                {
                    name: amenityForm.amenityType.trim(),
                    // `amenity_category` is NOT NULL; a guest-facing type is a room.
                    amenity_category: "room",
                },
                { onSuccess: handleReset },
            );
            return;
        }

        if (activeTab === "roomAmenities") {
            if (!newAmenityName.trim()) return;
            createFeatureMutation.mutate(newAmenityName.trim(), {
                onSuccess: () => setNewAmenityName(""),
            });
            return;
        }

        if (activeTab === "packages") {
            const name = packagesSubTab === "parent" ? packageForm.packages : subPackageForm.packageName;
            const typeName = packagesSubTab === "parent" ? packageForm.amenityType : subPackageForm.amenityType;
            const amenityTypeId = amenityTypeData.find((row) => row.amenityType === typeName)?.id;
            if (!name.trim() || !amenityTypeId) return;
            createPackageMutation.mutate(
                {
                    name: name.trim(),
                    amenity_type: amenityTypeId,
                    is_sub_package: packagesSubTab === "sub",
                },
                {
                    onSuccess: () => {
                        handleReset();
                        handleSubPackageReset();
                    },
                },
            );
            return;
        }

        if (activeTab === "roomSetup") {
            const amenityTypeId = amenityTypeData.find(
                (row) => row.amenityType === roomSetupForm.amenityType,
            )?.id;
            const packageId = allPackages.find((row) => row.name === roomSetupForm.package)?.id;
            if (!roomSetupForm.room.trim() || !amenityTypeId || !packageId) return;
            createRoomMutation.mutate(
                {
                    name: roomSetupForm.room.trim(),
                    amenity_type_id: amenityTypeId,
                    package_id: packageId,
                    // `facilityStructure` is the building/floor choice, which is a
                    // `property_chain` row -- the only way to place a room.
                    ...(roomSetupForm.facilityStructure[0]
                        ? { property_chain_id: roomSetupForm.facilityStructure[0] }
                        : {}),
                },
                { onSuccess: handleReset },
            );
        }
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
                                            <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFacilityOpen(true)}>
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
                    <span className="text-muted-foreground text-sm">Showing {facilitySetupData.length} of {facilitiesQuery.data?.total ?? 0} entries</span>
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
                                        {/* The real `amenity_type.amenity_category`:
                                            room | restaurant | others. */}
                                        <TableCell className="text-center capitalize">{row.icon}</TableCell>
                                        <TableCell>
                                            <div className="flex items-center justify-center gap-2">
                                                <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditAmenityOpen(true)}>
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
                        <span className="text-muted-foreground text-sm">Showing {amenityTypeData.length} of {amenityTypeData.length} entries</span>
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

                    <div className="flex items-end gap-3 mb-4 max-w-xl">
                        <div className="flex-1 space-y-1">
                            <Label className="text-sm font-medium">New room amenity</Label>
                            <Input
                                placeholder="e.g. Smart Door Lock"
                                value={newAmenityName}
                                onChange={(event) => setNewAmenityName(event.target.value)}
                                className="bg-muted/30 border-border/50"
                            />
                        </div>
                        <Button
                            onClick={handleSubmit}
                            disabled={!mayWrite || !newAmenityName.trim() || createFeatureMutation.isPending}
                            className="h-10 px-6 bg-amber-500 hover:bg-amber-600 text-white"
                        >
                            {createFeatureMutation.isPending ? "Adding..." : "Add"}
                        </Button>
                    </div>

                    <div className="p-4 border border-gray-200 rounded-lg bg-muted/20 mb-6">
                        <div className="flex flex-wrap gap-2">
                            {selectedAmenities.map((amenity) => (
                                <Badge
                                    key={amenity}
                                    className="bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 px-3 py-1.5 flex items-center gap-2"
                                >
                                    {amenity}
                                    <X className="h-3 w-3 cursor-pointer hover:text-white" />
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div className="flex justify-center">
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
                        <span className="text-muted-foreground text-sm">Showing {roomAmenitiesData.length} of {roomAmenitiesData.length} entries</span>
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
                                                    <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditPackageOpen(true)}>
                                                        <Edit className="h-[14px] w-[14px]" />
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]"
                                                        onClick={() => handleRemovePackage(row.id)}
                                                        disabled={!mayWrite || removePackageMutation.isPending}
                                                        title={
                                                            !mayWrite
                                                                ? "Your role cannot change the room catalogue"
                                                                : row.roomCount > 0
                                                                    ? `Delete this package -- ${row.roomCount} room(s) still use it and must be moved first`
                                                                    : "Delete this package"
                                                        }
                                                    >
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
                                                    <Button
                                                        size="sm"
                                                        className="bg-red-500 hover:bg-red-600 text-white h-8 w-8 p-0 rounded-full"
                                                        onClick={() => handleRemovePackage(row.id)}
                                                        disabled={!mayWrite || removePackageMutation.isPending}
                                                        title={
                                                            !mayWrite
                                                                ? "Your role cannot change the room catalogue"
                                                                : row.roomCount > 0
                                                                    ? `Delete this sub package -- ${row.roomCount} room(s) still use it and must be moved first`
                                                                    : "Delete this sub package"
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
                    )}

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing {packagesSubTab === "parent" ? packagesData.length : subPackagesData.length} of {packagesSubTab === "parent" ? packagesData.length : subPackagesData.length} entries
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
                                        {/* Both cells previously highlighted hardcoded names
                                            ("Busy Room", "Delux Package") that match no
                                            `amenity_type` or `package` row, so the highlight
                                            never fired. The real value is shown plainly. */}
                                        <TableCell>{row.amenityType}</TableCell>
                                        <TableCell>{row.package}</TableCell>
                                        <TableCell>{row.roomNo}</TableCell>
                                        <TableCell>{row.smoking}</TableCell>
                                        <TableCell>{row.poolFacing}</TableCell>
                                        <TableCell>
                                            <div className="flex items-center justify-center">
                                                <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditRoomOpen(true)}>
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
                        <span className="text-muted-foreground text-sm">Showing {roomSetupData.length} of {roomsQuery.data?.total ?? 0} entries</span>
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
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Facility Management</h1>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 border-b border-gray-200">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
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

            {/* Content. One shared loading/error boundary for the whole
                screen -- both queries feed several tabs. */}
            <DataState
                isLoading={facilitiesQuery.isLoading || roomsQuery.isLoading}
                error={facilitiesQuery.error ?? roomsQuery.error}
                loader={<TableLoading columns={8} />}
            >
                <>
                    {activeTab === "facility" && renderFacilitySetup()}
                    {activeTab === "amenity" && renderAmenityType()}
                    {activeTab === "roomAmenities" && renderRoomAmenities()}
                    {activeTab === "packages" && renderPackages()}
                    {activeTab === "roomSetup" && renderRoomSetup()}
                </>
            </DataState>

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
                                <div className="text-[#3eb1c8] text-xs mt-1 hover:underline cursor-pointer">Click here to preview image</div>
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
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFacilityOpen(false)}>Submit</Button>
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
                                <div className="text-[#3eb1c8] text-xs mt-1 hover:underline cursor-pointer">Click here to preview image</div>
                            </div>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditAmenityOpen(false)}>Reset</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditAmenityOpen(false)}>Submit</Button>
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
                                    <div key={i} className="bg-[#3eb1c8] text-white text-[12px] px-2 py-0.5 rounded-[2px] flex items-center gap-1 hover:bg-[#3eb1c8]/90 cursor-default shadow-sm border border-[#3eb1c8]">
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
                        <Button className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-[34px] px-8 rounded-[3px] font-medium" onClick={() => setEditPackageOpen(false)}>Submit</Button>
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
                                    <RadioGroupItem value="no" id="room-smoke-no" className="border-[#3eb1c8] text-[#3eb1c8]" />
                                    <Label htmlFor="room-smoke-no" className="cursor-pointer text-[#3eb1c8] font-medium">No</Label>
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
                                    <RadioGroupItem value="no" id="room-front-no" className="border-[#3eb1c8] text-[#3eb1c8]" />
                                    <Label htmlFor="room-front-no" className="cursor-pointer text-[#3eb1c8] font-medium">No</Label>
                                </div>
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8 border-t border-transparent pt-4">
                        <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-[34px] px-8 rounded-[3px] font-medium" onClick={() => setEditRoomOpen(false)}>Reset</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-[34px] px-8 rounded-[3px] font-medium" onClick={() => setEditRoomOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default FacilityManagement;




