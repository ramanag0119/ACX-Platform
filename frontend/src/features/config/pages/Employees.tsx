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

// Sample Department Data
const departmentData = [
    { id: "1", name: "Admin" },
    { id: "2", name: "Deputy Housekeeping" },
    { id: "3", name: "floor house keeper" },
    { id: "4", name: "Food Service" },
    { id: "5", name: "Housekeeping" },
    { id: "6", name: "Housekeeping Manager" },
    { id: "7", name: "Maintenance" },
    { id: "8", name: "Room service" },
];

// Sample Function Data
const functionData = [
    { id: "1", name: "Admin" },
    { id: "2", name: "Cleaner" },
    { id: "3", name: "Electrician" },
    { id: "4", name: "Food servant" },
    { id: "5", name: "Housekeeping Manager" },
    { id: "6", name: "Janitor" },
    { id: "7", name: "Maid" },
    { id: "8", name: "Manager" },
    { id: "9", name: "Plumber" },
    { id: "10", name: "Room service boy" },
    { id: "11", name: "Sweeper" },
    { id: "12", name: "Supervisor" },
];

// Sample Employee Data
const employeeData = [
    { id: "19case068", usrId: "ackshaya", firstName: "Ackshaya", lastName: "K", role: "Maintenance staff", department: "Maintenance", function: "Food servant", email: "ackshaya2004@gmail.com", mobile: "+91 8300824298", status: "InActive" },
    { id: "A-101", usrId: "alice", firstName: "Alice", lastName: "Konyak", role: "service manager", department: "Housekeeping Manager", function: "Housekeeping Manager", email: "alice@gmail.com", mobile: "+91 9362606433", status: "Active" },
    { id: "PE00002", usrId: "ashok", firstName: "Ashok", lastName: "g", role: "Room service", department: "Deputy Housekeeping", function: "Cleaner", email: "staffone123@gmail.com", mobile: "+91 9025009918", status: "InActive" },
    { id: "PF-02", usrId: "balaji", firstName: "Balaji", lastName: "G", role: "Service staff", department: "Housekeeping", function: "Sweeper", email: "balaji123@gmail.com", mobile: "+91 8903140344", status: "Active" },
    { id: "PE0003", usrId: "bharathy", firstName: "BHARATHY VENKAT", lastName: "KUMAR A", role: "Manager", department: "Housekeeping Manager", function: "Housekeeping Manager", email: "bharathyvld@gmail.com", mobile: "+91 6379961321", status: "InActive" },
    { id: "PE00015", usrId: "brindha", firstName: "Brindha", lastName: "G", role: "Service staff", department: "Housekeeping", function: "Food servant", email: "brindha123@gmail.com", mobile: "+91 9360180250", status: "Active" },
    { id: "Tikasse34", usrId: "Client", firstName: "Client", lastName: "D", role: "food service", department: "Room service", function: "Food servant", email: "client@gmail.com", mobile: "+91 9994873645", status: "InActive" },
    { id: "PE0009", usrId: "staffone", firstName: "CIXI", lastName: "staff", role: "Room service", department: "floor house keeper", function: "Cleaner", email: "cixi0203@gmail.com", mobile: "+91 9789368024", status: "Active" },
    { id: "9", usrId: "cixi", firstName: "CIXI, TAB", lastName: "fab", role: "Floor Manager", department: "Maintenance", function: "Manager", email: "test@gmail.com", mobile: "+91 8300275377", status: "Active" },
    { id: "PE0001", usrId: "ganesan", firstName: "Ganesan", lastName: "K", role: "Manager", department: "Maintenance", function: "Supervisor", email: "test123@gmail.com", mobile: "+91 9840014016", status: "Active" },
];

// Role options
const roleOptions = ["Manager", "Staff", "Service staff", "Maintenance staff", "Floor Manager", "food service", "service manager", "Room service"];

// Country codes
const countryCodes = ["+91", "+1", "+44", "+971", "+65"];

// Supervisor options
const supervisorOptions = ["Admin", "Manager", "Floor Manager", "Housekeeping Manager"];

type TabType = "department" | "function" | "employee";

const Employees = () => {
    const [activeTab, setActiveTab] = useState<TabType>("department");
    const [showAddEmployee, setShowAddEmployee] = useState(false);

    // Modal states
    const [editDepartmentOpen, setEditDepartmentOpen] = useState(false);
    const [editFunctionOpen, setEditFunctionOpen] = useState(false);
    const [editEmployeeOpen, setEditEmployeeOpen] = useState(false);

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
    const handleDepartmentSubmit = () => console.log("Department Submit:", { departmentName });
    const handleFunctionReset = () => setFunctionName("");
    const handleFunctionSubmit = () => console.log("Function Submit:", { functionName });
    const handleEmployeeSubmit = () => {
        console.log("Employee Submit:", newEmployee);
        setShowAddEmployee(false);
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
            <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
                <div className="flex items-center justify-between mb-2">
                    <h1 className="text-2xl font-semibold text-foreground">Employee Management</h1>
                    <Button onClick={() => setShowAddEmployee(false)} className="bg-red-500 hover:bg-red-600 text-white">
                        Cancel
                    </Button>
                </div>

                <Card className="border-0 shadow-lg rounded-2xl bg-white">
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
                                    <Button onClick={generatePassword} className="bg-cyan-600 hover:bg-cyan-700 text-white">Generate</Button>
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
                            <div className="flex justify-center pt-6">
                                <Button onClick={handleEmployeeSubmit} className="bg-cyan-600 hover:bg-cyan-700 text-white px-12">Submit</Button>
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
                        <div className="flex justify-center gap-4">
                            <Button onClick={handleDepartmentReset} className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">Reset</Button>
                            <Button onClick={handleDepartmentSubmit} variant="outline" className="border-border/50 px-8">Submit</Button>
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
                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Department Name ▲</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedDepartments.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}>
                                        <TableCell className="text-cyan-600 hover:underline cursor-pointer">{item.name}</TableCell>
                                        <TableCell className="text-center">
                                            <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditDepartmentOpen(true)}>
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
                        <div className="flex justify-center gap-4">
                            <Button onClick={handleFunctionReset} className="bg-cyan-600 hover:bg-cyan-700 text-white px-8">Reset</Button>
                            <Button onClick={handleFunctionSubmit} variant="outline" className="border-border/50 px-8">Submit</Button>
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
                    <div className="rounded-xl overflow-hidden border border-gray-200">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                                    <TableHead className="text-gray-600 font-medium">Function Name ▲</TableHead>
                                    <TableHead className="text-gray-600 font-medium text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedFunctions.map((item, index) => (
                                    <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}>
                                        <TableCell className="text-cyan-600 hover:underline cursor-pointer">{item.name}</TableCell>
                                        <TableCell className="text-center">
                                            <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditFunctionOpen(true)}>
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
                                <Button key={page} variant={functionCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${functionCurrentPage === page ? "bg-primary text-white" : "text-muted-foreground"}`} onClick={() => setFunctionCurrentPage(page)}>{page}</Button>
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
                                <TableRow key={item.id} className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} hover:bg-muted/40 transition-colors`}>
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
                                            <Button size="sm" className="bg-[#3eb1c8] hover:bg-[#3eb1c8]/90 text-white h-7 w-7 p-0 rounded-[3px]" onClick={() => setEditEmployeeOpen(true)}>
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
                    <span className="text-muted-foreground text-sm">Showing {employeeStartIndex + 1} to {Math.min(employeeEndIndex, filteredEmployees.length)} of {filteredEmployees.length} entries</span>
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(1)} disabled={employeeCurrentPage === 1}>First</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(Math.max(1, employeeCurrentPage - 1))} disabled={employeeCurrentPage === 1}>Previous</Button>
                        {Array.from({ length: Math.min(4, employeeTotalPages) }, (_, i) => i + 1).map((page) => (
                            <Button key={page} variant={employeeCurrentPage === page ? "default" : "ghost"} size="sm" className={`w-9 h-9 p-0 ${employeeCurrentPage === page ? "bg-primary text-white" : "text-muted-foreground"}`} onClick={() => setEmployeeCurrentPage(page)}>{page}</Button>
                        ))}
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(Math.min(employeeTotalPages, employeeCurrentPage + 1))} disabled={employeeCurrentPage === employeeTotalPages}>Next</Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setEmployeeCurrentPage(employeeTotalPages)} disabled={employeeCurrentPage === employeeTotalPages}>Last</Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold text-foreground">Employee Management</h1>
                <Button onClick={() => setShowAddEmployee(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white">
                    Add Employee
                </Button>
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

            {/* Content */}
            {activeTab === "department" && renderDepartmentTab()}
            {activeTab === "function" && renderFunctionTab()}
            {activeTab === "employee" && renderEmployeeTab()}

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
                                defaultValue="Deputy Housekeeping"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditDepartmentOpen(false)}>Reset</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditDepartmentOpen(false)}>Update</Button>
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
                                defaultValue="Cleaner"
                                className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-8">
                        <Button variant="outline" className="text-amber-500 border-amber-500 hover:bg-amber-50 hover:text-amber-600 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFunctionOpen(false)}>Reset</Button>
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-6 rounded-[3px] font-normal" onClick={() => setEditFunctionOpen(false)}>Update</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Employee Modal */}
            <Dialog open={editEmployeeOpen} onOpenChange={setEditEmployeeOpen}>
                <DialogContent className="max-w-[600px] bg-white text-gray-900 border-0 p-0 overflow-hidden flex flex-col hide-close-button shadow-2xl [&>button]:hidden rounded-[4px]">
                    <div className="flex justify-between items-center p-3 px-5 bg-white border-b border-gray-200">
                        <h2 className="text-[17px] font-semibold text-gray-800 tracking-wide">Edit Employee</h2>
                        <Button variant="ghost" className="h-7 w-7 p-0 border-[1.5px] border-gray-300 rounded-[2px] hover:bg-gray-100" onClick={() => setEditEmployeeOpen(false)}>
                            <X className="h-4 w-4 text-gray-500 stroke-[3]" />
                        </Button>
                    </div>
                    <div className="p-6 px-10 space-y-5 max-h-[70vh] overflow-y-auto custom-scrollbar">
                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Employee ID <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="4563" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">First Name <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="Alice" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Last Name <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="Konyak" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Date of Joining <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="20/09/2022" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Supervisor <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Housekeeping Manager</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Department <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Housekeeping Manager</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Role <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Housekeeping Manager</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Function <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>Housekeeping Manager</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4 pt-2">
                            <Label className="text-sm font-medium text-gray-800">Status</Label>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input type="radio" name="status" checked className="h-4 w-4 border-gray-300 text-cyan-600 focus:ring-cyan-600" onChange={() => { }} /> Active
                                </label>
                                <label className="flex items-center gap-2 text-sm text-gray-600">
                                    <input type="radio" name="status" className="h-4 w-4 border-gray-300 text-cyan-600 focus:ring-cyan-600" onChange={() => { }} /> In Active
                                </label>
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Email <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="alice@gmail.com" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Country Code <span className="text-red-500">*</span></Label>
                            <div className="relative">
                                <select className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm appearance-none outline-none">
                                    <option>+91</option>
                                </select>
                                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-center gap-4">
                            <Label className="text-sm font-medium text-gray-800">Mobile Number <span className="text-red-500">*</span></Label>
                            <input type="text" defaultValue="9362606433" className="w-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 pb-1 text-sm outline-none" />
                        </div>

                        <div className="grid grid-cols-[160px_1fr] items-start gap-4 h-24 pt-2">
                            <Label className="text-sm font-medium text-gray-800 pt-1">Address</Label>
                            <textarea
                                defaultValue="kerala"
                                className="w-full h-full bg-transparent border-0 border-b border-gray-300 text-gray-500 focus:ring-0 px-0 text-sm outline-none resize-none pt-1"
                            />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 pb-6 mt-2 pt-2 border-t border-gray-100">
                        <Button className="bg-transparent text-[#3eb1c8] border border-[#3eb1c8] hover:bg-cyan-50 h-8 px-8 rounded-[3px] font-normal" onClick={() => setEditEmployeeOpen(false)}>Update</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Employees;




