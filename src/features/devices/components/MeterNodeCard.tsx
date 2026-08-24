import { Building2, LayoutGrid } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EnergyNode } from "../data/meters";

/** Buildings and rooms carry the building glyph, floors the floor-plan glyph. */
const KIND_ICON = {
  building: Building2,
  floor: LayoutGrid,
  room: Building2,
};

interface MeterNodeCardProps {
  node: EnergyNode;
  selected?: boolean;
  /**
   * Which pair of figures the top section shows. Both start with live kW on the
   * left; the bold right-hand figure is energy from midnight in Energy View and
   * today's peak demand in Power View.
   */
  metric?: "energy" | "power";
  /** Top (white) section click - drills into the children of this node. */
  onDrillDown: (node: EnergyNode) => void;
  /** Bottom (tinted) section click - opens the Appliances Energy modal. */
  onOpenAppliances: (node: EnergyNode) => void;
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

  return (
    <div className={cn("overflow-hidden rounded-[2px]", selected && "ring-2 ring-[#5865F2]")}>
      {/* Top section: readings + title. Click drills into the children. */}
      <button
        type="button"
        onClick={() => onDrillDown(node)}
        aria-expanded={selected}
        className="w-full bg-white px-4 pb-3.5 pt-3 transition-colors hover:bg-[#f5f5f7] focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#5865F2]"
      >
        <div className="flex items-stretch">
          <span
            className="flex-1 text-center text-[13px] font-semibold leading-none text-[#f0616f]"
            title="Live load (kW)"
          >
            {node.liveKw}
          </span>
          <span className="w-px shrink-0 bg-[#dcdce1]" aria-hidden="true" />
          <span
            className="flex-1 text-center text-[13px] font-bold leading-none text-[#111114]"
            title={isPower ? "Peak demand today (kW)" : "Energy from midnight (kWh)"}
          >
            {isPower ? node.peakKw : node.energyKwh}
          </span>
        </div>

        <h4 className="mt-3 truncate text-center text-[13px] font-bold text-[#f0616f]">
          {node.name}
          {node.code && <span className="ml-1 text-[11px] font-medium text-[#f0616f]/70">- {node.code}</span>}
          {node.alerts > 0 && (
            <sup className="ml-1 text-[10px] font-bold text-[#d32f2f]" title={`${node.alerts} active alerts`}>
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
        className="w-full border-t border-[#C9C7FF] bg-[#EDEDFF] px-4 py-2.5 text-left text-[#4A4FE3] transition-colors hover:bg-[#E1E2FB] focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#5865F2]"
      >
        <span className="flex items-center gap-2.5">
          <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2} />
          <span className="text-[13px] font-bold leading-none">{node.deviceCount}</span>
        </span>
        {node.path && (
          <span className="mt-1 block truncate text-[9px] font-medium leading-none text-[#4A4FE3]/70">
            {node.path}
          </span>
        )}
      </button>
    </div>
  );
};
