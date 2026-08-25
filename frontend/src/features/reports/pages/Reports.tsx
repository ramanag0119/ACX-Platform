import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight, Download, FileSpreadsheet, Loader2 } from "lucide-react";
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
import { DataState, TableLoading } from "@/core/components/DataState";
import { useAuth } from "@/core/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { apiClient, describeApiError, type QueryParams } from "@/lib/api/client";
import { useReport, useReportDefinitions } from "@/lib/api/hooks";
import { downloadReportXlsx, type ReportColumn, type ReportFilterSpec } from "@/lib/api/reports";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useQuery } from "@tanstack/react-query";

/**
 * Reports, connected to GET /api/v1/reports.
 *
 * The nine reports and their columns and filters are DECLARED BY THE BACKEND
 * (`app/services/reports.py`) and rendered from that declaration. Nothing about
 * a report's shape is restated here, which is what stops this screen and the
 * Excel export from disagreeing.
 *
 *   GET /reports                    the definitions -> tabs, columns, filters
 *   GET /reports/{key}              a page of rows for the chosen filters
 *   GET /reports/{key}/export.xlsx  the same rows, every page, as a workbook
 *
 * Each report reads through the service that already backs its module, so a row
 * created, edited or soft deleted anywhere in the app appears here on the next
 * Generate.
 *
 * PDF is not offered yet: the layout is being taken from a reference document,
 * and a button that produced a different layout would have to be redone. Excel
 * carries the same rows in the meantime.
 */

/** Rows per page. Capped at the backend's limit so a choice can never 422. */
const PAGE_SIZES = ["10", "25", "50", "100"] as const;

/**
 * The label field differs per lookup table -- `category_name`, `department_name`,
 * `device_name` and so on -- so the first present key wins rather than a
 * per-endpoint special case.
 */
const LABEL_KEYS = [
  "name", "category_name", "department_name", "function_name", "device_name",
  "room_name", "title", "param_name", "user_name", "feature_name",
];

interface Option {
  value: string;
  label: string;
}

function toOption(row: Record<string, unknown>): Option | null {
  const id = row.id ?? row.value;
  if (id === undefined || id === null) return null;
  for (const key of LABEL_KEYS) {
    const candidate = row[key];
    if (typeof candidate === "string" && candidate.trim()) {
      return { value: String(id), label: candidate };
    }
  }
  // `app_user` has no single name column.
  const full = [row.first_name, row.last_name].filter(Boolean).join(" ");
  return { value: String(id), label: full || String(id) };
}

/**
 * Options for a `select` filter, from the real list endpoint the backend named.
 * No option list is hardcoded: a filter the schema cannot populate shows as
 * empty rather than inventing values.
 */
function useFilterOptions(path: string | null) {
  return useQuery({
    queryKey: ["report-filter-options", path],
    enabled: Boolean(path),
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const body = await apiClient.get<unknown>(path as string, {
        page: 1,
        page_size: MAX_PAGE_SIZE,
      });
      // Lookup endpoints return a bare array; paged ones return {items}.
      const rows = Array.isArray(body)
        ? body
        : ((body as { items?: unknown[] })?.items ?? []);
      return rows
        .map((row) => toOption(row as Record<string, unknown>))
        .filter((o): o is Option => o !== null);
    },
  });
}

/** One filter control, rendered from the backend's description of it. */
const FilterField = ({
  spec,
  value,
  onChange,
}: {
  spec: ReportFilterSpec;
  value: string;
  onChange: (next: string) => void;
}) => {
  const options = useFilterOptions(spec.kind === "select" ? spec.options_from : null);

  if (spec.kind === "date") {
    return (
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">{spec.label}</Label>
        <Input
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 bg-muted/20 border-border dark:border-slate-700/80"
        />
      </div>
    );
  }

  if (spec.kind === "boolean") {
    return (
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">{spec.label}</Label>
        <Select value={value || "any"} onValueChange={(v) => onChange(v === "any" ? "" : v)}>
          <SelectTrigger className="h-9 bg-muted/20 border-border dark:border-slate-700/80">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent className="bg-popover text-popover-foreground border-border">
            <SelectItem value="any">Any</SelectItem>
            <SelectItem value="true">Yes</SelectItem>
            <SelectItem value="false">No</SelectItem>
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (spec.kind === "select") {
    return (
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">{spec.label}</Label>
        <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
          <SelectTrigger className="h-9 bg-muted/20 border-border dark:border-slate-700/80">
            <SelectValue placeholder={`All ${spec.label.toLowerCase()}`} />
          </SelectTrigger>
          <SelectContent className="bg-popover text-popover-foreground border-border max-h-72">
            <SelectItem value="all">All</SelectItem>
            {options.isLoading && (
              <div className="px-3 py-2 text-sm text-muted-foreground">Loading...</div>
            )}
            {options.error && (
              <div className="px-3 py-2 text-sm text-muted-foreground">
                {describeApiError(options.error)}
              </div>
            )}
            {(options.data ?? []).map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  // Plain text -- a stay status, a request source, a severity.
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{spec.label}</Label>
      <Input
        value={value}
        placeholder="Any"
        onChange={(e) => onChange(e.target.value)}
        className="h-9 bg-muted/20 border-border dark:border-slate-700/80"
      />
    </div>
  );
};

/** Render one cell according to the column kind the backend declared. */
function formatCell(value: unknown, kind: ReportColumn["kind"]): string {
  if (value === null || value === undefined || value === "") return "-";
  if (kind === "boolean") {
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (typeof value === "number") return value ? "Yes" : "No";
    return String(value);
  }
  if (kind === "date" || kind === "datetime") {
    const parsed = new Date(String(value));
    if (Number.isNaN(parsed.getTime())) return String(value);
    return kind === "date"
      ? parsed.toLocaleDateString()
      : parsed.toLocaleString();
  }
  if (kind === "number") {
    return typeof value === "number" ? value.toLocaleString() : String(value);
  }
  return String(value);
}

const Reports = () => {
  const { canRead } = useAuth();
  const mayRead = canRead("reports");
  const { toast } = useToast();

  const definitionsQuery = useReportDefinitions();
  // Memoised: a fresh [] each render would retrigger the effect below.
  const definitions = useMemo(
    () => definitionsQuery.data ?? [],
    [definitionsQuery.data],
  );

  const [activeKey, setActiveKey] = useState<string>("");
  // Filter values per report, so switching tabs does not lose what was typed.
  const [filterState, setFilterState] = useState<Record<string, Record<string, string>>>({});
  const [generatedKeys, setGeneratedKeys] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<string>("25");
  const [exporting, setExporting] = useState(false);

  // Land on the first report the backend declares rather than a hardcoded tab.
  useEffect(() => {
    if (!activeKey && definitions.length) setActiveKey(definitions[0].key);
  }, [activeKey, definitions]);

  const definition = definitions.find((d) => d.key === activeKey);
  const filters = useMemo(
    () => filterState[activeKey] ?? {},
    [filterState, activeKey],
  );
  const generated = Boolean(generatedKeys[activeKey]);

  /** Only non-empty filters travel; the backend ignores what it does not declare. */
  const activeFilters = useMemo<QueryParams>(() => {
    const out: QueryParams = {};
    for (const [name, value] of Object.entries(filters)) {
      if (value !== "" && value !== undefined) out[name] = value;
    }
    return out;
  }, [filters]);

  const queryParams = useMemo<QueryParams>(
    () => ({ ...activeFilters, page, page_size: Number(pageSize) }),
    [activeFilters, page, pageSize],
  );

  const reportQuery = useReport(activeKey || undefined, queryParams, generated);
  const report = reportQuery.data;
  const columns = report?.columns ?? definition?.columns ?? [];
  const rows = report?.items ?? [];
  const total = report?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / Number(pageSize)));

  const setFilter = (name: string, value: string) => {
    setFilterState((prev) => ({
      ...prev,
      [activeKey]: { ...(prev[activeKey] ?? {}), [name]: value },
    }));
    // A changed filter means page 1; staying on page 7 of a narrower result
    // would show an empty table.
    setPage(1);
  };

  const selectTab = (key: string) => {
    setActiveKey(key);
    setPage(1);
  };

  const generate = () => {
    setPage(1);
    setGeneratedKeys((prev) => ({ ...prev, [activeKey]: true }));
    // Already generated once: pick up any filter change immediately.
    if (generated) void reportQuery.refetch();
  };

  const resetFilters = () => {
    setFilterState((prev) => ({ ...prev, [activeKey]: {} }));
    setPage(1);
  };

  const exportExcel = async () => {
    if (!definition) return;
    setExporting(true);
    try {
      const filename = await downloadReportXlsx(definition.key, activeFilters);
      toast({ title: "Report downloaded", description: filename });
    } catch (error) {
      toast({
        title: "Download failed",
        description: describeApiError(error),
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  if (!mayRead) {
    return (
      <div className="space-y-6 animate-fade-in">
        <h1 className="text-xl font-semibold text-foreground tracking-tight">Reports</h1>
        <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card">
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            Your role does not grant access to reports.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in text-foreground">
      <div className="mb-2">
        <h1 className="text-xl font-semibold text-foreground tracking-tight">Reports</h1>
        <p className="text-xs text-muted-foreground mt-1">
          Every report reads the live HMS database through the module that owns
          the data, so it always reflects the latest records.
        </p>
      </div>

      {/* Tabs come from the backend's report list, not a local array. */}
      <div className="flex gap-1 flex-wrap border-b border-border/70 dark:border-slate-800">
        {definitionsQuery.isLoading && (
          <div className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading reports...
          </div>
        )}
        {definitionsQuery.error && (
          <div className="py-3 text-sm text-muted-foreground">
            {describeApiError(definitionsQuery.error)}
          </div>
        )}
        {definitions.map((report) => (
          <button
            key={report.key}
            onClick={() => selectTab(report.key)}
            className={`relative px-3 pb-3 pt-1 text-sm font-medium transition-colors ${
              activeKey === report.key
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {report.title}
            {activeKey === report.key && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#5865F2] rounded-full" />
            )}
          </button>
        ))}
      </div>

      {definition && (
        <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card">
          <CardContent className="p-6 space-y-6">
            <div>
              <h2 className="text-base font-semibold text-foreground">{definition.title}</h2>
              <p className="text-xs text-muted-foreground mt-1">{definition.description}</p>
              <p className="text-[11px] text-muted-foreground/80 mt-1 font-mono">
                Source: {definition.source}
              </p>
            </div>

            {/* Filters, rendered from what this report declares it accepts. */}
            {definition.filters.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {definition.filters.map((spec) => (
                  <FilterField
                    key={spec.name}
                    spec={spec}
                    value={filters[spec.name] ?? ""}
                    onChange={(next) => setFilter(spec.name, next)}
                  />
                ))}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-border/40">
              <Button
                onClick={generate}
                disabled={reportQuery.isFetching}
                className="h-10 px-8 min-w-[170px] rounded-xl bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
              >
                {reportQuery.isFetching ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Generating...
                  </>
                ) : (
                  "Generate Report"
                )}
              </Button>

              <Button
                variant="outline"
                onClick={exportExcel}
                disabled={!generated || exporting || total === 0}
                title={
                  total === 0
                    ? "Generate a report with at least one row first"
                    : "Download every matching row as .xlsx"
                }
                className="h-10 px-6 rounded-xl border-border hover:bg-muted font-medium text-sm"
              >
                {exporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <FileSpreadsheet className="h-4 w-4 mr-2" />
                )}
                Excel (.xlsx)
              </Button>

              <Button
                variant="ghost"
                onClick={resetFilters}
                className="h-10 px-4 text-muted-foreground hover:text-foreground text-sm"
              >
                Reset filters
              </Button>

              {generated && (
                <span className="text-xs text-muted-foreground ml-auto">
                  {total.toLocaleString()} row{total === 1 ? "" : "s"}
                </span>
              )}
            </div>

            {/* What the backend actually applied -- not what was typed. */}
            {generated && report && Object.keys(report.filters_applied).length > 0 && (
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.filters_applied).map(([name, value]) => {
                  const label =
                    definition.filters.find((f) => f.name === name)?.label ?? name;
                  return (
                    <Badge key={name} variant="outline" className="text-[11px] font-normal">
                      {label}: {value}
                    </Badge>
                  );
                })}
              </div>
            )}

            {/* Results */}
            {!generated ? (
              <div className="rounded-lg border border-dashed border-border/80 dark:border-slate-800 py-12 text-center">
                <Download className="h-6 w-6 mx-auto text-muted-foreground/60 mb-3" />
                <p className="text-sm text-muted-foreground">
                  Choose your filters, then select Generate Report.
                </p>
              </div>
            ) : (
              <>
                <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                      <TableRow className="border-b border-border dark:border-slate-800">
                        {columns.map((column) => (
                          <TableHead
                            key={column.key}
                            className={`text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3 whitespace-nowrap ${
                              column.kind === "number" ? "text-right" : ""
                            }`}
                          >
                            {column.header}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reportQuery.isLoading || reportQuery.error || rows.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={Math.max(columns.length, 1)} className="py-2">
                            <DataState
                              isLoading={reportQuery.isLoading}
                              error={reportQuery.error}
                              isEmpty
                              emptyTitle="No rows matched this report"
                              emptyDescription="Widen the date range or clear a filter."
                              loader={<TableLoading columns={Math.max(columns.length, 1)} />}
                            >
                              <span />
                            </DataState>
                          </TableCell>
                        </TableRow>
                      ) : (
                        rows.map((row, index) => (
                          <TableRow
                            key={index}
                            className={`${
                              index % 2 === 0
                                ? "bg-card dark:bg-[#101526]/80"
                                : "bg-muted/10 dark:bg-[#0d1120]/80"
                            } hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}
                          >
                            {columns.map((column) => (
                              <TableCell
                                key={column.key}
                                className={`text-xs py-2.5 px-3 text-foreground/90 ${
                                  column.kind === "number" ? "text-right" : ""
                                }`}
                              >
                                {formatCell(row[column.key], column.kind)}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Show</span>
                    <Select
                      value={pageSize}
                      onValueChange={(value) => {
                        setPageSize(value);
                        setPage(1);
                      }}
                    >
                      <SelectTrigger className="w-20 h-8 bg-muted/20 border-border dark:border-slate-700/80 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-popover text-popover-foreground border-border">
                        {PAGE_SIZES.map((size) => (
                          <SelectItem key={size} value={size}>
                            {size}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <span className="text-xs text-muted-foreground">
                      of {total.toLocaleString()} entries
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setPage(1)}
                      disabled={page === 1}
                    >
                      First
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                      Previous
                    </Button>
                    <span className="text-xs text-muted-foreground px-2">
                      Page {Math.min(page, totalPages)} of {totalPages}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page >= totalPages}
                    >
                      Next
                      <ChevronRight className="h-3.5 w-3.5 ml-1" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setPage(totalPages)}
                      disabled={page >= totalPages}
                    >
                      Last
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Reports;
