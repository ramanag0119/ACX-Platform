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
import { Card, CardContent } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Pencil, Trash2, Hourglass } from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { describeApiError } from "@/lib/api/client";
import { useOffers, useRooms } from "@/lib/api/hooks";
import { useCreateOffer, useUpdateOffer } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

// Sample Offers Data
/**
 * Offers, connected to GET/POST/PATCH /offers.
 *
 * An offer IS a `promo_code` row, and the rooms it applies to are
 * `promo_code_amenity` rows -- which is why "Applicable To" lists room names.
 * `discount_percentage`, `max_discount_value` and `min_order_value` are all real
 * columns; there is no separate discount engine.
 */

const Offers = () => {
    const offersQuery = useOffers({ page: 1, page_size: MAX_PAGE_SIZE });
    const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
    const { canWrite } = useAuth();
    const mayWrite = canWrite("offers");
    const createOffer = useCreateOffer();
    const updateOffer = useUpdateOffer();

    const offersData = (offersQuery.data?.items ?? []).map((offer) => ({
        id: offer.id,
        offerName: offer.offer_name ?? "-",
        applicableTo: offer.room_names.join(", ") || "All rooms",
        couponCode: offer.promo_code,
        couponDescription: offer.promo_code_description ?? "-",
        offerBy: offer.offered_by ?? "-",
        validityFrom: offer.start_time ? new Date(offer.start_time).toLocaleDateString() : "-",
        validityTo: offer.expiry_time ? new Date(offer.expiry_time).toLocaleDateString() : "-",
        image: "-",
        discount: offer.discount_percentage ?? "-",
    }));
    /** One table row. Derived from the mapping above so the two cannot drift. */
    type OfferRow = (typeof offersData)[number];

    const [isModalOpen, setIsModalOpen] = useState(false);
    /** The Add Offer form. Every field maps to a `promo_code` column. */
    const [offerForm, setOfferForm] = useState({
        offerName: "",
        couponCode: "",
        description: "",
        offeredBy: "",
        discount: "",
        validFrom: "",
        validTo: "",
        roomIds: [] as string[],
    });
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    const [selectedItemToDelete, setSelectedItemToDelete] = useState<OfferRow | null>(null);
    const [selectedItemToEdit, setSelectedItemToEdit] = useState<OfferRow | null>(null);
    /** The Edit Offer form, seeded from the selected `promo_code` row. */
    const [editForm, setEditForm] = useState({
        offerName: "",
        couponCode: "",
        description: "",
        offeredBy: "",
        validFrom: "",
        validTo: "",
    });

    const filteredData = offersData.filter(item =>
        item.offerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.couponCode.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, startIndex + parseInt(entriesPerPage));

    /** Toggles a real `amenity.id` on the offer being composed. */
    const handleRoomToggle = (roomId: string) => {
        setOfferForm((prev) => ({
            ...prev,
            roomIds: prev.roomIds.includes(roomId)
                ? prev.roomIds.filter((id) => id !== roomId)
                : [...prev.roomIds, roomId],
        }));
    };

    const handleWithdrawClick = (item: OfferRow) => {
        setSelectedItemToDelete(item);
        setIsDeleteModalOpen(true);
    };

    /** Copy the chosen row into the edit form. `offersData` rows carry the
     *  formatted values shown in the table, so dates are converted back to the
     *  yyyy-mm-dd an <input type="date"> needs. */
    const seedEditForm = (item: OfferRow) => {
        const source = (offersQuery.data?.items ?? []).find((row) => row.id === item.id);
        const toDateInput = (value: string | null | undefined) =>
            value ? new Date(value).toISOString().slice(0, 10) : "";
        setEditForm({
            offerName: source?.offer_name ?? "",
            couponCode: source?.promo_code ?? "",
            description: source?.promo_code_description ?? "",
            offeredBy: source?.offered_by ?? "",
            validFrom: toDateInput(source?.start_time),
            validTo: toDateInput(source?.expiry_time),
        });
    };

    const handleEditClick = (item: OfferRow) => {
        setSelectedItemToEdit(item);
        seedEditForm(item);
        setIsEditModalOpen(true);
    };

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Offers Management</h1>
                <Button onClick={() => setIsModalOpen(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white">Add Offers</Button>
            </div>


            {/* Table Section */}
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                                <SelectContent className="bg-white">
                                    <SelectItem value="10">10</SelectItem>
                                    <SelectItem value="25">25</SelectItem>
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input placeholder="Offer name, Coupon code" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-64 h-9 bg-muted/30 border-border/50" />
                        </div>
                    </div>

                    <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Offer Name ↕</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Applicable To</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Coupon Code ↕</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Coupon Description</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Offer By ↕</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Validity From ↕</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Validity To</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Offer Withdrawal</TableHead>
                                    <TableHead className="text-gray-600 font-medium whitespace-nowrap">Image</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedData.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                        <TableCell className="text-cyan-600 whitespace-nowrap">{item.offerName}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.applicableTo}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.couponCode}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.couponDescription}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.offerBy}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.validityFrom}</TableCell>
                                        <TableCell className="whitespace-nowrap">{item.validityTo}</TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex justify-center">
                                                <Button size="sm" className="h-8 w-8 p-0 bg-[#3eb1c8] hover:bg-[#3eb1c8]/90" onClick={() => handleWithdrawClick(item)}>
                                                    <Hourglass className="h-4 w-4 text-white" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                        <TableCell className="whitespace-nowrap text-center">
                                            {item.image !== "-" ? <span className="text-cyan-600 hover:underline cursor-pointer">{item.image}</span> : "-"}
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex gap-2 justify-center">
                                                <Button size="sm" className="h-8 w-8 p-0 bg-[#f2716b] hover:bg-[#f2716b]/90 rounded-md" onClick={() => handleEditClick(item)}>
                                                    <Pencil className="h-4 w-4 text-white" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing {startIndex + 1} to {Math.min(startIndex + parseInt(entriesPerPage), filteredData.length)} of {filteredData.length} entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${currentPage === page ? "bg-cyan-600 text-white" : ""}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Add Offer Modal */}
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader><DialogTitle>Add New Offer</DialogTitle></DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            {/* Every input binds to `offerForm`, which is what the
                                Submit button below reads. Offer Name previously wrote
                                to an unrelated state and Coupon Code had no binding at
                                all, so `offerForm.couponCode` stayed empty and the
                                button was permanently disabled. */}
                            <div className="space-y-2">
                                <Label>Offer Name<span className="text-red-500">*</span></Label>
                                <Input
                                    placeholder="Enter offer name"
                                    value={offerForm.offerName}
                                    onChange={(e) => setOfferForm((prev) => ({ ...prev, offerName: e.target.value }))}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Coupon Code<span className="text-red-500">*</span></Label>
                                <Input
                                    placeholder="Enter coupon code"
                                    value={offerForm.couponCode}
                                    onChange={(e) => setOfferForm((prev) => ({ ...prev, couponCode: e.target.value }))}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Coupon Description</Label>
                                <Input
                                    placeholder="Enter description"
                                    value={offerForm.description}
                                    onChange={(e) => setOfferForm((prev) => ({ ...prev, description: e.target.value }))}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Offer By</Label>
                                <Input
                                    placeholder="Enter offered by"
                                    value={offerForm.offeredBy}
                                    onChange={(e) => setOfferForm((prev) => ({ ...prev, offeredBy: e.target.value }))}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Discount %</Label>
                            <Input
                                type="number"
                                placeholder="Enter discount percentage"
                                value={offerForm.discount}
                                onChange={(e) => setOfferForm((prev) => ({ ...prev, discount: e.target.value }))}
                                className="bg-muted/30 border-border/50"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Applicable Rooms</Label>
                            {/* Real amenities from GET /rooms. A promo_code applies to
                                `promo_code_amenity` rows, so these are rooms -- not the
                                package names the previous hardcoded list showed. */}
                            <div className="grid grid-cols-3 gap-2 max-h-[180px] overflow-y-auto">
                                {roomsQuery.isLoading && (
                                    <p className="text-sm text-muted-foreground col-span-3">Loading rooms...</p>
                                )}
                                {roomsQuery.error && (
                                    <p className="text-sm text-muted-foreground col-span-3">
                                        {describeApiError(roomsQuery.error)}
                                    </p>
                                )}
                                {(roomsQuery.data?.items ?? []).map((room) => (
                                    <div key={room.id} className="flex items-center space-x-2">
                                        <Checkbox
                                            id={`room-${room.id}`}
                                            checked={offerForm.roomIds.includes(room.id)}
                                            onCheckedChange={() => handleRoomToggle(room.id)}
                                        />
                                        <label htmlFor={`room-${room.id}`} className="text-sm">
                                            {room.name}
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Validity From<span className="text-red-500">*</span></Label>
                                <Input
                                    type="date"
                                    value={offerForm.validFrom}
                                    onChange={(e) => setOfferForm((prev) => ({ ...prev, validFrom: e.target.value }))}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Validity To<span className="text-red-500">*</span></Label>
                                <Input
                                    type="date"
                                    value={offerForm.validTo}
                                    onChange={(e) => setOfferForm((prev) => ({ ...prev, validTo: e.target.value }))}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>
                        <div className="flex justify-center gap-4 pt-4">
                            <Button
                                variant="outline"
                                className="px-8"
                                onClick={() =>
                                    setOfferForm({
                                        offerName: "",
                                        couponCode: "",
                                        description: "",
                                        offeredBy: "",
                                        discount: "",
                                        validFrom: "",
                                        validTo: "",
                                        roomIds: [],
                                    })
                                }
                            >
                                Reset
                            </Button>
                            <Button
                                className="bg-cyan-600 hover:bg-cyan-700 text-white px-8"
                                disabled={!mayWrite || !offerForm.couponCode.trim() || createOffer.isPending}
                                onClick={() =>
                                    createOffer.mutate(
                                        {
                                            promo_code: offerForm.couponCode.trim(),
                                            offer_name: offerForm.offerName || null,
                                            promo_code_description: offerForm.description || null,
                                            offered_by: offerForm.offeredBy || null,
                                            discount_percentage: offerForm.discount || null,
                                            start_time: offerForm.validFrom
                                                ? new Date(offerForm.validFrom).toISOString()
                                                : null,
                                            expiry_time: offerForm.validTo
                                                ? new Date(offerForm.validTo).toISOString()
                                                : null,
                                            amenity_ids: offerForm.roomIds,
                                        },
                                        { onSuccess: () => setIsModalOpen(false) },
                                    )
                                }
                            >
                                {createOffer.isPending ? "Saving..." : "Submit"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Withdraw Modal */}
            <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
                <DialogContent className="max-w-[400px] bg-white border-0 shadow-lg [&>button]:hidden sm:rounded-md p-8">
                    <div className="flex flex-col items-center text-center space-y-4">
                        <div className="w-16 h-16 rounded-full border-[3px] border-[#f8bb86] text-[#f8bb86] flex items-center justify-center text-5xl font-light font-serif">
                            !
                        </div>
                        <h2 className="text-2xl font-semibold text-[#545454]">Are you sure?</h2>
                        <p className="text-[#545454] text-[15px]">You won't be able to revert this!</p>

                        <div className="flex gap-4 pt-4 w-full justify-center">
                            <Button className="bg-[#3085d6] hover:bg-[#3085d6]/90 text-white px-5 rounded-md text-base shadow-md h-11" onClick={() => setIsDeleteModalOpen(false)}>
                                Yes, delete it!
                            </Button>
                            <Button className="bg-[#d33] hover:bg-[#d33]/90 text-white px-5 rounded-md text-base shadow-md h-11" onClick={() => setIsDeleteModalOpen(false)}>
                                Cancel
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Action Modal */}
            <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
                <DialogContent className="max-w-[1000px] w-[90vw] bg-white text-foreground border-gray-200 p-0 overflow-hidden flex flex-col hide-close-button shadow-lg [&>button]:hidden">
                    <div className="flex justify-between items-center p-3 px-6 bg-gray-50 border-b border-gray-200">
                        <h2 className="text-base font-medium text-foreground">Offers Management</h2>
                        <Button variant="destructive" className="bg-[#f2716b] hover:bg-red-500 h-8 px-6 font-normal rounded-md" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
                    </div>

                    <div className="px-10 py-8 space-y-6 overflow-y-auto max-h-[85vh]">
                        {/* Bound to the selected `promo_code` row. Every field in this
                            dialog was hardcoded ("Pooja Offer", "pooja45", rooms
                            101-103) and read-only, and Update had no handler, so the
                            edit could never reach the API. */}
                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Offer Name <span className="text-red-500">*</span></Label>
                            <Input
                                value={editForm.offerName}
                                onChange={(e) => setEditForm((prev) => ({ ...prev, offerName: e.target.value }))}
                                className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center">
                            <Label className="text-sm font-medium text-gray-700">Applicable To <span className="text-red-500">*</span></Label>
                            {/* The offer's real `promo_code_amenity` rooms. */}
                            <div className="border border-gray-300 rounded-sm p-1.5 flex flex-wrap gap-2 items-center bg-white min-h-[36px] max-w-2xl">
                                {selectedItemToEdit?.applicableTo &&
                                selectedItemToEdit.applicableTo !== "All rooms" ? (
                                    selectedItemToEdit.applicableTo
                                        .split(", ")
                                        .map((room: string) => (
                                            <div key={room} className="bg-[#3eb1c8] text-white text-xs px-2 py-0.5 rounded-sm">
                                                {room}
                                            </div>
                                        ))
                                ) : (
                                    <span className="text-xs text-gray-500">All rooms</span>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Coupon Code <span className="text-red-500">*</span></Label>
                            <Input
                                value={editForm.couponCode}
                                onChange={(e) => setEditForm((prev) => ({ ...prev, couponCode: e.target.value }))}
                                className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Coupon Description</Label>
                            <Input
                                value={editForm.description}
                                onChange={(e) => setEditForm((prev) => ({ ...prev, description: e.target.value }))}
                                className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Offer By</Label>
                            <Input
                                value={editForm.offeredBy}
                                onChange={(e) => setEditForm((prev) => ({ ...prev, offeredBy: e.target.value }))}
                                className="bg-transparent border-0 border-b border-gray-300 rounded-none text-foreground focus-visible:ring-0 px-0 h-8 max-w-2xl font-medium"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-4">
                            <Label className="text-sm font-medium text-gray-700">Validity From <span className="text-red-500">*</span></Label>
                            <Input
                                type="date"
                                value={editForm.validFrom}
                                onChange={(e) => setEditForm((prev) => ({ ...prev, validFrom: e.target.value }))}
                                className="bg-white text-foreground border border-gray-300 rounded-sm h-9 max-w-[calc(100%-400px)] px-3 font-medium"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-2">
                            <Label className="text-sm font-medium text-gray-700">Validity To <span className="text-red-500">*</span></Label>
                            <Input
                                type="date"
                                value={editForm.validTo}
                                onChange={(e) => setEditForm((prev) => ({ ...prev, validTo: e.target.value }))}
                                className="bg-white text-foreground border border-gray-300 rounded-sm h-9 max-w-[calc(100%-400px)] px-3 font-medium"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] gap-6 items-center pt-4">
                            <Label className="text-sm font-medium text-gray-700">Image</Label>
                            <div className="flex items-center gap-2 border-b border-gray-300 pb-1 w-full max-w-2xl">
                                <Button size="sm" variant="outline" className="h-7 bg-white text-foreground hover:bg-gray-50 rounded-sm text-xs px-3 font-medium border-gray-300">Choose file</Button>
                                <span className="text-xs text-gray-500">No file chosen</span>
                            </div>
                        </div>

                        <div className="flex justify-center mt-10 gap-4">
                            <Button
                                variant="outline"
                                className="bg-white hover:bg-gray-50 text-gray-600 border-gray-300 h-9 px-8 rounded-sm font-medium transition-colors"
                                onClick={() => selectedItemToEdit && seedEditForm(selectedItemToEdit)}
                            >
                                Reset
                            </Button>
                            <Button
                                className="bg-cyan-600 hover:bg-cyan-700 text-white border-transparent h-9 px-8 rounded-sm font-medium transition-colors"
                                disabled={
                                    !mayWrite ||
                                    !selectedItemToEdit ||
                                    !editForm.couponCode.trim() ||
                                    updateOffer.isPending
                                }
                                onClick={() =>
                                    updateOffer.mutate(
                                        {
                                            id: selectedItemToEdit.id,
                                            body: {
                                                promo_code: editForm.couponCode.trim(),
                                                offer_name: editForm.offerName.trim() || null,
                                                promo_code_description: editForm.description.trim() || null,
                                                offered_by: editForm.offeredBy.trim() || null,
                                                start_time: editForm.validFrom
                                                    ? new Date(editForm.validFrom).toISOString()
                                                    : null,
                                                expiry_time: editForm.validTo
                                                    ? new Date(editForm.validTo).toISOString()
                                                    : null,
                                            },
                                        },
                                        { onSuccess: () => setIsEditModalOpen(false) },
                                    )
                                }
                            >
                                {updateOffer.isPending ? "Updating..." : "Update"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Offers;
