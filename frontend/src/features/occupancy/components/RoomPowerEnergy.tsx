/**
 * Power and Energy for ONE room, inside Room Details.
 *
 * This is where the retired Power View and Energy View went. It reuses their
 * reads verbatim, narrowed to a single amenity so nothing can bleed between
 * rooms:
 *
 *   Power   -> GET /device-stats?param_name=active_power&amenity_id=...
 *              `device_param` 18/27, unit KW. Instantaneous load.
 *   Energy  -> GET /device-stats?param_name=active_energy&amenity_id=...
 *              `device_param` 7/11, unit kWh. Cumulative meter reading.
 *   Energy  -> GET /energy-stats/summary?group_by=amenity&amenity_id=...
 *              SUM over `energy_stat.energy_consumed`, the figure Energy View
 *              showed. That table has no unit column, so the API returns
 *              `energy_unit: null` and this figure is never labelled kWh.
 *   Room    -> GET /device-stats?param_name=room_temperature | air_quality
 *              The environment sensor's own parameters (device_type 2).
 *
 * POWER AND ENERGY ARE NOT INTERCHANGED. `active_power` is only ever rendered
 * as load and `active_energy` / `energy_consumed` only ever as consumption.
 *
 * Every unit shown comes from the API's own `unit` field, never from a literal
 * here. A parameter a room's devices have not reported renders "-"; nothing is
 * inferred, defaulted or filled in.
 *
 * RBAC. /device-stats is gated on `caleido_network` and /energy-stats on
 * `reports` -- neither is the `occupancy` grant that opens this dialog. Each
 * read is therefore requested only when its grant is held, so a housekeeping
 * role sees a plain note instead of a wall of 403s.
 */

import { useMemo } from "react";

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { DataState } from "@/core/components/DataState";
import { DETAIL_GRID, EMPTY_VALUE, Field } from "./DetailField";
import { useAuth } from "@/core/contexts/AuthContext";
import { useDeviceStats, useEnergySummary } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE, type DeviceStatRead } from "@/lib/api/types";

const PAGE = { page: 1, page_size: MAX_PAGE_SIZE };

/**
 * Column heading styling for the per-device table below the totals.
 *
 * The grid above it no longer declares styles of its own: its labels and values
 * come from the shared `Field`, so this tab matches the Details tab instead of
 * inventing a second typography for the same kind of data. The two constants
 * that used to live here were byte-identical to each other, and the one applied
 * to VALUES carried this table padding -- see DetailField for what that did.
 */
const HEAD_CLASS =
    "text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-2.5 px-3";

/** One device's most recent reading of one parameter, as stored. */
interface Reading {
    deviceId: string;
    deviceLabel: string;
    value: number;
    unit: string | null;
    timestamp: string;
}

/**
 * The latest reading per device for one parameter.
 *
 * /device-stats is ordered `timestamp DESC, id DESC`, so the first row seen for
 * a device is its newest -- the same rule the metering hierarchy used. Values
 * are VARCHAR in `device_stat`; a non-numeric one is skipped rather than
 * coerced to zero.
 */
const latestPerDevice = (rows: DeviceStatRead[] | undefined) => {
    const byDevice = new Map<string, Reading>();
    for (const row of rows ?? []) {
        if (byDevice.has(row.device_id)) continue;
        if (row.device_param_value === null) continue;
        const value = Number(row.device_param_value);
        if (Number.isNaN(value)) continue;
        byDevice.set(row.device_id, {
            deviceId: row.device_id,
            deviceLabel: row.device_name ?? row.device_uid ?? "Unnamed device",
            value,
            unit: row.unit,
            timestamp: row.timestamp,
        });
    }
    return byDevice;
};

const round = (value: number, decimals = 3) => {
    const factor = 10 ** decimals;
    return Math.round(value * factor) / factor;
};

/**
 * Sums the readings in scope. Null when no device reported the parameter.
 *
 * Only valid for the additive parameters: load and consumption across the
 * meters in one room really do add up. Ambient readings do not -- see `latest`.
 */
const total = (readings: Map<string, Reading>) => {
    if (readings.size === 0) return null;
    let sum = 0;
    for (const reading of readings.values()) sum += reading.value;
    return round(sum);
};

/**
 * The single most recent reading in scope.
 *
 * Used for temperature and air quality, which are ambient measurements: two
 * sensors in one room describe the same condition, so adding or averaging them
 * would invent a figure the database does not hold. The newest sample is
 * reported as stored.
 */
const latest = (readings: Map<string, Reading>): Reading | null => {
    let newest: Reading | null = null;
    for (const reading of readings.values()) {
        if (!newest || reading.timestamp > newest.timestamp) newest = reading;
    }
    return newest;
};

/** The unit the API reported for a parameter. Blank when the table stores none. */
const unitOf = (readings: Map<string, Reading>) => {
    for (const reading of readings.values()) if (reading.unit) return reading.unit;
    return null;
};

const show = (value: number | null, unit: string | null) =>
    value === null ? EMPTY_VALUE : unit ? `${value} ${unit}` : String(value);

const formatDateTime = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString() : EMPTY_VALUE;

const Note = ({ children }: { children: React.ReactNode }) => (
    <p className="text-xs text-muted-foreground">{children}</p>
);

interface RoomPowerEnergyProps {
    /** `amenity.id` of the room this dialog is showing, or null when closed. */
    amenityId: string | null;
}

export function RoomPowerEnergy({ amenityId }: RoomPowerEnergyProps) {
    const { canRead } = useAuth();
    const mayReadTelemetry = canRead("caleido_network");
    const mayReadEnergy = canRead("reports");

    // A closed dialog carries no amenity id, and a role without the grant must
    // not ask at all -- hence `enabled` rather than undefined params, which
    // these hooks would otherwise fetch unfiltered.
    const telemetryOn = Boolean(amenityId) && mayReadTelemetry;
    const energyOn = Boolean(amenityId) && mayReadEnergy;

    const stats = (paramName: string) =>
        telemetryOn
            ? { ...PAGE, param_name: paramName, amenity_id: amenityId as string }
            : undefined;

    const powerQuery = useDeviceStats(stats("active_power"), { enabled: telemetryOn });
    const energyQuery = useDeviceStats(stats("active_energy"), { enabled: telemetryOn });
    const temperatureQuery = useDeviceStats(stats("room_temperature"), {
        enabled: telemetryOn,
    });
    const airQualityQuery = useDeviceStats(stats("air_quality"), { enabled: telemetryOn });
    const energySummaryQuery = useEnergySummary(
        energyOn ? { group_by: "amenity", amenity_id: amenityId as string } : undefined,
        { enabled: energyOn },
    );

    const power = useMemo(() => latestPerDevice(powerQuery.data?.items), [powerQuery.data]);
    const energy = useMemo(() => latestPerDevice(energyQuery.data?.items), [energyQuery.data]);
    const temperature = useMemo(
        () => latestPerDevice(temperatureQuery.data?.items),
        [temperatureQuery.data],
    );
    const airQuality = useMemo(
        () => latestPerDevice(airQualityQuery.data?.items),
        [airQualityQuery.data],
    );

    // One row per device that reported load or consumption for this room.
    const meteredDevices = useMemo(() => {
        const ids = new Set([...power.keys(), ...energy.keys()]);
        return [...ids]
            .map((deviceId) => {
                const load = power.get(deviceId);
                const consumption = energy.get(deviceId);
                return {
                    deviceId,
                    label: (load ?? consumption)!.deviceLabel,
                    load,
                    consumption,
                    // The newest of the two readings this row shows.
                    lastSeen: [load?.timestamp, consumption?.timestamp]
                        .filter(Boolean)
                        .sort()
                        .pop() as string | undefined,
                };
            })
            .sort((a, b) => a.label.localeCompare(b.label));
    }, [power, energy]);

    const isLoading =
        powerQuery.isLoading ||
        energyQuery.isLoading ||
        temperatureQuery.isLoading ||
        airQualityQuery.isLoading ||
        energySummaryQuery.isLoading;
    const error =
        powerQuery.error ??
        energyQuery.error ??
        temperatureQuery.error ??
        airQualityQuery.error ??
        energySummaryQuery.error;

    // `energy_stat` stores no unit column, so this stays unlabelled by design.
    const recorded = energySummaryQuery.data;
    const recordedTotal =
        recorded && recorded.reading_count > 0 ? round(recorded.total_energy_consumed) : null;

    if (!mayReadTelemetry && !mayReadEnergy) {
        return (
            <Note>
                Power and energy readings need read access to{" "}
                <span className="font-mono">caleido_network</span> or{" "}
                <span className="font-mono">reports</span>, which your role does not hold.
            </Note>
        );
    }

    return (
        <DataState isLoading={isLoading} error={error}>
            <div className="space-y-4">
                {/* Room totals, grouped by domain rather than by the order the
                    reads happen to be declared in: the ambient conditions the
                    environment sensor reports first, then everything the meters
                    report. Both rows use the shared DETAIL_GRID, so these values
                    sit on the same four columns -- and in the same typography --
                    as the Details tab. Power and energy remain separate figures
                    from separate parameters and are never combined. */}
                <div className="space-y-6">
                    {/* Environmental. Two items on the first two tracks; the
                        remaining two stay empty so the power row underneath
                        keeps its own columns. */}
                    <div className={DETAIL_GRID}>
                        <Field
                            label="Room Temperature"
                            value={show(
                                latest(temperature)?.value ?? null,
                                latest(temperature)?.unit ?? null,
                            )}
                        />
                        <Field
                            label="Air Quality"
                            value={show(
                                latest(airQuality)?.value ?? null,
                                latest(airQuality)?.unit ?? null,
                            )}
                        />
                    </div>

                    {/* Electrical. */}
                    <div className={DETAIL_GRID}>
                        <Field
                            label="Power Consumed"
                            value={show(total(power), unitOf(power))}
                        />
                        <Field
                            label="Energy Consumed"
                            value={show(total(energy), unitOf(energy))}
                        />
                        <Field
                            label="Recorded Consumption"
                            value={show(recordedTotal, recorded?.energy_unit ?? null)}
                            title={
                                "SUM over energy_stat for this room. That table has no unit " +
                                "column, so the API returns energy_unit: null and the figure " +
                                "is shown unlabelled."
                            }
                        />
                        <Field
                            label="Last Reading"
                            value={recorded?.reading_count ?? EMPTY_VALUE}
                        />
                    </div>
                </div>

                {!mayReadTelemetry && (
                    <Note>
                        Live load and meter readings need read access to{" "}
                        <span className="font-mono">caleido_network</span>.
                    </Note>
                )}
                {!mayReadEnergy && (
                    <Note>
                        Recorded consumption needs read access to{" "}
                        <span className="font-mono">reports</span>.
                    </Note>
                )}

                {/* Per-device breakdown, so a room total can be traced to the
                    device that produced it. */}
                <div className="rounded-lg overflow-hidden overflow-x-auto scrollbar-thin border border-border/80 dark:border-slate-800">
                    <DataState
                        isLoading={false}
                        error={null}
                        isEmpty={meteredDevices.length === 0}
                        emptyTitle="No metered readings recorded for this room"
                    >
                        <Table>
                            <TableHeader className="bg-muted/40 dark:bg-[#0e1322]">
                                <TableRow>
                                    <TableHead className={HEAD_CLASS}>Device</TableHead>
                                    <TableHead className={HEAD_CLASS}>Power Consumed</TableHead>
                                    <TableHead className={HEAD_CLASS}>Energy Consumed</TableHead>
                                    <TableHead className={`${HEAD_CLASS} text-right`}>
                                        Last Reading
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {meteredDevices.map((row) => (
                                    <TableRow key={row.deviceId} className="hover:bg-muted/5">
                                        <TableCell>{row.label}</TableCell>
                                        <TableCell>
                                            {show(row.load?.value ?? null, row.load?.unit ?? null)}
                                        </TableCell>
                                        <TableCell>
                                            {show(
                                                row.consumption?.value ?? null,
                                                row.consumption?.unit ?? null,
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {formatDateTime(row.lastSeen)}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </DataState>
                </div>
            </div>
        </DataState>
    );
}
