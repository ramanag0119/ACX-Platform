import { Button } from "@/components/ui/button";
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
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { DataState, TableLoading } from "@/core/components/DataState";
import type { ReportColumn, ReportRow } from "@/lib/api/reports";

const PAGE_SIZES = ["10", "25", "50", "100"] as const;

const STATUS_LABELS: Record<string | number, string> = {
  0: "Available",
  1: "Occupied",
  2: "Unavailable",
  3: "Allotted",
};

function formatCell(value: unknown, kind: ReportColumn["kind"], columnKey?: string): string {
  if (value === null || value === undefined || value === "") return "—";

  if (columnKey === "status" || columnKey === "status_name") {
    if (typeof value === "number" || (typeof value === "string" && value in STATUS_LABELS)) {
      return STATUS_LABELS[value as keyof typeof STATUS_LABELS];
    }
    if (typeof value === "string") {
      if (value.toLowerCase() === "active") return "In-House";
      return value;
    }
  }

  if (kind === "boolean") {
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (typeof value === "number") return value ? "Yes" : "No";
    return String(value);
  }
  if (kind === "date" || kind === "datetime") {
    const parsed = new Date(String(value));
    if (Number.isNaN(parsed.getTime())) return String(value);
    return kind === "date"
      ? parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
      : parsed.toLocaleString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
  }
  if (kind === "number") {
    return typeof value === "number" ? value.toLocaleString() : String(value);
  }
  return String(value);
}

interface ReportTableContainerProps {
  columns: ReportColumn[];
  rows: ReportRow[];
  total: number;
  page: number;
  pageSize: string;
  totalPages: number;
  isLoading: boolean;
  error: unknown;
  onPageChange: (nextPage: number) => void;
  onPageSizeChange: (nextPageSize: string) => void;
}

export const ReportTableContainer = ({
  columns,
  rows,
  total,
  page,
  pageSize,
  totalPages,
  isLoading,
  error,
  onPageChange,
  onPageSizeChange,
}: ReportTableContainerProps) => {
  const startRow = total === 0 ? 0 : (page - 1) * Number(pageSize) + 1;
  const endRow = Math.min(page * Number(pageSize), total);

  return (
    <div className="space-y-4">
      {/* Table Top Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-medium">Show</span>
          <Select value={pageSize} onValueChange={onPageSizeChange}>
            <SelectTrigger className="w-20 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
              {PAGE_SIZES.map((size) => (
                <SelectItem key={size} value={size}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground font-medium">
            entries per page
          </span>
        </div>

        <div className="text-xs text-muted-foreground font-medium">
          Showing <span className="font-semibold text-foreground">{startRow}</span> to{" "}
          <span className="font-semibold text-foreground">{endRow}</span> of{" "}
          <span className="font-semibold text-foreground">{total.toLocaleString()}</span> entries
        </div>
      </div>

      {/* Table Surface - Clean single border container */}
      <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800 bg-card overflow-x-auto scrollbar-thin shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 dark:bg-[#0e1322] border-b border-border dark:border-slate-800">
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  className={`text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-3.5 whitespace-nowrap ${
                    column.kind === "number" ? "text-right" : "text-left"
                  }`}
                >
                  {column.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading || error || rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={Math.max(columns.length, 1)} className="py-8">
                  <DataState
                    isLoading={isLoading}
                    error={error}
                    isEmpty
                    emptyTitle="No records found"
                    emptyDescription="Try adjusting or clearing your filters to see results."
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
                  className="hover:bg-[var(--hms-table-row-hover-bg)] border-b border-border/50 dark:border-slate-800/70 transition-colors"
                >
                  {columns.map((column) => {
                    const formatted = formatCell(row[column.key], column.kind, column.key);
                    const isDash = formatted === "—";
                    return (
                      <TableCell
                        key={column.key}
                        className={`text-xs py-2.5 px-3.5 text-foreground/90 whitespace-nowrap ${
                          column.kind === "number" ? "text-right font-mono" : ""
                        }`}
                      >
                        {isDash ? (
                          <span className="text-muted-foreground/60 font-medium">—</span>
                        ) : (
                          formatted
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <div className="text-xs text-muted-foreground">
          Page <span className="font-semibold text-foreground">{Math.min(page, totalPages)}</span> of{" "}
          <span className="font-semibold text-foreground">{totalPages}</span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-2 text-xs border-border text-muted-foreground hover:text-foreground"
            onClick={() => onPageChange(1)}
            disabled={page === 1}
            title="First Page"
          >
            <ChevronsLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-2.5 text-xs border-border text-muted-foreground hover:text-foreground"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-3.5 w-3.5 mr-1" />
            Previous
          </Button>
          <span className="text-xs text-muted-foreground px-2 font-medium">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-2.5 text-xs border-border text-muted-foreground hover:text-foreground"
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
          >
            Next
            <ChevronRight className="h-3.5 w-3.5 ml-1" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-2 text-xs border-border text-muted-foreground hover:text-foreground"
            onClick={() => onPageChange(totalPages)}
            disabled={page >= totalPages}
            title="Last Page"
          >
            <ChevronsRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
};
