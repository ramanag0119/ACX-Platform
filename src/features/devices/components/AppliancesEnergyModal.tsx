import * as DialogPrimitive from "@radix-ui/react-dialog";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { type EnergyNode, KIND_LABEL, nodeLabel } from "../data/meters";

interface AppliancesEnergyModalProps {
  node: EnergyNode | null;
  onClose: () => void;
}

const COLUMNS = [
  { label: "S.No", align: "left" as const, width: "w-[70px]" },
  { label: "Device", align: "left" as const, width: "w-[170px]" },
  { label: "Voltage (V)", align: "right" as const, width: "w-[110px]" },
  { label: "Current (A)", align: "right" as const, width: "w-[110px]" },
  { label: "Power Factor", align: "right" as const, width: "w-[120px]" },
  { label: "Energy (5 min in kWh)", align: "right" as const, width: "w-[170px]" },
  { label: "Energy (from mid night in kWh)", align: "right" as const, width: "" },
];

export const AppliancesEnergyModal = ({ node, onClose }: AppliancesEnergyModalProps) => {
  const appliances = node?.appliances ?? [];
  const limitCount = appliances.filter((appliance) => appliance.limitExceeded).length;
  const loadCount = appliances.filter((appliance) => appliance.loadExceeded).length;

  return (
    <DialogPrimitive.Root open={Boolean(node)} onOpenChange={(open) => !open && onClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-6 z-50 w-[calc(100%-2rem)] max-w-4xl -translate-x-1/2 overflow-hidden rounded-[2px] bg-[#4b4b52] shadow-2xl duration-200 data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
          {/* White title bar with the boxed close button */}
          <div className="flex items-start justify-between gap-4 bg-white px-5 py-3.5">
            <div className="min-w-0">
              <DialogPrimitive.Title className="text-[15px] font-semibold text-[#111114]">
                Appliances Energy
              </DialogPrimitive.Title>
              {node && (
                <DialogPrimitive.Description className="mt-0.5 truncate text-[11px] font-medium text-[#6b6b73]">
                  {KIND_LABEL[node.kind]} &middot; {nodeLabel(node)}
                  {node.path ? ` · ${node.path}` : ""}
                </DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close className="flex h-8 w-8 shrink-0 items-center justify-center border-2 border-[#111114] bg-white text-[#111114] transition-colors hover:bg-[#f0f0f2] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5865F2]">
              <X className="h-4 w-4" strokeWidth={3} />
              <span className="sr-only">Close</span>
            </DialogPrimitive.Close>
          </div>

          {/* Limit / Load counters */}
          <div className="flex items-center justify-end gap-2 px-5 py-2 text-[11px] font-bold">
            <span className="inline-flex items-center gap-1 text-[#ffc400]">
              Limit <ArrowDown className="h-3 w-3" strokeWidth={3} /> ({limitCount})
            </span>
            <span className="text-white/40">|</span>
            <span className="inline-flex items-center gap-1 text-[#ff5252]">
              Load <ArrowUp className="h-3 w-3" strokeWidth={3} /> ({loadCount})
            </span>
          </div>

          {/* Appliance meter table */}
          <div className="max-h-[70vh] overflow-auto px-3 pb-4">
            <table className="w-full min-w-[820px] border-collapse text-[12px]">
              <thead>
                <tr className="bg-[#3c3c43]">
                  {COLUMNS.map((column) => (
                    <th
                      key={column.label}
                      scope="col"
                      className={cn(
                        "whitespace-nowrap border border-[#5f5f68] px-3 py-2.5 font-bold text-white",
                        column.align === "right" ? "text-right" : "text-left",
                        column.width,
                      )}
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {appliances.length === 0 ? (
                  <tr>
                    <td
                      colSpan={COLUMNS.length}
                      className="border border-[#5f5f68] px-3 py-10 text-center text-white/70"
                    >
                      No appliance data available for this selection.
                    </td>
                  </tr>
                ) : (
                  appliances.map((appliance, index) => (
                    <tr key={appliance.id} className="bg-[#45454d] hover:bg-[#50505a]">
                      <td className="border border-[#5f5f68] px-3 py-2 text-white/80">{index + 1}</td>
                      <td className="border border-[#5f5f68] px-3 py-2 font-medium text-white">
                        <span className="flex items-center gap-1.5">
                          {appliance.device}
                          {appliance.limitExceeded && (
                            <span title="Consumption limit exceeded">
                              <ArrowDown className="h-3 w-3 text-[#ffc400]" strokeWidth={3} />
                            </span>
                          )}
                          {appliance.loadExceeded && (
                            <span title="Load threshold exceeded">
                              <ArrowUp className="h-3 w-3 text-[#ff5252]" strokeWidth={3} />
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="border border-[#5f5f68] px-3 py-2 text-right tabular-nums text-white">
                        {appliance.voltage}
                      </td>
                      <td className="border border-[#5f5f68] px-3 py-2 text-right tabular-nums text-white">
                        {appliance.current}
                      </td>
                      <td className="border border-[#5f5f68] px-3 py-2 text-right tabular-nums text-white">
                        {appliance.powerFactor}
                      </td>
                      <td className="border border-[#5f5f68] px-3 py-2 text-right tabular-nums text-white">
                        {appliance.energy5Min}
                      </td>
                      <td className="border border-[#5f5f68] px-3 py-2 text-right font-bold tabular-nums text-white">
                        {appliance.energyFromMidnight}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
};
