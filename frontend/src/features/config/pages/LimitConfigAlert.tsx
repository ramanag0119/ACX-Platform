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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Pencil, Trash2 } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { DataState, TableLoading } from "@/core/components/DataState";
import { useDeviceParams, useDevices, useLimitConfigs } from "@/lib/api/hooks";
import { useAuth } from "@/core/contexts/AuthContext";
import { useCreateLimitConfig, useUpdateLimitConfig } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

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
    // --- Live data -------------------------------------------------------
    const paramsQuery = useDeviceParams({ page: 1, page_size: MAX_PAGE_SIZE });
    const devicesQuery = useDevices({ page: 1, page_size: MAX_PAGE_SIZE });
    const configsQuery = useLimitConfigs({ page: 1, page_size: MAX_PAGE_SIZE });

    // --- Mutations
    const { canWrite } = useAuth();
    const mayWrite = canWrite("caleido_network");
    const createConfig = useCreateLimitConfig();
    const updateConfig = useUpdateLimitConfig();

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

    // Every column is a real `value_alert_limit_config` column now.
    const limitConfigData = (configsQuery.data?.items ?? []).map((config) => ({
        id: config.id,
        parameter: config.parameter,
        deviceName: config.device_name,
        roomNo: "-",
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

    // Table state
    const [searchQuery, setSearchQuery] = useState("");
    const [entriesPerPage, setEntriesPerPage] = useState("10");
    const [currentPage, setCurrentPage] = useState(1);

    // Filter data
    const filteredData = limitConfigData.filter(item =>
        item.deviceName?.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(filteredData.length / parseInt(entriesPerPage));
    const startIndex = (currentPage - 1) * parseInt(entriesPerPage);
    const endIndex = startIndex + parseInt(entriesPerPage);
    const paginatedData = filteredData.slice(startIndex, endIndex);

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
        const device = (devicesQuery.data?.items ?? []).find((row) => row.id === deviceName);
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

    return (
        <div className="space-y-6 animate-fade-in text-foreground">
            {/* Header */}
            <div className="mb-2">
                <h1 className="text-xl font-semibold text-foreground tracking-tight">Limit Config Alert</h1>
            </div>

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
                                        <TableCell colSpan={10} className="py-2">
                                            <DataState
                                                isLoading={configsQuery.isLoading}
                                                error={configsQuery.error}
                                                isEmpty
                                                emptyTitle="No limit configurations yet"
                                                loader={<TableLoading columns={10} />}
                                            >
                                                <span />
                                            </DataState>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    paginatedData.map((item, index) => (
                                        <TableRow key={index} className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.parameter}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 font-medium text-foreground">{item.deviceName}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitCheck}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitBy}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.nominal}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitLow}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitHigh}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitLowValue}</TableCell>
                                            <TableCell className="whitespace-nowrap text-xs py-3 px-4 text-foreground/90">{item.limitHighValue}</TableCell>
                                            <TableCell className="text-center py-3 px-4">
                                                <div className="flex gap-1.5 justify-center">
                                                    <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700 h-7 w-7 p-0 rounded-md">
                                                        <Pencil className="h-3.5 w-3.5 text-white" />
                                                    </Button>
                                                    <Button size="sm" className="bg-red-500 hover:bg-red-600 h-7 w-7 p-0 rounded-md">
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
                            Showing {filteredData.length > 0 ? startIndex + 1 : 0} to {Math.min(endIndex, filteredData.length)} of {filteredData.length} entries
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
        </div>
    );
};

export default LimitConfigAlert;




