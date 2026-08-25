/**
 * The single HMS Web API client. There is deliberately only one.
 *
 * Base URL comes from `VITE_API_BASE_URL` (see `.env.example`); it falls back
 * to a relative `/api/v1`, which the Vite dev proxy forwards to FastAPI. No
 * production host is hardcoded anywhere.
 *
 * Every FastAPI error arrives as {"error": {"code", "message", "detail"}} and
 * is surfaced here as a single `ApiError`, so screens never parse envelopes
 * themselves.
 */

import type { ApiErrorBody, ApiErrorResponse } from "./types";

const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
/** Normalised, no trailing slash. */
export const API_BASE_URL = RAW_BASE.replace(/\/+$/, "");

const TOKEN_KEY = "hms.access_token";

/** Broadcast when the backend rejects our token, so AuthContext can sign out. */
export const UNAUTHORIZED_EVENT = "hms:unauthorized";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * One error type for every failure mode, so screens can branch on `status`
 * rather than sniffing messages.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.detail = body.detail;
  }

  /** Not signed in, or the token expired/was rejected. */
  get isUnauthorized() {
    return this.status === 401;
  }

  /** Signed in, but the role lacks the module grant. */
  get isForbidden() {
    return this.status === 403;
  }

  get isNotFound() {
    return this.status === 404;
  }

  /** Bad query parameters -- e.g. page_size above the backend's 100. */
  get isValidation() {
    return this.status === 422;
  }

  /** 500 from the app, or 503 when PostgreSQL is unreachable. */
  get isServerError() {
    return this.status >= 500;
  }

  /** The request contradicts current state, or breaks a uniqueness rule. */
  get isConflict() {
    return this.status === 409;
  }

  /** The request never reached the backend at all. */
  get isNetworkError() {
    return this.status === 0;
  }

  /** Field-level messages from a 422, for showing next to inputs. */
  get fieldErrors(): Record<string, string> {
    if (!this.isValidation || !Array.isArray(this.detail)) return {};
    const errors: Record<string, string> = {};
    for (const entry of this.detail as { loc?: unknown[]; msg?: string }[]) {
      // FastAPI reports ["body", "field_name"]; the last string wins.
      const field = [...(entry.loc ?? [])].reverse().find((part) => typeof part === "string");
      if (typeof field === "string" && field !== "body" && entry.msg) {
        errors[field] = entry.msg;
      }
    }
    return errors;
  }
}

/** Human text for the states Step 7 requires every screen to handle. */
export function describeApiError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : "Something went wrong.";
  }
  if (error.isNetworkError) return "Cannot reach the HMS API. Is the backend running?";
  if (error.isUnauthorized) return "Your session has expired. Please sign in again.";
  if (error.isForbidden) return "Your role does not grant access to this module.";
  if (error.isNotFound) return "That record no longer exists.";
  if (error.isConflict) return error.message || "That change conflicts with existing data.";
  if (error.isValidation) {
    const fields = Object.entries(error.fieldErrors);
    if (fields.length) return fields.map(([f, m]) => `${f}: ${m}`).join("; ");
    return error.message || "The request was rejected.";
  }
  if (error.status === 503) return "The HMS database is unavailable. Please try again shortly.";
  if (error.isServerError) return "The HMS API failed to handle this request.";
  return error.message;
}

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue>;

/** Drops empty params so we never send a filter the backend does not expect. */
function buildQuery(params?: QueryParams): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.append(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody = {
    code: `http_${response.status}`,
    message: response.statusText || "Request failed",
  };
  try {
    const parsed = (await response.json()) as ApiErrorResponse;
    if (parsed && typeof parsed === "object" && parsed.error) body = parsed.error;
  } catch {
    // A non-JSON body (a proxy error page, say) keeps the fallback above.
  }
  return new ApiError(response.status, body);
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  params?: QueryParams;
  body?: unknown;
  /** Login must not trigger the global sign-out broadcast on 401. */
  skipAuthRedirect?: boolean;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", params, body, skipAuthRedirect, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };

  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${buildQuery(params)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, {
      code: "network_error",
      message: "The HMS API could not be reached.",
    });
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (error.isUnauthorized && !skipAuthRedirect) {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
    throw error;
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * Fetch a file (a report export) rather than JSON.
 *
 * Goes through the same base URL, bearer token and error envelope as every
 * other call, so a 401 still signs the user out and a 403 still reads as a
 * missing module grant. The filename comes from Content-Disposition, because
 * the backend owns the naming.
 */
async function download(
  path: string,
  params?: QueryParams,
): Promise<{ blob: Blob; filename: string }> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${buildQuery(params)}`, { headers });
  } catch {
    throw new ApiError(0, {
      code: "network_error",
      message: "The HMS API could not be reached.",
    });
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (error.isUnauthorized) {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
    throw error;
  }

  // `attachment; filename="occupancy-report-20260825.xlsx"`
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const matched = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const fallback = path.split("/").pop() || "report";
  return {
    blob: await response.blob(),
    filename: matched ? decodeURIComponent(matched[1]) : fallback,
  };
}

/** Hand a fetched blob to the browser as a download. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking immediately can cancel the download in some browsers.
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export const apiClient = {
  get: <T>(path: string, params?: QueryParams, signal?: AbortSignal) =>
    request<T>(path, { params, signal }),
  /** Binary GET for exports; see `download` above. */
  download,
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "POST", body }),
  /** Partial update: only the fields sent are written. */
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  /** Full replacement of a collection (a permission matrix, item lines). */
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
