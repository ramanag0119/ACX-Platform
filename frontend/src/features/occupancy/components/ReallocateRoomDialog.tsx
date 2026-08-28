import { useMemo, useState } from "react";

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
import { useOccupancy, useStayRoomAllocations } from "@/lib/api/hooks";
import { useReallocateRoom } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

interface ReallocateRoomDialogProps {
  open: boolean;
  onClose: () => void;
  stayId: string | null;
  currentRoomName: string;
}

/**
 * Move a stay to a different room.
 *
 * The backend does this in ONE transaction: the allocation moves, the old room
 * goes Available and the new room takes the stay's current state (Occupied if
 * the guest is in-house, otherwise Allotted). A room another live stay holds is
 * refused with 409, which surfaces as the shared error toast.
 *
 * Only rooms with no live stay are offered, so the common case does not rely on
 * the conflict check to explain itself.
 */
export const ReallocateRoomDialog = ({
  open,
  onClose,
  stayId,
  currentRoomName,
}: ReallocateRoomDialogProps) => {
  const [targetRoom, setTargetRoom] = useState("");

  const occupancyQuery = useOccupancy(
    open ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
  );
  // Reallocation is keyed on the ALLOCATION row, not the stay.
  const allocationsQuery = useStayRoomAllocations(open ? stayId : null);
  const reallocate = useReallocateRoom();

  const allocationId = useMemo(() => {
    const rows = allocationsQuery.data ?? [];
    return (rows.find((row) => row.room_name === currentRoomName) ?? rows[0])?.id ?? null;
  }, [allocationsQuery.data, currentRoomName]);

  const freeRooms = useMemo(
    () =>
      (occupancyQuery.data?.items ?? []).filter(
        (item) => !item.current_stay && item.room_name !== currentRoomName,
      ),
    [occupancyQuery.data, currentRoomName],
  );

  const handleSubmit = () => {
    if (!allocationId || !targetRoom) return;
    reallocate.mutate(
      { allocationId, roomId: targetRoom },
      {
        onSuccess: () => {
          setTargetRoom("");
          onClose();
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reallocate room {currentRoomName}</DialogTitle>
        </DialogHeader>

        <DataState
          isLoading={occupancyQuery.isLoading || allocationsQuery.isLoading}
          error={occupancyQuery.error ?? allocationsQuery.error}
          isEmpty={freeRooms.length === 0}
          emptyTitle="No free room to move this stay into"
        >
          <div className="space-y-2">
            <Label>New room</Label>
            <Select value={targetRoom} onValueChange={setTargetRoom}>
              <SelectTrigger>
                <SelectValue placeholder="Select a room" />
              </SelectTrigger>
              <SelectContent>
                {freeRooms.map((room) => (
                  <SelectItem key={room.amenity_id} value={room.amenity_id}>
                    {room.room_name} · {room.amenity_type_name ?? "-"} · {room.status_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              The old room is released in the same transaction, so the stay can never
              hold two rooms.
            </p>
          </div>
        </DataState>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!targetRoom || !allocationId || reallocate.isPending}
          >
            {reallocate.isPending ? "Moving..." : "Reallocate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
