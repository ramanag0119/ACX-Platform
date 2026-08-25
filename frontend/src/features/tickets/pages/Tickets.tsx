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
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Pencil } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DataState, TableLoading } from "@/core/components/DataState";
import {
  useRooms,
  useServiceRequests,
  useServiceTypes,
  useUsers,
} from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useServiceCategories } from "@/lib/api/hooks";
import {
  useCancelServiceRequest,
  useCreateServiceRequest,
  useUpdateServiceRequest,
} from "@/lib/api/mutations";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  ServiceRequestActionsDialog,
  type ServiceRequestActionTarget,
} from "@/features/services/components/ServiceRequestActionsDialog";

/**
 * Tickets, connected to the Phase 2.5 service APIs.
 *
 *   Table          -> GET /service-requests
 *   Room picker    -> GET /rooms
 *   Service types  -> GET /service-types
 *   Assignee/dept  -> GET /users (staff only; departments ride along on users)
 *
 * A "ticket" here is a `service_request` row: the schema has no separate
 * ticket table. The Quantity column lives on the request's ITEMS, which only
 * GET /service-requests/{id} returns, so it shows "-" in the list.
 *
 * Note on RBAC: this route is guarded with the `tickets` module (its nav
 * entry), while the backend gates /service-requests on `service_tracking`. A
 * role holding one but not the other will see the screen answer 403 through
 * the shared error state -- the backend stays authoritative.
 *
 * The create form is display-only: raising a request needs a write endpoint.
 */

const Tickets = () => {
  // --- Live data -----------------------------------------------------------
  const requestsQuery = useServiceRequests({ page: 1, page_size: MAX_PAGE_SIZE });
  const roomsQuery = useRooms({ page: 1, page_size: MAX_PAGE_SIZE });
  const serviceTypesQuery = useServiceTypes({ page: 1, page_size: MAX_PAGE_SIZE });
  const usersQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 });

  const roomNumbers = (roomsQuery.data?.items ?? []).map((room) => room.name);
  const serviceTypes = (serviceTypesQuery.data?.items ?? []).map((type) => ({
    value: String(type.id),
    label: type.name,
  }));
  const staffUsers = usersQuery.data?.items ?? [];
  const departments = [
    ...new Map(
      staffUsers
        .filter((user) => user.department_id && user.department_name)
        .map((user) => [user.department_id as string, {
          value: user.department_id as string,
          label: user.department_name as string,
        }]),
    ).values(),
  ].sort((a, b) => a.label.localeCompare(b.label));
  const staffMembers = staffUsers.map((user) => ({
    value: user.id,
    label: [user.first_name, user.last_name].filter(Boolean).join(" "),
  }));

  const categoriesQuery = useServiceCategories({ page: 1, page_size: MAX_PAGE_SIZE });
  const serviceCategories = categoriesQuery.data?.items ?? [];

  // --- Mutations
  const { canWrite } = useAuth();
  const mayWrite = canWrite("service_tracking");
  const createRequest = useCreateServiceRequest();
  const updateRequest = useUpdateServiceRequest();
  const cancelRequest = useCancelServiceRequest();
  const [actionTarget, setActionTarget] = useState<ServiceRequestActionTarget | null>(null);

  const ticketsData = (requestsQuery.data?.items ?? []).map((request) => ({
    id: request.id,
    serviceType: request.service_type_name ?? "-",
    serviceCategory: request.category_name ?? "-",
    serviceRequest: request.ref_number ?? "-",
    // Quantity is per ITEM and only the detail endpoint returns items.
    quantity: "-" as string | number,
    roomNo: request.amenity_name ?? "-",
    department: request.department_name ?? "-",
    assignTo: request.assignee?.name ?? "-",
    date: new Date(request.created_on).toLocaleDateString(),
    time: new Date(request.created_on).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    description: request.description ?? "",
    status: request.status_name ?? "-",
    statusId: request.status ?? null,
    assignedToId: request.assignee?.id ?? null,
  }));

  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  // Form state
  const [roomNo, setRoomNo] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [department, setDepartment] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [date, setDate] = useState("");
  const [timeHour, setTimeHour] = useState("");
  const [timeMinute, setTimeMinute] = useState("");
  const [timePeriod, setTimePeriod] = useState("AM");
  const [description, setDescription] = useState("");

  // Validation state
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {};
    if (!roomNo) newErrors.roomNo = "Room No is Required";
    if (!serviceType) newErrors.serviceType = "Service type is Required.";
    if (!department) newErrors.department = "Department is Required";
    if (!assignTo) newErrors.assignTo = "Assign to is Required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Raise a real service request.
   *
   * `service_type` and the room are what the schema requires; naming an
   * assignee moves the request straight to Assigned, which is the invariant
   * every seeded row with an assignee holds. The expected date is assembled
   * from the existing date + HH/MM/AM-PM controls.
   */
  const handleSubmit = () => {
    if (!validateForm()) return;

    const expected = (() => {
      if (!date) return null;
      const hour = Number(timeHour || "0") % 12 + (timePeriod === "PM" ? 12 : 0);
      const minute = Number(timeMinute || "0");
      const when = new Date(date);
      when.setHours(hour, minute, 0, 0);
      return when.toISOString();
    })();

    const room = (roomsQuery.data?.items ?? []).find((item) => item.name === roomNo);

    createRequest.mutate(
      {
        service_type: Number(serviceType),
        ...(room ? { amenity_id: room.id } : {}),
        ...(department ? { department_id: department } : {}),
        ...(assignTo ? { assigned_to: assignTo } : {}),
        ...(description ? { description } : {}),
        ...(expected ? { expected_date: expected } : {}),
      },
      { onSuccess: handleReset },
    );
  };

  const handleReset = () => {
    setRoomNo("");
    setServiceType("");
    setDepartment("");
    setAssignTo("");
    setDate("");
    setTimeHour("");
    setTimeMinute("");
    setTimePeriod("AM");
    setDescription("");
    setErrors({});
  };

  const filteredTickets = ticketsData.filter(ticket =>
    ticket.roomNo.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ticket.assignTo.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ticket.serviceType.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    if (status === "Completed") {
      return <Badge className="bg-green-500 text-white hover:bg-green-600">{status}</Badge>;
    }
    return <Badge className="bg-amber-500 text-white hover:bg-amber-600">{status}</Badge>;
  };

  return (
    <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Ticket Management</h1>
      </div>

      {/* Add Ticket Form */}
      <Card className="border-0 shadow-lg rounded-2xl bg-white">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
            {/* Room No */}
            <div className="flex items-center gap-4">
              <Label className="w-32 text-right shrink-0">Room No<span className="text-red-500">*</span></Label>
              <div className="flex-1">
                <Select value={roomNo} onValueChange={setRoomNo}>
                  <SelectTrigger className={`bg-muted/30 border-border/50 ${errors.roomNo ? 'border-red-500' : ''}`}>
                    <SelectValue placeholder="Select Room No" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {roomNumbers.map((room) => (
                      <SelectItem key={room} value={room}>{room}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.roomNo && <p className="text-red-500 text-xs mt-1">{errors.roomNo}</p>}
              </div>
            </div>

            {/* Empty space for alignment */}
            <div></div>

            {/* Service Type */}
            <div className="flex items-center gap-4">
              <Label className="w-32 text-right shrink-0">Service Type<span className="text-red-500">*</span></Label>
              <div className="flex-1">
                <Select value={serviceType} onValueChange={setServiceType}>
                  <SelectTrigger className={`bg-muted/30 border-border/50 ${errors.serviceType ? 'border-red-500' : ''}`}>
                    <SelectValue placeholder="Select Service Type" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {serviceTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.serviceType && <p className="text-red-500 text-xs mt-1">{errors.serviceType}</p>}
              </div>
            </div>

            {/* Empty space for alignment */}
            <div></div>

            {/* Department */}
            <div className="flex items-center gap-4">
              <Label className="w-32 text-right shrink-0">Department<span className="text-red-500">*</span></Label>
              <div className="flex-1">
                <Select value={department} onValueChange={setDepartment}>
                  <SelectTrigger className={`bg-muted/30 border-border/50 ${errors.department ? 'border-red-500' : ''}`}>
                    <SelectValue placeholder="Select Department" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {departments.map((dept) => (
                      <SelectItem key={dept.value} value={dept.value}>{dept.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.department && <p className="text-red-500 text-xs mt-1">{errors.department}</p>}
              </div>
            </div>

            {/* Empty space for alignment */}
            <div></div>

            {/* Assign To */}
            <div className="flex items-center gap-4">
              <Label className="w-32 text-right shrink-0">Assign to<span className="text-red-500">*</span></Label>
              <div className="flex-1">
                <Select value={assignTo} onValueChange={setAssignTo}>
                  <SelectTrigger className={`bg-muted/30 border-border/50 ${errors.assignTo ? 'border-red-500' : ''}`}>
                    <SelectValue placeholder="Select Assign to" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {staffMembers.map((staff) => (
                      <SelectItem key={staff.value} value={staff.value}>{staff.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.assignTo && <p className="text-red-500 text-xs mt-1">{errors.assignTo}</p>}
              </div>
            </div>

            {/* Empty space for alignment */}
            <div></div>

            {/* Date */}
            <div className="flex items-center gap-4">
              <Label className="w-32 text-right shrink-0">Date<span className="text-red-500">*</span></Label>
              <div className="flex-1">
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="bg-muted/30 border-border/50" placeholder="dd-mm-yyyy" />
              </div>
            </div>

            {/* Empty space for alignment */}
            <div></div>

            {/* Time */}
            <div className="flex items-center gap-4">
              <Label className="w-32 text-right shrink-0">Time<span className="text-red-500">*</span></Label>
              <div className="flex-1 flex gap-2">
                <Select value={timeHour} onValueChange={setTimeHour}>
                  <SelectTrigger className="w-20 bg-muted/30 border-border/50">
                    <SelectValue placeholder="HH" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')).map((h) => (
                      <SelectItem key={h} value={h}>{h}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={timeMinute} onValueChange={setTimeMinute}>
                  <SelectTrigger className="w-20 bg-muted/30 border-border/50">
                    <SelectValue placeholder="MM" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    {Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0')).map((m) => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={timePeriod} onValueChange={setTimePeriod}>
                  <SelectTrigger className="w-20 bg-muted/30 border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    <SelectItem value="AM">AM</SelectItem>
                    <SelectItem value="PM">PM</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Empty space for alignment */}
            <div></div>

            {/* Description */}
            <div className="flex items-start gap-4 md:col-span-2">
              <Label className="w-32 text-right shrink-0 pt-2">Description</Label>
              <div className="flex-1">
                <Textarea
                  placeholder="Enter Description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="bg-muted/30 border-border/50 min-h-[100px]"
                />
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex justify-center gap-4 mt-8">
            <Button variant="outline" onClick={handleReset} className="px-8 border-cyan-500 text-cyan-600 hover:bg-cyan-50">Reset</Button>
            <Button onClick={handleSubmit} className="px-8 bg-cyan-600 hover:bg-cyan-700 text-white">Submit</Button>
          </div>
        </CardContent>
      </Card>

      {/* Tickets Table */}
      <Card className="border-0 shadow-xl">
        <CardContent className="p-6">
          {/* Table Controls */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Show</span>
              <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover text-popover-foreground border-border">
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
                placeholder="Room no, Assign to"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64 h-9 bg-muted/30 border-border/50"
              />
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[140px]">Service Type ↕</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[150px]">Service Category ↕</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[150px]">Service Request ↕</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[90px] text-center">Quantity</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[100px] text-center">Room No ↕</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[130px]">Department</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[140px]">Assign to ↕</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[110px] text-center">Date ↓</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[90px] text-center">Time</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[180px]">Description</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[120px] text-center">Status</TableHead>
                  <TableHead className="text-gray-600 font-medium whitespace-nowrap min-w-[80px] text-center">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(requestsQuery.isLoading || requestsQuery.error || filteredTickets.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={12} className="py-2">
                      <DataState
                        isLoading={requestsQuery.isLoading}
                        error={requestsQuery.error}
                        isEmpty
                        emptyTitle="No tickets found"
                        loader={<TableLoading columns={11} />}
                      >
                        <span />
                      </DataState>
                    </TableCell>
                  </TableRow>
                )}
                {filteredTickets.map((ticket, index) => (
                  <TableRow key={ticket.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                    <TableCell className="text-cyan-600 whitespace-nowrap">{ticket.serviceType}</TableCell>
                    <TableCell className="whitespace-nowrap">{ticket.serviceCategory}</TableCell>
                    <TableCell className={ticket.serviceRequest === "Items" ? "text-amber-500" : "text-cyan-600"}>{ticket.serviceRequest}</TableCell>
                    <TableCell className="text-center">{ticket.quantity}</TableCell>
                    <TableCell className="text-center">{ticket.roomNo}</TableCell>
                    <TableCell className="whitespace-nowrap">{ticket.department}</TableCell>
                    <TableCell className="text-cyan-600 whitespace-nowrap">{ticket.assignTo}</TableCell>
                    <TableCell className="whitespace-nowrap text-center">{ticket.date}</TableCell>
                    <TableCell className="text-center">{ticket.time}</TableCell>
                    <TableCell className="max-w-[200px] truncate">{ticket.description || "-"}</TableCell>
                    <TableCell className="text-center">{getStatusBadge(ticket.status)}</TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="bg-cyan-600 hover:bg-cyan-700 h-7 w-7 p-0"
                        disabled={!mayWrite}
                        onClick={() =>
                          setActionTarget({
                            id: ticket.id,
                            ref: ticket.serviceRequest,
                            statusId: ticket.statusId,
                            assignedToId: ticket.assignedToId,
                          })
                        }
                        title={
                          mayWrite
                            ? "Assign, change status or cancel"
                            : "Your role cannot change service requests"
                        }
                      >
                        <Pencil className="h-3 w-3 text-white" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6">
            <span className="text-muted-foreground text-sm">Showing 1 to 10 of 52 entries</span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" className="text-muted-foreground">First</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground">Previous</Button>
              <Button size="sm" className="w-9 h-9 p-0 bg-cyan-600 text-white">1</Button>
              <Button variant="ghost" size="sm" className="w-9 h-9 p-0 text-muted-foreground">2</Button>
              <Button variant="ghost" size="sm" className="w-9 h-9 p-0 text-muted-foreground">3</Button>
              <Button variant="ghost" size="sm" className="w-9 h-9 p-0 text-muted-foreground">4</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground">Next</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground">Last</Button>
            </div>
          </div>
        </CardContent>
      </Card>
      <ServiceRequestActionsDialog
        open={Boolean(actionTarget)}
        onClose={() => setActionTarget(null)}
        target={actionTarget}
        canWrite={mayWrite}
      />
    </div>
  );
};

export default Tickets;
