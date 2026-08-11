import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Pencil, Trash2, X, ChevronDown, Edit } from "lucide-react";

// Notification types
const notificationTypes = [
    "booking-confirmation",
    "checkout-initiation",
    "checkout-acception",
    "checkout-confirmation",
    "checkout-reminder",
    "service-request-creation",
    "service-request-assigned",
    "service-request-status-change",
    "maintenance-request-creation",
    "maintenance-request-status-update",
    "checkin-confirmation",
    "checkout-extend",
    "share-default-key",
    "device-not-found",
];

// Sample data for the table
const sampleRoles = [
    { id: 1, userRole: "ASHOK", roleType: "Manager", notifications: "List of notifications subscribed to" },
    { id: 2, userRole: "Floor Manager", roleType: "Manager", notifications: "List of notifications subscribed to" },
    { id: 3, userRole: "food service", roleType: "Staff", notifications: "List of notifications subscribed to" },
    { id: 4, userRole: "Maintenance staff", roleType: "Staff", notifications: "List of notifications subscribed to" },
    { id: 5, userRole: "Manager", roleType: "Manager", notifications: "List of notifications subscribed to" },
    { id: 6, userRole: "manoj", roleType: "Manager", notifications: "List of notifications subscribed to" },
    { id: 7, userRole: "Nisha", roleType: "Staff", notifications: "List of notifications subscribed to" },
    { id: 8, userRole: "priya", roleType: "Manager", notifications: "List of notifications subscribed to" },
    { id: 9, userRole: "Room service", roleType: "Staff", notifications: "List of notifications subscribed to" },
];

// Web Modules data
const webModules = [
    { id: "dashboard", name: "Dashboard", view: true, edit: false },
    { id: "occupancy", name: "Occupancy", view: true, edit: true },
    { id: "bookings", name: "Bookings", view: true, edit: true },
    { id: "services", name: "Services", view: true, edit: false },
    { id: "configuration", name: "Configuration", view: false, edit: false },
    { id: "offers", name: "Offers", view: true, edit: true },
    { id: "holidays", name: "Holidays", view: true, edit: false },
    { id: "events", name: "Events", view: true, edit: true },
    { id: "devices", name: "Device Management", view: true, edit: false },
    { id: "reports", name: "Reports", view: true, edit: false },
    { id: "tickets", name: "Tickets", view: true, edit: true },
];

const UserRoles = () => {
    // Form state
    const [roleType, setRoleType] = useState("");
    const [roleName, setRoleName] = useState("");
    const [selectedNotifications, setSelectedNotifications] = useState<string[]>([]);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    // Table state
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [searchQuery, setSearchQuery] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const [editModalOpen, setEditModalOpen] = useState(false);

    // Web Modules state
    const [selectedRole, setSelectedRole] = useState("");
    const [modulePermissions, setModulePermissions] = useState(webModules);

    const handleNotificationToggle = (notification: string) => {
        setSelectedNotifications(prev =>
            prev.includes(notification)
                ? prev.filter(n => n !== notification)
                : [...prev, notification]
        );
    };

    const handleSelectAll = () => {
        if (selectedNotifications.length === notificationTypes.length) {
            setSelectedNotifications([]);
        } else {
            setSelectedNotifications([...notificationTypes]);
        }
    };

    const handleReset = () => {
        setRoleType("");
        setRoleName("");
        setSelectedNotifications([]);
    };

    const handleSubmit = () => {
        console.log("Submitting:", { roleType, roleName, selectedNotifications });
    };

    // Filter roles
    const filteredRoles = sampleRoles.filter(role =>
        role.userRole.toLowerCase().includes(searchQuery.toLowerCase()) ||
        role.roleType.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Pagination
    const totalEntries = filteredRoles.length;
    const entriesCount = parseInt(entriesPerPage);
    const totalPages = Math.ceil(totalEntries / entriesCount);
    const startIndex = (currentPage - 1) * entriesCount;
    const endIndex = Math.min(startIndex + entriesCount, totalEntries);
    const currentEntries = filteredRoles.slice(startIndex, endIndex);

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Header */}
            <div className="mb-2">
                <h1 className="text-2xl font-semibold text-foreground">User Role Management</h1>
            </div>

            <Tabs defaultValue="user-role" className="w-full">
                <TabsList className="bg-muted/30 p-1 rounded-xl w-fit mb-6">
                    <TabsTrigger value="user-role" className="px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 data-[state=active]:bg-white data-[state=active]:text-foreground data-[state=active]:shadow-sm">
                        User Role
                    </TabsTrigger>
                    <TabsTrigger value="web-modules" className="px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 data-[state=active]:bg-white data-[state=active]:text-foreground data-[state=active]:shadow-sm">
                        Web Modules
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="user-role" className="space-y-6">
                    {/* Form Section */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                                <div className="space-y-2">
                                    <Label htmlFor="role-type" className="text-sm font-medium">Role Type</Label>
                                    <Select value={roleType} onValueChange={setRoleType}>
                                        <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                            <SelectValue placeholder="Select Role type" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-white">
                                            <SelectItem value="staff">Staff</SelectItem>
                                            <SelectItem value="manager">Manager</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="role-name" className="text-sm font-medium">User Role Name</Label>
                                    <Input
                                        id="role-name"
                                        placeholder="Enter User Role Name"
                                        value={roleName}
                                        onChange={(e) => setRoleName(e.target.value)}
                                        className="h-10 bg-muted/30 border-border/50"
                                    />
                                </div>

                                <div className="space-y-2 relative">
                                    <Label className="text-sm font-medium">Select Notification</Label>
                                    <div className="relative">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                            className="w-full h-10 justify-between bg-muted/30 border-border/50 hover:bg-muted/50"
                                        >
                                            <span className="truncate">
                                                {selectedNotifications.length > 0
                                                    ? `${selectedNotifications.length} selected`
                                                    : "Select notifications"}
                                            </span>
                                        </Button>
                                        {isDropdownOpen && (
                                            <div className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-auto">
                                                <div className="flex items-center space-x-2 p-2 border-b bg-muted/20">
                                                    <Checkbox
                                                        id="select-all"
                                                        checked={selectedNotifications.length === notificationTypes.length}
                                                        onCheckedChange={handleSelectAll}
                                                    />
                                                    <label htmlFor="select-all" className="text-sm cursor-pointer flex-1">Select All</label>
                                                </div>
                                                {notificationTypes.map((notification) => (
                                                    <div key={notification} className="flex items-center space-x-2 p-2 hover:bg-muted/40 rounded">
                                                        <Checkbox
                                                            id={notification}
                                                            checked={selectedNotifications.includes(notification)}
                                                            onCheckedChange={() => handleNotificationToggle(notification)}
                                                        />
                                                        <label htmlFor={notification} className="text-sm cursor-pointer flex-1">{notification}</label>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-center gap-4 pt-6 mt-6 border-t border-border/30">
                                <Button onClick={handleReset} className="h-10 px-8 bg-cyan-600 text-white hover:bg-cyan-700">Reset</Button>
                                <Button onClick={handleSubmit} className="h-10 px-8 bg-amber-500 hover:bg-amber-600 text-white">Submit</Button>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Table Section */}
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground text-sm">Show</span>
                                    <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                                        <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50">
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
                                        placeholder="User role type..."
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
                                            <TableHead className="text-gray-600 font-medium">User Role ▲</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Role Type ▲</TableHead>
                                            <TableHead className="text-gray-600 font-medium">Subscribed Notifications ▲</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {currentEntries.map((role, index) => (
                                            <TableRow key={role.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                                <TableCell className="text-cyan-600 font-medium">{role.userRole}</TableCell>
                                                <TableCell>{role.roleType}</TableCell>
                                                <TableCell className="text-cyan-600">{role.notifications}</TableCell>
                                                <TableCell className="text-center">
                                                    <div className="flex gap-2 justify-center">
                                                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditModalOpen(true)}>
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

                            {/* Pagination */}
                            <div className="flex items-center justify-between mt-6">
                                <span className="text-muted-foreground text-sm">
                                    Showing {startIndex + 1} to {endIndex} of {totalEntries} entries
                                </span>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                                        <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${currentPage === page ? "bg-cyan-600 text-white" : ""}`} onClick={() => setCurrentPage(page)}>
                                            {page}
                                        </Button>
                                    ))}
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="web-modules" className="space-y-6">
                    <Card className="border-0 shadow-lg rounded-2xl bg-white">
                        <CardContent className="p-6">
                            <div className="space-y-4 max-w-md mb-6">
                                <Label className="text-sm font-medium">Select User Role</Label>
                                <Select value={selectedRole} onValueChange={setSelectedRole}>
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select a role" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-white">
                                        {sampleRoles.map((role) => (
                                            <SelectItem key={role.id} value={role.userRole}>{role.userRole}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="rounded-xl overflow-hidden border border-gray-200">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                            <TableHead className="text-gray-600 font-medium">Module Name</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">View</TableHead>
                                            <TableHead className="text-gray-600 font-medium text-center">Edit</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {modulePermissions.map((module, index) => (
                                            <TableRow key={module.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}>
                                                <TableCell className="font-medium">{module.name}</TableCell>
                                                <TableCell className="text-center">
                                                    <Checkbox checked={module.view} />
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    <Checkbox checked={module.edit} />
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>

                            <div className="flex justify-center gap-4 p-6">
                                <Button className="h-10 px-8 bg-cyan-600 text-white hover:bg-cyan-700">Reset</Button>
                                <Button className="h-10 px-8 bg-amber-500 hover:bg-amber-600 text-white">Save</Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Edit User Role Modal */}
            <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
                <DialogContent className="max-w-[650px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit User Role</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditModalOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-12 space-y-7">
                        <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Role type <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-400 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Manager</option>
                                    <option>Staff</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">User Role Name <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                defaultValue="ASHOK"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>

                        <div className="grid grid-cols-[200px_1fr] items-start gap-4">
                            <Label className="text-sm font-medium text-gray-800 pt-2">Notification Subscription</Label>
                            <div className="relative border border-gray-300 rounded-[4px] p-2 pr-8 flex flex-wrap gap-2 min-h-[40px] bg-transparent">
                                <div className="bg-[#3eb1c8] text-white text-[12px] px-2 py-0.5 rounded-[2px] flex items-center gap-1 hover:bg-[#3eb1c8]/90 cursor-default shadow-sm border border-[#3eb1c8]">
                                    maintenance-request-creation <X className="h-[10px] w-[10px] cursor-pointer hover:opacity-80 stroke-[3]" />
                                </div>
                                <ChevronDown className="absolute right-2 top-3 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Reset</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditModalOpen(false)}>Update</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default UserRoles;




