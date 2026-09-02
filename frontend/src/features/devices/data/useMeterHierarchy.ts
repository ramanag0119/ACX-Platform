/**
 * The live reads behind the Energy View / Power View metering hierarchy.
 *
 *   Buildings / Floors -> GET /buildings, GET /floors      (names + ordering)
 *   Rooms + status     -> GET /occupancy                   (`amenity_status`)
 *   Appliances         -> GET /devices                     (per room)
 *   Voltage / Current / Power Factor / Active Power
 *                      -> GET /device-stats?param_name=... (latest per device)
 *   Energy per room    -> GET /energy-stats/summary?group_by=amenity
 *   Energy per device  -> GET /energy-stats/summary?group_by=device
 *   Alerts             -> GET /value-alerts?status=0       (active only)
 *
 * `energy_stat` stores no unit and the API returns `energy_unit: null`, so the
 * energy figures here are never labelled kWh. Nothing is converted, costed or
 * carbon-weighted, and a parameter a device has not reported stays null.
 *
 * Every list is capped at MAX_PAGE_SIZE, the backend's own limit. /device-stats
 * comes back newest-first, so the first row seen per device is its latest
 * reading -- the same rule the previous room list used.
 */

import { useMemo, useState } from "react";

import {
  useBuildings,
  useDeviceStats,
  useDevices,
  useEnergySummary,
  useFloors,
  useOccupancy,
  useValueAlerts,
} from "@/lib/api/hooks";
import { MAX_PAGE_SIZE, type DeviceStatRead, type ValueAlertRead } from "@/lib/api/types";

import { buildMeterTree, type DeviceReadings, type MeterNode } from "./meters";

const PAGE = { page: 1, page_size: MAX_PAGE_SIZE };

/** The filter selections, already narrowed to the ids the API accepts. */
export interface MeterScope {
  building_id?: string;
  floor_id?: string;
  amenity_id?: string;
}

/** The Building / Floor / Room filters. "all" means the level is unfiltered. */
export interface MeterFilterState {
  building: string;
  floor: string;
  room: string;
  onBuildingChange: (value: string) => void;
  onFloorChange: (value: string) => void;
  onRoomChange: (value: string) => void;
}

/**
 * The filter state and the API scope it produces.
 *
 * Choosing a level clears the ones below it: a floor id from the previous
 * building, or a room id from the previous floor, would otherwise be sent
 * alongside the new selection and match nothing.
 */
export const useMeterFilters = (): { scope: MeterScope; filters: MeterFilterState } => {
  const [building, setBuilding] = useState("all");
  const [floor, setFloor] = useState("all");
  const [room, setRoom] = useState("all");

  return {
    scope: {
      ...(building !== "all" ? { building_id: building } : {}),
      ...(floor !== "all" ? { floor_id: floor } : {}),
      ...(room !== "all" ? { amenity_id: room } : {}),
    },
    filters: {
      building,
      floor,
      room,
      onBuildingChange: (value) => {
        setBuilding(value);
        setFloor("all");
        setRoom("all");
      },
      onFloorChange: (value) => {
        setFloor(value);
        setRoom("all");
      },
      onRoomChange: setRoom,
    },
  };
};

/** Latest numeric reading per device. /device-stats is ordered timestamp DESC,
 *  so the first row seen for a device is the one to keep. */
const latestByDevice = (rows: DeviceStatRead[] | undefined) => {
  const values = new Map<string, number>();
  for (const row of rows ?? []) {
    if (values.has(row.device_id)) continue;
    const value = Number(row.device_param_value);
    if (row.device_param_value !== null && !Number.isNaN(value)) {
      values.set(row.device_id, value);
    }
  }
  return values;
};

export interface MeterHierarchy {
  tree: MeterNode[];
  isLoading: boolean;
  error: unknown;
  /** For the Buildings filter. */
  buildings: { id: string; name: string }[];
  /** For the Floors filter, already narrowed by the selected building. */
  floors: { id: string; name: string }[];
  /** For the Rooms filter, in the current scope. */
  rooms: { id: string; name: string }[];
  /** Devices reporting `is_power_off === false` in scope. */
  activeDevices: number;
  /** Rooms whose `amenity_status` is Occupied, in scope. */
  occupiedRooms: number;
  /** SUM over `energy_stat` in scope. Carries no unit. */
  totalEnergy: number;
}

export const useMeterHierarchy = (scope: MeterScope): MeterHierarchy => {
  const buildingsQuery = useBuildings(PAGE);
  const floorsQuery = useFloors({
    ...PAGE,
    ...(scope.building_id ? { building_id: scope.building_id } : {}),
  });

  const occupancyQuery = useOccupancy({ ...PAGE, ...scope });
  const devicesQuery = useDevices({ ...PAGE, ...scope });

  const voltageQuery = useDeviceStats({ ...PAGE, param_name: "voltage", ...scope });
  const currentQuery = useDeviceStats({ ...PAGE, param_name: "current", ...scope });
  const powerFactorQuery = useDeviceStats({ ...PAGE, param_name: "power_factor", ...scope });
  const activePowerQuery = useDeviceStats({ ...PAGE, param_name: "active_power", ...scope });

  const roomEnergyQuery = useEnergySummary({ group_by: "amenity", ...scope });
  const deviceEnergyQuery = useEnergySummary({ group_by: "device", ...scope });

  // /value-alerts filters on the device or the room, not the chain, so it is
  // narrowed only when a specific room is selected.
  const alertsQuery = useValueAlerts({
    ...PAGE,
    status: 0,
    ...(scope.amenity_id ? { amenity_id: scope.amenity_id } : {}),
  });

  // Memoised because the `?? []` fallback would otherwise be a fresh array on
  // every render, rebuilding the tree each time.
  const rooms = useMemo(() => occupancyQuery.data?.items ?? [], [occupancyQuery.data]);
  const devices = useMemo(() => devicesQuery.data?.items ?? [], [devicesQuery.data]);

  const readingsByDevice = useMemo(() => {
    const voltage = latestByDevice(voltageQuery.data?.items);
    const current = latestByDevice(currentQuery.data?.items);
    const powerFactor = latestByDevice(powerFactorQuery.data?.items);
    const activePower = latestByDevice(activePowerQuery.data?.items);

    const deviceIds = new Set([
      ...voltage.keys(),
      ...current.keys(),
      ...powerFactor.keys(),
      ...activePower.keys(),
    ]);

    const readings = new Map<string, DeviceReadings>();
    for (const deviceId of deviceIds) {
      readings.set(deviceId, {
        voltage: voltage.get(deviceId) ?? null,
        current: current.get(deviceId) ?? null,
        powerFactor: powerFactor.get(deviceId) ?? null,
        activePower: activePower.get(deviceId) ?? null,
      });
    }
    return readings;
  }, [
    voltageQuery.data,
    currentQuery.data,
    powerFactorQuery.data,
    activePowerQuery.data,
  ]);

  const alertsByDevice = useMemo(() => {
    const grouped = new Map<string, ValueAlertRead[]>();
    for (const alert of alertsQuery.data?.items ?? []) {
      const bucket = grouped.get(alert.device_id);
      if (bucket) bucket.push(alert);
      else grouped.set(alert.device_id, [alert]);
    }
    return grouped;
  }, [alertsQuery.data]);

  const tree = useMemo(
    () =>
      buildMeterTree({
        buildings: buildingsQuery.data?.items ?? [],
        floors: floorsQuery.data?.items ?? [],
        rooms,
        devices,
        energyByAmenity: new Map(
          (roomEnergyQuery.data?.buckets ?? []).map((bucket) => [
            bucket.bucket,
            bucket.total_energy_consumed,
          ]),
        ),
        energyByDeviceName: new Map(
          (deviceEnergyQuery.data?.buckets ?? []).map((bucket) => [
            bucket.bucket,
            bucket.total_energy_consumed,
          ]),
        ),
        readingsByDevice,
        alertsByDevice,
      }),
    [
      buildingsQuery.data,
      floorsQuery.data,
      rooms,
      devices,
      roomEnergyQuery.data,
      deviceEnergyQuery.data,
      readingsByDevice,
      alertsByDevice,
    ],
  );

  return {
    tree,
    // The tree cannot be drawn without its rooms, their devices or the
    // readings behind the card figures.
    isLoading:
      occupancyQuery.isLoading ||
      devicesQuery.isLoading ||
      activePowerQuery.isLoading ||
      roomEnergyQuery.isLoading,
    error:
      occupancyQuery.error ??
      devicesQuery.error ??
      activePowerQuery.error ??
      roomEnergyQuery.error,
    buildings: (buildingsQuery.data?.items ?? []).map((building) => ({
      id: building.id,
      name: building.name,
    })),
    floors: (floorsQuery.data?.items ?? []).map((floor) => ({
      id: floor.id,
      name: floor.name,
    })),
    rooms: rooms.map((room) => ({ id: room.amenity_id, name: room.room_name })),
    activeDevices: devices.filter((device) => device.is_power_off === false).length,
    occupiedRooms: rooms.filter((room) => room.status_name === "Occupied").length,
    totalEnergy: roomEnergyQuery.data?.total_energy_consumed ?? 0,
  };
};
