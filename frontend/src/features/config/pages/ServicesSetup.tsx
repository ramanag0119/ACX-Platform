import { useState, useRef, useEffect } from "react";
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
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { X, Check, Pencil, Trash2, ChevronDown, Edit } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useRooms, useServiceCategories, useServiceItems, useServiceTypes } from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  useCreateServiceCategory,
  useCreateServiceItem,
} from "@/lib/api/mutations";
import { toast } from "@/hooks/use-toast";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

type TabType = "room-service" | "travel-desk" | "business-center" | "food-order" | "facility-maintenance" | "health-fitness" | "sanitation-maintenance";

// The Room Service pickers used to be driven by a hardcoded map of categories
// and service names ("Room Amenities" -> "Room 1".."Room 5", ...). None of those
// strings matched a `service_category` row, so a submission could never resolve
// a category id. They are now read from the API -- see roomServiceCategoryOptions.

/**
 * Services Setup, connected to the Phase 2.5 catalogue APIs.
 *
 *   GET /service-types      the seven real service types
 *   GET /service-categories one row per category, carrying its service_type
 *   GET /service-items      the items inside each category, with price_per_unit
 *
 * Every tab below is a projection of those three lists filtered by service
 * type -- Room Service, Travel Desk, Business Center, Food Order, Facility
 * Maintenance Service, Health & Fitness and Sanitation Maintenance Service.
 * The category/item names are whatever the database holds; none are hardcoded.
 *
 * Columns with no column behind them, shown as "-":
 *   Veg/Non-Veg and Spicy on the food menu -- `service_item` stores neither.
 *   "Type of Service" for facility/sanitation services -- the schema has one
 *   category level, not a category plus a sub-type.
 *
 * Phase 3.0 writes:
 *   A new "menu" / service entry -> POST /service-items in the tab's category
 *   A new category               -> POST /service-categories for the tab's type
 *
 * Which of the two a tab creates follows the schema: `service_category` groups
 * items within a service type, and `service_category_item` is the item itself.
 */

// Multi-select dropdown component
const MultiSelectDropdown = ({
    options,
    selectedValues,
    onChange,
    placeholder = "Select options"
}: {
    options: { id: string; label: string }[];
    selectedValues: string[];
    onChange: (values: string[]) => void;
    placeholder?: string;
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const filteredOptions = options.filter(option =>
        option.label.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const toggleOption = (id: string) => {
        if (selectedValues.includes(id)) {
            onChange(selectedValues.filter(v => v !== id));
        } else {
            onChange([...selectedValues, id]);
        }
    };

    const toggleAll = () => {
        if (selectedValues.length === options.length) {
            onChange([]);
        } else {
            onChange(options.map(o => o.id));
        }
    };

    const removeTag = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        onChange(selectedValues.filter(v => v !== id));
    };

    const selectedLabels = options.filter(o => selectedValues.includes(o.id));

    return (
        <div ref={dropdownRef} className="relative w-full">
            <div
                onClick={() => setIsOpen(!isOpen)}
                className="min-h-[42px] px-3 py-2 bg-muted/30 border border-gray-200 rounded-md cursor-pointer flex items-center flex-wrap gap-1"
            >
                {selectedLabels.length === 0 ? (
                    <span className="text-muted-foreground">{placeholder}</span>
                ) : (
                    selectedLabels.map(option => (
                        <span
                            key={option.id}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-cyan-600 text-foreground text-xs rounded"
                        >
                            {option.label}
                            <X
                                className="h-3 w-3 cursor-pointer hover:text-red-300"
                                onClick={(e) => removeTag(option.id, e)}
                            />
                        </span>
                    ))
                )}
            </div>

            {isOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-md shadow-lg z-50 max-h-64 overflow-hidden">
                    {/* Select/Unselect All */}
                    <div className="p-2 border-b border-gray-200">
                        <label className="flex items-center gap-2 cursor-pointer text-gray-700 hover:bg-gray-50 p-1 rounded">
                            <Checkbox
                                checked={selectedValues.length === options.length}
                                onCheckedChange={toggleAll}
                            />
                            <span className="text-sm">
                                {selectedValues.length === options.length ? "Unselect All" : "Select All"}
                            </span>
                        </label>
                    </div>

                    {/* Search */}
                    <div className="p-2 border-b border-gray-200">
                        <Input
                            placeholder="Search"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="h-8 bg-white border-cyan-400 text-gray-700"
                        />
                    </div>

                    {/* Options */}
                    <div className="max-h-40 overflow-y-auto">
                        {filteredOptions.map(option => (
                            <label
                                key={option.id}
                                className="flex items-center gap-2 px-3 py-2 cursor-pointer text-gray-700 hover:bg-gray-50"
                            >
                                <Checkbox
                                    checked={selectedValues.includes(option.id)}
                                    onCheckedChange={() => toggleOption(option.id)}
                                    className="border-cyan-500 data-[state=checked]:bg-cyan-500"
                                />
                                <span className="text-sm">{option.label}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const ServicesSetup = () => {
    // --- Live data -------------------------------------------------------
    const serviceTypesQuery = useServiceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
    const categoriesQuery = useServiceCategories({ page: 1, page_size: MAX_PAGE_SIZE });
    const itemsQuery = useServiceItems({ page: 1, page_size: MAX_PAGE_SIZE });
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });

    // --- Mutations
    const { canWrite } = useAuth();
    const mayWrite = canWrite("service_setup");
    const createCategory = useCreateServiceCategory();
    const createItem = useCreateServiceItem();

    /**
     * Create a catalogue row for the tab in view.
     *
     * `kind` says which table the tab is really editing: a category (a grouping
     * inside a service type) or an item (a line a guest can request).
     */
    const createCatalogueRow = (
        kind: "category" | "item",
        typeName: string,
        name: string,
        categoryName?: string,
        price?: string,
    ) => {
        const trimmed = name.trim();
        if (!trimmed) return;
        const serviceTypeId = typeId(typeName);
        if (serviceTypeId === undefined) {
            toast({
                title: "Unknown service type",
                description: `${typeName} is not in the service_type table.`,
                variant: "destructive",
            });
            return;
        }
        if (kind === "category") {
            createCategory.mutate({ category_name: trimmed, service_type: serviceTypeId });
            return;
        }
        const category = categoriesOfType(typeName).find(
            (row) => !categoryName || row.category_name === categoryName,
        );
        if (!category) {
            toast({
                title: "Create a category first",
                description: `${typeName} has no category to attach this item to.`,
                variant: "destructive",
            });
            return;
        }
        createItem.mutate({
            item_name: trimmed,
            category_id: category.id,
            ...(price ? { price_per_unit: price } : {}),
        });
    };

    const setupIsLoading =
        serviceTypesQuery.isLoading || categoriesQuery.isLoading || itemsQuery.isLoading;
    const setupError =
        serviceTypesQuery.error ?? categoriesQuery.error ?? itemsQuery.error;

    const allCategories = categoriesQuery.data?.items ?? [];
    const allItems = itemsQuery.data?.items ?? [];

    /** Resolve a service type id from its stored name. */
    const typeId = (name: string) =>
        serviceTypesQuery.data?.items.find((type) => type.name === name)?.id;

    const categoriesOfType = (name: string) => {
        const id = typeId(name);
        return id === undefined ? [] : allCategories.filter((category) => category.service_type === id);
    };
    const itemsOfType = (name: string) => {
        const id = typeId(name);
        return id === undefined ? [] : allItems.filter((item) => item.service_type === id);
    };

    // Room Service: one row per item, labelled with its category.
    const roomServicesData = itemsOfType("Room Service").map((item) => ({
        id: item.id,
        roomServices: item.category_name ?? "-",
        selectedServices: item.item_name,
    }));

    const travelDeskMenuOptions = categoriesOfType("Travel Desk").map((category) => ({
        id: category.id,
        label: category.category_name ?? "-",
    }));
    const travelDeskData = itemsOfType("Travel Desk").map((item) => ({
        id: item.id,
        travelRequestMenu: item.item_name,
    }));

    const businessCenterMenuOptions = categoriesOfType("Business Center").map((category) => ({
        id: category.id,
        label: category.category_name ?? "-",
    }));
    const businessCenterData = itemsOfType("Business Center").map((item) => ({
        id: item.id,
        businessCenterMenu: item.item_name,
    }));

    const foodCategoryData = categoriesOfType("Food Order").map((category) => ({
        id: category.id,
        category: category.category_name ?? "-",
    }));
    const servedByOptions = (roomsQuery.data?.items ?? []).map((room) => room.name);
    const foodMenuData = itemsOfType("Food Order").map((item) => ({
        id: item.id,
        foodCategory: item.category_name ?? "-",
        name: item.item_name,
        description: item.description ?? "-",
        // `service_item` stores neither a diet nor a spice flag.
        vegNonveg: "-",
        spicy: "-",
        price: item.price_per_unit ?? "-",
    }));

    const facilityServicesOptions = categoriesOfType("Facility Maintenance Service").map((category) => ({
        id: category.id,
        label: category.category_name ?? "-",
    }));
    const facilityServicesData = facilityServicesOptions.map((option) => ({
        id: option.id,
        facilityService: option.label,
    }));
    // One category level only: the item name is the closest thing the schema
    // has to a "type of service" under a facility service.
    const facilityServicesTypeData = itemsOfType("Facility Maintenance Service").map((item) => ({
        id: item.id,
        facilityService: item.category_name ?? "-",
        typeOfService: item.item_name,
    }));

    const healthFitnessMenuOptions = categoriesOfType("Health & Fitness").map((category) => ({
        id: category.id,
        label: category.category_name ?? "-",
    }));
    const healthFitnessData = itemsOfType("Health & Fitness").map((item) => ({
        id: item.id,
        healthFitness: item.item_name,
    }));

    const sanitationServicesOptions = categoriesOfType("Sanitation Maintenance Service").map((category) => ({
        id: category.id,
        label: category.category_name ?? "-",
    }));
    const sanitationServicesData = sanitationServicesOptions.map((option) => ({
        id: option.id,
        sanitationService: option.label,
    }));
    const sanitationServicesTypeData = itemsOfType("Sanitation Maintenance Service").map((item) => ({
        id: item.id,
        sanitationService: item.category_name ?? "-",
        typeOfService: item.item_name,
    }));

    const [activeTab, setActiveTab] = useState<TabType>("room-service");

    // Room Service state
    const [selectedRoomServiceType, setSelectedRoomServiceType] = useState("");
    const [selectedService, setSelectedService] = useState("");
    const [roomServiceSearch, setRoomServiceSearch] = useState("");
    const [roomServiceEntriesPerPage, setRoomServiceEntriesPerPage] = useState("10");
    const [roomServiceCurrentPage, setRoomServiceCurrentPage] = useState(1);

    // Travel Desk state
    const [selectedTravelDeskMenus, setSelectedTravelDeskMenus] = useState<string[]>([]);
    const [travelDeskSearch, setTravelDeskSearch] = useState("");
    const [travelDeskEntriesPerPage, setTravelDeskEntriesPerPage] = useState("10");
    const [travelDeskCurrentPage, setTravelDeskCurrentPage] = useState(1);

    // Business Center state
    const [selectedBusinessCenterMenus, setSelectedBusinessCenterMenus] = useState<string[]>([]);
    const [businessCenterSearch, setBusinessCenterSearch] = useState("");
    const [businessCenterEntriesPerPage, setBusinessCenterEntriesPerPage] = useState("10");
    const [businessCenterCurrentPage, setBusinessCenterCurrentPage] = useState(1);

    // Food Order state
    const [foodOrderSubTab, setFoodOrderSubTab] = useState<"food-category" | "food-menu">("food-category");
    // Food Category state
    const [newFoodCategory, setNewFoodCategory] = useState("");
    const [foodCategorySearch, setFoodCategorySearch] = useState("");
    const [foodCategoryEntriesPerPage, setFoodCategoryEntriesPerPage] = useState("10");
    const [foodCategoryCurrentPage, setFoodCategoryCurrentPage] = useState(1);
    // Food Menu state
    const [selectedFoodCategory, setSelectedFoodCategory] = useState("");
    const [foodCode, setFoodCode] = useState("");
    const [foodName, setFoodName] = useState("");
    const [servedBy, setServedBy] = useState("");
    const [foodDescription, setFoodDescription] = useState("");
    const [vegNonveg, setVegNonveg] = useState("");
    const [spicy, setSpicy] = useState("");
    const [foodPrice, setFoodPrice] = useState("");
    const [foodMenuSearch, setFoodMenuSearch] = useState("");
    const [foodMenuEntriesPerPage, setFoodMenuEntriesPerPage] = useState("10");
    const [foodMenuCurrentPage, setFoodMenuCurrentPage] = useState(1);

    // Facility Maintenance Service state
    const [facilityMaintenanceSubTab, setFacilityMaintenanceSubTab] = useState<"facility-services" | "facility-services-type">("facility-services");
    // Facility Services state
    const [selectedFacilityServices, setSelectedFacilityServices] = useState<string[]>([]);
    const [facilityServicesSearch, setFacilityServicesSearch] = useState("");
    const [facilityServicesEntriesPerPage, setFacilityServicesEntriesPerPage] = useState("10");
    const [facilityServicesCurrentPage, setFacilityServicesCurrentPage] = useState(1);
    // Facility Services Type state
    const [selectedFacilityServiceForType, setSelectedFacilityServiceForType] = useState("");
    const [servicesType, setServicesType] = useState("");
    const [estimateTime, setEstimateTime] = useState("");
    const [facilityServicesTypeSearch, setFacilityServicesTypeSearch] = useState("");
    const [facilityServicesTypeEntriesPerPage, setFacilityServicesTypeEntriesPerPage] = useState("10");
    const [facilityServicesTypeCurrentPage, setFacilityServicesTypeCurrentPage] = useState(1);

    // Health & Fitness state
    const [selectedHealthFitnessMenus, setSelectedHealthFitnessMenus] = useState<string[]>([]);
    const [healthFitnessSearch, setHealthFitnessSearch] = useState("");
    const [healthFitnessEntriesPerPage, setHealthFitnessEntriesPerPage] = useState("10");
    const [healthFitnessCurrentPage, setHealthFitnessCurrentPage] = useState(1);

    // Sanitation Maintenance Service state
    const [sanitationMaintenanceSubTab, setSanitationMaintenanceSubTab] = useState<"sanitation-services" | "sanitation-services-type">("sanitation-services");
    // Sanitation Services state
    const [selectedSanitationServices, setSelectedSanitationServices] = useState<string[]>([]);
    const [sanitationServicesSearch, setSanitationServicesSearch] = useState("");
    const [sanitationServicesEntriesPerPage, setSanitationServicesEntriesPerPage] = useState("10");
    const [sanitationServicesCurrentPage, setSanitationServicesCurrentPage] = useState(1);
    // Sanitation Services Type state
    const [selectedSanitationServiceForType, setSelectedSanitationServiceForType] = useState("");
    const [sanitationServicesType, setSanitationServicesType] = useState("");
    const [sanitationEstimateTime, setSanitationEstimateTime] = useState("");
    const [sanitationServicesTypeSearch, setSanitationServicesTypeSearch] = useState("");
    const [sanitationServicesTypeEntriesPerPage, setSanitationServicesTypeEntriesPerPage] = useState("10");
    const [sanitationServicesTypeCurrentPage, setSanitationServicesTypeCurrentPage] = useState(1);

    // Modal states
    const [editFoodCategoryOpen, setEditFoodCategoryOpen] = useState(false);
    const [editFacilityServiceOpen, setEditFacilityServiceOpen] = useState(false);
    const [editSanitationServiceOpen, setEditSanitationServiceOpen] = useState(false);
    const [editFoodMenuOpen, setEditFoodMenuOpen] = useState(false);

    const tabs = [
        { id: "room-service" as TabType, label: "Room Service" },
        { id: "travel-desk" as TabType, label: "Travel Desk" },
        { id: "business-center" as TabType, label: "Business Center" },
        { id: "food-order" as TabType, label: "Food Order" },
        { id: "facility-maintenance" as TabType, label: "Facility Maintenance Service" },
        { id: "health-fitness" as TabType, label: "Health & Fitness" },
        { id: "sanitation-maintenance" as TabType, label: "Sanitation Maintenance Service" },
    ];

    /** Categories of the Room Service type, for the form's first picker. */
    const roomServiceCategoryOptions = categoriesOfType("Room Service").map((category) => ({
        id: category.id,
        label: category.category_name ?? "-",
    }));

    /**
     * The multi-select tabs (Travel Desk, Business Center, Facility Services,
     * Health & Fitness, Sanitation Services) all work the same way: the picker
     * lists the real `service_category` rows of that service type, and the table
     * below lists the `service_category_item` rows. Submitting therefore creates
     * one item per selected category, named after that category -- which is the
     * only mapping the schema supports, and uses real ids and real names.
     */
    const submitMenuSelection = (
        selectedIds: string[],
        options: { id: string; label: string }[],
        clear: (value: string[]) => void,
        label: string,
    ) => {
        if (!selectedIds.length) {
            toast({
                title: `Select at least one ${label}`,
                variant: "destructive",
            });
            return;
        }
        for (const id of selectedIds) {
            const option = options.find((entry) => entry.id === id);
            if (!option) continue;
            createItem.mutate({ item_name: option.label, category_id: option.id });
        }
        clear([]);
    };

    /** Create one `service_category_item` under a chosen category. */
    const submitItemForCategory = (
        categoryId: string,
        itemName: string,
        clear: () => void,
        extra?: { description?: string | null; price_per_unit?: string | null },
    ) => {
        const trimmed = itemName.trim();
        if (!categoryId || !trimmed) {
            toast({
                title: "Both fields are required",
                description: "Choose a category and enter a name.",
                variant: "destructive",
            });
            return;
        }
        createItem.mutate(
            { item_name: trimmed, category_id: categoryId, ...(extra ?? {}) },
            { onSuccess: clear },
        );
    };

    const handleRoomServiceSubmit = () => {
        submitItemForCategory(selectedRoomServiceType, selectedService, () => {
            setSelectedService("");
        });
    };

    const handleTravelDeskSubmit = () => {
        submitMenuSelection(
            selectedTravelDeskMenus, travelDeskMenuOptions,
            setSelectedTravelDeskMenus, "travel desk menu",
        );
    };

    const handleBusinessCenterSubmit = () => {
        submitMenuSelection(
            selectedBusinessCenterMenus, businessCenterMenuOptions,
            setSelectedBusinessCenterMenus, "business center menu",
        );
    };

    const handleFacilityServicesSubmit = () => {
        submitMenuSelection(
            selectedFacilityServices, facilityServicesOptions,
            setSelectedFacilityServices, "facility service",
        );
    };

    /**
     * "Estimate time" has NO column on `service_category_item`, so it cannot be
     * stored. It is recorded in `description` -- the only free-text column the
     * table has -- rather than being silently dropped.
     */
    const handleFacilityServicesTypeSubmit = () => {
        submitItemForCategory(
            selectedFacilityServiceForType, servicesType,
            handleFacilityServicesTypeReset,
            estimateTime.trim()
                ? { description: `Estimated time: ${estimateTime.trim()}` }
                : undefined,
        );
    };

    const handleFacilityServicesTypeReset = () => {
        setSelectedFacilityServiceForType("");
        setServicesType("");
        setEstimateTime("");
    };

    const handleHealthFitnessSubmit = () => {
        submitMenuSelection(
            selectedHealthFitnessMenus, healthFitnessMenuOptions,
            setSelectedHealthFitnessMenus, "health & fitness menu",
        );
    };

    const handleSanitationServicesSubmit = () => {
        submitMenuSelection(
            selectedSanitationServices, sanitationServicesOptions,
            setSelectedSanitationServices, "sanitation service",
        );
    };

    const handleSanitationServicesTypeSubmit = () => {
        submitItemForCategory(
            selectedSanitationServiceForType, sanitationServicesType,
            handleSanitationServicesTypeReset,
            sanitationEstimateTime.trim()
                ? { description: `Estimated time: ${sanitationEstimateTime.trim()}` }
                : undefined,
        );
    };

    const handleSanitationServicesTypeReset = () => {
        setSelectedSanitationServiceForType("");
        setSanitationServicesType("");
        setSanitationEstimateTime("");
    };

    /** Food Category is a `service_category` under the Food Order service type. */
    const handleFoodCategorySubmit = () => {
        createCatalogueRow("category", "Food Order", newFoodCategory);
        setNewFoodCategory("");
    };

    const handleFoodCategoryReset = () => {
        setNewFoodCategory("");
    };

    /**
     * Food Menu is a `service_category_item`. `food code`, `served by`, diet and
     * spice level have no columns on that table; the ones that carry real
     * meaning are folded into `description`, and nothing is invented.
     */
    const handleFoodMenuSubmit = () => {
        const notes = [
            foodCode.trim() && `Code: ${foodCode.trim()}`,
            servedBy.trim() && `Served by: ${servedBy.trim()}`,
            vegNonveg && `Diet: ${vegNonveg}`,
            spicy && `Spice: ${spicy}`,
            foodDescription.trim(),
        ].filter(Boolean).join(" | ");
        submitItemForCategory(selectedFoodCategory, foodName, handleFoodMenuReset, {
            ...(notes ? { description: notes } : {}),
            ...(foodPrice.trim() ? { price_per_unit: foodPrice.trim() } : {}),
        });
    };

    const handleFoodMenuReset = () => {
        setSelectedFoodCategory("");
        setFoodCode("");
        setFoodName("");
        setServedBy("");
        setFoodDescription("");
        setVegNonveg("");
        setSpicy("");
        setFoodPrice("");
    };

    // Filter Room Services data
    const filteredRoomServicesData = roomServicesData.filter(item =>
        item.roomServices.toLowerCase().includes(roomServiceSearch.toLowerCase()) ||
        item.selectedServices.toLowerCase().includes(roomServiceSearch.toLowerCase())
    );

    // Filter Travel Desk data
    const filteredTravelDeskData = travelDeskData.filter(item =>
        item.travelRequestMenu.toLowerCase().includes(travelDeskSearch.toLowerCase())
    );

    // Filter Business Center data
    const filteredBusinessCenterData = businessCenterData.filter(item =>
        item.businessCenterMenu.toLowerCase().includes(businessCenterSearch.toLowerCase())
    );

    // Pagination calculations
    const roomServiceTotalPages = Math.ceil(filteredRoomServicesData.length / parseInt(roomServiceEntriesPerPage));
    const roomServiceStartIndex = (roomServiceCurrentPage - 1) * parseInt(roomServiceEntriesPerPage);
    const roomServiceEndIndex = roomServiceStartIndex + parseInt(roomServiceEntriesPerPage);
    const paginatedRoomServicesData = filteredRoomServicesData.slice(roomServiceStartIndex, roomServiceEndIndex);

    const travelDeskTotalPages = Math.ceil(filteredTravelDeskData.length / parseInt(travelDeskEntriesPerPage));
    const travelDeskStartIndex = (travelDeskCurrentPage - 1) * parseInt(travelDeskEntriesPerPage);
    const travelDeskEndIndex = travelDeskStartIndex + parseInt(travelDeskEntriesPerPage);
    const paginatedTravelDeskData = filteredTravelDeskData.slice(travelDeskStartIndex, travelDeskEndIndex);

    const businessCenterTotalPages = Math.ceil(filteredBusinessCenterData.length / parseInt(businessCenterEntriesPerPage));
    const businessCenterStartIndex = (businessCenterCurrentPage - 1) * parseInt(businessCenterEntriesPerPage);
    const businessCenterEndIndex = businessCenterStartIndex + parseInt(businessCenterEntriesPerPage);
    const paginatedBusinessCenterData = filteredBusinessCenterData.slice(businessCenterStartIndex, businessCenterEndIndex);

    // Filter Food Category data
    const filteredFoodCategoryData = foodCategoryData.filter(item =>
        item.category.toLowerCase().includes(foodCategorySearch.toLowerCase())
    );
    const foodCategoryTotalPages = Math.ceil(filteredFoodCategoryData.length / parseInt(foodCategoryEntriesPerPage));
    const foodCategoryStartIndex = (foodCategoryCurrentPage - 1) * parseInt(foodCategoryEntriesPerPage);
    const foodCategoryEndIndex = foodCategoryStartIndex + parseInt(foodCategoryEntriesPerPage);
    const paginatedFoodCategoryData = filteredFoodCategoryData.slice(foodCategoryStartIndex, foodCategoryEndIndex);

    // Filter Food Menu data
    const filteredFoodMenuData = foodMenuData.filter(item =>
        item.name.toLowerCase().includes(foodMenuSearch.toLowerCase()) ||
        item.foodCategory.toLowerCase().includes(foodMenuSearch.toLowerCase())
    );
    const foodMenuTotalPages = Math.ceil(filteredFoodMenuData.length / parseInt(foodMenuEntriesPerPage));
    const foodMenuStartIndex = (foodMenuCurrentPage - 1) * parseInt(foodMenuEntriesPerPage);
    const foodMenuEndIndex = foodMenuStartIndex + parseInt(foodMenuEntriesPerPage);
    const paginatedFoodMenuData = filteredFoodMenuData.slice(foodMenuStartIndex, foodMenuEndIndex);

    // Filter Facility Services data
    const filteredFacilityServicesData = facilityServicesData.filter(item =>
        item.facilityService.toLowerCase().includes(facilityServicesSearch.toLowerCase())
    );
    const facilityServicesTotalPages = Math.ceil(filteredFacilityServicesData.length / parseInt(facilityServicesEntriesPerPage));
    const facilityServicesStartIndex = (facilityServicesCurrentPage - 1) * parseInt(facilityServicesEntriesPerPage);
    const facilityServicesEndIndex = facilityServicesStartIndex + parseInt(facilityServicesEntriesPerPage);
    const paginatedFacilityServicesData = filteredFacilityServicesData.slice(facilityServicesStartIndex, facilityServicesEndIndex);

    // Filter Facility Services Type data
    const filteredFacilityServicesTypeData = facilityServicesTypeData.filter(item =>
        item.facilityService.toLowerCase().includes(facilityServicesTypeSearch.toLowerCase()) ||
        item.typeOfService.toLowerCase().includes(facilityServicesTypeSearch.toLowerCase())
    );
    const facilityServicesTypeTotalPages = Math.ceil(filteredFacilityServicesTypeData.length / parseInt(facilityServicesTypeEntriesPerPage));
    const facilityServicesTypeStartIndex = (facilityServicesTypeCurrentPage - 1) * parseInt(facilityServicesTypeEntriesPerPage);
    const facilityServicesTypeEndIndex = facilityServicesTypeStartIndex + parseInt(facilityServicesTypeEntriesPerPage);
    const paginatedFacilityServicesTypeData = filteredFacilityServicesTypeData.slice(facilityServicesTypeStartIndex, facilityServicesTypeEndIndex);

    // Filter Health & Fitness data
    const filteredHealthFitnessData = healthFitnessData.filter(item =>
        item.healthFitness.toLowerCase().includes(healthFitnessSearch.toLowerCase())
    );
    const healthFitnessTotalPages = Math.ceil(filteredHealthFitnessData.length / parseInt(healthFitnessEntriesPerPage));
    const healthFitnessStartIndex = (healthFitnessCurrentPage - 1) * parseInt(healthFitnessEntriesPerPage);
    const healthFitnessEndIndex = healthFitnessStartIndex + parseInt(healthFitnessEntriesPerPage);
    const paginatedHealthFitnessData = filteredHealthFitnessData.slice(healthFitnessStartIndex, healthFitnessEndIndex);

    // Filter Sanitation Services data
    const filteredSanitationServicesData = sanitationServicesData.filter(item =>
        item.sanitationService.toLowerCase().includes(sanitationServicesSearch.toLowerCase())
    );
    const sanitationServicesTotalPages = Math.ceil(filteredSanitationServicesData.length / parseInt(sanitationServicesEntriesPerPage));
    const sanitationServicesStartIndex = (sanitationServicesCurrentPage - 1) * parseInt(sanitationServicesEntriesPerPage);
    const sanitationServicesEndIndex = sanitationServicesStartIndex + parseInt(sanitationServicesEntriesPerPage);
    const paginatedSanitationServicesData = filteredSanitationServicesData.slice(sanitationServicesStartIndex, sanitationServicesEndIndex);

    // Filter Sanitation Services Type data
    const filteredSanitationServicesTypeData = sanitationServicesTypeData.filter(item =>
        item.sanitationService.toLowerCase().includes(sanitationServicesTypeSearch.toLowerCase()) ||
        item.typeOfService.toLowerCase().includes(sanitationServicesTypeSearch.toLowerCase())
    );
    const sanitationServicesTypeTotalPages = Math.ceil(filteredSanitationServicesTypeData.length / parseInt(sanitationServicesTypeEntriesPerPage));
    const sanitationServicesTypeStartIndex = (sanitationServicesTypeCurrentPage - 1) * parseInt(sanitationServicesTypeEntriesPerPage);
    const sanitationServicesTypeEndIndex = sanitationServicesTypeStartIndex + parseInt(sanitationServicesTypeEntriesPerPage);
    const paginatedSanitationServicesTypeData = filteredSanitationServicesTypeData.slice(sanitationServicesTypeStartIndex, sanitationServicesTypeEndIndex);

    const renderRoomServiceTab = () => (
        <div className="space-y-6">
            {/* Form Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                        {/* Type of Room Service */}
                        <div className="space-y-2">
                            <Label className="text-foreground">
                                Type of Room Service<span className="text-red-500">*</span>
                            </Label>
                            {/* Real `service_category` rows of the Room Service type.
                                The previous hardcoded slugs matched no row, so a
                                submission could never resolve a category id. */}
                            <Select value={selectedRoomServiceType} onValueChange={setSelectedRoomServiceType}>
                                <SelectTrigger className="bg-muted/30 border-border/50 text-foreground">
                                    <SelectValue placeholder="Select Room Service" />
                                </SelectTrigger>
                                <SelectContent className="bg-white">
                                    {roomServiceCategoryOptions.length === 0 ? (
                                        <div className="px-3 py-2 text-sm text-muted-foreground">
                                            No Room Service category exists yet
                                        </div>
                                    ) : (
                                        roomServiceCategoryOptions.map((option) => (
                                            <SelectItem key={option.id} value={option.id}>
                                                {option.label}
                                            </SelectItem>
                                        ))
                                    )}
                                </SelectContent>
                            </Select>
                            {!selectedRoomServiceType && (
                                <p className="text-red-400 text-xs">Room Service is Required</p>
                            )}
                        </div>

                        {/* Services -- the item name to add under that category. */}
                        <div className="space-y-2">
                            <Label className="text-foreground">
                                Services<span className="text-red-500">*</span>
                            </Label>
                            <Input
                                placeholder="Enter service name"
                                value={selectedService}
                                onChange={(event) => setSelectedService(event.target.value)}
                                disabled={!selectedRoomServiceType}
                                className="bg-muted/30 border-border/50 text-foreground"
                            />
                        </div>
                    </div>

                    {/* Submit Button */}
                    <div className="flex justify-center mt-6">
                        <Button
                            onClick={handleRoomServiceSubmit}
                            disabled={!mayWrite || !selectedRoomServiceType || !selectedService.trim() || createItem.isPending}
                            className="bg-cyan-600 hover:bg-cyan-700 text-foreground px-8"
                        >
                            {createItem.isPending ? "Saving..." : "Submit"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {/* Controls */}
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={roomServiceEntriesPerPage} onValueChange={setRoomServiceEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-white">
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
                            <Input
                                placeholder="Service category, Service"
                                value={roomServiceSearch}
                                onChange={(e) => setRoomServiceSearch(e.target.value)}
                                className="w-64 h-9 bg-muted/30 border-border/50 text-foreground"
                            />
                        </div>
                    </div>

                    {/* Table */}
                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Room Services</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-right">Selected Services</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedRoomServicesData.map((item, index) => (
                                    <TableRow
                                        key={item.id}
                                        className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}
                                    >
                                        <TableCell className="text-cyan-600 hover:underline cursor-pointer">
                                            {item.roomServices}
                                        </TableCell>
                                        <TableCell className="text-foreground text-right">
                                            {item.selectedServices}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing {roomServiceStartIndex + 1} to {Math.min(roomServiceEndIndex, filteredRoomServicesData.length)} of {filteredRoomServicesData.length} entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setRoomServiceCurrentPage(1)}
                                disabled={roomServiceCurrentPage === 1}
                            >
                                First
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setRoomServiceCurrentPage(Math.max(1, roomServiceCurrentPage - 1))}
                                disabled={roomServiceCurrentPage === 1}
                            >
                                Previous
                            </Button>
                            {Array.from({ length: Math.min(3, roomServiceTotalPages) }, (_, i) => i + 1).map((page) => (
                                <Button
                                    key={page}
                                    variant={roomServiceCurrentPage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`w-9 h-9 p-0 ${roomServiceCurrentPage === page
                                        ? "bg-cyan-600 text-foreground"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    onClick={() => setRoomServiceCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setRoomServiceCurrentPage(Math.min(roomServiceTotalPages, roomServiceCurrentPage + 1))}
                                disabled={roomServiceCurrentPage === roomServiceTotalPages}
                            >
                                Next
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setRoomServiceCurrentPage(roomServiceTotalPages)}
                                disabled={roomServiceCurrentPage === roomServiceTotalPages}
                            >
                                Last
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderTravelDeskTab = () => (
        <div className="space-y-6">
            {/* Form Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="max-w-2xl mx-auto space-y-4">
                        {/* Travel Desk Menu */}
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">
                                Travel Desk Menu<span className="text-red-500">*</span>
                            </Label>
                            <MultiSelectDropdown
                                options={travelDeskMenuOptions}
                                selectedValues={selectedTravelDeskMenus}
                                onChange={setSelectedTravelDeskMenus}
                                placeholder="Select Travel Desk Menu"
                            />
                        </div>

                        {/* Submit Button */}
                        <div className="flex justify-center mt-6">
                            <Button
                                onClick={handleTravelDeskSubmit}
                                className="bg-cyan-600 hover:bg-cyan-700 text-foreground px-8"
                            >
                                Submit
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {/* Controls */}
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={travelDeskEntriesPerPage} onValueChange={setTravelDeskEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-white">
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
                            <Input
                                placeholder="Travel request menu"
                                value={travelDeskSearch}
                                onChange={(e) => setTravelDeskSearch(e.target.value)}
                                className="w-64 h-9 bg-muted/30 border-border/50 text-foreground"
                            />
                        </div>
                    </div>

                    {/* Table */}
                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium text-center">Travel Request Menu</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedTravelDeskData.map((item, index) => (
                                    <TableRow
                                        key={item.id}
                                        className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}
                                    >
                                        <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">
                                            {item.travelRequestMenu}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing {travelDeskStartIndex + 1} to {Math.min(travelDeskEndIndex, filteredTravelDeskData.length)} of {filteredTravelDeskData.length} entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setTravelDeskCurrentPage(1)}
                                disabled={travelDeskCurrentPage === 1}
                            >
                                First
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setTravelDeskCurrentPage(Math.max(1, travelDeskCurrentPage - 1))}
                                disabled={travelDeskCurrentPage === 1}
                            >
                                Previous
                            </Button>
                            {Array.from({ length: Math.min(3, travelDeskTotalPages) }, (_, i) => i + 1).map((page) => (
                                <Button
                                    key={page}
                                    variant={travelDeskCurrentPage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`w-9 h-9 p-0 ${travelDeskCurrentPage === page
                                        ? "bg-cyan-600 text-foreground"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    onClick={() => setTravelDeskCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setTravelDeskCurrentPage(Math.min(travelDeskTotalPages, travelDeskCurrentPage + 1))}
                                disabled={travelDeskCurrentPage === travelDeskTotalPages}
                            >
                                Next
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setTravelDeskCurrentPage(travelDeskTotalPages)}
                                disabled={travelDeskCurrentPage === travelDeskTotalPages}
                            >
                                Last
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderBusinessCenterTab = () => (
        <div className="space-y-6">
            {/* Form Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="max-w-2xl mx-auto space-y-4">
                        {/* Business Center Menu */}
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">
                                Business Center Menu<span className="text-red-500">*</span>
                            </Label>
                            <MultiSelectDropdown
                                options={businessCenterMenuOptions}
                                selectedValues={selectedBusinessCenterMenus}
                                onChange={setSelectedBusinessCenterMenus}
                                placeholder="Select Business Center Menu"
                            />
                        </div>

                        {/* Submit Button */}
                        <div className="flex justify-center mt-6">
                            <Button
                                onClick={handleBusinessCenterSubmit}
                                className="bg-cyan-600 hover:bg-cyan-700 text-foreground px-8"
                            >
                                Submit
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    {/* Controls */}
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={businessCenterEntriesPerPage} onValueChange={setBusinessCenterEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-white">
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
                            <Input
                                placeholder="Business center menu"
                                value={businessCenterSearch}
                                onChange={(e) => setBusinessCenterSearch(e.target.value)}
                                className="w-64 h-9 bg-muted/30 border-border/50 text-foreground"
                            />
                        </div>
                    </div>

                    {/* Table */}
                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium text-center">Business Center Menu</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedBusinessCenterData.map((item, index) => (
                                    <TableRow
                                        key={item.id}
                                        className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background transition-colors`}
                                    >
                                        <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">
                                            {item.businessCenterMenu}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">
                            Showing {businessCenterStartIndex + 1} to {Math.min(businessCenterEndIndex, filteredBusinessCenterData.length)} of {filteredBusinessCenterData.length} entries
                        </span>

                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setBusinessCenterCurrentPage(1)}
                                disabled={businessCenterCurrentPage === 1}
                            >
                                First
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setBusinessCenterCurrentPage(Math.max(1, businessCenterCurrentPage - 1))}
                                disabled={businessCenterCurrentPage === 1}
                            >
                                Previous
                            </Button>
                            {Array.from({ length: Math.min(3, businessCenterTotalPages) }, (_, i) => i + 1).map((page) => (
                                <Button
                                    key={page}
                                    variant={businessCenterCurrentPage === page ? "default" : "ghost"}
                                    size="sm"
                                    className={`w-9 h-9 p-0 ${businessCenterCurrentPage === page
                                        ? "bg-cyan-600 text-foreground"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                    onClick={() => setBusinessCenterCurrentPage(page)}
                                >
                                    {page}
                                </Button>
                            ))}
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setBusinessCenterCurrentPage(Math.min(businessCenterTotalPages, businessCenterCurrentPage + 1))}
                                disabled={businessCenterCurrentPage === businessCenterTotalPages}
                            >
                                Next
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-foreground"
                                onClick={() => setBusinessCenterCurrentPage(businessCenterTotalPages)}
                                disabled={businessCenterCurrentPage === businessCenterTotalPages}
                            >
                                Last
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderFoodOrderTab = () => (
        <div className="space-y-4">
            {/* Sub-tabs for Food Order */}
            <div className="flex gap-2">
                <button
                    onClick={() => setFoodOrderSubTab("food-category")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${foodOrderSubTab === "food-category"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"}`}
                >
                    Food Category
                </button>
                <button
                    onClick={() => setFoodOrderSubTab("food-menu")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${foodOrderSubTab === "food-menu"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"}`}
                >
                    Food Menu
                </button>
            </div>

            {foodOrderSubTab === "food-category" ? (
                <div className="space-y-6">
                    {/* Food Category Form */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="max-w-2xl mx-auto space-y-4">
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">
                                        Food Category<span className="text-red-500">*</span>
                                    </Label>
                                    <Input
                                        placeholder="Enter Food Category"
                                        value={newFoodCategory}
                                        onChange={(e) => setNewFoodCategory(e.target.value)}
                                        className="bg-muted/30 border-border/50 text-foreground"
                                    />
                                </div>
                                <div className="flex justify-center gap-4 mt-6 pt-6 border-t border-border/30">
                                    <Button onClick={handleFoodCategoryReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 font-semibold text-sm shadow-sm transition-all">
                                        Reset
                                    </Button>
                                    <Button onClick={handleFoodCategorySubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                                        Submit
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Food Category Table */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={foodCategoryEntriesPerPage} onValueChange={setFoodCategoryEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-white">
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
                                        placeholder="Food category"
                                        value={foodCategorySearch}
                                        onChange={(e) => setFoodCategorySearch(e.target.value)}
                                        className="w-48 h-9 bg-muted/30 border-border/50 text-foreground"
                                    />
                                </div>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-gray-200">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gradient-to-r from-[#4a4a4a] to-[#5a5a5a]">
                                            <TableHead className="text-gray-600 font-medium text-center">Food Category</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedFoodCategoryData.map((item, index) => (
                                            <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background`}>
                                                <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">{item.category}</TableCell>
                                                <TableCell className="text-center">
                                                    <div className="flex justify-center gap-2">
                                                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFoodCategoryOpen(true)}>
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
                                <span className="text-muted-foreground text-sm">Showing {foodCategoryStartIndex + 1} to {Math.min(foodCategoryEndIndex, filteredFoodCategoryData.length)} of {filteredFoodCategoryData.length} entries</span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodCategoryCurrentPage(1)} disabled={foodCategoryCurrentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodCategoryCurrentPage(Math.max(1, foodCategoryCurrentPage - 1))} disabled={foodCategoryCurrentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(3, foodCategoryTotalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={foodCategoryCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${foodCategoryCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setFoodCategoryCurrentPage(page)}>{page}</Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodCategoryCurrentPage(Math.min(foodCategoryTotalPages, foodCategoryCurrentPage + 1))} disabled={foodCategoryCurrentPage === foodCategoryTotalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodCategoryCurrentPage(foodCategoryTotalPages)} disabled={foodCategoryCurrentPage === foodCategoryTotalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Food Menu Form */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="grid grid-cols-2 gap-6 max-w-4xl mx-auto">
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-sm font-medium text-right">Food Category<span className="text-red-500">*</span></Label>
                                        <Select value={selectedFoodCategory} onValueChange={setSelectedFoodCategory}>
                                            <SelectTrigger className="bg-muted/30 border-border/50 text-foreground"><SelectValue placeholder="Select Food Category" /></SelectTrigger>
                                            <SelectContent className="bg-white">
                                                {/* value is the `service_category.id` UUID -- it goes straight
                                                    to `category_id` on POST /service-items. The visible label
                                                    stays the category name. Sending the name here was what
                                                    made submit fail its UUID validation. */}
                                                {foodCategoryData.map(cat => (<SelectItem key={cat.id} value={cat.id}>{cat.category}</SelectItem>))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-foreground text-right">Food Code</Label>
                                        <Input placeholder="Enter Food Code" value={foodCode} onChange={(e) => setFoodCode(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-sm font-medium text-right">Food Name<span className="text-red-500">*</span></Label>
                                        <Input placeholder="Enter Food Name" value={foodName} onChange={(e) => setFoodName(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-foreground text-right">Served By</Label>
                                        <Select value={servedBy} onValueChange={setServedBy}>
                                            <SelectTrigger className="bg-muted/30 border-border/50 text-foreground"><SelectValue placeholder="Select Served By" /></SelectTrigger>
                                            <SelectContent className="bg-white">
                                                {servedByOptions.map(opt => (<SelectItem key={opt} value={opt}>{opt}</SelectItem>))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-sm font-medium text-right">Description<span className="text-red-500">*</span></Label>
                                        <Input placeholder="Enter Description" value={foodDescription} onChange={(e) => setFoodDescription(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-sm font-medium text-right">Veg/Nonveg<span className="text-red-500">*</span></Label>
                                        <Select value={vegNonveg} onValueChange={setVegNonveg}>
                                            <SelectTrigger className="bg-muted/30 border-border/50 text-foreground"><SelectValue placeholder="Select" /></SelectTrigger>
                                            <SelectContent className="bg-white">
                                                <SelectItem value="Veg">Veg</SelectItem>
                                                <SelectItem value="Non-Veg">Non-Veg</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-sm font-medium text-right">Spicy<span className="text-red-500">*</span></Label>
                                        <Select value={spicy} onValueChange={setSpicy}>
                                            <SelectTrigger className="bg-muted/30 border-border/50 text-foreground"><SelectValue placeholder="Select" /></SelectTrigger>
                                            <SelectContent className="bg-white">
                                                <SelectItem value="Yes">Yes</SelectItem>
                                                <SelectItem value="No">No</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-sm font-medium text-right">Price<span className="text-red-500">*</span></Label>
                                        <Input placeholder="Enter Price" value={foodPrice} onChange={(e) => setFoodPrice(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 items-center">
                                        <Label className="text-foreground text-right">Food Image</Label>
                                        <Input type="file" className="bg-muted/30 border-border/50 text-foreground" />
                                    </div>
                                </div>
                            </div>
                            <div className="flex justify-center gap-4 mt-6 pt-6 border-t border-border/30">
                                <Button onClick={handleFoodMenuReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
                                <Button onClick={handleFoodMenuSubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Submit</Button>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Food Menu Table */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={foodMenuEntriesPerPage} onValueChange={setFoodMenuEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground"><SelectValue /></SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="10">10</SelectItem>
                                            <SelectItem value="25">25</SelectItem>
                                            <SelectItem value="50">50</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <span className="text-muted-foreground text-sm">entries</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Search:</span>
                                    <Input placeholder="Food category or name" value={foodMenuSearch} onChange={(e) => setFoodMenuSearch(e.target.value)} className="w-48 h-9 bg-muted/30 border-border/50 text-foreground" />
                                </div>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gradient-to-r from-[#4a4a4a] to-[#5a5a5a]">
                                            <TableHead className="text-gray-600 font-medium">Food Category</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Name</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Description</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Veg/Nonveg</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Spicy</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Price</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedFoodMenuData.map((item, index) => (
                                            <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background`}>
                                                <TableCell className="text-cyan-600 hover:underline cursor-pointer">{item.foodCategory}</TableCell>
                                                <TableCell className="text-foreground">{item.name}</TableCell>
                                                <TableCell className="text-foreground">{item.description}</TableCell>
                                                <TableCell className="text-foreground">{item.vegNonveg}</TableCell>
                                                <TableCell className="text-foreground">{item.spicy}</TableCell>
                                                <TableCell className="text-foreground">{item.price}</TableCell>
                                                <TableCell className="text-center">
                                                    <div className="flex justify-center gap-2">
                                                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFoodMenuOpen(true)}>
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
                                <span className="text-muted-foreground text-sm">Showing {foodMenuStartIndex + 1} to {Math.min(foodMenuEndIndex, filteredFoodMenuData.length)} of {filteredFoodMenuData.length} entries</span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodMenuCurrentPage(1)} disabled={foodMenuCurrentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodMenuCurrentPage(Math.max(1, foodMenuCurrentPage - 1))} disabled={foodMenuCurrentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(3, foodMenuTotalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={foodMenuCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${foodMenuCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setFoodMenuCurrentPage(page)}>{page}</Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodMenuCurrentPage(Math.min(foodMenuTotalPages, foodMenuCurrentPage + 1))} disabled={foodMenuCurrentPage === foodMenuTotalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFoodMenuCurrentPage(foodMenuTotalPages)} disabled={foodMenuCurrentPage === foodMenuTotalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );

    const renderFacilityMaintenanceTab = () => (
        <div className="space-y-4">
            {/* Sub-tabs for Facility Maintenance */}
            <div className="flex gap-2">
                <button
                    onClick={() => setFacilityMaintenanceSubTab("facility-services")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${facilityMaintenanceSubTab === "facility-services"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"}`}
                >
                    Facility Services
                </button>
                <button
                    onClick={() => setFacilityMaintenanceSubTab("facility-services-type")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${facilityMaintenanceSubTab === "facility-services-type"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"}`}
                >
                    Facility Services Type
                </button>
            </div>

            {facilityMaintenanceSubTab === "facility-services" ? (
                <div className="space-y-6">
                    {/* Facility Services Form */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="max-w-2xl mx-auto space-y-4">
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">
                                        Facility Service<span className="text-red-500">*</span>
                                    </Label>
                                    <MultiSelectDropdown
                                        options={facilityServicesOptions}
                                        selectedValues={selectedFacilityServices}
                                        onChange={setSelectedFacilityServices}
                                        placeholder="Select Facility Services"
                                    />
                                </div>
                                <div className="flex justify-center mt-6">
                                    <Button onClick={handleFacilityServicesSubmit} className="bg-cyan-600 hover:bg-cyan-700 text-foreground px-8">
                                        Submit
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Facility Services Table */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={facilityServicesEntriesPerPage} onValueChange={setFacilityServicesEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground"><SelectValue /></SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="10">10</SelectItem>
                                            <SelectItem value="25">25</SelectItem>
                                            <SelectItem value="50">50</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <span className="text-muted-foreground text-sm">entries</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Search:</span>
                                    <Input placeholder="Service category" value={facilityServicesSearch} onChange={(e) => setFacilityServicesSearch(e.target.value)} className="w-48 h-9 bg-muted/30 border-border/50 text-foreground" />
                                </div>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-gray-200">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gradient-to-r from-[#4a4a4a] to-[#5a5a5a]">
                                            <TableHead className="text-gray-600 font-medium text-center">Facility Service</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedFacilityServicesData.map((item, index) => (
                                            <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background`}>
                                                <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">{item.facilityService}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <div className="flex items-center justify-between mt-6">
                                <span className="text-muted-foreground text-sm">Showing {facilityServicesStartIndex + 1} to {Math.min(facilityServicesEndIndex, filteredFacilityServicesData.length)} of {filteredFacilityServicesData.length} entries</span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesCurrentPage(1)} disabled={facilityServicesCurrentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesCurrentPage(Math.max(1, facilityServicesCurrentPage - 1))} disabled={facilityServicesCurrentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(3, facilityServicesTotalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={facilityServicesCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${facilityServicesCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setFacilityServicesCurrentPage(page)}>{page}</Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesCurrentPage(Math.min(facilityServicesTotalPages, facilityServicesCurrentPage + 1))} disabled={facilityServicesCurrentPage === facilityServicesTotalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesCurrentPage(facilityServicesTotalPages)} disabled={facilityServicesCurrentPage === facilityServicesTotalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Create Services Type Form */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <h2 className="text-lg font-semibold mb-6">Create Services Type</h2>
                            <div className="max-w-2xl mx-auto space-y-4">
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">Facility service<span className="text-red-500">*</span></Label>
                                    <Select value={selectedFacilityServiceForType} onValueChange={setSelectedFacilityServiceForType}>
                                        <SelectTrigger className="bg-muted/30 border-border/50 text-foreground"><SelectValue placeholder="Select Facility service" /></SelectTrigger>
                                        <SelectContent className="bg-white">
                                            {facilityServicesData.map(item => (<SelectItem key={item.id} value={item.facilityService}>{item.facilityService}</SelectItem>))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">Services Type<span className="text-red-500">*</span></Label>
                                    <Input placeholder="Enter Type of Services" value={servicesType} onChange={(e) => setServicesType(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                </div>
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">Estimate time (in minutes)<span className="text-red-500">*</span></Label>
                                    <Input placeholder="Enter Estimated time in minutes" value={estimateTime} onChange={(e) => setEstimateTime(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                </div>
                                <div className="flex justify-center gap-4 mt-6 pt-6 border-t border-border/30">
                                    <Button onClick={handleFacilityServicesTypeReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
                                    <Button onClick={handleFacilityServicesTypeSubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Submit</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Facility Services Type Table */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={facilityServicesTypeEntriesPerPage} onValueChange={setFacilityServicesTypeEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground"><SelectValue /></SelectTrigger>
                                        <SelectContent className="bg-popover"><SelectItem value="10">10</SelectItem><SelectItem value="25">25</SelectItem><SelectItem value="50">50</SelectItem></SelectContent>
                                    </Select>
                                    <span className="text-muted-foreground text-sm">entries</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Search:</span>
                                    <Input placeholder="Services Type" value={facilityServicesTypeSearch} onChange={(e) => setFacilityServicesTypeSearch(e.target.value)} className="w-48 h-9 bg-muted/30 border-border/50 text-foreground" />
                                </div>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-gray-200">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                            <TableHead className="text-gray-600 font-medium">Services Type ▲</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Estimate time (in minutes)</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedFacilityServicesTypeData.map((item, index) => (
                                            <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}>
                                                <TableCell className="text-cyan-600 hover:underline cursor-pointer">{item.typeOfService}</TableCell>
                                                <TableCell>30</TableCell>
                                                <TableCell className="text-center">
                                                    <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFacilityServiceOpen(true)}>
                                                        <Edit className="h-[14px] w-[14px]" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <div className="flex items-center justify-between mt-6">
                                <span className="text-muted-foreground text-sm">Showing {facilityServicesTypeStartIndex + 1} to {Math.min(facilityServicesTypeEndIndex, filteredFacilityServicesTypeData.length)} of {filteredFacilityServicesTypeData.length} entries</span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesTypeCurrentPage(1)} disabled={facilityServicesTypeCurrentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesTypeCurrentPage(Math.max(1, facilityServicesTypeCurrentPage - 1))} disabled={facilityServicesTypeCurrentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(3, facilityServicesTypeTotalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={facilityServicesTypeCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${facilityServicesTypeCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setFacilityServicesTypeCurrentPage(page)}>{page}</Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesTypeCurrentPage(Math.min(facilityServicesTypeTotalPages, facilityServicesTypeCurrentPage + 1))} disabled={facilityServicesTypeCurrentPage === facilityServicesTypeTotalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFacilityServicesTypeCurrentPage(facilityServicesTypeTotalPages)} disabled={facilityServicesTypeCurrentPage === facilityServicesTypeTotalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );

    const renderHealthFitnessTab = () => (
        <div className="space-y-6">
            {/* Health & Fitness Form */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="max-w-2xl mx-auto space-y-4">
                        <div className="grid grid-cols-2 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">
                                Health & Fitness Menu<span className="text-red-500">*</span>
                            </Label>
                            <MultiSelectDropdown
                                options={healthFitnessMenuOptions}
                                selectedValues={selectedHealthFitnessMenus}
                                onChange={setSelectedHealthFitnessMenus}
                                placeholder="Select Health & Fitness Menu"
                            />
                        </div>
                        <div className="flex justify-center mt-6">
                            <Button onClick={handleHealthFitnessSubmit} className="bg-cyan-600 hover:bg-cyan-700 text-foreground px-8">
                                Submit
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Health & Fitness Table */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={healthFitnessEntriesPerPage} onValueChange={setHealthFitnessEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground"><SelectValue /></SelectTrigger>
                                <SelectContent className="bg-white">
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
                                placeholder="Health & fitness menu"
                                value={healthFitnessSearch}
                                onChange={(e) => setHealthFitnessSearch(e.target.value)}
                                className="w-48 h-9 bg-muted/30 border-border/50 text-foreground"
                            />
                        </div>
                    </div>
                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gradient-to-r from-[#4a4a4a] to-[#5a5a5a]">
                                    <TableHead className="text-gray-600 font-medium text-center">Health and Fitness</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedHealthFitnessData.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background`}>
                                        <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">{item.healthFitness}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing {healthFitnessStartIndex + 1} to {Math.min(healthFitnessEndIndex, filteredHealthFitnessData.length)} of {filteredHealthFitnessData.length} entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setHealthFitnessCurrentPage(1)} disabled={healthFitnessCurrentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setHealthFitnessCurrentPage(Math.max(1, healthFitnessCurrentPage - 1))} disabled={healthFitnessCurrentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(3, healthFitnessTotalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={healthFitnessCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${healthFitnessCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setHealthFitnessCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setHealthFitnessCurrentPage(Math.min(healthFitnessTotalPages, healthFitnessCurrentPage + 1))} disabled={healthFitnessCurrentPage === healthFitnessTotalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setHealthFitnessCurrentPage(healthFitnessTotalPages)} disabled={healthFitnessCurrentPage === healthFitnessTotalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderSanitationMaintenanceTab = () => (
        <div className="space-y-4">
            {/* Sub-tabs for Sanitation Maintenance */}
            <div className="flex gap-2">
                <button
                    onClick={() => setSanitationMaintenanceSubTab("sanitation-services")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${sanitationMaintenanceSubTab === "sanitation-services"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"}`}
                >
                    Sanitation Services
                </button>
                <button
                    onClick={() => setSanitationMaintenanceSubTab("sanitation-services-type")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${sanitationMaintenanceSubTab === "sanitation-services-type"
                        ? "bg-white text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"}`}
                >
                    Sanitation Services Type
                </button>
            </div>

            {sanitationMaintenanceSubTab === "sanitation-services" ? (
                <div className="space-y-6">
                    {/* Sanitation Services Form */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="max-w-2xl mx-auto space-y-4">
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">
                                        Sanitation Service<span className="text-red-500">*</span>
                                    </Label>
                                    <MultiSelectDropdown
                                        options={sanitationServicesOptions}
                                        selectedValues={selectedSanitationServices}
                                        onChange={setSelectedSanitationServices}
                                        placeholder="Select Sanitation Services"
                                    />
                                </div>
                                <div className="flex justify-center mt-6">
                                    <Button onClick={handleSanitationServicesSubmit} className="bg-cyan-600 hover:bg-cyan-700 text-foreground px-8">
                                        Submit
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Sanitation Services Table */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={sanitationServicesEntriesPerPage} onValueChange={setSanitationServicesEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground"><SelectValue /></SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="10">10</SelectItem>
                                            <SelectItem value="25">25</SelectItem>
                                            <SelectItem value="50">50</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <span className="text-muted-foreground text-sm">entries</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Search:</span>
                                    <Input placeholder="Service category" value={sanitationServicesSearch} onChange={(e) => setSanitationServicesSearch(e.target.value)} className="w-48 h-9 bg-muted/30 border-border/50 text-foreground" />
                                </div>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-gray-200">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gradient-to-r from-[#4a4a4a] to-[#5a5a5a]">
                                            <TableHead className="text-gray-600 font-medium text-center">Sanitation Services</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedSanitationServicesData.map((item, index) => (
                                            <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background`}>
                                                <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">{item.sanitationService}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <div className="flex items-center justify-between mt-6">
                                <span className="text-muted-foreground text-sm">Showing {sanitationServicesStartIndex + 1} to {Math.min(sanitationServicesEndIndex, filteredSanitationServicesData.length)} of {filteredSanitationServicesData.length} entries</span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesCurrentPage(1)} disabled={sanitationServicesCurrentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesCurrentPage(Math.max(1, sanitationServicesCurrentPage - 1))} disabled={sanitationServicesCurrentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(3, sanitationServicesTotalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={sanitationServicesCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${sanitationServicesCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setSanitationServicesCurrentPage(page)}>{page}</Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesCurrentPage(Math.min(sanitationServicesTotalPages, sanitationServicesCurrentPage + 1))} disabled={sanitationServicesCurrentPage === sanitationServicesTotalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesCurrentPage(sanitationServicesTotalPages)} disabled={sanitationServicesCurrentPage === sanitationServicesTotalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Create Services Type Form */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <h2 className="text-lg font-semibold mb-6">Create Services Type</h2>
                            <div className="max-w-2xl mx-auto space-y-4">
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">Sanitation service<span className="text-red-500">*</span></Label>
                                    <Select value={selectedSanitationServiceForType} onValueChange={setSelectedSanitationServiceForType}>
                                        <SelectTrigger className="bg-muted/30 border-border/50 text-foreground"><SelectValue placeholder="Select Sanitation Services" /></SelectTrigger>
                                        <SelectContent className="bg-white">
                                            {/* value is the `service_category.id` UUID -- it becomes
                                                `category_id` on POST /service-items. The label stays the
                                                service name. Sending the name here was what made submit
                                                fail its UUID validation. */}
                                            {sanitationServicesData.map(item => (<SelectItem key={item.id} value={item.id}>{item.sanitationService}</SelectItem>))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">Services Type<span className="text-red-500">*</span></Label>
                                    <Input placeholder="Enter Type of Services" value={sanitationServicesType} onChange={(e) => setSanitationServicesType(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                </div>
                                <div className="grid grid-cols-2 gap-4 items-center">
                                    <Label className="text-sm font-medium text-right">Estimate time (in minutes)<span className="text-red-500">*</span></Label>
                                    <Input placeholder="Enter Estimated time in minutes" value={sanitationEstimateTime} onChange={(e) => setSanitationEstimateTime(e.target.value)} className="bg-muted/30 border-border/50 text-foreground" />
                                </div>
                                <div className="flex justify-center gap-4 mt-6 pt-6 border-t border-border/30">
                                    <Button onClick={handleSanitationServicesTypeReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
                                    <Button onClick={handleSanitationServicesTypeSubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Submit</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Sanitation Services Type Table */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={sanitationServicesTypeEntriesPerPage} onValueChange={setSanitationServicesTypeEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 text-foreground"><SelectValue /></SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="10">10</SelectItem>
                                            <SelectItem value="25">25</SelectItem>
                                            <SelectItem value="50">50</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <span className="text-muted-foreground text-sm">entries</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Search:</span>
                                    <Input placeholder="Service category, Type of service" value={sanitationServicesTypeSearch} onChange={(e) => setSanitationServicesTypeSearch(e.target.value)} className="w-64 h-9 bg-muted/30 border-border/50 text-foreground" />
                                </div>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-gray-200">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gradient-to-r from-[#4a4a4a] to-[#5a5a5a]">
                                            <TableHead className="text-gray-600 font-medium text-center">Sanitation Services</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Type of Services</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedSanitationServicesTypeData.map((item, index) => (
                                            <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"} hover:bg-background`}>
                                                <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">{item.sanitationService}</TableCell>
                                                <TableCell className="text-cyan-600 hover:underline text-center cursor-pointer">{item.typeOfService}</TableCell>
                                                <TableCell className="text-center">
                                                    <div className="flex justify-center gap-2">
                                                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditSanitationServiceOpen(true)}>
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
                                <span className="text-muted-foreground text-sm">Showing {sanitationServicesTypeStartIndex + 1} to {Math.min(sanitationServicesTypeEndIndex, filteredSanitationServicesTypeData.length)} of {filteredSanitationServicesTypeData.length} entries</span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesTypeCurrentPage(1)} disabled={sanitationServicesTypeCurrentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesTypeCurrentPage(Math.max(1, sanitationServicesTypeCurrentPage - 1))} disabled={sanitationServicesTypeCurrentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(3, sanitationServicesTypeTotalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={sanitationServicesTypeCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${sanitationServicesTypeCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setSanitationServicesTypeCurrentPage(page)}>{page}</Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesTypeCurrentPage(Math.min(sanitationServicesTypeTotalPages, sanitationServicesTypeCurrentPage + 1))} disabled={sanitationServicesTypeCurrentPage === sanitationServicesTypeTotalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setSanitationServicesTypeCurrentPage(sanitationServicesTypeTotalPages)} disabled={sanitationServicesTypeCurrentPage === sanitationServicesTypeTotalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );

    const renderPlaceholderTab = (tabName: string) => (
        <Card className="border-0 shadow-lg rounded-2xl bg-white">
            <CardContent className="p-12 text-center">
                <p className="text-muted-foreground text-lg">{tabName} content coming soon...</p>
            </CardContent>
        </Card>
    );

    const renderTabContent = () => {
        switch (activeTab) {
            case "room-service":
                return renderRoomServiceTab();
            case "travel-desk":
                return renderTravelDeskTab();
            case "business-center":
                return renderBusinessCenterTab();
            case "food-order":
                return renderFoodOrderTab();
            case "facility-maintenance":
                return renderFacilityMaintenanceTab();
            case "health-fitness":
                return renderHealthFitnessTab();
            case "sanitation-maintenance":
                return renderSanitationMaintenanceTab();
            default:
                return null;
        }
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Page Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Services</h1>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-6 border-b border-border dark:border-slate-800">
                <div className="flex flex-wrap gap-6">
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
            </div>

            {/* Tab Content. One boundary for the whole screen: the three
                catalogue queries feed every tab. */}
            <DataState
                isLoading={setupIsLoading}
                error={setupError}
                loader={<TableLoading columns={6} />}
            >
                {renderTabContent()}
            </DataState>

            {/* Edit Food Category Modal */}
            <Dialog open={editFoodCategoryOpen} onOpenChange={setEditFoodCategoryOpen}>
                <DialogContent className="max-w-[450px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Food Category</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditFoodCategoryOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-7">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Food Category <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="Curry"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditFoodCategoryOpen(false)}>Reset</Button>
                        <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditFoodCategoryOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Service Menu Modal */}
            <Dialog open={editSanitationServiceOpen} onOpenChange={setEditSanitationServiceOpen}>
                <DialogContent className="max-w-[500px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Service Menu</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditSanitationServiceOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-12 space-y-7">
                        <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Sanitation service <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Sanitation</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Services Type <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="Guest Room sanitation"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Estimate time <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="1"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditSanitationServiceOpen(false)}>Reset</Button>
                        <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditSanitationServiceOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Food Menu Modal */}
            <Dialog open={editFoodMenuOpen} onOpenChange={setEditFoodMenuOpen}>
                <DialogContent className="max-w-[600px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Food Menu</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditFoodMenuOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-12 space-y-6">
                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800 text-left">Food Category <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Dessert</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800 text-left">Food Menu <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="Brownie"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-start gap-4 h-24">
                            <Label className="text-sm font-medium text-gray-800 text-left pt-2">Description <span className="text-red-500">*</span></Label>
                            <textarea
                                defaultValue="2 Brownies"
                                className="w-full h-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none resize-none pt-2"
                            />
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4 pt-4">
                            <Label className="text-sm font-medium text-gray-800 text-left">Veg/Nonveg <span className="text-red-500">*</span></Label>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input type="radio" name="veg-type" defaultChecked className="h-4 w-4 border-gray-300 text-cyan-600 focus:ring-cyan-600" /> Veg
                                </label>
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input type="radio" name="veg-type" className="h-4 w-4 border-gray-300 text-cyan-600 focus:ring-cyan-600" /> Non Veg
                                </label>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800 text-left">Spicy <span className="text-red-500">*</span></Label>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input type="radio" name="spicy" className="h-4 w-4 border-gray-300 text-cyan-600 focus:ring-cyan-600" /> Yes
                                </label>
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input type="radio" name="spicy" defaultChecked className="h-4 w-4 border-gray-300 text-cyan-600 focus:ring-cyan-600" /> No
                                </label>
                            </div>
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800 text-left">Price <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="200" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[140px_1fr] items-center gap-4 pt-2">
                            <Label className="text-sm font-medium text-gray-800 text-left">Food Image</Label>
                            <div className="space-y-3">
                                <div className="flex items-center border-b border-gray-300 pb-1">
                                    <Button variant="outline" className="h-7 px-3 bg-gray-100 text-gray-700 text-xs border border-gray-300 rounded-[2px]">Choose file</Button>
                                    <span className="ml-3 text-xs text-gray-400">No file chosen</span>
                                </div>
                                <div className="text-[#3eb1c8] text-xs cursor-pointer hover:underline">Click here for previous image</div>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8 mt-2">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditFoodMenuOpen(false)}>Reset</Button>
                        <Button className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all" onClick={() => setEditFoodMenuOpen(false)}>Submit</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default ServicesSetup;













