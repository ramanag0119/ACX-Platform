import { useEffect, useMemo, useState } from "react";

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
import {
  useAmenityStatuses,
  useOccupancy,
  useStayRoomAllocations,
} from "@/lib/api/hooks";
import { useReallocateRoom } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE, ROOM_STATUS } from "@/lib/api/types";

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
 * WHICH ROOMS ARE OFFERED: rooms that are BOTH Available AND a guest-occupancy
 * space (`amenity_category = "room"`). Status alone is not enough -- the Gym,
 * the Restaurant and the Conference Room are all amenities too and are
 * routinely Available, but a stay cannot be moved into one. The status id is
 * resolved from GET /amenity-statuses rather than written here, so it can never
 * drift from the lookup table, and BOTH filters are applied BY THE BACKEND via
 * `?status=` and `?amenity_category=`, not by a pass over a fetched page.
 *
 * This previously filtered on `!current_stay` -- the STAY GRAPH -- which is a
 * different question from the room's status. The two diverge in the live data
 * (a room can be flagged Occupied, Unavailable or Allotted while holding no
 * stay), so Unavailable and Allotted rooms were being offered as targets. The
 * `!current_stay` check is kept as a second guard for the opposite divergence:
 * a room flagged Available that a live stay still holds.
 */
export const ReallocateRoomDialog = ({
  open,
  onClose,
  stayId,
  currentRoomName,
}: ReallocateRoomDialogProps) => {
  const [targetRoom, setTargetRoom] = useState("");

  /**
   * Clear the selection every time the dialog opens.
   *
   * Without this the component keeps the room chosen for the PREVIOUS stay:
   * reopening Reassign for another room showed that stale id already selected,
   * and it is very likely no longer Available -- it may even be the room the
   * last reassign just filled. Submitting it sends an id that is not in the
   * offered list, which the server rejects. Reassign now always opens empty.
   */
  useEffect(() => {
    if (open) setTargetRoom("");
  }, [open, stayId]);

  // The Available id comes from the lookup table, never from a literal.
  const statusesQuery = useAmenityStatuses(
    open ? { page: 1, page_size: MAX_PAGE_SIZE } : undefined,
    { enabled: open },
  );
  const availableStatusId = useMemo(
    () =>
      (statusesQuery.data?.items ?? []).find(
        (status) => status.amenity_status_name === ROOM_STATUS.AVAILABLE,
      )?.id,
    [statusesQuery.data],
  );

  // Genuinely disabled until the id is known. The conditional params are not
  // enough on their own: with `undefined` params this hook fetches the
  // UNFILTERED room list, which is exactly the set this dialog must not offer.
  // `enabled` is what holds the request until `?status=` can be sent with it.
  const roomsReady = open && availableStatusId !== undefined;
  const occupancyQuery = useOccupancy(
    roomsReady
      ? {
          page: 1,
          page_size: MAX_PAGE_SIZE,
          status: availableStatusId,
          // A stay can only move into a guest-occupancy space. `amenity_category`
          // is the real discriminator -- "room" covers Guest Room and Suite,
          // while Restaurant, Gym and Conference Room are "restaurant"/"others"
          // and are excluded however Available they happen to be. This is the
          // same category the Guest tab filters on, and it is resolved from
          // `amenity_type.amenity_category`, so a type added later sorts itself.
          amenity_category: "room",
        }
      : undefined,
    { enabled: roomsReady },
  );
  // Reallocation is keyed on the ALLOCATION row, not the stay.
  const allocationsQuery = useStayRoomAllocations(open ? stayId : null);
  const reallocate = useReallocateRoom();

  const allocationId = useMemo(() => {
    const rows = allocationsQuery.data ?? [];
    return (rows.find((row) => row.room_name === currentRoomName) ?? rows[0])?.id ?? null;
  }, [allocationsQuery.data, currentRoomName]);

  // The backend has already restricted this page to Available rooms; all that
  // is left is to drop the room the stay is being moved out of.
  const freeRooms = useMemo(
    () =>
      (occupancyQuery.data?.items ?? []).filter(
        (item) => !item.current_stay && item.room_name !== currentRoomName,
      ),
    [occupancyQuery.data, currentRoomName],
  );

  /**
   * The stay holds no `room_allocation` row, so there is nothing to move.
   * Reassign is keyed on the allocation, not the stay, so this case can only
   * fail -- it is reported rather than left as a button that does nothing.
   */
  const allocationMissing =
    !allocationsQuery.isLoading && Boolean(stayId) && allocationId === null;

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
          <DialogTitle>Reassign Room {currentRoomName}</DialogTitle>
        </DialogHeader>

        <DataState
          isLoading={
            statusesQuery.isLoading ||
            occupancyQuery.isLoading ||
            allocationsQuery.isLoading
          }
          error={
            statusesQuery.error ?? occupancyQuery.error ?? allocationsQuery.error
          }
          isEmpty={freeRooms.length === 0}
          emptyTitle="No Available Room to move this stay into"
        >
          <div className="space-y-2">
            <Label>New Room</Label>
            <Select value={targetRoom} onValueChange={setTargetRoom}>
              <SelectTrigger>
                <SelectValue placeholder="Select a Room" />
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
              The old Room is released in the same transaction, so the stay can never
              hold two Rooms.
            </p>
            {allocationMissing && (
              <p className="text-xs font-medium text-destructive">
                This stay holds no Room allocation, so there is nothing to reassign.
                Allocate a Room to the stay first.
              </p>
            )}
          </div>
        </DataState>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!targetRoom || !allocationId || reallocate.isPending}
            // A disabled button with no explanation reads as a broken screen.
            title={
              allocationMissing
                ? "This stay holds no Room allocation to move"
                : !targetRoom
                  ? "Select a Room to move this stay into"
                  : undefined
            }
          >
            {reallocate.isPending ? "Moving..." : "Reassign"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
