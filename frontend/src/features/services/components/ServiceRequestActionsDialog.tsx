import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { DataState } from "@/core/components/DataState";
import { useServiceStatuses, useUsers } from "@/lib/api/hooks";
import { useCancelServiceRequest, useUpdateServiceRequest } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

export interface ServiceRequestActionTarget {
  id: string;
  ref: string;
  statusId: number | null;
  assignedToId: string | null;
  statusReason?: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  target: ServiceRequestActionTarget | null;
  /** False when the role holds no `service_tracking` write grant. */
  canWrite: boolean;
}

/**
 * The one dialog behind every service-request action, on both Tickets and
 * Services Tracking: assign, change status, record a reason, or cancel.
 *
 * Statuses come from `service_status` (Pending, Assigned, Partially completed,
 * Completed, Canceled) and assignees from staff `app_user` rows -- neither is
 * hardcoded. The backend stamps `completed_on` when the status reaches
 * Completed and clears it on the way out, so the UI never has to.
 */
export const ServiceRequestActionsDialog = ({ open, onClose, target, canWrite }: Props) => {
  const statusesQuery = useServiceStatuses(
    open ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
  );
  const staffQuery = useUsers(
    open ? { page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 } : undefined,
  );
  const update = useUpdateServiceRequest();
  const cancel = useCancelServiceRequest();

  const [statusId, setStatusId] = useState<string>("");
  const [assignee, setAssignee] = useState<string>("");
  const [reason, setReason] = useState<string>("");

  useEffect(() => {
    if (!open || !target) return;
    setStatusId(target.statusId ? String(target.statusId) : "");
    setAssignee(target.assignedToId ?? "");
    setReason(target.statusReason ?? "");
  }, [open, target]);

  const handleSave = () => {
    if (!target) return;
    update.mutate(
      {
        id: target.id,
        body: {
          ...(statusId ? { status: Number(statusId) } : {}),
          ...(assignee ? { assigned_to: assignee } : {}),
          ...(reason ? { status_reason: reason } : {}),
        },
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Service request {target?.ref ?? ""}</DialogTitle>
        </DialogHeader>

        <DataState
          isLoading={statusesQuery.isLoading || staffQuery.isLoading}
          error={statusesQuery.error ?? staffQuery.error}
        >
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={statusId} onValueChange={setStatusId} disabled={!canWrite}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a status" />
                </SelectTrigger>
                <SelectContent>
                  {(statusesQuery.data?.items ?? []).map((status) => (
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
                      {[user.emp_id, [user.first_name, user.last_name].filter(Boolean).join(" ")]
                        .filter(Boolean)
                        .join(" / ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Assigning a pending request moves it to Assigned automatically.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Status reason</Label>
              <Textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Why the status changed (optional)"
                disabled={!canWrite}
              />
            </div>
          </div>
        </DataState>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            className="border-red-400 text-red-600 hover:bg-red-50"
            disabled={!canWrite || !target || cancel.isPending}
            onClick={() =>
              target &&
              cancel.mutate({ id: target.id, reason: reason || null }, { onSuccess: onClose })
            }
          >
            Cancel request
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button onClick={handleSave} disabled={!canWrite || update.isPending}>
            {update.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
