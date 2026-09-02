import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DataState } from "@/core/components/DataState";
import { useAmenityConditions } from "@/lib/api/hooks";
import { useSetRoomConditions } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

interface RoomConditionsDialogProps {
  open: boolean;
  onClose: () => void;
  amenityId: string | null;
  roomName: string;
  selectedIds: number[];
}

/**
 * Housekeeping conditions for one room.
 *
 * The options come from `amenity_condition` (Dirty, Low battery, Under
 * maintenance, Sanitation) rather than a hardcoded list, and saving REPLACES
 * the room's `amenity_condition_status` rows -- ticking and unticking both
 * persist.
 */
export const RoomConditionsDialog = ({
  open,
  onClose,
  amenityId,
  roomName,
  selectedIds,
}: RoomConditionsDialogProps) => {
  const conditionsQuery = useAmenityConditions(
    open ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
  );
  const setConditions = useSetRoomConditions();
  const [checked, setChecked] = useState<number[]>(selectedIds);

  // Re-seed from the row each time the dialog opens for a different room.
  useEffect(() => {
    if (open) setChecked(selectedIds);
  }, [open, amenityId, selectedIds]);

  const toggle = (id: number) =>
    setChecked((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );

  const handleSave = () => {
    if (!amenityId) return;
    setConditions.mutate(
      { amenityId, conditionIds: checked },
      { onSuccess: () => onClose() },
    );
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Conditions for room {roomName}</DialogTitle>
        </DialogHeader>

        <DataState isLoading={conditionsQuery.isLoading} error={conditionsQuery.error}>
          <div className="space-y-3">
            {(conditionsQuery.data?.items ?? []).map((condition) => (
              <label key={condition.id} className="flex items-center gap-3 text-sm">
                <Checkbox
                  checked={checked.includes(condition.id)}
                  onCheckedChange={() => toggle(condition.id)}
                />
                {condition.name}
              </label>
            ))}
            <p className="text-xs text-muted-foreground">
              Saving replaces this room's conditions with exactly what is ticked.
            </p>
          </div>
        </DataState>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={setConditions.isPending}>
            {setConditions.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
