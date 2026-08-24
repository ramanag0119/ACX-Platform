/**
 * Metering hierarchy shared by Energy View and Power View:
 * Building -> Floor -> Room -> Appliance.
 *
 * Every node exposes the same shape so the card grid can render any level of
 * the tree, and parent readings are aggregated from their children so the
 * numbers on a Building card always reconcile with its floors and rooms.
 */

export type EnergyNodeKind = "building" | "floor" | "room";

/** Housekeeping state of a room, shown as a colour tile in Power View. */
export type RoomOccupancy = "available" | "occupied" | "maintenance" | "non-smart";

export interface ApplianceReading {
  id: string;
  device: string;
  voltage: number;
  current: number;
  powerFactor: number;
  /** kWh accumulated in the last 5 minute window. */
  energy5Min: number;
  /** kWh accumulated since midnight. */
  energyFromMidnight: number;
  /** Configured consumption limit for the appliance was crossed. */
  limitExceeded: boolean;
  /** Instantaneous load crossed the configured threshold. */
  loadExceeded: boolean;
}

export interface EnergyNode {
  id: string;
  kind: EnergyNodeKind;
  name: string;
  /** Room/unit number rendered after the name, e.g. "Restaurant - 102". */
  code?: string;
  /** Breadcrumb of the ancestors, e.g. "Building A -> Floor 1". */
  path?: string;
  status: "online" | "offline";
  alerts: number;
  /** Live load in kW - the red figure on the card in both views. */
  liveKw: number;
  /** Energy since midnight in kWh - the bold figure in Energy View. */
  energyKwh: number;
  /** Peak demand recorded today in kW - the bold figure in Power View. */
  peakKw: number;
  /** Metered devices behind this node - the figure in the card footer. */
  deviceCount: number;
  /** Rooms only - drives the Power View room status tiles. */
  occupancy?: RoomOccupancy;
  appliances: ApplianceReading[];
  children: EnergyNode[];
}

/* ------------------------------------------------------------------ */
/* Mock meter readings                                                */
/* ------------------------------------------------------------------ */

/** Deterministic PRNG so the mock readings stay stable between renders. */
const seededRandom = (seed: string) => {
  let hash = 2166136261;
  for (let i = 0; i < seed.length; i += 1) {
    hash ^= seed.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return () => {
    hash = (Math.imul(hash, 1103515245) + 12345) & 0x7fffffff;
    return hash / 0x7fffffff;
  };
};

const round = (value: number, decimals: number) => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
};

const APPLIANCE_TYPES = [
  "Air Conditioner",
  "Lighting",
  "Ceiling Fan",
  "Power Socket",
  "Water Heater",
  "Mini Bar",
  "Television",
];

const buildAppliances = (roomId: string, offline: boolean): ApplianceReading[] => {
  const random = seededRandom(roomId);
  const count = 3 + Math.floor(random() * 3);

  return Array.from({ length: count }, (_, index) => {
    const voltage = offline ? 0 : round(228 + random() * 13, 1);
    const current = offline ? 0 : round(0.2 + random() * 6.3, 2);
    const powerFactor = offline ? 0 : round(0.82 + random() * 0.17, 2);
    const energy5Min = round((voltage * current * powerFactor) / 12000, 3);
    const hoursElapsed = 6 + random() * 10;

    return {
      id: `${roomId}-A${index + 1}`,
      device: APPLIANCE_TYPES[(index + roomId.length) % APPLIANCE_TYPES.length],
      voltage,
      current,
      powerFactor,
      energy5Min,
      energyFromMidnight: round(energy5Min * 12 * hoursElapsed, 2),
      limitExceeded: !offline && random() > 0.82,
      loadExceeded: !offline && current > 5.4,
    };
  });
};

/* ------------------------------------------------------------------ */
/* Tree construction                                                  */
/* ------------------------------------------------------------------ */

interface RoomSeed {
  name: string;
  code: string;
  offline?: boolean;
}

interface FloorSeed {
  name: string;
  rooms: RoomSeed[];
}

interface BuildingSeed {
  name: string;
  floors: FloorSeed[];
}

const BUILDING_SEEDS: BuildingSeed[] = [
  {
    name: "Building A",
    floors: [
      {
        name: "Floor 1",
        rooms: [
          { name: "Store Room", code: "101" },
          { name: "Restaurant", code: "102" },
          { name: "Restaurant", code: "104" },
          { name: "Restaurant", code: "105" },
          { name: "Car Parking", code: "109" },
          { name: "Store Room", code: "103", offline: true },
          { name: "Restaurant", code: "3" },
        ],
      },
      {
        name: "Floor 2",
        rooms: [
          { name: "Conference Hall", code: "201" },
          { name: "Guest Room", code: "202" },
          { name: "Guest Room", code: "203", offline: true },
          { name: "Pantry", code: "205" },
        ],
      },
      {
        name: "Floor 3",
        rooms: [
          { name: "Car Parking", code: "306" },
          { name: "Car Parking", code: "3002" },
          { name: "Car Parking", code: "303" },
          { name: "Car Parking", code: "311" },
        ],
      },
      {
        name: "Floor 4",
        rooms: [
          { name: "Spa", code: "401" },
          { name: "Gym", code: "402" },
          { name: "Laundry", code: "404", offline: true },
        ],
      },
      {
        name: "Floor 5",
        rooms: [
          { name: "Champagne Bar", code: "502" },
          { name: "Restaurant", code: "504" },
          { name: "Restaurant", code: "506" },
          { name: "Restaurant", code: "507" },
          { name: "Restaurant", code: "508" },
        ],
      },
    ],
  },
  {
    name: "Demo Box",
    floors: [
      {
        name: "US Demo",
        rooms: [
          { name: "Demo Room", code: "D1" },
          { name: "Demo Room", code: "D2" },
        ],
      },
      {
        name: "Demo",
        rooms: [{ name: "Show Room", code: "D3" }],
      },
    ],
  },
  {
    name: "Dev & Testing",
    floors: [
      {
        name: "Floor 1",
        rooms: [
          { name: "Senthil MDU Room", code: "T1" },
          { name: "Senthil USA", code: "T2", offline: true },
        ],
      },
    ],
  },
  {
    name: "Building D PILOT",
    floors: [
      {
        name: "Ground Floor",
        rooms: [
          { name: "Lobby", code: "G01" },
          { name: "Reception", code: "G02" },
          { name: "Utility Room", code: "G03", offline: true },
        ],
      },
    ],
  },
];

const slug = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

type AggregateInput = Omit<
  EnergyNode,
  "liveKw" | "energyKwh" | "peakKw" | "deviceCount" | "alerts" | "status"
>;

const aggregate = (node: AggregateInput): EnergyNode => {
  const { children } = node;
  return {
    ...node,
    liveKw: round(
      children.reduce((sum, child) => sum + child.liveKw, 0),
      2,
    ),
    energyKwh: round(
      children.reduce((sum, child) => sum + child.energyKwh, 0),
      2,
    ),
    peakKw: round(
      children.reduce((sum, child) => sum + child.peakKw, 0),
      2,
    ),
    deviceCount: children.reduce((sum, child) => sum + child.deviceCount, 0),
    alerts: children.reduce((sum, child) => sum + child.alerts, 0),
    status: children.some((child) => child.status === "online") ? "online" : "offline",
  };
};

const buildTree = (): EnergyNode[] =>
  BUILDING_SEEDS.map((building) => {
    const buildingId = slug(building.name);

    const floors = building.floors.map((floor) => {
      const floorId = `${buildingId}--${slug(floor.name)}`;

      const rooms: EnergyNode[] = floor.rooms.map((room) => {
        const roomId = `${floorId}--${slug(`${room.name}-${room.code}`)}`;
        const appliances = buildAppliances(roomId, Boolean(room.offline));
        const liveKw = round(
          appliances.reduce(
            (sum, appliance) => sum + (appliance.voltage * appliance.current * appliance.powerFactor) / 1000,
            0,
          ),
          2,
        );
        // A second draw from the room seed keeps peak and occupancy stable too.
        const roomRandom = seededRandom(`${roomId}-state`);
        const occupancyRoll = roomRandom();

        return {
          id: roomId,
          kind: "room" as const,
          name: room.name,
          code: room.code,
          path: `${building.name} -> ${floor.name}`,
          status: room.offline ? ("offline" as const) : ("online" as const),
          alerts: appliances.filter((appliance) => appliance.limitExceeded || appliance.loadExceeded).length,
          liveKw,
          energyKwh: round(
            appliances.reduce((sum, appliance) => sum + appliance.energyFromMidnight, 0),
            2,
          ),
          peakKw: round(liveKw * (1.15 + roomRandom() * 0.45), 2),
          deviceCount: appliances.length,
          // An unreachable meter cannot report a housekeeping state.
          occupancy: room.offline
            ? ("non-smart" as const)
            : occupancyRoll > 0.62
              ? ("available" as const)
              : occupancyRoll > 0.28
                ? ("occupied" as const)
                : ("maintenance" as const),
          appliances,
          children: [],
        };
      });

      return aggregate({
        id: floorId,
        kind: "floor",
        name: floor.name,
        path: building.name,
        appliances: rooms.flatMap((room) => room.appliances),
        children: rooms,
      });
    });

    return aggregate({
      id: buildingId,
      kind: "building",
      name: building.name,
      appliances: floors.flatMap((floor) => floor.appliances),
      children: floors,
    });
  });

export const energyTree: EnergyNode[] = buildTree();

/* ------------------------------------------------------------------ */
/* Selectors                                                          */
/* ------------------------------------------------------------------ */

export const flattenRooms = (nodes: EnergyNode[]): EnergyNode[] =>
  nodes.flatMap((node) => (node.kind === "room" ? [node] : flattenRooms(node.children)));

export const findNode = (nodes: EnergyNode[], id: string): EnergyNode | undefined => {
  for (const node of nodes) {
    if (node.id === id) return node;
    const match = findNode(node.children, id);
    if (match) return match;
  }
  return undefined;
};

export const nodeLabel = (node: EnergyNode) => (node.code ? `${node.name} - ${node.code}` : node.name);

export const KIND_LABEL: Record<EnergyNodeKind, string> = {
  building: "Building",
  floor: "Floor",
  room: "Room",
};
