import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/core/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { describeApiError, type QueryParams } from "@/lib/api/client";
import { useReport, useReportDefinitions } from "@/lib/api/hooks";
import { downloadReportXlsx } from "@/lib/api/reports";
import { PageHeader } from "@/components/layout/PageHeader";
import { getReportMeta } from "../lib/reportMeta";
import { ReportHeader } from "../components/ReportHeader";
import { ReportFilters } from "../components/ReportFilters";
import { ReportSummaryCards } from "../components/ReportSummaryCards";
import { ReportTableContainer } from "../components/ReportTableContainer";
import { ReportEmptyState } from "../components/ReportEmptyState";

/**
 * Enterprise Reports Dashboard
 * Connected to GET /api/v1/reports.
 *
 * Uses clean, underline-based report navigation matching the Service Planning
 * design language, with consistent spacing, standardized filters, and structured data tables.
 */
const Reports = () => {
  const { canRead } = useAuth();
  const mayRead = canRead("reports");
  const { toast } = useToast();

  const location = useLocation();
  const navigate = useNavigate();

  const definitionsQuery = useReportDefinitions();
  const definitions = useMemo(
    () => definitionsQuery.data ?? [],
    [definitionsQuery.data],
  );

  const [activeKey, setActiveKey] = useState<string>("");
  const [filterState, setFilterState] = useState<Record<string, Record<string, string>>>({});
  const [generatedKeys, setGeneratedKeys] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<string>("25");
  const [exporting, setExporting] = useState(false);

  // Addressable tab routing: /reports/occupancy, /reports/energy, etc.
  const urlKey = decodeURIComponent(location.pathname.replace(/^\/reports\/?/, "")).split("/")[0];

  useEffect(() => {
    if (activeKey || !definitions.length) return;
    const fromUrl = definitions.find((d) => d.key === urlKey);
    setActiveKey(fromUrl ? fromUrl.key : definitions[0].key);
  }, [activeKey, definitions, urlKey]);

  const definition = definitions.find((d) => d.key === activeKey);
  const meta = useMemo(
    () => getReportMeta(activeKey, definition?.title, definition?.description),
    [activeKey, definition],
  );

  const filters = useMemo(
    () => filterState[activeKey] ?? {},
    [filterState, activeKey],
  );
  const generated = Boolean(generatedKeys[activeKey]);

  /** Non-empty filters for API query */
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
    setPage(1);
  };

  const selectTab = (key: string) => {
    setActiveKey(key);
    setPage(1);
    navigate(`/reports/${key}`, { replace: true });
  };

  const generate = () => {
    setPage(1);
    setGeneratedKeys((prev) => ({ ...prev, [activeKey]: true }));
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
        <PageHeader title="Reports" />
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
      <PageHeader
        title="Reports"
        description="Access real-time operational, occupancy, employee, and facility reports across property operations."
      />

      {/* Clean Underline-based Report Navigation Tabs (matching Service Planning pattern) */}
      <div
        className="flex gap-6 border-b border-border dark:border-slate-800 overflow-x-auto [&::-webkit-scrollbar]:hidden"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {definitionsQuery.isLoading && (
          <div className="flex items-center gap-2 py-3 text-xs text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading reports...
          </div>
        )}
        {definitionsQuery.error && (
          <div className="py-3 text-xs text-destructive">
            {describeApiError(definitionsQuery.error)}
          </div>
        )}
        {definitions.map((r) => {
          const itemMeta = getReportMeta(r.key, r.title);
          const isActive = activeKey === r.key;
          return (
            <button
              key={r.key}
              type="button"
              onClick={() => selectTab(r.key)}
              className={`relative px-1 pb-3 text-sm font-medium whitespace-nowrap bg-transparent border-0 transition-all duration-200 focus:outline-none focus-visible:ring-1 focus-visible:ring-primary ${
                isActive
                  ? "text-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {itemMeta.title}
              {isActive && (
                <span className="absolute -bottom-[1px] left-0 right-0 h-[2px] bg-primary rounded-t-full z-10" />
              )}
            </button>
          );
        })}
      </div>

      {definition && (
        <div className="space-y-6">
          {/* Standard Report Header */}
          <ReportHeader
            title={meta.title}
            category={meta.category}
            description={meta.description}
            isGenerated={generated}
            totalRecords={total}
          />

          {/* Standard Filter Section */}
          <ReportFilters
            filterSpecs={definition.filters}
            filterValues={filters}
            onFilterChange={setFilter}
            onGenerate={generate}
            onReset={resetFilters}
            onExport={exportExcel}
            isGenerating={reportQuery.isFetching}
            isExporting={exporting}
            isGenerated={generated}
            totalRecords={total}
            filtersApplied={report?.filters_applied ?? {}}
          />

          {/* Pre-generation empty state */}
          {!generated ? (
            <ReportEmptyState
              reportTitle={meta.title}
              onGenerate={generate}
              isLoading={reportQuery.isFetching}
            />
          ) : (
            <>
              {/* Summary / KPI Cards */}
              <ReportSummaryCards
                reportKey={activeKey}
                total={total}
                rows={rows}
                filtersApplied={report?.filters_applied ?? {}}
                page={page}
                totalPages={totalPages}
              />

              {/* Data Table with Standard Pagination */}
              <ReportTableContainer
                columns={columns}
                rows={rows}
                total={total}
                page={page}
                pageSize={pageSize}
                totalPages={totalPages}
                isLoading={reportQuery.isLoading}
                error={reportQuery.error}
                onPageChange={(nextPage) => setPage(nextPage)}
                onPageSizeChange={(nextSize) => {
                  setPageSize(nextSize);
                  setPage(1);
                }}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Reports;
