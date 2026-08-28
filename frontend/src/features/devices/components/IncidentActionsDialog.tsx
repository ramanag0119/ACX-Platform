import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataState } from "@/core/components/DataState";
import { useUsers } from "@/lib/api/hooks";
import { useUpdateIncident } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/** `incident_status` -- the seeded lookup, in its real order. */
const INCIDENT_STATUSES = [
  { id: 1, name: "Unread" },
  { id: 2, name: "Read" },
  { id: 3, name: "Assigned" },
  { id: 4, name: "Resolved" },
];

interface Props {
  open: boolean;
  onClose: () => void;
  target: {
    id: string;
    subject: string;
    statusId: number | null;
    assignedToId: string | null;
  } | null;
  canWrite: boolean;
}

/**
 * Acknowledge, assign or resolve a device incident.
 *
 * The lifecycle lives on `device_incident.current_incident_status`, and every
 * transition the backend applies also appends an `incident_history` row --
 * including the 'Reopened' event when an incident moves back out of Resolved.
 *
 * ALERT SEVERITY IS NOT EDITABLE: an alert is a fact a device reported. Only
 * the incident has a lifecycle, which is exactly why Phase 2.7 kept them apart.
 */
export const IncidentActionsDialog = ({ open, onClose, target, canWrite }: Props) => {
  const staffQuery = useUsers(
    open ? { page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 } : undefined,
  );
  const update = useUpdateIncident();

  const [statusId, setStatusId] = useState("");
  const [assignee, setAssignee] = useState("");

  useEffect(() => {
    if (!open || !target) return;
    setStatusId(target.statusId ? String(target.statusId) : "");
    setAssignee(target.assignedToId ?? "");
  }, [open, target]);

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="truncate">{target?.subject ?? "Incident"}</DialogTitle>
        </DialogHeader>

        <DataState isLoading={staffQuery.isLoading} error={staffQuery.error}>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={statusId} onValueChange={setStatusId} disabled={!canWrite}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a status" />
                </SelectTrigger>
                <SelectContent>
                  {INCIDENT_STATUSES.map((status) => (
                    <SelectItem key={status.id} value={String(status.id)}>
                      {status.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Assign to</Label>
              <Select value={assignee} onValueChange={setAssignee} disabled={!canWrite}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a staff member" />
                </SelectTrigger>
                <SelectContent>
                  {(staffQuery.data?.items ?? []).map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {[user.first_name, user.last_name].filter(Boolean).join(" ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Assigning an unread incident moves it to Assigned, and every change is
                recorded in the incident's history.
              </p>
            </div>
          </div>
        </DataState>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button
            disabled={!canWrite || !target || update.isPending}
            onClick={() =>
              target &&
              update.mutate(
                {
                  id: target.id,
                  body: {
                    ...(statusId ? { current_incident_status: Number(statusId) } : {}),
                    ...(assignee ? { assigned_to: assignee } : {}),
                  },
                },
                { onSuccess: onClose },
              )
            }
          >
            {update.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
