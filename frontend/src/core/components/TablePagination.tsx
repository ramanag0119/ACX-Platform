import { Button } from "@/components/ui/button";

/**
 * The footer under a paginated table: the "Showing x to y of n" count and the
 * First / Previous / pages / Next / Last controls.
 *
 * WHY THIS EXISTS. Twelve pages had hand-rolled their own copy of this markup.
 * Eight were wired up; four -- Employees, Facility Management, Services Setup
 * and Service Tracking, sixteen footers between them -- rendered the buttons
 * with no `onClick` at all, so First/Previous/Next/Last and every page number
 * were inert. Service Tracking went further and hardcoded its summary line to
 * `of 136 entries` over a fixed run of page buttons `1 2 3 4 5 ... 14`,
 * regardless of how many rows the filter actually matched.
 *
 * The count and the page list are derived from `totalEntries` and `pageSize`
 * here, so a page cannot state a total its table does not hold.
 */

/** Pages either side of the current one before the list elides. */
const WINDOW = 2;

/**
 * The page numbers to show, elided to a window around the current page.
 * `null` marks a gap and renders as an ellipsis.
 *
 * Rendering every page was the other half of the old duplication: a list of
 * 1,000 rows at 10 per page produced 100 buttons and wrapped the footer over
 * several lines.
 */
const pageWindow = (current: number, total: number): (number | null)[] => {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  const pages = new Set<number>([1, total]);
  for (let p = current - WINDOW; p <= current + WINDOW; p++) {
    if (p > 1 && p < total) pages.add(p);
  }

  const sorted = [...pages].sort((a, b) => a - b);
  const out: (number | null)[] = [];
  let previous = 0;
  for (const page of sorted) {
    if (previous && page - previous > 1) out.push(null);
    out.push(page);
    previous = page;
  }
  return out;
};

export interface TablePaginationProps {
  /** 1-based. */
  currentPage: number;
  onPageChange: (page: number) => void;
  /** Rows the current filter matched, NOT the rows on this page. */
  totalEntries: number;
  pageSize: number;
  /** Extra classes for the wrapper, for pages that need different spacing. */
  className?: string;
}

export const TablePagination = ({
  currentPage,
  onPageChange,
  totalEntries,
  pageSize,
  className = "mt-5",
}: TablePaginationProps) => {
  const size = pageSize > 0 ? pageSize : 10;
  const totalPages = Math.max(1, Math.ceil(totalEntries / size));

  /*
    Clamp rather than trust the caller. Narrowing a filter while on page 9 of 9
    leaves `currentPage` past the end, which showed an empty table under a
    footer still claiming page 9. Reading a clamped value keeps the footer
    honest even where the page has not reset its own state.
  */
  const page = Math.min(Math.max(1, currentPage), totalPages);

  const startIndex = (page - 1) * size;
  const firstShown = totalEntries > 0 ? startIndex + 1 : 0;
  const lastShown = Math.min(startIndex + size, totalEntries);

  const go = (next: number) => onPageChange(Math.min(Math.max(1, next), totalPages));

  const stepClass =
    "h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground";

  return (
    <div className={`flex flex-wrap items-center justify-between gap-4 ${className}`}>
      <span className="text-muted-foreground text-xs">
        Showing {firstShown} to {lastShown} of {totalEntries} entries
      </span>

      <nav className="flex items-center gap-1" aria-label="Pagination">
        <Button variant="ghost" size="sm" className={stepClass} onClick={() => go(1)} disabled={page === 1}>
          First
        </Button>
        <Button variant="ghost" size="sm" className={stepClass} onClick={() => go(page - 1)} disabled={page === 1}>
          Previous
        </Button>

        {pageWindow(page, totalPages).map((entry, index) =>
          entry === null ? (
            // Index-keyed on purpose: a gap has no identity of its own, and
            // there is at most one on each side of the window.
            <span key={`gap-${index}`} className="px-2 text-muted-foreground text-xs">
              &hellip;
            </span>
          ) : (
            <Button
              key={entry}
              variant={entry === page ? "default" : "ghost"}
              size="sm"
              className={`h-8 w-8 p-0 text-xs rounded-xl ${
                entry === page
                  ? "bg-brand hover:bg-brand-hover text-white font-semibold shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => go(entry)}
              aria-current={entry === page ? "page" : undefined}
            >
              {entry}
            </Button>
          ),
        )}

        <Button variant="ghost" size="sm" className={stepClass} onClick={() => go(page + 1)} disabled={page === totalPages}>
          Next
        </Button>
        <Button variant="ghost" size="sm" className={stepClass} onClick={() => go(totalPages)} disabled={page === totalPages}>
          Last
        </Button>
      </nav>
    </div>
  );
};
