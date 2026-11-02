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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Pencil, Trash2, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useDeviceParams, useDevices, useLimitConfigs } from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import {
  useCreateLimitConfig,
  useDeleteLimitConfig,
  useUpdateLimitConfig,
} from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";
import { toast } from "@/hooks/use-toast";
import { describeApiError } from "@/lib/api/client";
import type { LimitConfigRead } from "@/lib/api/writes";

/**
 * Limit Config Alert, connected to the Phase 2.7 / 2.9 APIs.
 *
 *   Parameter list -> GET /device-params  (the real telemetry parameter names)
 *   Device list    -> GET /devices
 *   Table          -> GET /value-alerts   (the recorded limit breaches)
 *
 * The table now lists the CONFIGURATIONS themselves (GET /limit-configs, new in
 * Phase 3.0) rather than the breaches, because that is what this screen edits.
 * `is_percentage_value` selects which pair of limit columns applies, and the
 * backend stores the IKANOS text flags ('Y' / 'yes') behind the booleans.
 *
 * Both /device-params and /value-alerts are gated on `caleido_network` by the
 * backend, which is the module this route is guarded with.
 */

const LimitConfigAlert = () => {
    // Table state
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = parseInt(entriesPerPage) || 10;

    // --- Live data -------------------------------------------------------
    const paramsQuery = useDeviceParams({ page: 1, page_size: MAX_PAGE_SIZE });
    const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE });
    const configsQuery = useLimitConfigs({
        page: currentPage,
        page_size: pageSize,
        q: searchQuery || undefined,
    });

    const { canWrite } = useAuth();
    const mayWrite = canWrite("caleido_network");

    // --- Mutations
    const createConfig = useCreateLimitConfig();
    const updateConfig = useUpdateLimitConfig();
    const deleteConfig = useDeleteLimitConfig();

    // `param_name` is not unique across device types, so de-duplicate by name.
    const parameterOptions = [
        ...new Map(
            (paramsQuery.data?.items ?? []).map((param) => [param.param_name, {
                id: String(param.id),
                name: param.unit ? `${param.param_name} (${param.unit})` : param.param_name,
            }]),
        ).values(),
    ].sort((a, b) => a.name.localeCompare(b.name));

    const deviceNameOptions = (devicesQuery.data?.items ?? []).map((device) => ({
        id: device.id,
        name: [device.device_name, device.appliance_name].filter(Boolean).join(" - ")
            || device.device_uid
            || device.id,
    }));

    // Every column is a real `value_alert_limit_config` column, with room mapped from device.
    const limitConfigData = (configsQuery.data?.items ?? []).map((config) => ({
        id: config.id,
        parameter: config.parameter,
        deviceName: config.device_name,
        roomNo: config.room_number ?? "-",
        limitCheck: config.limit_check ? "Yes" : "No",
        limitBy: config.is_percentage_value ? "Percentage" : "Value",
        nominal: config.nominal ?? "-",
        limitLow: config.limit_low_percentage ?? "-",
        limitHigh: config.limit_high_percentage ?? "-",
        limitLowValue: config.limit_low_value ?? "-",
        limitHighValue: config.limit_high_value ?? "-",
        description: config.remarks,
        timestamp: new Date(config.updated_on).toLocaleString(),
        isPercentage: config.is_percentage_value,
        raw: config,
    }));

    // Form state
    const [parameter, setParameter] = useState("");
    const [deviceName, setDeviceName] = useState("");
    const [limitCheck, setLimitCheck] = useState("yes");
    const [limitBy, setLimitBy] = useState("percentage");
    const [nominal, setNominal] = useState("");
    const [limitLow, setLimitLow] = useState("");
    const [limitHigh, setLimitHigh] = useState("");
    const [comments, setComments] = useState("");

    // Edit state
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [editingConfig, setEditingConfig] = useState<LimitConfigRead | null>(null);
    const [editParameter, setEditParameter] = useState("");
    const [editDeviceName, setEditDeviceName] = useState("");
    const [editLimitCheck, setEditLimitCheck] = useState("yes");
    const [editLimitBy, setEditLimitBy] = useState("percentage");
    const [editNominal, setEditNominal] = useState("");
    const [editLimitLow, setEditLimitLow] = useState("");
    const [editLimitHigh, setEditLimitHigh] = useState("");
    const [editComments, setEditComments] = useState("");

    // Delete state
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [configToDelete, setConfigToDelete] = useState<LimitConfigRead | null>(null);

    // Pagination sits at the bottom of the table; without this the new
    // page kept the old scroll offset and the sticky header stayed
    // above the fold. See use-scroll-to-top.
    useScrollToTop(currentPage);

    const totalEntries = configsQuery.data?.total ?? 0;
    const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
    const startIndex = totalEntries === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const endIndex = Math.min(currentPage * pageSize, totalEntries);
    const paginatedData = limitConfigData;

    const handleReset = () => {
        setParameter("");
        setDeviceName("");
        setLimitCheck("yes");
        setLimitBy("percentage");
        setNominal("");
        setLimitLow("");
        setLimitHigh("");
        setComments("");
    };

    /**
     * Create a monitoring threshold.
     *
     * `limit_by` picks which pair of columns is written: the percentage pair or
     * the absolute pair. The backend rejects a low limit that is not below the
     * high one, and the (device_name, parameter, facility) triple is unique.
     */
    const handleSubmit = () => {
        const device = (devicesQuery.data?.items ?? []).find((row) =>
            row.id === deviceName ||
            row.device_name === deviceName ||
            [row.device_name, row.appliance_name].filter(Boolean).join(" - ") === deviceName
        );
        if (!parameter || !device) return;
        const byPercentage = limitBy === "percentage";
        createConfig.mutate(
            {
                parameter,
                device_name: device.device_name ?? device.device_uid ?? "",
                device_id: device.id,
                limit_check: limitCheck === "yes",
                is_percentage_value: byPercentage,
                nominal: nominal || null,
                ...(byPercentage
                    ? { limit_low_percentage: limitLow || null, limit_high_percentage: limitHigh || null }
                    : { limit_low_value: limitLow || null, limit_high_value: limitHigh || null }),
                remarks: comments || "",
            },
            { onSuccess: handleReset },
        );
    };

    const handleOpenEdit = (config: LimitConfigRead) => {
        setEditingConfig(config);
        setEditParameter(config.parameter);
        setEditDeviceName(config.device_name);
        setEditLimitCheck(config.limit_check ? "yes" : "no");
        setEditLimitBy(config.is_percentage_value ? "percentage" : "limit-value");
        setEditNominal(config.nominal ?? "");
        if (config.is_percentage_value) {
            setEditLimitLow(config.limit_low_percentage ?? "");
            setEditLimitHigh(config.limit_high_percentage ?? "");
        } else {
            setEditLimitLow(config.limit_low_value ?? "");
            setEditLimitHigh(config.limit_high_value ?? "");
        }
        setEditComments(config.remarks ?? "");
        setEditModalOpen(true);
    };

    const handleResetEdit = () => {
        if (!editingConfig) return;
        setEditParameter(editingConfig.parameter);
        setEditDeviceName(editingConfig.device_name);
        setEditLimitCheck(editingConfig.limit_check ? "yes" : "no");
        setEditLimitBy(editingConfig.is_percentage_value ? "percentage" : "limit-value");
        setEditNominal(editingConfig.nominal ?? "");
        if (editingConfig.is_percentage_value) {
            setEditLimitLow(editingConfig.limit_low_percentage ?? "");
            setEditLimitHigh(editingConfig.limit_high_percentage ?? "");
        } else {
            setEditLimitLow(editingConfig.limit_low_value ?? "");
            setEditLimitHigh(editingConfig.limit_high_value ?? "");
        }
        setEditComments(editingConfig.remarks ?? "");
    };

    const handleEditSubmit = () => {
        if (!editingConfig) return;
        if (!editParameter.trim() || !editDeviceName.trim()) {
            toast({
                title: "Required fields missing",
                description: "Parameter and Device Name are required.",
                variant: "destructive",
            });
            return;
        }

        const byPercentage = editLimitBy === "percentage";
        const lowNum = editLimitLow ? parseFloat(editLimitLow) : null;
        const highNum = editLimitHigh ? parseFloat(editLimitHigh) : null;

        if (lowNum !== null && highNum !== null && lowNum >= highNum) {
            toast({
                title: "Invalid limits",
                description: `Low ${byPercentage ? "percentage" : "value"} limit must be below the high limit.`,
                variant: "destructive",
            });
            return;
        }

        const matchedDevice = (devicesQuery.data?.items ?? []).find((row) =>
            row.id === editDeviceName ||
            row.device_name === editDeviceName ||
            [row.device_name, row.appliance_name].filter(Boolean).join(" - ") === editDeviceName
        );

        updateConfig.mutate(
            {
                id: editingConfig.id,
                body: {
                    parameter: editParameter.trim(),
                    device_name: matchedDevice ? (matchedDevice.device_name ?? matchedDevice.device_uid ?? editDeviceName) : editDeviceName,
                    ...(matchedDevice ? { device_id: matchedDevice.id } : {}),
                    limit_check: editLimitCheck === "yes",
                    is_percentage_value: byPercentage,
                    nominal: editNominal || null,
                    ...(byPercentage
                        ? { limit_low_percentage: editLimitLow || null, limit_high_percentage: editLimitHigh || null, limit_low_value: null, limit_high_value: null }
                        : { limit_low_value: editLimitLow || null, limit_high_value: editLimitHigh || null, limit_low_percentage: null, limit_high_percentage: null }),
                    remarks: editComments || "",
                },
            },
            {
                onSuccess: () => {
                    setEditModalOpen(false);
                    setEditingConfig(null);
                },
                onError: (err) => {
                    toast({
                        title: "Failed to update configuration",
                        description: describeApiError(err),
                        variant: "destructive",
                    });
                },
            }
        );
    };

    const handleOpenDelete = (config: LimitConfigRead) => {
        setConfigToDelete(config);
        setDeleteModalOpen(true);
    };

    const handleConfirmDelete = () => {
        if (!configToDelete) return;
        deleteConfig.mutate(configToDelete.id, {
            onSuccess: () => {
                setDeleteModalOpen(false);
                setConfigToDelete(null);
            },
            onError: (err) => {
                toast({
                    title: "Cannot delete configuration",
                    description: describeApiError(err),
                    variant: "destructive",
                });
            },
        });
    };

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            <PageHeader title="Limit Config Alert" />

            {/* Form Section */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground">
                <CardContent className="p-6">
                    <div className="space-y-6">
                        {/* Parameter */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Parameter<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={parameter} onValueChange={setParameter}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Parameter" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {parameterOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            parameterOptions.map(param => (
                                                <SelectItem key={param.id} value={param.name}>{param.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Device Name */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Device Name<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={deviceName} onValueChange={setDeviceName}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Device Name" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {deviceNameOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            deviceNameOptions.map(device => (
                                                <SelectItem key={device.id} value={device.name}>{device.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Limit Check */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit Check</Label>
                            <div className="col-span-2">
                                <RadioGroup value={limitCheck} onValueChange={setLimitCheck} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="yes" id="limit-check-yes" />
                                        <Label htmlFor="limit-check-yes" className="cursor-pointer">Yes</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="no" id="limit-check-no" />
                                        <Label htmlFor="limit-check-no" className="cursor-pointer">No</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Limit By */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit By</Label>
                            <div className="col-span-2">
                                <RadioGroup value={limitBy} onValueChange={setLimitBy} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="percentage" id="limit-by-percentage" />
                                        <Label htmlFor="limit-by-percentage" className="cursor-pointer">Percentage</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="limit-value" id="limit-by-value" />
                                        <Label htmlFor="limit-by-value" className="cursor-pointer">Limit Value</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Nominal */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Nominal<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Nominal"
                                    value={nominal}
                                    onChange={(e) => setNominal(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Limit Low (%) */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit Low (%)<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Limit Low"
                                    value={limitLow}
                                    onChange={(e) => setLimitLow(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Limit High (%) */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit High (%)<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Limit High"
                                    value={limitHigh}
                                    onChange={(e) => setLimitHigh(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Comments/Remarks */}
                        <div className="grid grid-cols-3 gap-4 items-start">
                            <Label className="text-sm font-medium text-right pt-2">Comments/Remarks</Label>
                            <div className="col-span-2">
                                <Textarea
                                    placeholder="Enter Your Remarks"
                                    value={comments}
                                    onChange={(e) => setComments(e.target.value)}
                                    className="bg-muted/30 border-border/50 min-h-[80px]"
                                />
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex justify-center gap-4">
                            <Button onClick={handleReset} variant="outline" className="px-8 border-red-500 text-red-500 hover:bg-red-50">
                                Reset
                            </Button>
                            <Button onClick={handleSubmit} className="h-10 px-8 min-w-[160px] rounded-xl bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all">
                                Submit
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table Section */}
            <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
                <CardContent className="p-5">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-xs font-medium">Show</span>
                            <Select value={entriesPerPage} onValueChange={(val) => { setEntriesPerPage(val); setCurrentPage(1); }}>
                                <SelectTrigger className="w-18 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                                    <SelectItem value="10">10</SelectItem>
                                    <SelectItem value="25">25</SelectItem>
                                    <SelectItem value="50">50</SelectItem>
                                </SelectContent>
                            </Select>
                            <span className="text-muted-foreground text-xs font-medium">entries</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground text-xs font-medium">Search:</span>
                            <Input
                                placeholder="Device Name"
                                value={searchQuery}
                                onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                                className="w-64 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                            />
                        </div>
                    </div>

                    <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto scrollbar-thin">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Parameter</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Device Name</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Room No.</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Limit Check</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Limit By</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Nominal</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Limit Low (%)</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Limit High (%)</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Limit Low Value</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 whitespace-nowrap">Limit High Value</TableHead>
                                    <TableHead className="text-muted-foreground dark:text-slate-400 font-semibold text-xs py-3 px-4 text-center">Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {configsQuery.isLoading || configsQuery.error || paginatedData.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={11} className="py-2">
                                            <DataState
                                                isLoading={configsQuery.isLoading}
                                                error={configsQuery.error}
                                                isEmpty
                                                emptyTitle="No limit configurations yet"
                                                loader={<TableLoading columns={11} />}
                                            >
                                                <span />
                                            </DataState>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    paginatedData.map((item) => (
                                        <TableRow key={item.id} className="hover:bg-[var(--hms-table-row-hover-bg)] border-b border-border/50 dark:border-slate-800/70 transition-colors">
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.parameter}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 font-medium text-foreground">{item.deviceName}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.roomNo}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitCheck}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitBy}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.nominal}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitLow}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitHigh}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitLowValue}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitHighValue}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <div className="flex gap-1.5 justify-center">
                                                    <Button
                                                        size="sm"
                                                        className="h-7 w-7 p-0 rounded-md"
                                                        disabled={!mayWrite}
                                                        title={!mayWrite ? "Permission required" : "Edit configuration"}
                                                        onClick={() => handleOpenEdit(item.raw)}
                                                    >
                                                        <Pencil className="h-3.5 w-3.5 text-white" />
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        className="bg-red-500 hover:bg-red-600 h-7 w-7 p-0 rounded-md"
                                                        disabled={!mayWrite || deleteConfig.isPending}
                                                        title={!mayWrite ? "Permission required" : "Delete configuration"}
                                                        onClick={() => handleOpenDelete(item.raw)}
                                                    >
                                                        <Trash2 className="h-3.5 w-3.5 text-white" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
                        <span className="text-muted-foreground text-xs">
                            Showing {totalEntries > 0 ? startIndex : 0} to {endIndex} of {totalEntries} entries
                        </span>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                <Button key={page} variant={currentPage === page ? "default" : "ghost"} size="sm" className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`} onClick={() => setCurrentPage(page)}>{page}</Button>
                            ))}
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
                            <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Edit Limit Config Modal */}
            <Dialog open={editModalOpen} onOpenChange={(open) => !updateConfig.isPending && setEditModalOpen(open)}>
                <DialogContent className="max-w-[650px] max-h-[90vh] overflow-y-auto bg-card text-card-foreground border border-border shadow-2xl rounded-xl p-0 [&>button]:hidden">
                    <div className="flex justify-between items-center p-4 px-6 border-b border-border bg-muted/20">
                        <h2 className="text-lg font-semibold text-foreground">Edit Limit Configuration</h2>
                        <Button variant="ghost" className="h-8 w-8 p-0 rounded-md hover:bg-muted" onClick={() => setEditModalOpen(false)}>
                            <X className="h-4 w-4 text-muted-foreground" />
                        </Button>
                    </div>

                    <div className="p-6 space-y-5">
                        {/* Parameter */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Parameter<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={editParameter} onValueChange={setEditParameter}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Parameter" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {parameterOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            parameterOptions.map(param => (
                                                <SelectItem key={param.id} value={param.name}>{param.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Device Name */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Device Name<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Select value={editDeviceName} onValueChange={setEditDeviceName}>
                                    <SelectTrigger className="bg-muted/30 border-border/50">
                                        <SelectValue placeholder="Select Device Name" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-popover">
                                        {deviceNameOptions.length === 0 ? (
                                            <div className="py-3 px-4 text-muted-foreground text-sm">No data available</div>
                                        ) : (
                                            deviceNameOptions.map(device => (
                                                <SelectItem key={device.id} value={device.name}>{device.name}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Limit Check */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit Check</Label>
                            <div className="col-span-2">
                                <RadioGroup value={editLimitCheck} onValueChange={setEditLimitCheck} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="yes" id="edit-limit-check-yes" />
                                        <Label htmlFor="edit-limit-check-yes" className="cursor-pointer">Yes</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="no" id="edit-limit-check-no" />
                                        <Label htmlFor="edit-limit-check-no" className="cursor-pointer">No</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Limit By */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Limit By</Label>
                            <div className="col-span-2">
                                <RadioGroup value={editLimitBy} onValueChange={setEditLimitBy} className="flex gap-6">
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="percentage" id="edit-limit-by-percentage" />
                                        <Label htmlFor="edit-limit-by-percentage" className="cursor-pointer">Percentage</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <RadioGroupItem value="limit-value" id="edit-limit-by-value" />
                                        <Label htmlFor="edit-limit-by-value" className="cursor-pointer">Limit Value</Label>
                                    </div>
                                </RadioGroup>
                            </div>
                        </div>

                        {/* Nominal */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">Nominal<span className="text-red-500">*</span></Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Nominal"
                                    value={editNominal}
                                    onChange={(e) => setEditNominal(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Limit Low */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">
                                {editLimitBy === "percentage" ? "Limit Low (%)" : "Limit Low Value"}<span className="text-red-500">*</span>
                            </Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Limit Low"
                                    value={editLimitLow}
                                    onChange={(e) => setEditLimitLow(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Limit High */}
                        <div className="grid grid-cols-3 gap-4 items-center">
                            <Label className="text-sm font-medium text-right">
                                {editLimitBy === "percentage" ? "Limit High (%)" : "Limit High Value"}<span className="text-red-500">*</span>
                            </Label>
                            <div className="col-span-2">
                                <Input
                                    placeholder="Enter Limit High"
                                    value={editLimitHigh}
                                    onChange={(e) => setEditLimitHigh(e.target.value)}
                                    className="bg-muted/30 border-border/50"
                                />
                            </div>
                        </div>

                        {/* Comments/Remarks */}
                        <div className="grid grid-cols-3 gap-4 items-start">
                            <Label className="text-sm font-medium text-right pt-2">Comments/Remarks</Label>
                            <div className="col-span-2">
                                <Textarea
                                    placeholder="Enter Your Remarks"
                                    value={editComments}
                                    onChange={(e) => setEditComments(e.target.value)}
                                    className="bg-muted/30 border-border/50 min-h-[80px]"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 p-4 px-6 border-t border-border bg-muted/20">
                        <Button
                            variant="outline"
                            onClick={handleResetEdit}
                            disabled={updateConfig.isPending}
                            className="rounded-lg px-5"
                        >
                            Reset
                        </Button>
                        <Button
                            onClick={handleEditSubmit}
                            disabled={updateConfig.isPending}
                            className="bg-brand hover:bg-brand-hover text-white rounded-lg px-6 font-semibold"
                        >
                            {updateConfig.isPending ? "Updating..." : "Update"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteModalOpen} onOpenChange={(open) => !deleteConfig.isPending && setDeleteModalOpen(open)}>
                <DialogContent className="max-w-[440px] bg-card text-card-foreground border border-border p-6 overflow-hidden rounded-xl shadow-2xl [&>button]:hidden">
                    <div className="flex flex-col space-y-4">
                        <div className="flex items-center gap-3 text-red-600">
                            <div className="p-2 bg-red-100 dark:bg-red-950/50 rounded-full">
                                <Trash2 className="h-5 w-5" />
                            </div>
                            <h3 className="text-lg font-semibold text-foreground">
                                Delete Limit Configuration
                            </h3>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Are you sure you want to delete the configuration for <span className="font-semibold text-foreground">"{configToDelete?.parameter}"</span> on device <span className="font-semibold text-foreground">"{configToDelete?.device_name}"</span>?
                        </p>
                        <div className="flex justify-end gap-3 pt-4 border-t border-border">
                            <Button
                                variant="outline"
                                disabled={deleteConfig.isPending}
                                onClick={() => {
                                    setDeleteModalOpen(false);
                                    setConfigToDelete(null);
                                }}
                                className="rounded-lg px-4"
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="destructive"
                                disabled={deleteConfig.isPending}
                                onClick={handleConfirmDelete}
                                className="rounded-lg px-4"
                            >
                                {deleteConfig.isPending ? "Deleting..." : "Delete"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default LimitConfigAlert;




