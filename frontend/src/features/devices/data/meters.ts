/**
 * Metering hierarchy shared by Energy View and Power View:
 * Building -> Floor -> Room -> Appliance.
 *
 * Every node exposes the same shape so the card grid can render any level of
 * the tree, and parent readings are folded up from their children so the
 * numbers on a Building card always reconcile with its floors and rooms.
 *
 * This module holds the shape, the selectors and the adapter that folds the
 * live HMS reads into it. It carries NO readings of its own: every figure
 * below arrives from the API, and anything a device has not reported stays
 * null rather than being inferred.
 */

import type {
  BuildingRead,
  DeviceRead,
  FloorRead,
  OccupancyRead,
  ValueAlertRead,
} from "@/lib/api/types";

export type MeterNodeKind = "building" | "floor" | "room";

/* ------------------------------------------------------------------ */
/* Room status                                                        */
/* ------------------------------------------------------------------ */

/**
 * The real `amenity_status` names -- all FOUR of them -- plus a bucket for a
 * room that reports none. Allotted (held by a stay that has not checked in)
 * is its own state and is deliberately not folded into Occupied.
 */
export const ROOM_STATUS_ORDER = [
  "Available",
  "Occupied",
  "Allotted",
  "Unavailable",
  "Unknown",
] as const;

export type RoomOccupancy = (typeof ROOM_STATUS_ORDER)[number];

export const FALLBACK_ROOM_STATUS: RoomOccupancy = "Unknown";

const KNOWN_ROOM_STATUS = new Set<string>(ROOM_STATUS_ORDER);

/** Narrows a stored `amenity_status.name` onto the union, without guessing. */
export const toRoomStatus = (name: string | null | undefined): RoomOccupancy =>
  name && KNOWN_ROOM_STATUS.has(name) ? (name as RoomOccupancy) : FALLBACK_ROOM_STATUS;

/* ------------------------------------------------------------------ */
/* Node shape                                                         */
/* ------------------------------------------------------------------ */

/**
 * One metered appliance, from `device` plus its latest `device_stat` rows.
 *
 * Each figure is null when the device has not reported that parameter. Power
 * factor is commonly null: `device_param` defines it, but not every device
 * type publishes it.
 */
export interface ApplianceReading {
  id: string;
  device: string;
  /** device_param `voltage`, in V. */
  voltage: number | null;
  /** device_param `current`, in Amps. */
  current: number | null;
  /** device_param `power_factor`, unitless. */
  powerFactor: number | null;
  /** device_param `active_power`, in KW. */
  activePower: number | null;
  /** SUM over `energy_stat` for this device. That table stores NO unit. */
  energyTotal: number | null;
  /** An active `value_alert` on a consumption parameter for this device. */
  limitExceeded: boolean;
  /** An active `value_alert` on an instantaneous load parameter. */
  loadExceeded: boolean;
}

export interface MeterNode {
  id: string;
  kind: MeterNodeKind;
  name: string;
  /** Room/unit number rendered after the name, e.g. "Guest Room - 102". */
  code?: string;
  /** Breadcrumb of the ancestors, e.g. "Building A -> Floor 1". */
  path?: string;
  /** Online when at least one device in scope reports health_status Active. */
  status: "online" | "offline";
  /** Active `value_alert` rows against the devices in scope. */
  alerts: number;
  /** Summed `active_power` in scope, in KW -- the red figure on the card. */
  liveKw: number;
  /** Summed `energy_stat` consumption in scope. Carries NO unit. */
  energyTotal: number;
  /** Highest single-device `active_power` in scope, in KW. Null if none. */
  peakLoad: number | null;
  /** Metered devices behind this node - the figure in the card footer. */
  deviceCount: number;
  /** Rooms only - drives the room status board. */
  occupancy?: RoomOccupancy;
  appliances: ApplianceReading[];
  children: MeterNode[];
}

/* ------------------------------------------------------------------ */
/* Adapter input                                                      */
/* ------------------------------------------------------------------ */

/** The latest numeric reading per electrical parameter for one device. */
export interface DeviceReadings {
  voltage: number | null;
  current: number | null;
  powerFactor: number | null;
  activePower: number | null;
}

/**
 * Everything `buildMeterTree` needs, already keyed. The caller owns the
 * fetching; this module stays a pure function of what came back.
 */
export interface MeterHierarchyInput {
  /** Used for building display names and ordering only. */
  buildings: BuildingRead[];
  /** Used for floor display names and ordering only. */
  floors: FloorRead[];
  /** GET /occupancy -- the rooms, already scoped by the page's filters. */
  rooms: OccupancyRead[];
  /** GET /devices -- the appliances, already scoped. */
  devices: DeviceRead[];
  /** amenity_id -> SUM(energy_consumed), from group_by=amenity. */
  energyByAmenity: Map<string, number>;
  /** device_name -> SUM(energy_consumed), from group_by=device. */
  energyByDeviceName: Map<string, number>;
  /** device_id -> latest reading per parameter. */
  readingsByDevice: Map<string, DeviceReadings>;
  /** device_id -> active value alerts. */
  alertsByDevice: Map<string, ValueAlertRead[]>;
}

/**
 * `limit_config.parameter` values that describe instantaneous load. An alert
 * on anything else (voltage, active_energy) reads as a consumption limit.
 */
const LOAD_PARAMS = new Set(["current", "active_power", "reactive_power"]);

const round = (value: number, decimals = 2) => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
};

/** Sums a column, returning null when nothing in scope reported it. */
const sumOrNull = (values: (number | null)[]): number | null => {
  const present = values.filter((value): value is number => value !== null);
  return present.length === 0 ? null : present.reduce((total, value) => total + value, 0);
};

const maxOrNull = (values: (number | null)[]): number | null => {
  const present = values.filter((value): value is number => value !== null);
  return present.length === 0 ? null : Math.max(...present);
};

const applianceLabel = (device: DeviceRead) =>
  device.appliance_name ?? device.device_name ?? device.device_uid ?? "Unnamed device";

const toAppliance = (
  device: DeviceRead,
  input: MeterHierarchyInput,
): ApplianceReading => {
  const readings = input.readingsByDevice.get(device.id);
  const alerts = input.alertsByDevice.get(device.id) ?? [];

  return {
    id: device.id,
    device: applianceLabel(device),
    voltage: readings?.voltage ?? null,
    current: readings?.current ?? null,
    powerFactor: readings?.powerFactor ?? null,
    activePower: readings?.activePower ?? null,
    energyTotal: device.device_name
      ? input.energyByDeviceName.get(device.device_name) ?? null
      : null,
    limitExceeded: alerts.some(
      (alert) => !alert.parameter || !LOAD_PARAMS.has(alert.parameter),
    ),
    loadExceeded: alerts.some(
      (alert) => alert.parameter !== null && LOAD_PARAMS.has(alert.parameter),
    ),
  };
};

/** Rolls a parent up from its children so every level reconciles. */
const aggregate = (
  node: Omit<
    MeterNode,
    "liveKw" | "energyTotal" | "peakLoad" | "deviceCount" | "alerts" | "status"
  >,
): MeterNode => {
  const { children } = node;
  return {
    ...node,
    liveKw: round(children.reduce((total, child) => total + child.liveKw, 0)),
    energyTotal: round(children.reduce((total, child) => total + child.energyTotal, 0), 3),
    peakLoad: maxOrNull(children.map((child) => child.peakLoad)),
    deviceCount: children.reduce((total, child) => total + child.deviceCount, 0),
    alerts: children.reduce((total, child) => total + child.alerts, 0),
    status: children.some((child) => child.status === "online") ? "online" : "offline",
  };
};

/* ------------------------------------------------------------------ */
/* Tree construction                                                  */
/* ------------------------------------------------------------------ */

const UNASSIGNED = "unassigned";

/** Label used for rooms whose `property_chain` leaves a level unset. */
const UNASSIGNED_LABEL = "Unassigned";

const groupBy = <T>(items: T[], key: (item: T) => string) => {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const bucket = groups.get(key(item));
    if (bucket) bucket.push(item);
    else groups.set(key(item), [item]);
  }
  return groups;
};

/**
 * Folds the live reads into the Building -> Floor -> Room tree.
 *
 * The tree is built upward from `rooms`, so it always reflects exactly the
 * scope the caller fetched: a building with no rooms in scope does not appear,
 * and a room whose chain leaves the building or floor unset is grouped under
 * an explicit "Unassigned" node rather than being dropped.
 */
export const buildMeterTree = (input: MeterHierarchyInput): MeterNode[] => {
  const devicesByAmenity = groupBy(input.devices, (device) => device.amenity_id);
  const buildingNames = new Map(input.buildings.map((b) => [b.id, b.name]));
  const floorNames = new Map(input.floors.map((f) => [f.id, f.name]));

  // Ordering follows the reference lists, so the grid is stable between
  // renders and matches the order the filter dropdowns show.
  const buildingOrder = new Map(input.buildings.map((b, index) => [b.id, index]));
  const floorOrder = new Map(input.floors.map((f, index) => [f.id, index]));
  const rank = (order: Map<string, number>, id: string) => order.get(id) ?? Number.MAX_SAFE_INTEGER;

  const roomsByBuilding = groupBy(input.rooms, (room) => room.building_id ?? UNASSIGNED);

  const buildings = [...roomsByBuilding.entries()]
    .sort(([a], [b]) => rank(buildingOrder, a) - rank(buildingOrder, b))
    .map(([buildingId, buildingRooms]) => {
      const buildingLabel =
        buildingId === UNASSIGNED
          ? UNASSIGNED_LABEL
          : buildingNames.get(buildingId) ??
            buildingRooms[0].building_name ??
            UNASSIGNED_LABEL;

      const roomsByFloor = groupBy(buildingRooms, (room) => room.floor_id ?? UNASSIGNED);

      const floors = [...roomsByFloor.entries()]
        .sort(([a], [b]) => rank(floorOrder, a) - rank(floorOrder, b))
        .map(([floorId, floorRooms]) => {
          const floorLabel =
            floorId === UNASSIGNED
              ? UNASSIGNED_LABEL
              : floorNames.get(floorId) ?? floorRooms[0].floor_name ?? UNASSIGNED_LABEL;

          const rooms: MeterNode[] = floorRooms.map((room) => {
            const roomDevices = devicesByAmenity.get(room.amenity_id) ?? [];
            const appliances = roomDevices.map((device) => toAppliance(device, input));
            const loads = appliances.map((appliance) => appliance.activePower);

            return {
              id: room.amenity_id,
              kind: "room" as const,
              // `amenity_type_name` is the kind of room, `room_name` the unit
              // number -- the card renders them as "Guest Room - 101".
              name: room.amenity_type_name ?? room.room_name,
              code: room.amenity_type_name ? room.room_name : undefined,
              path: `${buildingLabel} -> ${floorLabel}`,
              status: roomDevices.some((device) => device.health_status === "Active")
                ? ("online" as const)
                : ("offline" as const),
              alerts: roomDevices.reduce(
                (total, device) => total + (input.alertsByDevice.get(device.id)?.length ?? 0),
                0,
              ),
              liveKw: round(sumOrNull(loads) ?? 0),
              energyTotal: round(input.energyByAmenity.get(room.amenity_id) ?? 0, 3),
              peakLoad: maxOrNull(loads),
              deviceCount: roomDevices.length,
              occupancy: toRoomStatus(room.status_name),
              appliances,
              children: [],
            };
          });

          return aggregate({
            id: `${buildingId}--${floorId}`,
            kind: "floor",
            name: floorLabel,
            path: buildingLabel,
            appliances: rooms.flatMap((room) => room.appliances),
            children: rooms,
          });
        });

      return aggregate({
        id: buildingId,
        kind: "building",
        name: buildingLabel,
        appliances: floors.flatMap((floor) => floor.appliances),
        children: floors,
      });
    });

  return buildings;
};

/* ------------------------------------------------------------------ */
/* Selectors                                                          */
/* ------------------------------------------------------------------ */

export const flattenRooms = (nodes: MeterNode[]): MeterNode[] =>
  nodes.flatMap((node) => (node.kind === "room" ? [node] : flattenRooms(node.children)));

export const findNode = (nodes: MeterNode[], id: string): MeterNode | undefined => {
  for (const node of nodes) {
    if (node.id === id) return node;
    const match = findNode(node.children, id);
    if (match) return match;
  }
  return undefined;
};

export const nodeLabel = (node: MeterNode) => (node.code ? `${node.name} - ${node.code}` : node.name);

export const KIND_LABEL: Record<MeterNodeKind, string> = {
  building: "Building",
  floor: "Floor",
  room: "Room",
};
