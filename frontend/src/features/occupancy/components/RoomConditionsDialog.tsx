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
import { Badge } from "@/components/ui/badge";
import { DataState } from "@/core/components/DataState";
import { useRoomApplicableConditions } from "@/lib/api/hooks";
import { useSetRoomConditions } from "@/lib/api/mutations";
import { describeApiError } from "@/lib/api/client";
import { conditionLabel } from "../lib/roomStatus";

interface RoomConditionsDialogProps {
  open: boolean;
  onClose: () => void;
  amenityId: string | null;
  roomName: string;
  selectedIds: number[];
  currentConditions?: string[];
  roomStatus?: string;
}

/**
 * Operational condition for one room.
 *
 * Each room maintains exactly ONE active operational condition at a time.
 * Condition options are dynamically loaded from the database based on the room's
 * authoritative status (room_status_condition_applicability table).
 * Persisted conditions and selectable choices are kept strictly distinct.
 */
export const RoomConditionsDialog = ({
  open,
  onClose,
  amenityId,
  roomName,
  selectedIds,
  currentConditions = [],
  roomStatus,
}: RoomConditionsDialogProps) => {
  const conditionsQuery = useRoomApplicableConditions(
    open && amenityId ? amenityId : null,
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

  const applicableConditions = conditionsQuery.data ?? [];

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

            {/* Current Persisted Room Condition */}
            <div className="rounded-lg bg-muted/40 p-3 border border-border/60 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">Room Workflow Status:</span>
                <Badge variant="outline" className="font-semibold text-xs">
                  {roomStatus || "Unknown"}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">Active Condition:</span>
                <span className="font-semibold text-primary">
                  {currentConditions.length > 0
                    ? currentConditions.join(", ")
                    : "None (No active condition)"}
                </span>
              </div>
            </div>

            {/* Applicable Condition Choices */}
            <div className="space-y-2">
              <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Applicable Conditions
              </Label>

              {applicableConditions.length === 0 ? (
                <div className="py-6 text-center text-sm text-muted-foreground border border-dashed rounded-md">
                  No applicable conditions configured for this room's status.
                </div>
              ) : (
                <RadioGroup
                  value={selectedId !== null ? String(selectedId) : ""}
                  onValueChange={(val) => {
                    if (val) {
                      setSelectedId(Number(val));
                      setLocalError(null);
                    }
                  }}
                  className="space-y-2"
                  disabled={setConditions.isPending}
                >
                  {applicableConditions.map((condition) => (
                    <div
                      key={condition.id}
                      className="flex items-center gap-3 cursor-pointer select-none rounded-md p-2 hover:bg-muted/40 transition-colors"
                    >
                      <RadioGroupItem
                        id={`condition-${condition.id}`}
                        value={String(condition.id)}
                        disabled={setConditions.isPending}
                      />
                      <Label
                        htmlFor={`condition-${condition.id}`}
                        className="text-sm font-normal cursor-pointer select-none flex-1 flex items-center justify-between"
                      >
                        <span>{condition.display_name || conditionLabel(condition.name)}</span>
                        {condition.blocks_checkin && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 font-medium border border-amber-500/20">
                            Blocks Check-In
                          </span>
                        )}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              )}
            </div>

            <p className="text-xs text-muted-foreground pt-1">
              Selecting an applicable option updates the room's operational condition and synchronizes room workflow status according to configured business rules.
            </p>
          </div>
        </DataState>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={setConditions.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={
              setConditions.isPending ||
              selectedId === null ||
              applicableConditions.length === 0
            }
          >
            {setConditions.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
