import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useAuth } from "@/core/contexts/AuthContext";
import { useFacilities } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { facilityOptions, filtersToSearch, parseFilters, type MessageFilters } from "./presentation";

/**
 * The signed-in user's facility scope (from /auth/me) plus facility names.
 *
 * Names come from the existing GET /facilities, which is gated on the same
 * `facility_management` grant as the integration endpoints. If that list
 * cannot be read the screens still work and label facilities by short id.
 * The backend remains the isolation boundary: it scopes every integration
 * figure to the caller regardless of what the browser asks for.
 */
export function useFacilityScope() {
  const { user } = useAuth();
  const facilitiesQuery = useFacilities({ page: 1, page_size: MAX_PAGE_SIZE });
  const scopeIds = useMemo(() => user?.facility_ids ?? [], [user]);
  const facilities = useMemo(
    () => (facilitiesQuery.data?.items ?? []).map((f) => ({ id: f.id, name: f.name })),
    [facilitiesQuery.data],
  );
  const names = useMemo(() => new Map(facilities.map((f) => [f.id, f.name])), [facilities]);
  const options = useMemo(() => facilityOptions(facilities, scopeIds), [facilities, scopeIds]);
  return { scopeIds, names, options };
}

/** Filters live in the URL so a link (e.g. "HTNG message logs") can preset them. */
export function useUrlFilters(defaultPageSize = 20): [MessageFilters, (next: MessageFilters) => void] {
  const [search, setSearch] = useSearchParams();
  const filters = useMemo(() => parseFilters(search, defaultPageSize), [search, defaultPageSize]);
  const setFilters = useCallback(
    (next: MessageFilters) => setSearch(filtersToSearch(next, defaultPageSize), { replace: true }),
    [setSearch, defaultPageSize],
  );
  return [filters, setFilters];
}
