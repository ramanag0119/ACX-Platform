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
import { DataState, TableLoading } from "@/core/components/DataState";
import { useNotificationTemplates, useRolePermissions, useRoles } from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  useCreateRole,
  useReplaceRolePermissions,
  useUpdateRole,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * User Role Management, connected to the Phase 2.3 access APIs.
 *
 *   User Role tab -> GET /roles
 *   Web Modules   -> GET /roles/{id}/permissions
 *
 * The Web Modules matrix IS the authoritative RBAC data: one row per
 * `role_module` grant with the real `read_access` / `write_access` flags.
 * `write_applicable` comes from the module definition and decides whether an
 * Edit checkbox means anything at all. No role name is interpreted anywhere.
 *
 * The notification picker lists the template names actually registered
 * (GET /notification-templates) instead of a hardcoded list. Template BODIES
 * are never fetched -- they can carry OTPs and keypad keys.
 *
 * Phase 3.0 writes:
 *   Create role -> POST /roles
 *   Edit role   -> PATCH /roles/{id}
 *   Web Modules -> PUT /roles/{id}/permissions (the whole matrix, one call)
 *
 * The backend refuses write-without-read, and write on a module whose
 * `write_applicable` is false, so an invalid matrix cannot be stored.
 *
 * Per-role notification subscriptions have no column and no endpoint: the
 * picker lists real template names but there is nothing to attach them to.
 */

const UserRoles = () => {
    // --- Live data -------------------------------------------------------
    const rolesQuery = useRoles({ page: 1, page_size: MAX_PAGE_SIZE });
    const { canWrite } = useAuth();
    const mayWrite = canWrite("user_roles");
    const createRole = useCreateRole();
    const updateRole = useUpdateRole();
    const savePermissions = useReplaceRolePermissions();
    const [editingRole, setEditingRole] = useState<{
        id: string;
        name: string;
        roleType: string;
    } | null>(null);
    /** Pending matrix ticks, keyed by module id; empty until the user changes one. */
    const [matrixEdits, setMatrixEdits] = useState<
        Record<string, { view: boolean; edit: boolean }>
    >({});
    const templatesQuery = useNotificationTemplates({ page: 1, page_size: MAX_PAGE_SIZE });
    const notificationTypes = (templatesQuery.data?.items ?? []).map((template) => template.name);

    const roles = (rolesQuery.data?.items ?? []).map((role) => ({
        id: role.id,
        userRole: role.name,
        roleType: role.role_type,
        // `role` carries a description; per-role notification subscriptions
        // are not exposed by any endpoint.
        notifications: role.description ?? "-",
    }));

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

    // Web Modules state -- the matrix is whatever the backend reports for the
    // selected role, never something derived from the role's name.
    const [selectedRole, setSelectedRole] = useState("");
    const permissionsQuery = useRolePermissions(selectedRole || null);
    const modulePermissions = (permissionsQuery.data ?? []).map((permission) => {
        const key = String(permission.module_id);
        const pending = matrixEdits[key];
        return {
            id: key,
            moduleId: permission.module_id,
            name: permission.module_name,
            view: pending ? pending.view : permission.read_access,
            edit: pending ? pending.edit : Boolean(permission.write_access),
            editApplicable: permission.write_applicable !== false,
        };
    });

    /** Write requires read, so unticking View clears Edit with it. */
    const toggleMatrix = (moduleId: number, column: "view" | "edit", value: boolean) => {
        const key = String(moduleId);
        const row = modulePermissions.find((entry) => entry.id === key);
        if (!row) return;
        const view = column === "view" ? value : row.view;
        const edit = column === "edit" ? value : row.edit;
        setMatrixEdits((edits) => ({
            ...edits,
            [key]: { view, edit: view ? edit : false },
        }));
    };

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
        if (!roleName.trim() || !roleType) return;
        createRole.mutate(
            { name: roleName.trim(), role_type: roleType as "staff" | "manager" | "admin" },
            {
                onSuccess: () => {
                    setRoleName("");
                    setRoleType("");
                    setSelectedNotifications([]);
                },
            },
        );
    };

    // Filter roles
    const filteredRoles = roles.filter(role =>
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
                                        <SelectContent className="bg-popover text-popover-foreground border-border">
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
                                <Button onClick={handleReset} className="h-10 px-8 min-w-[120px] rounded-xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
                                <Button
                                    onClick={handleSubmit}
                                    className="h-10 px-8 min-w-[120px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                                    disabled={!mayWrite || !roleName.trim() || !roleType || createRole.isPending}
                                    title={mayWrite ? "Create this role" : "Your role cannot manage roles"}
                                >
                                    {createRole.isPending ? "Creating..." : "Submit"}
                                </Button>
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
                                        placeholder="User role type..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-48 h-9 bg-muted/30 border-border/50"
                                    />
                                </div>
                            </div>

                            <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                              <DataState
                                isLoading={rolesQuery.isLoading}
                                error={rolesQuery.error}
                                isEmpty={currentEntries.length === 0}
                                emptyTitle="No roles found"
                                loader={<TableLoading columns={4} />}
                              >
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
                                            <TableRow key={role.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                                <TableCell className="text-cyan-600 font-medium">{role.userRole}</TableCell>
                                                <TableCell>{role.roleType}</TableCell>
                                                <TableCell className="text-cyan-600">{role.notifications}</TableCell>
                                                <TableCell className="text-center">
                                                    <div className="flex gap-2 justify-center">
                                                        <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" disabled={!mayWrite} onClick={() => { setEditingRole({ id: role.id, name: role.userRole, roleType: role.roleType }); setEditModalOpen(true); }}>
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
                              </DataState>
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
                                <Select
                                    value={selectedRole}
                                    onValueChange={(next) => {
                                        setMatrixEdits({});
                                        setSelectedRole(next);
                                    }}
                                >
                                    <SelectTrigger className="h-10 bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select a role" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover text-popover-foreground border-border">
                                        {roles.map((role) => (
                                            <SelectItem key={role.id} value={role.id}>{role.userRole}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                              <DataState
                                isLoading={Boolean(selectedRole) && permissionsQuery.isLoading}
                                error={permissionsQuery.error}
                                isEmpty={!selectedRole || modulePermissions.length === 0}
                                emptyTitle={selectedRole ? "This role has no module grants" : "Select a role to see its module permissions"}
                                loader={<TableLoading columns={3} />}
                              >
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
                                            <TableRow key={module.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                                <TableCell className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3">{module.name}</TableCell>
                                                <TableCell className="text-center">
                                                    <Checkbox
                                                        checked={module.view}
                                                        disabled={!mayWrite}
                                                        onCheckedChange={(next) =>
                                                            toggleMatrix(module.moduleId, "view", Boolean(next))
                                                        }
                                                    />
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {module.editApplicable ? (
                                                        <Checkbox
                                                            checked={module.edit}
                                                            disabled={!mayWrite || !module.view}
                                                            onCheckedChange={(next) =>
                                                                toggleMatrix(module.moduleId, "edit", Boolean(next))
                                                            }
                                                        />
                                                    ) : (
                                                        <span className="text-xs text-muted-foreground">n/a</span>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                              </DataState>
                            </div>

                            <div className="flex flex-col items-center gap-2 p-6">
                                <div className="flex justify-center gap-4">
                                    <Button
                                        className="h-10 px-8 min-w-[120px] rounded-xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all"
                                        onClick={() => setMatrixEdits({})}
                                        disabled={Object.keys(matrixEdits).length === 0}
                                    >
                                        Reset
                                    </Button>
                                    <Button
                                        className="h-10 px-8 min-w-[120px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                                        disabled={!mayWrite || !selectedRole || savePermissions.isPending}
                                        onClick={() =>
                                            savePermissions.mutate(
                                                {
                                                    id: selectedRole,
                                                    permissions: modulePermissions.map((row) => ({
                                                        module_id: row.moduleId,
                                                        read_access: row.view,
                                                        write_access: row.editApplicable && row.edit,
                                                    })),
                                                },
                                                { onSuccess: () => setMatrixEdits({}) },
                                            )
                                        }
                                    >
                                        {savePermissions.isPending ? "Saving..." : "Save"}
                                    </Button>
                                </div>
                                {!mayWrite && (
                                    <p className="text-xs text-muted-foreground">
                                        Your role holds no write grant on user_roles.
                                    </p>
                                )}
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
                                <select
                                    className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-600 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none"
                                    value={editingRole?.roleType ?? ""}
                                    onChange={(event) =>
                                        setEditingRole((current) =>
                                            current ? { ...current, roleType: event.target.value } : current,
                                        )
                                    }
                                >
                                    <option value="manager">Manager</option>
                                    <option value="staff">Staff</option>
                                    <option value="admin">Admin</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">User Role Name <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editingRole?.name ?? ""}
                                onChange={(event) =>
                                    setEditingRole((current) =>
                                        current ? { ...current, name: event.target.value } : current,
                                    )
                                }
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-700 focus:ring-0 px-0 pb-1 text-sm outline-none"
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
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditModalOpen(false)}>Reset</Button>
                        <Button
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                            disabled={!editingRole?.name || updateRole.isPending}
                            onClick={() =>
                                editingRole &&
                                updateRole.mutate(
                                    {
                                        id: editingRole.id,
                                        body: {
                                            name: editingRole.name,
                                            role_type: editingRole.roleType as
                                                | "staff"
                                                | "manager"
                                                | "admin",
                                        },
                                    },
                                    { onSuccess: () => setEditModalOpen(false) },
                                )
                            }
                        >
                            Update
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default UserRoles;




