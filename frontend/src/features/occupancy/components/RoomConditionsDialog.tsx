import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { DataState } from "@/core/components/DataState";
import { useAmenityConditions } from "@/lib/api/hooks";
import { useSetRoomConditions } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { describeApiError } from "@/lib/api/client";
import { conditionLabel } from "../lib/roomStatus";

interface RoomConditionsDialogProps {
  open: boolean;
  onClose: () => void;
  amenityId: string | null;
  roomName: string;
  selectedIds: number[];
}

/**
 * Operational condition for one room.
 *
 * Each room maintains exactly ONE active operational condition at a time.
 * Selecting a condition immediately replaces any previous condition.
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
  const [selectedId, setSelectedId] = useState<number | null>(() => selectedIds[0] ?? null);
  const [localError, setLocalError] = useState<string | null>(null);

  // Track the room id initialized so we only seed on open or room switch.
  const initializedRoomRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open || !amenityId) {
      initializedRoomRef.current = null;
      setLocalError(null);
      return;
    }

    // Only re-seed from props when dialog opens or when switching to another room.
    // Crucially do not re-seed on every render, mutation state change, or background query refetch.
    if (initializedRoomRef.current !== amenityId) {
      initializedRoomRef.current = amenityId;
      setSelectedId(selectedIds[0] ?? null);
      setLocalError(null);
      setConditions.reset();
    }
  }, [open, amenityId, selectedIds, setConditions]);

  const handleSave = () => {
    if (!amenityId || setConditions.isPending || selectedId === null) return;
    setLocalError(null);
    setConditions.mutate(
      { amenityId, conditionIds: [selectedId] },
      {
        onSuccess: () => {
          onClose();
        },
        onError: (err) => {
          setLocalError(describeApiError(err));
        },
      },
    );
  };

  const errorMessage =
    localError || (setConditions.error ? describeApiError(setConditions.error) : null);

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Room {roomName} Condition</DialogTitle>
        </DialogHeader>

        <DataState isLoading={conditionsQuery.isLoading} error={conditionsQuery.error}>
          <div className="space-y-4">
            {errorMessage && (
              <div
                role="alert"
                className="rounded-md bg-destructive/15 p-3 text-xs text-destructive font-medium border border-destructive/20"
              >
                {errorMessage}
              </div>
            )}

            <RadioGroup
              value={selectedId !== null ? String(selectedId) : ""}
              onValueChange={(val) => {
                if (val) {
                  setSelectedId(Number(val));
                  setLocalError(null);
                }
              }}
              className="space-y-3"
              disabled={setConditions.isPending}
            >
              {(conditionsQuery.data?.items ?? []).map((condition) => (
                <div
                  key={condition.id}
                  className="flex items-center gap-3 cursor-pointer select-none"
                >
                  <RadioGroupItem
                    id={`condition-${condition.id}`}
                    value={String(condition.id)}
                    disabled={setConditions.isPending}
                  />
                  <Label
                    htmlFor={`condition-${condition.id}`}
                    className="text-sm font-normal cursor-pointer select-none flex-1"
                  >
                    {conditionLabel(condition.name)}
                  </Label>
                </div>
              ))}
            </RadioGroup>

            <p className="text-xs text-muted-foreground pt-1">
              Each room has one active operational condition. Selecting a new option replaces the current condition.
            </p>
          </div>
        </DataState>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={setConditions.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={setConditions.isPending || selectedId === null}
          >
            {setConditions.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
