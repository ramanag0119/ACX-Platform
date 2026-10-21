import { useEffect, useState } from "react";
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Search, ChevronDown, Edit, Trash2, Upload, X, Check } from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import {
    useAmenityTypes,
    useBuildings,
    useCurrencies,
    useFacilities,
    useFeatures,
    useFloors,
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
    useUpdatePackage,
    useUpdateRoom,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE, type FacilityRead, type RoomRead } from "@/lib/api/types";
import type { AmenityTypeRead, PackageRead } from "@/lib/api/writes";
import { PageHeader } from "@/components/layout/PageHeader";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";
import { TablePagination } from "@/core/components/TablePagination";

type TabType = "facility" | "amenity" | "roomAmenities" | "packages" | "roomSetup";

/**
 * Facility Management, connected to the Phase 2.2 and Phase 3.0 facility APIs.
 *
 * CONNECTED (live database records):
 *   Facility Setup -> GET /facilities, PATCH /facilities/{id}
 *   Amenity Type   -> GET/POST/PATCH /amenity-types
 *   Room Amenities -> GET/POST /features (the `feature` table)
 *   Packages       -> GET/POST/PATCH /packages, including `package_feature`
 *   Room Setup     -> GET/POST/PATCH /rooms (a room IS an `amenity`)
 *   Buildings/Floors -> GET /buildings, GET /floors (property_chain hierarchy)
 */

const FacilityManagement = () => {
    const [activeTab, setActiveTab] = useState<TabType>("facility");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    useScrollToTop(currentPage);

    const pageSize = parseInt(entriesPerPage, 10) || 10;
    useEffect(() => {
        setCurrentPage(1);
    }, [activeTab, entriesPerPage, searchQuery]);

    const pageOf = <T,>(rows: T[]) => rows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

    // Modal visibility states
    const [editFacilityOpen, setEditFacilityOpen] = useState(false);
    const [editAmenityOpen, setEditAmenityOpen] = useState(false);
    const [editPackageOpen, setEditPackageOpen] = useState(false);
    const [editRoomOpen, setEditRoomOpen] = useState(false);

    // Active record being edited
    const [editingFacility, setEditingFacility] = useState<FacilityRead | null>(null);
    const [editingAmenityType, setEditingAmenityType] = useState<AmenityTypeRead | null>(null);
    const [editingPackage, setEditingPackage] = useState<PackageRead | null>(null);
    const [editingRoom, setEditingRoom] = useState<RoomRead | null>(null);

    // Edit modal form states
    const [editFacilityForm, setEditFacilityForm] = useState({
        name: "",
        guestRooms: "",
        city: "",
        state: "",
        pinCode: "",
        email: "",
        additionalEmail: "",
        googleMapLink: "",
        currencyId: null as number | null,
    });

    const [editAmenityForm, setEditAmenityForm] = useState({
        name: "",
        amenityCategory: "room" as "room" | "restaurant" | "others",
    });

    const [editPackageForm, setEditPackageForm] = useState({
        name: "",
        amenityTypeId: "",
        price: "",
        selectedFeatureIds: [] as string[],
        subPackageId: "",
        parentPackageId: "",
    });

    const [editRoomForm, setEditRoomForm] = useState({
        name: "",
        amenityTypeId: "",
        packageId: "",
        propertyChainId: "",
        smoking: "no",
        poolFacing: "no",
    });

    // Create form states
    const [amenityForm, setAmenityForm] = useState({
        amenityType: "",
        amenitiesIcon: null as File | null,
    });

    const [packageForm, setPackageForm] = useState({
        packages: "",
        roomType: "",
        price: "",
        selectedFeatureIds: [] as string[],
        subPackageId: "",
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

    // Sub Packages form state
    const [subPackageForm, setSubPackageForm] = useState({
        parentPackage: "",
        packageName: "",
        roomType: "",
        selectedFeatureIds: [] as string[],
        packageImage: "",
    });

    const [packagesSubTab, setPackagesSubTab] = useState<"parent" | "sub">("parent");
    const [newAmenityName, setNewAmenityName] = useState("");

    // --- Live Queries ---
    const facilitiesQuery = useFacilities({ page: 1, page_size: MAX_PAGE_SIZE });
    const buildingsQuery = useBuildings({ page: 1, page_size: MAX_PAGE_SIZE });
    const floorsQuery = useFloors({ page: 1, page_size: MAX_PAGE_SIZE });
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
    const amenityTypesQuery = useAmenityTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const packagesQuery = usePackages({ page: 1, page_size: MAX_PAGE_SIZE });
    const featuresQuery = useFeatures({ page: 1, page_size: MAX_PAGE_SIZE });
    const currenciesQuery = useCurrencies();
    const currencies = currenciesQuery.data ?? [];

    // --- Mutations ---
    const { canWrite } = useAuth();
    const mayWrite = canWrite("facility_management");

    const createAmenityType = useCreateAmenityType();
    const updateAmenityTypeMutation = useUpdateAmenityType();
    const createPackageMutation = useCreatePackage();
    const updatePackageMutation = useUpdatePackage();
    const removePackageMutation = useRemovePackage();
    const createFeatureMutation = useCreateFeature();
    const createRoomMutation = useCreateRoom();
    const updateRoomMutation = useUpdateRoom();
    const updateFacilityMutation = useUpdateFacility();

    // Data derivations
    // Data derivations & Authoritative Category/Status Filters
    const facilities = facilitiesQuery.data?.items ?? [];
    const buildings = buildingsQuery.data?.items ?? [];
    const floors = floorsQuery.data?.items ?? [];
    const rooms = roomsQuery.data?.items ?? [];
    const amenityTypes = amenityTypesQuery.data?.items ?? [];
    const allPackages = packagesQuery.data?.items ?? [];
    const featuresList = featuresQuery.data?.items ?? [];

    // Filtered authoritative lists for dropdowns:
    // Room Types: only amenity types with amenity_category == 'room' and active (status != 0)
    const roomTypes = amenityTypes.filter((at) => at.amenity_category === "room" && at.status !== 0);
    // Active Amenity Types (status != 0)
    const activeAmenityTypes = amenityTypes.filter((at) => at.status !== 0);
    // Active Parent Packages (not sub-packages and status != 0)
    const activeParentPackages = allPackages.filter((p) => !p.is_sub_package && p.status !== 0);
    // Active Sub-Packages (is_sub_package == true and status != 0)
    const activeSubPackages = allPackages.filter((p) => p.is_sub_package && p.status !== 0);
    // Active Room Amenities / Features (status != 0)
    const activeFeatures = featuresList.filter((f) => f.status !== 0);

    const facilitySetupData = facilities.map((facility) => ({
        id: facility.id,
        raw: facility,
        organizationName: facility.name,
        hospitalityName: facility.facility_uid || "-",
        guestRooms: facility.guest_rooms ?? "-",
        hotelImage: facility.facility_image_id ? "View" : "-",
        currency: facility.currency?.code ?? (facility.currency_id === 1 ? "INR" : (facility.currency_id ? String(facility.currency_id) : "-")),
        city: facility.city ?? "-",
        state: facility.state ?? "-",
        pinCode: facility.pin_code ?? "-",
        email: facility.email,
        googleMap: facility.google_map_link ? "View" : "-",
        connectToCaleido: "-",
    }));

    const amenityTypeData = activeAmenityTypes.map((row) => ({
        id: row.id,
        raw: row,
        amenityType: row.name,
        icon: row.amenity_category,
    }));

    const packagesData = activeParentPackages.map((row) => ({
        id: row.id,
        raw: row,
        packageName: row.name,
        amenityType: row.amenity_type_name ?? "-",
        price: row.price ? `${row.currency_symbol || "₹"} ${row.price}` : "-",
        subPackages: row.sub_package_names?.length ? row.sub_package_names.join(", ") : "-",
        features: row.feature_names?.join(", ") || "-",
        image: "-",
        roomCount: row.room_count,
    }));

    const subPackagesData = activeSubPackages.map((row, index) => ({
        id: row.id,
        raw: row,
        sNo: index + 1,
        packageName: row.name,
        amenityType: row.amenity_type_name ?? "-",
        price: row.price ? `${row.currency_symbol || "₹"} ${row.price}` : "-",
        parentPackages: row.parent_package_names?.length ? row.parent_package_names.join(", ") : "-",
        features: row.feature_names?.join(", ") || "-",
        image: "-",
        roomCount: row.room_count,
    }));

    const roomAmenitiesData = activeFeatures.map((row) => ({
        id: row.id,
        raw: row,
        amenity: row.feature_name,
    }));
    const selectedAmenities = roomAmenitiesData.map((row) => row.amenity);

    const roomSetupData = rooms.map((room) => ({
        id: room.id,
        raw: room,
        amenityTypeId: room.amenity_type_id,
        packageId: room.package_id,
        amenityType: room.amenity_type_name ?? "-",
        package: room.package_name ?? "-",
        roomNo: room.name,
        smoking: "-",
        poolFacing: "-",
    }));

    // Filtered rows based on search
    const filteredFacilityData = facilitySetupData.filter((row) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
            row.organizationName?.toLowerCase().includes(q) ||
            row.hospitalityName?.toLowerCase().includes(q) ||
            row.city?.toLowerCase().includes(q) ||
            row.state?.toLowerCase().includes(q) ||
            row.email?.toLowerCase().includes(q)
        );
    });

    const filteredAmenityTypeData = amenityTypeData.filter((row) => {
        if (!searchQuery.trim()) return true;
        return row.amenityType?.toLowerCase().includes(searchQuery.toLowerCase());
    });

    const filteredRoomAmenitiesData = roomAmenitiesData.filter((row) => {
        if (!searchQuery.trim()) return true;
        return row.amenity?.toLowerCase().includes(searchQuery.toLowerCase());
    });

    const filteredPackagesData = packagesData.filter((row) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
            row.packageName?.toLowerCase().includes(q) ||
            row.amenityType?.toLowerCase().includes(q)
        );
    });

    const filteredSubPackagesData = subPackagesData.filter((row) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
            row.packageName?.toLowerCase().includes(q) ||
            row.amenityType?.toLowerCase().includes(q)
        );
    });

    const filteredRoomSetupData = roomSetupData.filter((row) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
            row.roomNo?.toLowerCase().includes(q) ||
            row.amenityType?.toLowerCase().includes(q) ||
            row.package?.toLowerCase().includes(q)
        );
    });

    // Delete actions
    const handleRemovePackage = (packageId: string) => {
        removePackageMutation.mutate(packageId);
    };

    const handleRemoveAmenityType = (amenityTypeId: string) => {
        updateAmenityTypeMutation.mutate({ id: amenityTypeId, body: { status: 0 } });
    };

    // Reset handlers
    const handleReset = () => {
        if (activeTab === "amenity") {
            setAmenityForm({ amenityType: "", amenitiesIcon: null });
        } else if (activeTab === "packages") {
            setPackageForm({ packages: "", roomType: "", selectedFeatureIds: [], subPackageId: "", packageImage: "" });
        } else if (activeTab === "roomSetup") {
            setRoomSetupForm({ amenityType: "", package: "", facilityStructure: [], room: "", smoking: "no", poolFacing: "no" });
        }
    };

    const handleSubPackageReset = () => {
        setSubPackageForm({
            parentPackage: "",
            packageName: "",
            roomType: "",
            selectedFeatureIds: [],
            packageImage: "",
        });
    };

    // Create submits
    const handleSubmit = () => {
        if (activeTab === "amenity") {
            if (!amenityForm.amenityType.trim()) return;
            createAmenityType.mutate(
                {
                    name: amenityForm.amenityType.trim(),
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
            if (packagesSubTab === "parent") {
                if (!packageForm.packages.trim() || !packageForm.roomType) return;
                createPackageMutation.mutate(
                    {
                        name: packageForm.packages.trim(),
                        amenity_type: packageForm.roomType,
                        is_sub_package: false,
                        price: packageForm.price ? packageForm.price : undefined,
                        feature_ids: packageForm.selectedFeatureIds,
                        sub_package_ids: packageForm.subPackageId ? [packageForm.subPackageId] : [],
                    },
                    {
                        onSuccess: () => {
                            handleReset();
                        },
                    },
                );
            } else {
                if (!subPackageForm.packageName.trim() || !subPackageForm.roomType || !subPackageForm.parentPackage) return;
                createPackageMutation.mutate(
                    {
                        name: subPackageForm.packageName.trim(),
                        amenity_type: subPackageForm.roomType,
                        is_sub_package: true,
                        feature_ids: subPackageForm.selectedFeatureIds,
                        parent_package_id: subPackageForm.parentPackage,
                    },
                    {
                        onSuccess: () => {
                            handleSubPackageReset();
                        },
                    },
                );
            }
            return;
        }

        if (activeTab === "roomSetup") {
            if (!roomSetupForm.room.trim() || !roomSetupForm.amenityType || !roomSetupForm.package) return;
            createRoomMutation.mutate(
                {
                    name: roomSetupForm.room.trim(),
                    amenity_type_id: roomSetupForm.amenityType,
                    package_id: roomSetupForm.package,
                    ...(roomSetupForm.facilityStructure[0]
                        ? { property_chain_id: roomSetupForm.facilityStructure[0] }
                        : {}),
                },
                { onSuccess: handleReset },
            );
        }
    };

    // Open Edit Modals with authoritative database row data
    const handleOpenEditFacility = (facility: FacilityRead) => {
        setEditingFacility(facility);
        setEditFacilityForm({
            name: facility.name || "",
            guestRooms: facility.guest_rooms !== null && facility.guest_rooms !== undefined ? String(facility.guest_rooms) : "",
            city: facility.city || "",
            state: facility.state || "",
            pinCode: facility.pin_code || "",
            email: facility.email || "",
            additionalEmail: facility.additional_email || "",
            googleMapLink: facility.google_map_link || "",
            currencyId: facility.currency_id ?? null,
        });
        setEditFacilityOpen(true);
    };

    const handleSaveFacility = () => {
        if (!editingFacility) return;
        const guestRoomsNum = editFacilityForm.guestRooms.trim() ? parseInt(editFacilityForm.guestRooms.trim(), 10) : null;
        updateFacilityMutation.mutate(
            {
                id: editingFacility.id,
                body: {
                    name: editFacilityForm.name.trim() || undefined,
                    guest_rooms: guestRoomsNum !== null && !isNaN(guestRoomsNum) ? guestRoomsNum : null,
                    city: editFacilityForm.city.trim() || null,
                    state: editFacilityForm.state.trim() || null,
                    pin_code: editFacilityForm.pinCode.trim() || null,
                    email: editFacilityForm.email.trim() || undefined,
                    additional_email: editFacilityForm.additionalEmail.trim() || null,
                    google_map_link: editFacilityForm.googleMapLink.trim() || null,
                    currency_id: editFacilityForm.currencyId ? Number(editFacilityForm.currencyId) : null,
                },
            },
            {
                onSuccess: () => {
                    setEditFacilityOpen(false);
                },
            }
        );
    };

    const handleOpenEditAmenity = (item: AmenityTypeRead) => {
        setEditingAmenityType(item);
        setEditAmenityForm({
            name: item.name,
            amenityCategory: item.amenity_category,
        });
        setEditAmenityOpen(true);
    };

    const handleSaveAmenityType = () => {
        if (!editingAmenityType || !editAmenityForm.name.trim()) return;
        updateAmenityTypeMutation.mutate(
            {
                id: editingAmenityType.id,
                body: {
                    name: editAmenityForm.name.trim(),
                    amenity_category: editAmenityForm.amenityCategory,
                },
            },
            {
                onSuccess: () => {
                    setEditAmenityOpen(false);
                },
            }
        );
    };

    const handleOpenEditPackage = (pkg: PackageRead) => {
        setEditingPackage(pkg);
        setEditPackageForm({
            name: pkg.name,
            amenityTypeId: pkg.amenity_type,
            price: pkg.price !== null && pkg.price !== undefined ? String(pkg.price) : "",
            selectedFeatureIds: [...(pkg.feature_ids || [])],
            subPackageId: pkg.sub_package_ids?.[0] || "",
            parentPackageId: pkg.parent_package_ids?.[0] || "",
        });
        setEditPackageOpen(true);
    };

    const handleSavePackage = () => {
        if (!editingPackage || !editPackageForm.name.trim()) return;
        const isSub = editingPackage.is_sub_package;
        updatePackageMutation.mutate(
            {
                id: editingPackage.id,
                body: {
                    name: editPackageForm.name.trim(),
                    amenity_type: editPackageForm.amenityTypeId || undefined,
                    price: editPackageForm.price ? editPackageForm.price : undefined,
                    feature_ids: editPackageForm.selectedFeatureIds,
                    sub_package_ids: !isSub && editPackageForm.subPackageId ? [editPackageForm.subPackageId] : [],
                    parent_package_id: isSub && editPackageForm.parentPackageId ? editPackageForm.parentPackageId : undefined,
                },
            },
            {
                onSuccess: () => {
                    setEditPackageOpen(false);
                },
            }
        );
    };

    const handleOpenEditRoom = (room: RoomRead) => {
        setEditingRoom(room);
        setEditRoomForm({
            name: room.name,
            amenityTypeId: room.amenity_type_id,
            packageId: room.package_id,
            propertyChainId: room.property_chain_id || "",
            smoking: "no",
            poolFacing: "no",
        });
        setEditRoomOpen(true);
    };

    const handleSaveRoom = () => {
        if (!editingRoom || !editRoomForm.name.trim() || !editRoomForm.amenityTypeId || !editRoomForm.packageId) return;
        updateRoomMutation.mutate(
            {
                id: editingRoom.id,
                body: {
                    name: editRoomForm.name.trim(),
                    amenity_type_id: editRoomForm.amenityTypeId,
                    package_id: editRoomForm.packageId,
                    ...(editRoomForm.propertyChainId ? { property_chain_id: editRoomForm.propertyChainId } : {}),
                },
            },
            {
                onSuccess: () => {
                    setEditRoomOpen(false);
                },
            }
        );
    };

    const tabs = [
        { id: "facility" as TabType, label: "Facility Setup" },
        { id: "amenity" as TabType, label: "Amenity Type" },
        { id: "roomAmenities" as TabType, label: "Room Amenities" },
        { id: "packages" as TabType, label: "Packages" },
        { id: "roomSetup" as TabType, label: "Room Setup" },
    ];

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
                                <TableHead className="text-gray-600 font-medium">Base Currency</TableHead>
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
                            {filteredFacilityData.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={12} className="text-center py-6 text-muted-foreground">
                                        No facilities found
                                    </TableCell>
                                </TableRow>
                            ) : (
                                pageOf(filteredFacilityData).map((row) => (
                                    <TableRow
                                        key={row.id}
                                        className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                                    >
                                        <TableCell>{row.organizationName}</TableCell>
                                        <TableCell>{row.hospitalityName}</TableCell>
                                        <TableCell>{row.guestRooms}</TableCell>
                                        <TableCell>
                                            <span className="text-cyan-400 cursor-pointer hover:underline">{row.hotelImage}</span>
                                        </TableCell>
                                        <TableCell className="font-semibold text-brand">{row.currency}</TableCell>
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
                                                <Button
                                                    size="sm"
                                                    className="h-7 w-7 p-0 rounded-[3px]"
                                                    onClick={() => handleOpenEditFacility(row.raw)}
                                                    disabled={!mayWrite}
                                                    title={!mayWrite ? "You do not have write permissions" : "Edit Facility"}
                                                >
                                                    <Edit className="h-[14px] w-[14px]" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>

                <TablePagination
                    currentPage={currentPage}
                    onPageChange={setCurrentPage}
                    totalEntries={filteredFacilityData.length}
                    pageSize={pageSize}
                    className="mt-6"
                />
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
                        <Button
                            onClick={handleSubmit}
                            disabled={!mayWrite || !amenityForm.amenityType.trim() || createAmenityType.isPending}
                            className="h-11 px-8 min-w-[120px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                        >
                            {createAmenityType.isPending ? "Submitting..." : "Submit"}
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
                                {filteredAmenityTypeData.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center py-6 text-muted-foreground">
                                            No amenity types found
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    pageOf(filteredAmenityTypeData).map((row) => (
                                        <TableRow
                                            key={row.id}
                                            className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                                        >
                                            <TableCell className="text-center">{row.amenityType}</TableCell>
                                            <TableCell className="text-center capitalize">{row.icon}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center justify-center gap-2">
                                                    <Button
                                                        size="sm"
                                                        className="h-7 w-7 p-0 rounded-[3px]"
                                                        onClick={() => handleOpenEditAmenity(row.raw)}
                                                        disabled={!mayWrite}
                                                        title="Edit Amenity Type"
                                                    >
                                                        <Edit className="h-[14px] w-[14px]" />
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]"
                                                        onClick={() => handleRemoveAmenityType(row.id)}
                                                        disabled={!mayWrite || updateAmenityTypeMutation.isPending}
                                                        title="Delete Amenity Type"
                                                    >
                                                        <Trash2 className="h-[14px] w-[14px]" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <TablePagination
                        currentPage={currentPage}
                        onPageChange={setCurrentPage}
                        totalEntries={filteredAmenityTypeData.length}
                        pageSize={pageSize}
                        className="mt-6"
                    />
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
                            className="h-10 px-6 bg-brand hover:bg-brand-hover text-white"
                        >
                            {createFeatureMutation.isPending ? "Adding..." : "Add"}
                        </Button>
                    </div>

                    <div className="p-4 border border-gray-200 rounded-lg bg-muted/20 mb-6">
                        <div className="flex flex-wrap gap-2.5">
                            {selectedAmenities.length === 0 ? (
                                <span className="text-xs text-muted-foreground">No features defined</span>
                            ) : (
                                selectedAmenities.map((amenity) => (
                                    <Badge
                                        key={amenity}
                                        className="bg-brand/15 text-brand dark:bg-brand/25 dark:text-[#c7d2fe] border border-brand/35 px-3.5 py-1.5 rounded-full flex items-center gap-2 font-medium text-xs shadow-sm hover:bg-brand/25 transition-all"
                                    >
                                        {amenity}
                                    </Badge>
                                ))
                            )}
                        </div>
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
                                {filteredRoomAmenitiesData.length === 0 ? (
                                    <TableRow>
                                        <TableCell className="text-center py-6 text-muted-foreground">
                                            No room amenities found
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    pageOf(filteredRoomAmenitiesData).map((row) => (
                                        <TableRow
                                            key={row.id}
                                            className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                                        >
                                            <TableCell className="text-center">{row.amenity}</TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <TablePagination
                        currentPage={currentPage}
                        onPageChange={setCurrentPage}
                        totalEntries={filteredRoomAmenitiesData.length}
                        pageSize={pageSize}
                        className="mt-6"
                    />
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
                                    <Label className="text-sm font-medium">
                                        Package Name <span className="text-red-500">*</span>
                                    </Label>
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
                                            {roomTypes.map((rt) => (
                                                <SelectItem key={rt.id} value={rt.id}>
                                                    {rt.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Rate / Price</Label>
                                    <Input
                                        type="number"
                                        step="0.01"
                                        placeholder="e.g. 2500.00"
                                        value={packageForm.price}
                                        onChange={(e) => setPackageForm({ ...packageForm, price: e.target.value })}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Sub Packages</Label>
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={packageForm.subPackageId}
                                            onValueChange={(v) => setPackageForm({ ...packageForm, subPackageId: v === "none" ? "" : v })}
                                        >
                                            <SelectTrigger className="h-10 bg-muted/30 border-border/50 flex-1">
                                                <SelectValue placeholder="Select Sub Package (Optional)" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-popover">
                                                <SelectItem value="none">None</SelectItem>
                                                {activeSubPackages.map((sp) => (
                                                    <SelectItem key={sp.id} value={sp.id}>
                                                        {sp.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
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

                            <div className="space-y-2 md:col-span-2">
                                <Label className="text-sm font-medium">Features / Room Amenities</Label>
                                <div className="flex flex-wrap gap-2 p-3 bg-muted/20 border border-border/40 rounded-xl min-h-[50px] items-center">
                                    {activeFeatures.length === 0 ? (
                                        <span className="text-xs text-muted-foreground">No room amenities configured.</span>
                                    ) : (
                                        activeFeatures.map((f) => {
                                            const selected = packageForm.selectedFeatureIds.includes(f.id);
                                            return (
                                                <button
                                                    key={f.id}
                                                    type="button"
                                                    onClick={() => {
                                                        const next = selected
                                                            ? packageForm.selectedFeatureIds.filter((id) => id !== f.id)
                                                            : [...packageForm.selectedFeatureIds, f.id];
                                                        setPackageForm({ ...packageForm, selectedFeatureIds: next });
                                                    }}
                                                    className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                                                        selected
                                                            ? "bg-brand text-white border-brand shadow-sm"
                                                            : "bg-white text-muted-foreground border-border/60 hover:border-brand/50"
                                                    }`}
                                                >
                                                    {f.feature_name}
                                                </button>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        // Sub Packages Form
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">
                                        Parent Package <span className="text-red-500">*</span>
                                    </Label>
                                    <Select
                                        value={subPackageForm.parentPackage}
                                        onValueChange={(v) => setSubPackageForm({ ...subPackageForm, parentPackage: v })}
                                    >
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Parent Package" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-popover">
                                            {activeParentPackages.map((p) => (
                                                <SelectItem key={p.id} value={p.id}>
                                                    {p.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">
                                        Sub-Package Name <span className="text-red-500">*</span>
                                    </Label>
                                    <Input
                                        placeholder="Enter Sub-Package Name"
                                        value={subPackageForm.packageName}
                                        onChange={(e) => setSubPackageForm({ ...subPackageForm, packageName: e.target.value })}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-primary text-sm font-medium">
                                        Room Type <span className="text-red-500">*</span>
                                    </Label>
                                    <Select
                                        value={subPackageForm.roomType}
                                        onValueChange={(v) => setSubPackageForm({ ...subPackageForm, roomType: v })}
                                    >
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Room Type" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-popover">
                                            {roomTypes.map((rt) => (
                                                <SelectItem key={rt.id} value={rt.id}>
                                                    {rt.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="space-y-4">
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

                            <div className="space-y-2 md:col-span-2">
                                <Label className="text-sm font-medium">Features / Room Amenities</Label>
                                <div className="flex flex-wrap gap-2 p-3 bg-muted/20 border border-border/40 rounded-xl min-h-[50px] items-center">
                                    {activeFeatures.length === 0 ? (
                                        <span className="text-xs text-muted-foreground">No room amenities configured.</span>
                                    ) : (
                                        activeFeatures.map((f) => {
                                            const selected = subPackageForm.selectedFeatureIds.includes(f.id);
                                            return (
                                                <button
                                                    key={f.id}
                                                    type="button"
                                                    onClick={() => {
                                                        const next = selected
                                                            ? subPackageForm.selectedFeatureIds.filter((id) => id !== f.id)
                                                            : [...subPackageForm.selectedFeatureIds, f.id];
                                                        setSubPackageForm({ ...subPackageForm, selectedFeatureIds: next });
                                                    }}
                                                    className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                                                        selected
                                                            ? "bg-brand text-white border-brand shadow-sm"
                                                            : "bg-white text-muted-foreground border-border/60 hover:border-brand/50"
                                                    }`}
                                                >
                                                    {f.feature_name}
                                                </button>
                                            );
                                        })
                                    )}
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
                        <Button
                            onClick={handleSubmit}
                            disabled={!mayWrite || createPackageMutation.isPending}
                            className="h-10 px-8 bg-brand hover:bg-brand-hover text-white"
                        >
                            {createPackageMutation.isPending ? "Submitting..." : "Submit"}
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
                                        <TableHead className="text-gray-600 font-medium">Rate / Price</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Sub Packages</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Features</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Image</TableHead>
                                        <TableHead className="text-red-400 font-semibold text-center">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredPackagesData.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={7} className="text-center py-6 text-muted-foreground">
                                                No parent packages found
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        pageOf(filteredPackagesData).map((row) => (
                                            <TableRow
                                                key={row.id}
                                                className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                                            >
                                                <TableCell className="text-primary">{row.packageName}</TableCell>
                                                <TableCell className="text-primary">{row.amenityType}</TableCell>
                                                <TableCell className="font-semibold text-emerald-600">{row.price}</TableCell>
                                                <TableCell>
                                                    {row.subPackages === "-" ? "-" : (
                                                        <span className="text-primary">{row.subPackages}</span>
                                                    )}
                                                </TableCell>
                                                <TableCell className="max-w-[300px] truncate">{row.features}</TableCell>
                                                <TableCell>{row.image}</TableCell>
                                                <TableCell>
                                                    <div className="flex items-center justify-center gap-2">
                                                        <Button
                                                            size="sm"
                                                            className="h-7 w-7 p-0 rounded-[3px]"
                                                            onClick={() => handleOpenEditPackage(row.raw)}
                                                            disabled={!mayWrite}
                                                            title="Edit Package"
                                                        >
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
                                        ))
                                    )}
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
                                        <TableHead className="text-gray-600 font-medium">Rate / Price</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Parent Package</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Features</TableHead>
                                        <TableHead className="text-gray-600 font-medium">Image</TableHead>
                                        <TableHead className="text-red-400 font-semibold text-center">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredSubPackagesData.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={8} className="text-center py-6 text-muted-foreground">
                                                No sub-packages found
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        pageOf(filteredSubPackagesData).map((row) => (
                                            <TableRow
                                                key={row.id}
                                                className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                                            >
                                                <TableCell>{row.sNo}</TableCell>
                                                <TableCell className="text-primary">{row.packageName}</TableCell>
                                                <TableCell className="text-primary">{row.amenityType}</TableCell>
                                                <TableCell className="font-semibold text-emerald-600">{row.price}</TableCell>
                                                <TableCell className="text-primary">{row.parentPackages}</TableCell>
                                                <TableCell className="max-w-[300px] truncate">{row.features}</TableCell>
                                                <TableCell>{row.image}</TableCell>
                                                <TableCell>
                                                    <div className="flex items-center justify-center gap-2">
                                                        <Button
                                                            size="sm"
                                                            className="h-8 w-8 p-0 rounded-full"
                                                            onClick={() => handleOpenEditPackage(row.raw)}
                                                            disabled={!mayWrite}
                                                            title="Edit Sub Package"
                                                        >
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
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    )}

                    <TablePagination
                        currentPage={currentPage}
                        onPageChange={setCurrentPage}
                        totalEntries={packagesSubTab === "parent" ? filteredPackagesData.length : filteredSubPackagesData.length}
                        pageSize={pageSize}
                        className="mt-6"
                    />
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
                                <Label className="text-sm font-medium">Room Type</Label>
                                <Select
                                    value={roomSetupForm.amenityType}
                                    onValueChange={(v) =>
                                        setRoomSetupForm({
                                            ...roomSetupForm,
                                            amenityType: v,
                                            package: "",
                                        })
                                    }
                                >
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Room Type" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {roomTypes.map((rt) => (
                                            <SelectItem key={rt.id} value={rt.id}>
                                                {rt.name}
                                            </SelectItem>
                                        ))}
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
                                        <SelectValue placeholder="Select Room Package" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {(roomSetupForm.amenityType
                                            ? activeParentPackages.filter(
                                                  (p) => !p.amenity_type || p.amenity_type === roomSetupForm.amenityType
                                              )
                                            : activeParentPackages
                                        ).map((p) => (
                                            <SelectItem key={p.id} value={p.id}>
                                                {p.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Facility Structure (Select Floor)</Label>
                                <div className="p-2 border border-gray-200 rounded-lg bg-white max-h-64 overflow-y-auto">
                                    <div className="space-y-0">
                                        {facilities.map((fac) => (
                                            <Collapsible key={fac.id} defaultOpen>
                                                <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                                    <span className="text-sm font-medium">{fac.name}</span>
                                                </CollapsibleTrigger>
                                                <CollapsibleContent className="ml-4 space-y-1">
                                                    {buildings
                                                        .filter((b) => !b.facility_id || b.facility_id === fac.id)
                                                        .map((b) => (
                                                            <Collapsible key={b.id} defaultOpen>
                                                                <CollapsibleTrigger className="flex items-center gap-1 w-full py-1 px-1 hover:bg-muted/20 rounded text-left">
                                                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                                                    <span className="text-sm">{b.name}</span>
                                                                </CollapsibleTrigger>
                                                                <CollapsibleContent className="ml-4 pl-2 border-l border-border/30 space-y-1">
                                                                    {floors
                                                                        .filter((f) => f.building_id === b.id)
                                                                        .map((f) => {
                                                                            const isSelected = roomSetupForm.facilityStructure[0] === f.property_chain_id;
                                                                            return (
                                                                                <div
                                                                                    key={f.id}
                                                                                    onClick={() =>
                                                                                        setRoomSetupForm({
                                                                                            ...roomSetupForm,
                                                                                            facilityStructure: [f.property_chain_id],
                                                                                        })
                                                                                    }
                                                                                    className={`py-1 px-2 text-sm rounded cursor-pointer flex items-center justify-between transition-colors ${
                                                                                        isSelected
                                                                                            ? "bg-brand/10 text-brand font-semibold"
                                                                                            : "hover:bg-muted/20 text-gray-700"
                                                                                    }`}
                                                                                >
                                                                                    <span>{f.name}</span>
                                                                                    {isSelected && <Check className="h-3.5 w-3.5 text-brand" />}
                                                                                </div>
                                                                            );
                                                                        })}
                                                                </CollapsibleContent>
                                                            </Collapsible>
                                                        ))}
                                                </CollapsibleContent>
                                            </Collapsible>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Room</Label>
                                <Input
                                    placeholder="e.g. 101, 102"
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
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pt-6 mt-6 border-t border-border/30">
                        <Button onClick={handleReset} variant="outline" className="h-10 px-8 bg-cyan-600 text-white border-0 hover:bg-cyan-700">
                            Reset
                        </Button>
                        <Button
                            onClick={handleSubmit}
                            disabled={!mayWrite || createRoomMutation.isPending}
                            className="h-10 px-8 bg-brand hover:bg-brand-hover text-white"
                        >
                            {createRoomMutation.isPending ? "Submitting..." : "Submit"}
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
                                {filteredRoomSetupData.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                                            No rooms found
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    pageOf(filteredRoomSetupData).map((row) => (
                                        <TableRow
                                            key={row.id}
                                            className="hover:bg-[var(--hms-table-row-hover-bg)] transition-colors"
                                        >
                                            <TableCell>{row.amenityType}</TableCell>
                                            <TableCell>{row.package}</TableCell>
                                            <TableCell>{row.roomNo}</TableCell>
                                            <TableCell>{row.smoking}</TableCell>
                                            <TableCell>{row.poolFacing}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center justify-center">
                                                    <Button
                                                        size="sm"
                                                        className="h-7 w-7 p-0 rounded-[3px]"
                                                        onClick={() => handleOpenEditRoom(row.raw)}
                                                        disabled={!mayWrite}
                                                        title="Edit Room"
                                                    >
                                                        <Edit className="h-[14px] w-[14px]" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <TablePagination
                        currentPage={currentPage}
                        onPageChange={setCurrentPage}
                        totalEntries={filteredRoomSetupData.length}
                        pageSize={pageSize}
                        className="mt-6"
                    />
                </CardContent>
            </Card>
        </>
    );

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            <PageHeader title="Facility Management" />

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

            {/* Content with live data loading / error boundary */}
            <DataState
                isLoading={
                    facilitiesQuery.isLoading ||
                    roomsQuery.isLoading ||
                    amenityTypesQuery.isLoading ||
                    packagesQuery.isLoading ||
                    featuresQuery.isLoading ||
                    buildingsQuery.isLoading ||
                    floorsQuery.isLoading
                }
                error={
                    facilitiesQuery.error ??
                    roomsQuery.error ??
                    amenityTypesQuery.error ??
                    packagesQuery.error ??
                    featuresQuery.error
                }
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
                            <input
                                type="text"
                                value={editFacilityForm.name}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, name: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Hospitality Code</Label>
                            <input
                                type="text"
                                value={editingFacility?.facility_uid || "-"}
                                readOnly
                                className="w-full bg-gray-50 border-0 border-b border-gray-300 text-gray-600 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">No. of guest Rooms <span className="text-red-500">*</span></Label>
                            <input
                                type="number"
                                min={0}
                                value={editFacilityForm.guestRooms}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, guestRooms: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Facility Structure</Label>
                            <div className="bg-transparent border border-gray-200 rounded p-3 text-sm max-h-[160px] overflow-y-auto custom-scrollbar w-full">
                                {editingFacility && (
                                    <div>
                                        <div className="flex items-center text-gray-800 font-medium">
                                            <ChevronDown className="h-4 w-4 mr-1 text-gray-500" />
                                            {editingFacility.name} ({editingFacility.facility_uid})
                                        </div>
                                        <div className="ml-5 mt-1 space-y-1">
                                            {buildings
                                                .filter((b) => !b.facility_id || b.facility_id === editingFacility.id)
                                                .map((b) => (
                                                    <div key={b.id}>
                                                        <div className="flex items-center text-gray-700 font-medium">
                                                            <ChevronDown className="h-4 w-4 mr-1 text-gray-500" />
                                                            {b.name}
                                                        </div>
                                                        <div className="ml-5 mt-1 space-y-0.5">
                                                            {floors
                                                                .filter((f) => f.building_id === b.id)
                                                                .map((f) => (
                                                                    <div key={f.id} className="text-gray-600 text-xs flex items-center before:content-['•'] before:mr-2 before:text-gray-400">
                                                                        {f.name} ({f.room_count} rooms)
                                                                    </div>
                                                                ))}
                                                        </div>
                                                    </div>
                                                ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">City <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editFacilityForm.city}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, city: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">State <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editFacilityForm.state}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, state: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">PIN Code <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editFacilityForm.pinCode}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, pinCode: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Base Currency</Label>
                            <Select
                                value={editFacilityForm.currencyId ? String(editFacilityForm.currencyId) : "1"}
                                onValueChange={(v) => setEditFacilityForm({ ...editFacilityForm, currencyId: Number(v) })}
                            >
                                <SelectTrigger className="h-9 bg-white border border-gray-300 rounded-[2px] text-sm">
                                    <SelectValue placeholder="Select Currency" />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    {currencies.map((c) => (
                                        <SelectItem key={c.id} value={String(c.id)}>
                                            {c.code} ({c.symbol}) - {c.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Email <span className="text-red-500">*</span></Label>
                            <input
                                type="email"
                                value={editFacilityForm.email}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, email: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Additional Email</Label>
                            <input
                                type="text"
                                value={editFacilityForm.additionalEmail}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, additionalEmail: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Google Map Link</Label>
                            <input
                                type="text"
                                value={editFacilityForm.googleMapLink}
                                onChange={(e) => setEditFacilityForm({ ...editFacilityForm, googleMapLink: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                    </div>
                    <div className="flex justify-center p-4 border-t border-gray-200">
                        <Button
                            className="bg-transparent text-brand-teal border border-brand-teal hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal"
                            onClick={handleSaveFacility}
                            disabled={!mayWrite || updateFacilityMutation.isPending}
                        >
                            {updateFacilityMutation.isPending ? "Saving..." : "Submit"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Hotel Amenities Modal */}
            <Dialog open={editAmenityOpen} onOpenChange={setEditAmenityOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Amenity Type</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditAmenityOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-6">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Amenity Name <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editAmenityForm.name}
                                onChange={(e) => setEditAmenityForm({ ...editAmenityForm, name: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Category <span className="text-red-500">*</span></Label>
                            <Select
                                value={editAmenityForm.amenityCategory}
                                onValueChange={(v: "room" | "restaurant" | "others") =>
                                    setEditAmenityForm({ ...editAmenityForm, amenityCategory: v })
                                }
                            >
                                <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    <SelectItem value="room">Room</SelectItem>
                                    <SelectItem value="restaurant">Restaurant</SelectItem>
                                    <SelectItem value="others">Others</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8">
                        <Button
                            variant="outline"
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                            onClick={() => setEditAmenityOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                            onClick={handleSaveAmenityType}
                            disabled={!mayWrite || updateAmenityTypeMutation.isPending}
                        >
                            {updateAmenityTypeMutation.isPending ? "Saving..." : "Submit"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Packages Modal */}
            <Dialog open={editPackageOpen} onOpenChange={setEditPackageOpen}>
                <DialogContent className="max-w-[700px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200 shadow-sm">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">
                            {editingPackage?.is_sub_package ? "Edit Sub Package" : "Edit Package"}
                        </h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditPackageOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-6">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Package Name <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editPackageForm.name}
                                onChange={(e) => setEditPackageForm({ ...editPackageForm, name: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Room Type <span className="text-red-500">*</span></Label>
                            <Select
                                value={editPackageForm.amenityTypeId}
                                onValueChange={(v) => setEditPackageForm({ ...editPackageForm, amenityTypeId: v })}
                            >
                                <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                    <SelectValue placeholder="Select Room Type" />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    {roomTypes.map((rt) => (
                                        <SelectItem key={rt.id} value={rt.id}>
                                            {rt.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Rate / Price</Label>
                            <input
                                type="number"
                                step="0.01"
                                placeholder="e.g. 2500.00"
                                value={editPackageForm.price}
                                onChange={(e) => setEditPackageForm({ ...editPackageForm, price: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        {editingPackage?.is_sub_package ? (
                            <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                                <Label className="text-sm font-medium text-gray-800">Parent Package</Label>
                                <Select
                                    value={editPackageForm.parentPackageId}
                                    onValueChange={(v) => setEditPackageForm({ ...editPackageForm, parentPackageId: v })}
                                >
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Parent Package" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {activeParentPackages
                                            .filter((p) => p.id !== editingPackage.id)
                                            .map((p) => (
                                                <SelectItem key={p.id} value={p.id}>
                                                    {p.name}
                                                </SelectItem>
                                            ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        ) : (
                            <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                                <Label className="text-sm font-medium text-gray-800">Sub Package</Label>
                                <Select
                                    value={editPackageForm.subPackageId}
                                    onValueChange={(v) => setEditPackageForm({ ...editPackageForm, subPackageId: v === "none" ? "" : v })}
                                >
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Sub Package" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        <SelectItem value="none">None</SelectItem>
                                        {activeSubPackages
                                            .filter((sp) => sp.id !== editingPackage?.id)
                                            .map((sp) => (
                                                <SelectItem key={sp.id} value={sp.id}>
                                                    {sp.name}
                                                </SelectItem>
                                            ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Features</Label>
                            <div className="border border-gray-300 rounded-[4px] p-2 flex flex-wrap gap-2 min-h-[60px] bg-transparent">
                                {activeFeatures.length === 0 ? (
                                    <span className="text-xs text-gray-400 p-1">No features configured</span>
                                ) : (
                                    activeFeatures.map((f) => {
                                        const isChecked = editPackageForm.selectedFeatureIds.includes(f.id);
                                        return (
                                            <button
                                                key={f.id}
                                                type="button"
                                                onClick={() => {
                                                    const next = isChecked
                                                        ? editPackageForm.selectedFeatureIds.filter((id) => id !== f.id)
                                                        : [...editPackageForm.selectedFeatureIds, f.id];
                                                    setEditPackageForm({ ...editPackageForm, selectedFeatureIds: next });
                                                }}
                                                className={`text-xs px-2.5 py-1 rounded-[2px] flex items-center gap-1 transition-all ${
                                                    isChecked
                                                        ? "bg-brand text-white shadow-sm font-medium"
                                                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                                                }`}
                                            >
                                                {f.feature_name}
                                            </button>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex justify-center p-4 border-t border-gray-200">
                        <Button
                            className="bg-brand-teal hover:bg-brand-teal/90 text-white h-[34px] px-8 rounded-[3px] font-medium"
                            onClick={handleSavePackage}
                            disabled={!mayWrite || updatePackageMutation.isPending}
                        >
                            {updatePackageMutation.isPending ? "Saving..." : "Submit"}
                        </Button>
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
                            <Label className="text-sm font-medium text-gray-800">Room Type <span className="text-red-500">*</span></Label>
                            <Select
                                value={editRoomForm.amenityTypeId}
                                onValueChange={(v) => setEditRoomForm({ ...editRoomForm, amenityTypeId: v })}
                            >
                                <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                    <SelectValue placeholder="Select Room Type" />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    {roomTypes.map((rt) => (
                                        <SelectItem key={rt.id} value={rt.id}>
                                            {rt.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Package <span className="text-red-500">*</span></Label>
                            <Select
                                value={editRoomForm.packageId}
                                onValueChange={(v) => setEditRoomForm({ ...editRoomForm, packageId: v })}
                            >
                                <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                    <SelectValue placeholder="Select Package" />
                                </SelectTrigger>
                                <SelectContent className="bg-popover">
                                    {activeParentPackages.map((p) => (
                                        <SelectItem key={p.id} value={p.id}>
                                            {p.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Facility Structure <span className="text-red-500">*</span></Label>
                            <div className="bg-transparent border border-gray-200 rounded p-3 text-sm max-h-[180px] overflow-y-auto custom-scrollbar w-full">
                                {facilities.map((fac) => (
                                    <div key={fac.id}>
                                        <div className="flex items-center text-gray-800 font-medium">
                                            <ChevronDown className="h-4 w-4 mr-1 text-gray-500" />
                                            {fac.name}
                                        </div>
                                        <div className="ml-5 mt-1 space-y-1">
                                            {buildings
                                                .filter((b) => !b.facility_id || b.facility_id === fac.id)
                                                .map((b) => (
                                                    <div key={b.id}>
                                                        <div className="flex items-center text-gray-700 font-medium">
                                                            <ChevronDown className="h-4 w-4 mr-1 text-gray-500" />
                                                            {b.name}
                                                        </div>
                                                        <div className="ml-5 mt-1 space-y-1">
                                                            {floors
                                                                .filter((f) => f.building_id === b.id)
                                                                .map((f) => {
                                                                    const isSelected = editRoomForm.propertyChainId === f.property_chain_id;
                                                                    return (
                                                                        <div
                                                                            key={f.id}
                                                                            onClick={() =>
                                                                                setEditRoomForm({
                                                                                    ...editRoomForm,
                                                                                    propertyChainId: f.property_chain_id,
                                                                                })
                                                                            }
                                                                            className={`py-1 px-2 text-xs rounded cursor-pointer flex items-center justify-between transition-colors ${
                                                                                isSelected
                                                                                    ? "bg-brand/10 text-brand font-semibold"
                                                                                    : "hover:bg-muted/20 text-gray-700"
                                                                            }`}
                                                                        >
                                                                            <span>{f.name}</span>
                                                                            {isSelected && <Check className="h-3.5 w-3.5 text-brand" />}
                                                                        </div>
                                                                    );
                                                                })}
                                                        </div>
                                                    </div>
                                                ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Room No <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editRoomForm.name}
                                onChange={(e) => setEditRoomForm({ ...editRoomForm, name: e.target.value })}
                                className="w-full bg-white border border-gray-300 text-gray-900 focus:ring-1 focus:ring-brand px-3 py-1.5 text-sm outline-none rounded-[2px]"
                            />
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4 mt-2">
                            <Label className="text-sm font-medium text-gray-800">Smoking</Label>
                            <RadioGroup
                                value={editRoomForm.smoking}
                                onValueChange={(v) => setEditRoomForm({ ...editRoomForm, smoking: v })}
                                className="flex gap-4"
                            >
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="yes" id="edit-room-smoke-yes" />
                                    <Label htmlFor="edit-room-smoke-yes" className="cursor-pointer text-sm">Yes</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="no" id="edit-room-smoke-no" />
                                    <Label htmlFor="edit-room-smoke-no" className="cursor-pointer text-sm">No</Label>
                                </div>
                            </RadioGroup>
                        </div>
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4 mt-2">
                            <Label className="text-sm font-medium text-gray-800">Front / Pool Facing</Label>
                            <RadioGroup
                                value={editRoomForm.poolFacing}
                                onValueChange={(v) => setEditRoomForm({ ...editRoomForm, poolFacing: v })}
                                className="flex gap-4"
                            >
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="yes" id="edit-room-front-yes" />
                                    <Label htmlFor="edit-room-front-yes" className="cursor-pointer text-sm">Yes</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="no" id="edit-room-front-no" />
                                    <Label htmlFor="edit-room-front-no" className="cursor-pointer text-sm">No</Label>
                                </div>
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="flex justify-center gap-4 pb-8 border-t border-gray-200 pt-4">
                        <Button
                            variant="outline"
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                            onClick={() => setEditRoomOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                            onClick={handleSaveRoom}
                            disabled={!mayWrite || updateRoomMutation.isPending}
                        >
                            {updateRoomMutation.isPending ? "Saving..." : "Submit"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default FacilityManagement;
