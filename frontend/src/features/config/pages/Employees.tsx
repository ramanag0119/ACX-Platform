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
import { Pencil, Trash2, Eye, EyeOff, X, Edit, ChevronDown } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { useDepartments, useJobFunctions, useRoles, useUsers } from "@/lib/api/hooks";
import {
  useCreateDepartment,
  useCreateJobFunction,
  useCreateUser,
  useDeactivateUser,
  useReactivateUser,
  useUpdateDepartment,
  useUpdateJobFunction,
  useUpdateUser,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Employees, connected to GET /users (module `employees`).
 *
 * Departments and job functions have NO endpoint of their own: `department`
 * and `job_function` are only reachable through the names carried on a user
 * row. Those two tabs therefore list the DISTINCT values in use, which can
 * omit a department that currently has no staff -- recorded as a gap rather
 * than padded out with sample rows.
 *
 * The Role column needs GET /roles, which the backend gates on the
 * `user_roles` module. A Duty Manager has no such grant (by design), so the
 * column degrades to "-" for them instead of the screen failing.
 *
 * NOTHING SENSITIVE IS RENDERED: /users returns no password hash, no token and
 * no credential. The password field WRITES (POST/PATCH /users hashes it with
 * bcrypt server-side) but is never read back.
 *
 * Phase 3.0 writes:
 *   Department tab -> POST/PATCH /departments
 *   Function tab   -> POST/PATCH /job-functions
 *   Employee tab   -> POST/PATCH /users, plus deactivate/reactivate
 *
 * A staff member is retired with `date_of_termination`, never deleted: stays
 * and service requests reference the row.
 */

// Country codes for the (display-only) add form.
const countryCodes = ["+91", "+1", "+44", "+971", "+65"];

type TabType = "department" | "function" | "employee";

const Employees = () => {
    const [activeTab, setActiveTab] = useState<TabType>("department");
    const [showAddEmployee, setShowAddEmployee] = useState(false);

    // Modal states
    const [editDepartmentOpen, setEditDepartmentOpen] = useState(false);
    const [editFunctionOpen, setEditFunctionOpen] = useState(false);

    // Department state
    const [departmentName, setDepartmentName] = useState("");
    const [departmentSearch, setDepartmentSearch] = useState("");
    const [departmentEntriesPerPage, setDepartmentEntriesPerPage] = useState("10");
    const [departmentCurrentPage, setDepartmentCurrentPage] = useState(1);

    // Function state
    const [functionName, setFunctionName] = useState("");
    const [functionSearch, setFunctionSearch] = useState("");
    const [functionEntriesPerPage, setFunctionEntriesPerPage] = useState("10");
    const [functionCurrentPage, setFunctionCurrentPage] = useState(1);

    // Employee list state
    const [employeeSearch, setEmployeeSearch] = useState("");
    const [employeeEntriesPerPage, setEmployeeEntriesPerPage] = useState("10");
    const [employeeCurrentPage, setEmployeeCurrentPage] = useState(1);

    // Add Employee form state
    const [newEmployee, setNewEmployee] = useState({
        employeeId: "",
        firstName: "",
        lastName: "",
        dateOfJoining: "",
        supervisor: "",
        department: "",
        role: "",
        function: "",
        userId: "",
        password: "",
        email: "",
        countryCode: "+91",
        mobile: "",
        address: "",
    });
    const [showPassword, setShowPassword] = useState(false);

    // --- Live data -------------------------------------------------------
    const { canRead, canWrite } = useAuth();
    const canReadRoles = canRead("user_roles");

    const usersQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 });
    const rolesQuery = useRoles(canReadRoles ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined);
    // Phase 3.0 gave `department` and `job_function` their own endpoints, so a
    // department with no staff assigned is no longer invisible.
    const departmentsQuery = useDepartments({ page: 1, page_size: MAX_PAGE_SIZE });
    const functionsQuery = useJobFunctions({ page: 1, page_size: MAX_PAGE_SIZE });

    const users = usersQuery.data?.items ?? [];

    const departmentData = (departmentsQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        name: row.department_name,
    }));

    const functionData = (functionsQuery.data?.items ?? []).map((row) => ({
        id: row.id,
        name: row.function_name,
    }));

    // --- Mutations
    const mayWrite = canWrite("employees");
    const createDepartment = useCreateDepartment();
    const updateDepartmentMutation = useUpdateDepartment();
    const createFunction = useCreateJobFunction();
    const updateFunctionMutation = useUpdateJobFunction();
    const createEmployee = useCreateUser();
    const updateEmployee = useUpdateUser();
    const deactivate = useDeactivateUser();
    const reactivate = useReactivateUser();

    // Which row an edit dialog is working on.
    const [editingDepartment, setEditingDepartment] = useState<{ id: string; name: string } | null>(null);
    const [editingFunction, setEditingFunction] = useState<{ id: string; name: string } | null>(null);
    const [editingEmployee, setEditingEmployeeRow] = useState<(typeof employeeData)[number] | null>(null);

    const roleOptions = (rolesQuery.data?.items ?? []).map((role) => role.name);
    // `app_user.supervisor` is free text, so the picker offers what is in use.
    const supervisorOptions = [
        ...new Set(users.map((user) => user.supervisor).filter(Boolean) as string[]),
    ].sort();

    const employeeData = users.map((user) => ({
        /** `app_user.id` -- what every mutation is keyed on. */
        userId: user.id,
        id: user.emp_id ?? user.user_uid,
        usrId: user.user_name ?? "-",
        firstName: user.first_name,
        lastName: user.last_name ?? "",
        // Per-user role names would need /users/{id} for each row; the list
        // endpoint does not carry them.
        role: "-",
        department: user.department_name ?? "-",
        function: user.job_function_name ?? "-",
        email: user.email ?? "-",
        mobile: user.phone_number ?? "-",
        // `date_of_termination` is what the schema uses to retire an employee.
        status: user.date_of_termination ? "InActive" : "Active",
    }));

    // Filter department data
    const filteredDepartments = departmentData.filter(item =>
        item.name.toLowerCase().includes(departmentSearch.toLowerCase())
    );
    const departmentTotalPages = Math.ceil(filteredDepartments.length / parseInt(departmentEntriesPerPage));
    const departmentStartIndex = (departmentCurrentPage - 1) * parseInt(departmentEntriesPerPage);
    const departmentEndIndex = departmentStartIndex + parseInt(departmentEntriesPerPage);
    const paginatedDepartments = filteredDepartments.slice(departmentStartIndex, departmentEndIndex);

    // Filter function data
    const filteredFunctions = functionData.filter(item =>
        item.name.toLowerCase().includes(functionSearch.toLowerCase())
    );
    const functionTotalPages = Math.ceil(filteredFunctions.length / parseInt(functionEntriesPerPage));
    const functionStartIndex = (functionCurrentPage - 1) * parseInt(functionEntriesPerPage);
    const functionEndIndex = functionStartIndex + parseInt(functionEntriesPerPage);
    const paginatedFunctions = filteredFunctions.slice(functionStartIndex, functionEndIndex);

    // Filter employee data
    const filteredEmployees = employeeData.filter(item =>
        item.id.toLowerCase().includes(employeeSearch.toLowerCase()) ||
        item.firstName.toLowerCase().includes(employeeSearch.toLowerCase()) ||
        item.lastName.toLowerCase().includes(employeeSearch.toLowerCase()) ||
        item.mobile.includes(employeeSearch)
    );
    const employeeTotalPages = Math.ceil(filteredEmployees.length / parseInt(employeeEntriesPerPage));
    const employeeStartIndex = (employeeCurrentPage - 1) * parseInt(employeeEntriesPerPage);
    const employeeEndIndex = employeeStartIndex + parseInt(employeeEntriesPerPage);
    const paginatedEmployees = filteredEmployees.slice(employeeStartIndex, employeeEndIndex);

    const handleDepartmentReset = () => setDepartmentName("");

    const handleDepartmentSubmit = () => {
        if (!departmentName.trim()) return;
        createDepartment.mutate(departmentName.trim(), {
            onSuccess: () => setDepartmentName(""),
        });
    };

    const handleFunctionReset = () => setFunctionName("");

    const handleFunctionSubmit = () => {
        if (!functionName.trim()) return;
        createFunction.mutate(functionName.trim(), {
            onSuccess: () => setFunctionName(""),
        });
    };

    /**
     * Create or update a staff member.
     *
     * A password is optional: it is what makes the account able to sign in, and
     * it is hashed with bcrypt server-side. Roles are `user_role` rows, so the
     * selected role is sent as `role_ids`.
     */
    const handleEmployeeSubmit = () => {
        const roleId = (rolesQuery.data?.items ?? []).find(
            (role) => role.name === newEmployee.role,
        )?.id;

        const body = {
            first_name: newEmployee.firstName,
            last_name: newEmployee.lastName || null,
            phone_number: `${newEmployee.countryCode}${newEmployee.mobile}`,
            email: newEmployee.email || null,
            user_name: newEmployee.userId || null,
            ...(newEmployee.password ? { password: newEmployee.password } : {}),
            ...(newEmployee.employeeId ? { emp_id: newEmployee.employeeId } : {}),
            ...(newEmployee.dateOfJoining
                ? { date_of_joining: new Date(newEmployee.dateOfJoining).toISOString() }
                : {}),
            address: newEmployee.address || null,
            department_id:
                departmentData.find((d) => d.name === newEmployee.department)?.id ?? null,
            job_function_id:
                functionData.find((f) => f.name === newEmployee.function)?.id ?? null,
            is_staff: 1,
            ...(roleId ? { role_ids: [roleId] } : {}),
        };

        if (editingEmployee) {
            updateEmployee.mutate(
                { id: editingEmployee.userId, body },
                { onSuccess: () => { setShowAddEmployee(false); setEditingEmployeeRow(null); } },
            );
            return;
        }
        createEmployee.mutate(body, { onSuccess: () => setShowAddEmployee(false) });
    };

    const generatePassword = () => {
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%";
        let password = "";
        for (let i = 0; i < 12; i++) {
            password += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        setNewEmployee({ ...newEmployee, password });
    };

    const tabs = [
        { id: "department" as TabType, label: "Department" },
        { id: "function" as TabType, label: "Function" },
        { id: "employee" as TabType, label: "Employee" },
    ];

    // Add Employee Form
    if (showAddEmployee) {
        return (
            <div className="space-y-6 animate-fade-in text-foreground">
                <div className="flex items-center justify-between mb-2">
                    <h1 className="text-xl font-semibold text-foreground tracking-tight">Employee Management</h1>
                    <Button onClick={() => setShowAddEmployee(false)} variant="destructive" className="h-9 px-4 text-xs font-semibold rounded-xl shadow-sm">
                        Cancel
                    </Button>
                </div>

                <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                    <CardContent className="p-8">
                        <div className="max-w-3xl mx-auto space-y-4">
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Employee ID<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Input placeholder="Enter Emp Id" value={newEmployee.employeeId} onChange={(e) => setNewEmployee({ ...newEmployee, employeeId: e.target.value })} className="bg-muted/30 border-border/50" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">First Name<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Input placeholder="Enter First Name" value={newEmployee.firstName} onChange={(e) => setNewEmployee({ ...newEmployee, firstName: e.target.value })} className="bg-muted/30 border-border/50" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Last Name<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Input placeholder="Enter Last Name" value={newEmployee.lastName} onChange={(e) => setNewEmployee({ ...newEmployee, lastName: e.target.value })} className="bg-muted/30 border-border/50" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Date of Joining<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Input type="date" value={newEmployee.dateOfJoining} onChange={(e) => setNewEmployee({ ...newEmployee, dateOfJoining: e.target.value })} className="bg-amber-500 border-border/50 text-white" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Supervisor<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Select value={newEmployee.supervisor} onValueChange={(val) => setNewEmployee({ ...newEmployee, supervisor: val })}>
                                        <SelectTrigger className="bg-muted/30 border-border/50"><SelectValue placeholder="Select Supervisor" /></SelectTrigger>
                                        <SelectContent className="bg-popover">{supervisorOptions.map(opt => (<SelectItem key={opt} value={opt}>{opt}</SelectItem>))}</SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Department<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Select value={newEmployee.department} onValueChange={(val) => setNewEmployee({ ...newEmployee, department: val })}>
                                        <SelectTrigger className="bg-muted/30 border-border/50"><SelectValue placeholder="Select Department" /></SelectTrigger>
                                        <SelectContent className="bg-popover">{departmentData.map(dept => (<SelectItem key={dept.id} value={dept.name}>{dept.name}</SelectItem>))}</SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Role<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Select value={newEmployee.role} onValueChange={(val) => setNewEmployee({ ...newEmployee, role: val })}>
                                        <SelectTrigger className="bg-muted/30 border-border/50"><SelectValue placeholder="Select Role" /></SelectTrigger>
                                        <SelectContent className="bg-popover">{roleOptions.map(role => (<SelectItem key={role} value={role}>{role}</SelectItem>))}</SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Function<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Select value={newEmployee.function} onValueChange={(val) => setNewEmployee({ ...newEmployee, function: val })}>
                                        <SelectTrigger className="bg-muted/30 border-border/50"><SelectValue placeholder="Select Function" /></SelectTrigger>
                                        <SelectContent className="bg-popover">{functionData.map(func => (<SelectItem key={func.id} value={func.name}>{func.name}</SelectItem>))}</SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">User Id</Label>
                                <div className="col-span-2">
                                    <Input placeholder="Enter User Name" value={newEmployee.userId} onChange={(e) => setNewEmployee({ ...newEmployee, userId: e.target.value })} className="bg-muted/30 border-border/50" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Password</Label>
                                <div className="col-span-2 flex gap-2">
                                    <Input type={showPassword ? "text" : "password"} placeholder="Enter Password" value={newEmployee.password} onChange={(e) => setNewEmployee({ ...newEmployee, password: e.target.value })} className="bg-muted/30 border-border/50 flex-1" />
                                    <Button onClick={generatePassword} className="rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Generate</Button>
                                    <Button onClick={() => setShowPassword(!showPassword)} className="bg-amber-500 hover:bg-amber-600 text-white p-2">
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </Button>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Email<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Input type="email" placeholder="Enter Email ID" value={newEmployee.email} onChange={(e) => setNewEmployee({ ...newEmployee, email: e.target.value })} className="bg-muted/30 border-border/50" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Country Code<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Select value={newEmployee.countryCode} onValueChange={(val) => setNewEmployee({ ...newEmployee, countryCode: val })}>
                                        <SelectTrigger className="bg-muted/30 border-border/50"><SelectValue placeholder="Select Country Code" /></SelectTrigger>
                                        <SelectContent className="bg-popover">{countryCodes.map(code => (<SelectItem key={code} value={code}>{code}</SelectItem>))}</SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-center">
                                <Label className="text-sm font-medium text-right">Mobile Number<span className="text-red-500">*</span></Label>
                                <div className="col-span-2">
                                    <Input placeholder="Enter Phone Number" value={newEmployee.mobile} onChange={(e) => setNewEmployee({ ...newEmployee, mobile: e.target.value })} className="bg-muted/30 border-border/50" />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 items-start">
                                <Label className="text-sm font-medium text-right pt-2">Address</Label>
                                <div className="col-span-2">
                                    <Textarea placeholder="Enter Address of the Employee" value={newEmployee.address} onChange={(e) => setNewEmployee({ ...newEmployee, address: e.target.value })} className="bg-muted/30 border-border/50 min-h-[100px]" />
                                </div>
                            </div>
                            <div className="flex justify-center pt-6 border-t border-border/30">
                                <Button onClick={handleEmployeeSubmit} className="h-11 px-12 min-w-[140px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Submit</Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const renderDepartmentTab = () => (
        <div className="space-y-6">
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="max-w-2xl mx-auto">
                        <div className="grid grid-cols-2 gap-4 items-center mb-6">
                            <Label className="text-sm font-medium text-right">Department Name<span className="text-red-500">*</span></Label>
                            <Input placeholder="Enter Department Name" value={departmentName} onChange={(e) => setDepartmentName(e.target.value)} className="bg-muted/30 border-border/50" />
                        </div>
                        <div className="flex justify-center gap-4 pt-6 border-t border-border/30">
                            <Button onClick={handleDepartmentReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
                            <Button onClick={handleDepartmentSubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Submit</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={departmentEntriesPerPage} onValueChange={setDepartmentEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                                <SelectContent className="bg-popover"><SelectItem value="10">10</SelectItem><SelectItem value="25">25</SelectItem><SelectItem value="50">50</SelectItem></SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input placeholder="Department name" value={departmentSearch} onChange={(e) => setDepartmentSearch(e.target.value)} className="w-48 h-9 bg-muted/30 border-border/50" />
                        </div>
                    </div>
                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Department Name ▲</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedDepartments.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                        <TableCell className="text-cyan-600 hover:underline cursor-pointer">{item.name}</TableCell>
                                        <TableCell className="text-center">
                                            <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" disabled={!mayWrite} onClick={() => { setEditingDepartment(item); setEditDepartmentOpen(true); }}>
                                                <Edit className="h-[14px] w-[14px]" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing {departmentStartIndex + 1} to {Math.min(departmentEndIndex, filteredDepartments.length)} of {filteredDepartments.length} entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setDepartmentCurrentPage(1)} disabled={departmentCurrentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setDepartmentCurrentPage(Math.max(1, departmentCurrentPage - 1))} disabled={departmentCurrentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(3, departmentTotalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={departmentCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${departmentCurrentPage === page ? "bg-primary text-white" : "text-muted-foreground"}`} onClick={() => setDepartmentCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setDepartmentCurrentPage(Math.min(departmentTotalPages, departmentCurrentPage + 1))} disabled={departmentCurrentPage === departmentTotalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setDepartmentCurrentPage(departmentTotalPages)} disabled={departmentCurrentPage === departmentTotalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderFunctionTab = () => (
        <div className="space-y-6">
            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="max-w-2xl mx-auto">
                        <div className="grid grid-cols-2 gap-4 items-center mb-6">
                            <Label className="text-sm font-medium text-right">Function Name<span className="text-red-500">*</span></Label>
                            <Input placeholder="Enter Function Name" value={functionName} onChange={(e) => setFunctionName(e.target.value)} className="bg-muted/30 border-border/50" />
                        </div>
                        <div className="flex justify-center gap-4 pt-6 border-t border-border/30">
                            <Button onClick={handleFunctionReset} variant="outline" className="h-11 px-8 min-w-[120px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all">Reset</Button>
                            <Button onClick={handleFunctionSubmit} className="h-11 px-8 min-w-[120px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">Submit</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card className="border-0 shadow-lg rounded-2xl bg-white">
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Show</span>
                            <Select value={functionEntriesPerPage} onValueChange={setFunctionEntriesPerPage}>
                                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                                <SelectContent className="bg-popover"><SelectItem value="10">10</SelectItem><SelectItem value="25">25</SelectItem><SelectItem value="50">50</SelectItem></SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-sm">entries</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-sm">Search:</span>
                            <Input placeholder="Function name" value={functionSearch} onChange={(e) => setFunctionSearch(e.target.value)} className="w-48 h-9 bg-muted/30 border-border/50" />
                        </div>
                    </div>
                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Function Name ▲</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedFunctions.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                        <TableCell className="text-cyan-600 hover:underline cursor-pointer">{item.name}</TableCell>
                                        <TableCell className="text-center">
                                            <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" disabled={!mayWrite} onClick={() => { setEditingFunction(item); setEditFunctionOpen(true); }}>
                                                <Edit className="h-[14px] w-[14px]" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                    <div className="flex items-center justify-between mt-6">
                        <span className="text-muted-foreground text-sm">Showing {functionStartIndex + 1} to {Math.min(functionEndIndex, filteredFunctions.length)} of {filteredFunctions.length} entries</span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFunctionCurrentPage(1)} disabled={functionCurrentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFunctionCurrentPage(Math.max(1, functionCurrentPage - 1))} disabled={functionCurrentPage === 1}>Previous</Button>
                            {Array.from({ length: Math.min(3, functionTotalPages) }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={functionCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${functionCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setFunctionCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFunctionCurrentPage(Math.min(functionTotalPages, functionCurrentPage + 1))} disabled={functionCurrentPage === functionTotalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setFunctionCurrentPage(functionTotalPages)} disabled={functionCurrentPage === functionTotalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );

    const renderEmployeeTab = () => (
        <Card className="border-0 shadow-lg rounded-2xl bg-white">
            <CardContent className="p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                        <span className="text-muted-foreground text-sm">Show</span>
                        <Select value={employeeEntriesPerPage} onValueChange={setEmployeeEntriesPerPage}>
                            <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50"><SelectValue /></SelectTrigger>
                            <SelectContent className="bg-popover"><SelectItem value="10">10</SelectItem><SelectItem value="25">25</SelectItem><SelectItem value="50">50</SelectItem></SelectContent>
                        </Select>
                        <span className="text-muted-foreground text-sm">entries</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-muted-foreground text-sm">Search:</span>
                        <Input placeholder="Employee ID, First name, Last name, Mobile Number" value={employeeSearch} onChange={(e) => setEmployeeSearch(e.target.value)} className="w-96 h-9 bg-muted/30 border-border/50" />
                    </div>
                </div>
                <div className="rounded-xl overflow-hidden border border-gray-200 overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Employee ID ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">User Id ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">First Name ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Last Name ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Role ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Department ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Function ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Email ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Mobile Number ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium whitespace-nowrap">Status ◆</TableHead>
                                <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedEmployees.map((item, index) => (
                                <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                    <TableCell className="text-cyan-600 hover:underline cursor-pointer whitespace-nowrap">{item.id}</TableCell>
                                    <TableCell className="text-cyan-600 whitespace-nowrap">{item.usrId}</TableCell>
                                    <TableCell className="text-cyan-600 whitespace-nowrap">{item.firstName}</TableCell>
                                    <TableCell className="text-cyan-600 whitespace-nowrap">{item.lastName}</TableCell>
                                    <TableCell className="text-cyan-600 whitespace-nowrap">{item.role}</TableCell>
                                    <TableCell className="text-cyan-600 whitespace-nowrap">{item.department}</TableCell>
                                    <TableCell className="text-cyan-600 hover:underline cursor-pointer whitespace-nowrap">{item.function}</TableCell>
                                    <TableCell className="text-cyan-600 hover:underline cursor-pointer whitespace-nowrap">{item.email}</TableCell>
                                    <TableCell className="text-cyan-600 whitespace-nowrap">{item.mobile}</TableCell>
                                    <TableCell className={`whitespace-nowrap ${item.status === "Active" ? "text-green-500" : "text-red-500"}`}>{item.status}</TableCell>
                                    <TableCell className="text-center">
                                        <div className="flex justify-center gap-2">
                                            <Button
                                                size="sm"
                                                className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]"
                                                disabled={!mayWrite}
                                                onClick={() => {
                                                    setEditingEmployeeRow(item);
                                                    setNewEmployee({
                                                        employeeId: item.id,
                                                        firstName: item.firstName,
                                                        lastName: item.lastName,
                                                        dateOfJoining: "",
                                                        supervisor: "",
                                                        department: item.department === "-" ? "" : item.department,
                                                        role: item.role === "-" ? "" : item.role,
                                                        function: item.function === "-" ? "" : item.function,
                                                        userId: item.usrId === "-" ? "" : item.usrId,
                                                        password: "",
                                                        email: item.email === "-" ? "" : item.email,
                                                        countryCode: "+91",
                                                        mobile: item.mobile === "-" ? "" : item.mobile,
                                                        address: "",
                                                    });
                                                    setShowAddEmployee(true);
                                                }}
                                            >
                                                <Edit className="h-[14px] w-[14px]" />
                                            </Button>
                                            {/* Deactivate, not delete: `date_of_termination` is how
                                                IKANOS retires a staff member, and stays and service
                                                requests reference the row. */}
                                            <Button
                                                size="sm"
                                                className="bg-red-500 hover:bg-red-600 text-white h-7 w-7 p-0 rounded-[3px]"
                                                disabled={!mayWrite || deactivate.isPending || reactivate.isPending}
                                                title={item.status === "Active" ? "Deactivate" : "Reactivate"}
                                                onClick={() =>
                                                    item.status === "Active"
                                                        ? deactivate.mutate(item.userId)
                                                        : reactivate.mutate(item.userId)
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
                <div className="flex items-center justify-between mt-6">
                    <span className="text-muted-foreground text-sm">Showing {employeeStartIndex + 1} to {Math.min(employeeEndIndex, filteredEmployees.length)} of {filteredEmployees.length} entries</span>
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(1)} disabled={employeeCurrentPage === 1}>First</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(Math.max(1, employeeCurrentPage - 1))} disabled={employeeCurrentPage === 1}>Previous</Button>
                        {Array.from({ length: Math.min(4, employeeTotalPages) }, (_, i) => i + 1).map((page) => (
                            <Button key={page} variant={employeeCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 rounded-xl ${employeeCurrentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground"}`} onClick={() => setEmployeeCurrentPage(page)}>{page}</Button>
                        ))}
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(Math.min(employeeTotalPages, employeeCurrentPage + 1))} disabled={employeeCurrentPage === employeeTotalPages}>Next</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(employeeTotalPages)} disabled={employeeCurrentPage === employeeTotalPages}>Last</Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Employee Management</h1>
                <Button onClick={() => setShowAddEmployee(true)} className="h-9 px-4 text-xs font-semibold rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white shadow-md hover:shadow-lg transition-all">
                    Add Employee
                </Button>
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
            <DataState
                isLoading={usersQuery.isLoading}
                error={usersQuery.error}
                loader={<TableLoading columns={9} />}
            >
                <>
                    {activeTab === "department" && renderDepartmentTab()}
                    {activeTab === "function" && renderFunctionTab()}
                    {activeTab === "employee" && renderEmployeeTab()}
                </>
            </DataState>

            {/* Edit Department Modal */}
            <Dialog open={editDepartmentOpen} onOpenChange={setEditDepartmentOpen}>
                <DialogContent className="max-w-[450px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Department</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditDepartmentOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-7">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Department Name <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editingDepartment?.name ?? ""}
                                onChange={(event) =>
                                    setEditingDepartment((current) =>
                                        current ? { ...current, name: event.target.value } : current,
                                    )
                                }
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-700 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditDepartmentOpen(false)}>Reset</Button>
                        <Button
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                            disabled={!editingDepartment?.name || updateDepartmentMutation.isPending}
                            onClick={() =>
                                editingDepartment &&
                                updateDepartmentMutation.mutate(
                                    { id: editingDepartment.id, name: editingDepartment.name },
                                    { onSuccess: () => setEditDepartmentOpen(false) },
                                )
                            }
                        >
                            Update
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Function Modal */}
            <Dialog open={editFunctionOpen} onOpenChange={setEditFunctionOpen}>
                <DialogContent className="max-w-[450px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Function</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditFunctionOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-8 px-10 space-y-7">
                        <div className="grid grid-cols-[140px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Function Name <span className="text-red-500">*</span></Label>
                            <input
                                type="text"
                                value={editingFunction?.name ?? ""}
                                onChange={(event) =>
                                    setEditingFunction((current) =>
                                        current ? { ...current, name: event.target.value } : current,
                                    )
                                }
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-700 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="h-10 px-8 min-w-[110px] rounded-2xl bg-slate-100 dark:bg-[#1e2336]/80 hover:bg-slate-200 dark:hover:bg-[#283049] border border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-white font-semibold text-sm shadow-sm transition-all" onClick={() => setEditFunctionOpen(false)}>Reset</Button>
                        <Button
                            className="h-10 px-8 min-w-[110px] rounded-2xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
                            disabled={!editingFunction?.name || updateFunctionMutation.isPending}
                            onClick={() =>
                                editingFunction &&
                                updateFunctionMutation.mutate(
                                    { id: editingFunction.id, name: editingFunction.name },
                                    { onSuccess: () => setEditFunctionOpen(false) },
                                )
                            }
                        >
                            Update
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* The Edit Employee dialog that used to live here was a second,
                hardcoded copy of the Add Employee fields. Editing now reuses the
                real form above (pre-filled from the row), which PATCHes
                /users/{id} -- one form, one code path, one source of truth. */}
        </div>
    );
};

export default Employees;




