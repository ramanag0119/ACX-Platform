import type { MouseEvent } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useCheckOutStay } from "@/lib/api/mutations";

interface CheckOutConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  stayId: string | null;
  roomName: string;
  guestName: string;
}

/**
 * Step two of Check-Out: the table button only opens this, and the check-out
 * request is sent from here alone.
 *
 * Check-out cannot be undone from the app -- it stamps the departure and sets
 * the room Available -- so a single stray click in a dense table must not
 * trigger it. An AlertDialog rather than a Dialog: it takes focus on Cancel and
 * does not close on an outside click, which is what a destructive confirm needs.
 *
 * The dialog stays open while the request runs and closes only on success; a
 * failure keeps it open beside the mutation's error toast so the operator can
 * retry or cancel. The success toast comes from useCheckOutStay itself.
 */
export function CheckOutConfirmDialog({
  open,
  onClose,
  stayId,
  roomName,
  guestName,
}: CheckOutConfirmDialogProps) {
  const checkOut = useCheckOutStay();

  const confirm = (event: MouseEvent<HTMLButtonElement>) => {
    // AlertDialogAction closes the dialog on click; hold it open until the
    // request has answered.
    event.preventDefault();
    if (!stayId) return;
    checkOut.mutate({ id: stayId }, { onSuccess: onClose });
  };

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !checkOut.isPending) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Check out Room {roomName}?</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to process this check-out? This action will release the room.
            {guestName !== "-" && (
              <span className="mt-2 block">
                Guest: <span className="font-medium text-foreground">{guestName}</span>
              </span>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={checkOut.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-purple-600 text-white hover:bg-purple-700"
            disabled={!stayId || checkOut.isPending}
            onClick={confirm}
          >
            {checkOut.isPending ? "Checking out..." : "Confirm Check-Out"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
