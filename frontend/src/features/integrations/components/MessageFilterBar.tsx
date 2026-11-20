import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { INTEGRATION_PROTOCOLS, MESSAGE_STATUSES, type IntegrationProtocol, type MessageStatus } from "@/lib/api/integrations";
import {
  PAGE_SIZES,
  PROTOCOL_META,
  presentStatus,
  type FacilityOption,
  type MessageFilters,
} from "../lib/presentation";

/** Radix Select cannot hold an empty value, so "All" is this sentinel. */
const ALL = "__all__";

/**
 * Server-side filters. Every change goes to the backend as query params and
 * resets to page 1; nothing is filtered in the browser.
 */
export const MessageFilterBar = ({
  filters,
  onChange,
  facilities,
  showStatus = true,
  dateError,
  idPrefix,
}: {
  filters: MessageFilters;
  onChange: (next: MessageFilters) => void;
  facilities: FacilityOption[];
  showStatus?: boolean;
  dateError?: string | null;
  idPrefix: string;
}) => {
  const set = (patch: Partial<MessageFilters>) => onChange({ ...filters, ...patch, page: 1 });
  const id = (name: string) => `${idPrefix}-${name}`;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <div className="space-y-1">
          <Label htmlFor={id("protocol")} className="text-xs">Protocol</Label>
          <Select
            value={filters.protocol ?? ALL}
            onValueChange={(v) => set({ protocol: v === ALL ? undefined : (v as IntegrationProtocol) })}
          >
            <SelectTrigger id={id("protocol")} aria-label="Protocol filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All protocols</SelectItem>
              {INTEGRATION_PROTOCOLS.map((p) => (
                <SelectItem key={p} value={p}>{PROTOCOL_META[p].label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {showStatus ? (
          <div className="space-y-1">
            <Label htmlFor={id("status")} className="text-xs">Status</Label>
            <Select
              value={filters.status ?? ALL}
              onValueChange={(v) => set({ status: v === ALL ? undefined : (v as MessageStatus) })}
            >
              <SelectTrigger id={id("status")} aria-label="Status filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All statuses</SelectItem>
                {MESSAGE_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{presentStatus(s).label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ) : null}

        <div className="space-y-1">
          <Label htmlFor={id("facility")} className="text-xs">Facility</Label>
          <Select
            value={filters.facilityId ?? ALL}
            onValueChange={(v) => set({ facilityId: v === ALL ? undefined : v })}
          >
            <SelectTrigger id={id("facility")} aria-label="Facility filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All my facilities</SelectItem>
              {facilities.map((f) => (
                <SelectItem key={f.id} value={f.id}>{f.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label htmlFor={id("from")} className="text-xs">From date</Label>
          <Input
            id={id("from")}
            type="date"
            value={filters.from ?? ""}
            max={filters.to}
            onChange={(e) => set({ from: e.target.value || undefined })}
            aria-invalid={dateError ? true : undefined}
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor={id("to")} className="text-xs">To date</Label>
          <Input
            id={id("to")}
            type="date"
            value={filters.to ?? ""}
            min={filters.from}
            onChange={(e) => set({ to: e.target.value || undefined })}
            aria-invalid={dateError ? true : undefined}
          />
        </div>

        <div className="flex items-end gap-2">
          <div className="flex-1 space-y-1">
            <Label htmlFor={id("size")} className="text-xs">Rows</Label>
            <Select value={String(filters.pageSize)} onValueChange={(v) => set({ pageSize: Number(v) })}>
              <SelectTrigger id={id("size")} aria-label="Rows per page"><SelectValue /></SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((n) => (
                  <SelectItem key={n} value={String(n)}>{n}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="outline"
            onClick={() => onChange({ page: 1, pageSize: filters.pageSize })}
          >
            Reset
          </Button>
        </div>
      </div>
      {dateError ? (
        <p role="alert" className="text-xs text-destructive">{dateError}</p>
      ) : null}
    </div>
  );
};
