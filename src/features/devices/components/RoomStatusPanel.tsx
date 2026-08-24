import { type EnergyNode, type RoomOccupancy, nodeLabel } from "../data/meters";

/**
 * Power View room board: one tile per room in the current scope, with a
 * per-status tally in the panel header. Tiles share the card footer's tint so
 * the board reads as one surface; status is carried as a label, not a colour.
 */

const STATUS_ORDER: RoomOccupancy[] = ["available", "occupied", "maintenance", "non-smart"];

const STATUS_LABEL: Record<RoomOccupancy, string> = {
  available: "Available",
  occupied: "Occupied",
  maintenance: "Maintenance",
  "non-smart": "Non-Smart room",
};

interface RoomStatusPanelProps {
  rooms: EnergyNode[];
  onSelectRoom: (room: EnergyNode) => void;
}

export const RoomStatusPanel = ({ rooms, onSelectRoom }: RoomStatusPanelProps) => {
  const counts = STATUS_ORDER.reduce<Record<RoomOccupancy, number>>(
    (totals, status) => ({
      ...totals,
      [status]: rooms.filter((room) => room.occupancy === status).length,
    }),
    {} as Record<RoomOccupancy, number>,
  );

  return (
    <section className="rounded-[2px] border border-border/60 bg-muted/20 p-4 dark:border-slate-800/80 dark:bg-slate-900/30">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <h3 className="text-[13px] font-bold text-foreground">Rooms</h3>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
          {STATUS_ORDER.map((status, index) => (
            <span key={status} className="flex items-center gap-1.5">
              {index > 0 && <span className="text-muted-foreground/40">|</span>}
              <span>
                {STATUS_LABEL[status]} <span className="font-bold text-foreground">({counts[status]})</span>
              </span>
            </span>
          ))}
        </div>
      </div>

      {rooms.length === 0 ? (
        <p className="py-6 text-center text-[12px] text-muted-foreground">
          No rooms configured for this selection.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {rooms.map((room) => {
            const status = room.occupancy ?? "non-smart";
            return (
              <button
                key={room.id}
                type="button"
                onClick={() => onSelectRoom(room)}
                title={`${nodeLabel(room)} - ${STATUS_LABEL[status]}`}
                className="flex items-center justify-between gap-2 rounded-[2px] border border-[#C9C7FF] bg-[#EDEDFF] px-3 py-2.5 text-left text-[#4A4FE3] transition-colors hover:bg-[#E1E2FB] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5865F2] focus-visible:ring-offset-1"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[13px] font-bold leading-none">
                    {room.code ?? room.name}
                  </span>
                  <span className="mt-1 block truncate text-[9px] font-medium leading-none text-[#4A4FE3]/70">
                    {room.name}
                  </span>
                </span>
                <span className="shrink-0 text-[9px] font-semibold leading-none text-[#4A4FE3]/70">
                  {STATUS_LABEL[status]}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
};
