import { useMemo, useState } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { MeterNodeCard } from "./MeterNodeCard";
import { RoomStatusPanel } from "./RoomStatusPanel";
import { AppliancesEnergyModal } from "./AppliancesEnergyModal";
import { type EnergyNode, energyTree, findNode, flattenRooms } from "../data/meters";

const SectionGrid = ({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) => (
  <section className="rounded-[2px] border border-border/60 bg-muted/20 p-4 dark:border-slate-800/80 dark:bg-slate-900/30">
    <div className="mb-3 flex items-center gap-2">
      <h3 className="text-[13px] font-bold text-foreground">{title}</h3>
      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground">{count}</span>
    </div>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{children}</div>
  </section>
);

interface MeterHierarchyViewProps {
  title: string;
  /** Drives the bold figure on each card and the total in the title strip. */
  metric: "energy" | "power";
  /** Renders the room status board underneath the room cards. */
  showRoomStatus?: boolean;
}

/**
 * Building -> Floor -> Room drill-down shared by Energy View and Power View.
 * Clicking a card's top section opens the next level down; clicking its footer
 * opens the appliance level meter readings for that node.
 */
export const MeterHierarchyView = ({ title, metric, showRoomStatus = false }: MeterHierarchyViewProps) => {
  const [buildingId, setBuildingId] = useState<string | null>(null);
  const [floorId, setFloorId] = useState<string | null>(null);
  const [applianceNode, setApplianceNode] = useState<EnergyNode | null>(null);

  const isPower = metric === "power";
  const building = buildingId ? findNode(energyTree, buildingId) : undefined;
  const floor = floorId ? findNode(energyTree, floorId) : undefined;

  // Rooms narrow down as the user drills in: whole site -> building -> floor.
  const rooms = useMemo(() => {
    if (floor) return floor.children;
    if (building) return flattenRooms(building.children);
    return flattenRooms(energyTree);
  }, [building, floor]);

  const summary = useMemo(() => {
    const scope = floor ?? building;
    const scopedRooms = scope ? flattenRooms([scope]) : flattenRooms(energyTree);
    const total = scopedRooms.reduce((sum, room) => sum + (isPower ? room.liveKw : room.energyKwh), 0);
    return {
      total: Math.round(total * 100) / 100,
      online: scopedRooms.filter((room) => room.status === "online").length,
      offline: scopedRooms.filter((room) => room.status === "offline").length,
      alerts: scopedRooms.reduce((sum, room) => sum + room.alerts, 0),
    };
  }, [building, floor, isPower]);

  const handleDrillDown = (node: EnergyNode) => {
    if (node.kind === "building") {
      // Clicking the open building again collapses it.
      setBuildingId(node.id === buildingId ? null : node.id);
      setFloorId(null);
      return;
    }

    if (node.kind === "floor") {
      setFloorId(node.id === floorId ? null : node.id);
      return;
    }

    // Rooms are leaves - drilling in shows their appliance meters.
    setApplianceNode(node);
  };

  const resetToSite = () => {
    setBuildingId(null);
    setFloorId(null);
  };

  return (
    <div className="-m-5 min-h-[calc(100vh-76px)] bg-background">
      {/* Grey title strip with the live status legend */}
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 bg-[#7a7a7a] px-5 py-2">
        <h1 className="text-[13px] font-bold text-white">{title}</h1>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-semibold">
          <span className="text-[#4ade80]">Online ({summary.online})</span>
          <span className="text-white/50">|</span>
          <span className="text-[#ffb74d]">Offline ({summary.offline})</span>
          <span className="text-white/50">|</span>
          <span className="text-[#ff5252]">Alerts Active ({summary.alerts})</span>
          <span className="text-white/50">|</span>
          <span className="text-white">
            {isPower ? `Power In ${summary.total} KW` : `Energy In ${summary.total} kWh`}
          </span>
        </div>
      </header>

      <div className="space-y-4 p-4">
        {/* Drill-down trail plus a key for the two figures on each card */}
        <nav className="flex flex-wrap items-center gap-1 text-[12px]" aria-label={`${title} hierarchy`}>
          <button
            type="button"
            onClick={resetToSite}
            className={cn(
              "rounded-[2px] px-2 py-1 font-semibold transition-colors hover:bg-muted",
              building ? "text-muted-foreground" : "text-foreground",
            )}
          >
            All Buildings
          </button>
          {building && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              <button
                type="button"
                onClick={() => setFloorId(null)}
                className={cn(
                  "rounded-[2px] px-2 py-1 font-semibold transition-colors hover:bg-muted",
                  floor ? "text-muted-foreground" : "text-foreground",
                )}
              >
                {building.name}
              </button>
            </>
          )}
          {floor && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="rounded-[2px] px-2 py-1 font-semibold text-foreground">{floor.name}</span>
            </>
          )}
          <span className="ml-auto text-[10px] font-medium text-muted-foreground">
            Card figures: <span className="text-[#f0616f]">live kW</span> |{" "}
            {isPower ? "peak demand today (kW)" : "energy from midnight (kWh)"}
          </span>
        </nav>

        {/* Level 1: buildings */}
        <SectionGrid title="Building" count={energyTree.length}>
          {energyTree.map((node) => (
            <MeterNodeCard
              key={node.id}
              node={node}
              metric={metric}
              selected={node.id === buildingId}
              onDrillDown={handleDrillDown}
              onOpenAppliances={setApplianceNode}
            />
          ))}
        </SectionGrid>

        {/* Level 2: floors of the selected building */}
        {building && (
          <SectionGrid title="Floor" count={building.children.length}>
            {building.children.length === 0 ? (
              <p className="col-span-full py-6 text-center text-[12px] text-muted-foreground">
                No floors configured for {building.name}.
              </p>
            ) : (
              building.children.map((node) => (
                <MeterNodeCard
                  key={node.id}
                  node={node}
                  metric={metric}
                  selected={node.id === floorId}
                  onDrillDown={handleDrillDown}
                  onOpenAppliances={setApplianceNode}
                />
              ))
            )}
          </SectionGrid>
        )}

        {/* Level 3: rooms in the current scope */}
        <SectionGrid
          title={floor ? `Room - ${floor.name}` : building ? `Room - ${building.name}` : "Room"}
          count={rooms.length}
        >
          {rooms.length === 0 ? (
            <p className="col-span-full py-6 text-center text-[12px] text-muted-foreground">
              No rooms configured for this selection.
            </p>
          ) : (
            rooms.map((node) => (
              <MeterNodeCard
                key={node.id}
                node={node}
                metric={metric}
                selected={applianceNode?.id === node.id}
                onDrillDown={handleDrillDown}
                onOpenAppliances={setApplianceNode}
              />
            ))
          )}
        </SectionGrid>

        {/* Room status board for the current scope */}
        {showRoomStatus && <RoomStatusPanel rooms={rooms} onSelectRoom={setApplianceNode} />}
      </div>

      <AppliancesEnergyModal node={applianceNode} onClose={() => setApplianceNode(null)} />
    </div>
  );
};
