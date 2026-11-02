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
  FileSpreadsheet,
  Loader2,
  Play,
  RotateCcw,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiClient, describeApiError } from "@/lib/api/client";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import type { ReportFilterSpec } from "@/lib/api/reports";

const LABEL_KEYS = [
  "name",
  "amenity_status_name",
  "category_name",
  "department_name",
  "function_name",
  "device_name",
  "room_name",
  "title",
  "param_name",
  "user_name",
  "feature_name",
  "display_name",
  "label",
  "description",
];

const STATUS_LABELS: Record<string | number, string> = {
  0: "Available",
  1: "Occupied",
  2: "Unavailable",
  3: "Allotted",
};

interface Option {
  value: string;
  label: string;
}

function toOption(row: Record<string, unknown>): Option | null {
  const id = row.id ?? row.value;
  if (id === undefined || id === null) return null;

  // Authoritative amenity status mapping
  if (row.amenity_status_name && typeof row.amenity_status_name === "string" && row.amenity_status_name.trim()) {
    return { value: String(id), label: row.amenity_status_name.trim() };
  }

  for (const key of LABEL_KEYS) {
    const candidate = row[key];
    if (typeof candidate === "string" && candidate.trim()) {
      return { value: String(id), label: candidate.trim() };
    }
  }
  const full = [row.first_name, row.last_name].filter(Boolean).join(" ");
  if (full) {
    return { value: String(id), label: full };
  }

  // Fallback for numeric status ids (0: Available, 1: Occupied, 2: Unavailable, 3: Allotted)
  if (id in STATUS_LABELS) {
    return { value: String(id), label: STATUS_LABELS[id] };
  }

  return { value: String(id), label: String(id) };
}

function useFilterOptions(path: string | null) {
  return useQuery({
    queryKey: ["report-filter-options", path],
    enabled: Boolean(path),
    staleTime: 5 * 60_000,
    queryFn: async () => {
      if (!path) return [];
      const [basePath, searchStr] = path.split("?");
      const extraParams: Record<string, string> = {};
      if (searchStr) {
        const sp = new URLSearchParams(searchStr);
        sp.forEach((v, k) => {
          extraParams[k] = v;
        });
      }
      const body = await apiClient.get<unknown>(basePath, {
        page: 1,
        page_size: MAX_PAGE_SIZE,
        ...extraParams,
      });
      const rows = Array.isArray(body)
        ? body
        : ((body as { items?: unknown[] })?.items ?? []);
      return rows
        .map((row) => toOption(row as Record<string, unknown>))
        .filter((o): o is Option => o !== null);
    },
  });
}

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
      <div className="space-y-1">
        <Label className="text-xs font-medium text-muted-foreground">{spec.label}</Label>
        <Input
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 text-xs bg-background border-border/80 dark:border-slate-700/80 rounded-md focus-visible:ring-1"
        />
      </div>
    );
  }

  if (spec.kind === "boolean") {
    return (
      <div className="space-y-1">
        <Label className="text-xs font-medium text-muted-foreground">{spec.label}</Label>
        <Select value={value || "any"} onValueChange={(v) => onChange(v === "any" ? "" : v)}>
          <SelectTrigger className="h-9 text-xs bg-background border-border/80 dark:border-slate-700/80 rounded-md focus:ring-1">
            <SelectValue placeholder="Any" />
          </SelectTrigger>
          <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
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
      <div className="space-y-1">
        <Label className="text-xs font-medium text-muted-foreground">{spec.label}</Label>
        <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
          <SelectTrigger className="h-9 text-xs bg-background border-border/80 dark:border-slate-700/80 rounded-md focus:ring-1">
            <SelectValue placeholder={`All ${spec.label.toLowerCase()}`} />
          </SelectTrigger>
          <SelectContent className="bg-popover text-popover-foreground border-border max-h-72 text-xs">
            <SelectItem value="all">All {spec.label}</SelectItem>
            {options.isLoading && (
              <div className="px-3 py-2 text-xs text-muted-foreground">Loading options...</div>
            )}
            {options.error && (
              <div className="px-3 py-2 text-xs text-destructive">
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

  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-muted-foreground">{spec.label}</Label>
      <Input
        value={value}
        placeholder={`Filter by ${spec.label.toLowerCase()}...`}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 text-xs bg-background border-border/80 dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60 focus-visible:ring-1"
      />
    </div>
  );
};

interface ReportFiltersProps {
  filterSpecs: ReportFilterSpec[];
  filterValues: Record<string, string>;
  onFilterChange: (name: string, value: string) => void;
  onGenerate: () => void;
  onReset: () => void;
  onExport: () => void;
  isGenerating: boolean;
  isExporting: boolean;
  isGenerated: boolean;
  totalRecords: number;
  filtersApplied: Record<string, string>;
}

export const ReportFilters = ({
  filterSpecs,
  filterValues,
  onFilterChange,
  onGenerate,
  onReset,
  onExport,
  isGenerating,
  isExporting,
  isGenerated,
  totalRecords,
  filtersApplied,
}: ReportFiltersProps) => {
  return (
    <div className="space-y-4">
      {/* Filters Grid - clean, visually lightweight layout without heavy outer card box */}
      {filterSpecs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {filterSpecs.map((spec) => (
            <FilterField
              key={spec.name}
              spec={spec}
              value={filterValues[spec.name] ?? ""}
              onChange={(next) => onFilterChange(spec.name, next)}
            />
          ))}
        </div>
      )}

      {/* Modern Report Action Toolbar - Clean horizontal layout, no boxed container or outer borders */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Primary Action: Generate Report */}
          <Button
            type="button"
            onClick={onGenerate}
            disabled={isGenerating}
            className="h-9 px-4 rounded-md bg-brand hover:bg-brand-hover text-white text-xs font-medium shadow-xs hover:shadow-sm focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none transition-all inline-flex items-center justify-center gap-1.5"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Generate Report</span>
              </>
            )}
          </Button>

          {/* Secondary Action: Excel (.xlsx) Export */}
          <Button
            type="button"
            variant="outline"
            onClick={onExport}
            disabled={!isGenerated || isExporting || totalRecords === 0}
            title={
              totalRecords === 0
                ? "Generate report with at least one record first"
                : "Export all matching records to Excel (.xlsx)"
            }
            className="h-9 px-3.5 rounded-md border-border bg-background hover:bg-muted text-foreground text-xs font-medium shadow-xs focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:pointer-events-none transition-colors inline-flex items-center justify-center gap-1.5"
          >
            {isExporting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            )}
            <span>Excel (.xlsx)</span>
          </Button>

          {/* Tertiary / Text Action: Reset Filters */}
          <Button
            type="button"
            variant="ghost"
            onClick={onReset}
            className="h-9 px-2.5 rounded-md text-xs font-normal text-muted-foreground hover:text-foreground hover:bg-muted/50 focus-visible:ring-1 focus-visible:ring-primary transition-colors inline-flex items-center justify-center gap-1.5"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset filters</span>
          </Button>
        </div>

        {/* Status / Count Indicator */}
        {isGenerated && (
          <div className="text-xs font-medium text-muted-foreground ml-auto">
            {totalRecords.toLocaleString()} record{totalRecords === 1 ? "" : "s"} found
          </div>
        )}
      </div>

      {/* Applied Filters Tags - Lightweight chip indicators */}
      {isGenerated && Object.keys(filtersApplied).length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap pt-0.5 text-xs text-muted-foreground">
          <span className="text-[11px] font-medium text-muted-foreground/80 mr-1">
            Active filters:
          </span>
          {Object.entries(filtersApplied).map(([name, value]) => {
            const label = filterSpecs.find((f) => f.name === name)?.label ?? name;
            return (
              <span
                key={name}
                className="inline-flex items-center text-[11px] px-2 py-0.5 rounded-md bg-muted/60 border border-border/70 text-foreground/80 font-normal"
              >
                <span className="font-medium mr-1 text-foreground/90">{label}:</span>
                {value}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};
