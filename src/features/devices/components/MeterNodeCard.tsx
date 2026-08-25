import { Building2, LayoutGrid, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MeterNode, MeterNodeKind } from "../data/meters";

/** Buildings and rooms carry the building glyph, floors the floor-plan glyph. */
const KIND_ICON: Record<MeterNodeKind, LucideIcon> = {
  building: Building2,
  floor: LayoutGrid,
  room: Building2,
};

interface MeterNodeCardProps {
  node: MeterNode;
  selected?: boolean;
  /**
   * Which pair of figures the top section shows. Both start with live kW on the
   * left; the bold right-hand figure is energy from midnight in Energy View and
   * today's peak demand in Power View.
   */
  metric?: "energy" | "power";
  /** Top (white) section click - drills into the children of this node. */
  onDrillDown: (node: MeterNode) => void;
  /** Bottom (tinted) section click - opens the Appliances Energy modal. */
  onOpenAppliances: (node: MeterNode) => void;
}

export const MeterNodeCard = ({
  node,
  selected,
  metric = "energy",
  onDrillDown,
  onOpenAppliances,
}: MeterNodeCardProps) => {
  const Icon = KIND_ICON[node.kind];
  const isPower = metric === "power";
  // Rooms are leaves: their top section opens the appliance dialog instead of
  // expanding, so it must not advertise itself as an expandable control.
  const isLeaf = node.children.length === 0;

  return (
    <div className={cn("overflow-hidden rounded-[2px]", selected && "ring-2 ring-meter-ring")}>
      {/* Top section: readings + title. Click drills into the children. */}
      <button
        type="button"
        onClick={() => onDrillDown(node)}
        aria-expanded={isLeaf ? undefined : selected}
        aria-haspopup={isLeaf ? "dialog" : undefined}
        className="w-full bg-meter-card px-4 pb-3.5 pt-3 transition-colors hover:bg-meter-card-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-meter-ring"
      >
        <div className="flex items-stretch">
          <span
            className="flex-1 text-center text-[13px] font-semibold leading-none text-meter-accent"
            title="Live load (kW)"
          >
            {node.liveKw}
          </span>
          <span className="w-px shrink-0 bg-meter-divider" aria-hidden="true" />
          <span
            className="flex-1 text-center text-[13px] font-bold leading-none text-meter-value"
            title={isPower ? "Peak demand today (kW)" : "Energy from midnight (kWh)"}
          >
            {isPower ? node.peakKw : node.energyKwh}
          </span>
        </div>

        <h4 className="mt-3 truncate text-center text-[13px] font-bold text-meter-accent">
          {node.name}
          {node.code && <span className="ml-1 text-[11px] font-medium text-meter-accent/70">- {node.code}</span>}
          {node.alerts > 0 && (
            <sup
              className="ml-1 text-[10px] font-bold text-meter-alert"
              title={`${node.alerts} active alert${node.alerts === 1 ? "" : "s"}`}
            >
              {node.alerts}
            </sup>
          )}
        </h4>
      </button>

      {/* Bottom section: device count. Click opens the Appliances Energy modal. */}
      <button
        type="button"
        onClick={() => onOpenAppliances(node)}
        title="View appliances energy"
        className="w-full border-t border-meter-footer-border bg-meter-footer px-4 py-2.5 text-left text-meter-footer-text transition-colors hover:bg-meter-footer-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-meter-ring"
      >
        <span className="flex items-center gap-2.5">
          <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2} />
          <span className="text-[13px] font-bold leading-none">{node.deviceCount}</span>
        </span>
        {node.path && (
          <span className="mt-1 block truncate text-[9px] font-medium leading-none text-meter-footer-text/70">
            {node.path}
          </span>
        )}
      </button>
    </div>
  );
};
