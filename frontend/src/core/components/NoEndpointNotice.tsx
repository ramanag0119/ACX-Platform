import { Info } from "lucide-react";

interface NoEndpointNoticeProps {
  /** The screen or tab this notice covers. */
  feature: string;
  /** The schema tables that hold the data, e.g. "job_order". */
  tables: string;
}

/**
 * Shown where a screen's data exists in the database but no Phase 2.x endpoint
 * exposes it yet.
 *
 * Phase 2.10 connects the frontend to the delivered API surface; it does not
 * add endpoints, and it does not keep sample rows on screen pretending to be
 * records. Each of these is listed as a gap in the phase report.
 */
export const NoEndpointNotice = ({ feature, tables }: NoEndpointNoticeProps) => (
  <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200">
    <Info className="mt-0.5 h-4 w-4 shrink-0" />
    <p>
      <span className="font-medium">{feature} is not connected yet.</span>{" "}
      The data lives in <span className="font-mono">{tables}</span>, which no API endpoint
      exposes. Nothing is listed here rather than sample data that looks real.
    </p>
  </div>
);
