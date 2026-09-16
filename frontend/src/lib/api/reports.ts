/**
 * Reporting API client.
 *
 *   GET /reports                          the nine reports and their shape
 *   GET /reports/{key}                    a page of rows, filtered
 *   GET /reports/{key}/export.xlsx        the same rows as a spreadsheet
 *
 * The backend owns the column list, so the Reports screen renders whatever it
 * is given rather than declaring the columns a second time. That is what keeps
 * the table and the downloaded file identical.
 *
 * No report data is shaped here. A value arrives ready to print, except for
 * date/number formatting, which is presentation and belongs to the view.
 */

import { apiClient, saveBlob, type QueryParams } from "./client";

/** Drives alignment on screen and the cell format in the spreadsheet. */
export type ReportColumnKind = "text" | "number" | "date" | "datetime" | "boolean";

export interface ReportColumn {
  key: string;
  header: string;
  kind: ReportColumnKind;
}

/** How the filter should be rendered. `select` options come from a real list
 *  endpoint named by `options_from`; there are no invented option sets. */
export type ReportFilterKind = "text" | "date" | "select" | "boolean" | "int" | "uuid";

export interface ReportFilterSpec {
  name: string;
  label: string;
  kind: ReportFilterKind;
  options_from: string | null;
}

/** A report's identity and shape, with no rows. */
export interface ReportInfo {
  key: string;
  title: string;
  /** The PostgreSQL tables behind it, shown under the report title. */
  source: string;
  description: string;
  columns: ReportColumn[];
  filters: ReportFilterSpec[];
}

/** Row values keyed by `ReportColumn.key`. Only declared columns are present. */
export type ReportRow = Record<string, unknown>;

export interface ReportPage extends ReportInfo {
  items: ReportRow[];
  /** Echoes only the filters the backend actually applied. */
  filters_applied: Record<string, string>;
  page: number;
  page_size: number;
  total: number;
}

export const listReports = () => apiClient.get<ReportInfo[]>("/reports");

export const runReport = (key: string, params?: QueryParams) =>
  apiClient.get<ReportPage>(`/reports/${key}`, params);

/**
 * Download the report as .xlsx. The export is NOT paginated -- it carries
 * every row matching the same filters, which is why `page`/`page_size` are
 * stripped before the request.
 */
export async function downloadReportXlsx(
  key: string,
  params?: QueryParams,
): Promise<string> {
  const query: QueryParams = { ...(params ?? {}) };
  delete query.page;
  delete query.page_size;
  const { blob, filename } = await apiClient.download(
    `/reports/${key}/export.xlsx`,
    query,
  );
  saveBlob(blob, filename);
  return filename;
}
