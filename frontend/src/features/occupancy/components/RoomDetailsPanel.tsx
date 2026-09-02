import { useMemo } from "react";
import { Settings } from "lucide-react";
import { useTheme } from "@/core/contexts/ThemeContext";
import { DataState } from "@/core/components/DataState";
import { useDeviceStats, useDevices, useOccupancyDetail } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

interface RoomDetailsPanelProps {
  /** The room's `amenity.id`. Everything on this panel is fetched with it. */
  amenityId: string;
  /** Optional placeholders, shown only until GET /occupancy/{id} answers. */
  roomNumber?: string;
  roomType?: string;
}

const formatDateTime = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString() : "-";

/**
 * Room detail, entirely backend-driven.
 *
 * Device cards are generated from the devices actually installed in the room
 * and their latest `device_stat` readings. Parameter names and units come from
 * `device_param`; no unit is assumed, and a parameter with no unit shows none.
 * There is no fixed IntelliHub/AirQ/Mikos/Kleio card list any more, because
 * which devices a room has is data, not layout.
 */
export const RoomDetailsPanel = ({ amenityId, roomNumber, roomType }: RoomDetailsPanelProps) => {
  const { isDark } = useTheme();

  const occupancyQuery = useOccupancyDetail(amenityId);
  const devicesQuery = useDevices({ amenity_id: amenityId, page: 1, page_size: MAX_PAGE_SIZE });
  const statsQuery = useDeviceStats({ amenity_id: amenityId, page: 1, page_size: MAX_PAGE_SIZE });

  // Theme tokens
  const cardBg = isDark ? "linear-gradient(180deg, #1e2233, #1a1e30)" : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const devCardBg = isDark ? "#1e2233" : "#ffffff";
  const devCardBorder = isDark ? "rgba(255,255,255,0.07)" : "rgba(124,92,255,0.12)";
  const devHeaderBg = isDark ? "#252a3e" : "#EEF2FF";
  const devHeaderBorder = isDark ? "#2a2f42" : "#e5e7eb";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const subTitleColor = isDark ? "#8b95a9" : "#5E5A7A";
  const labelColor = isDark ? "#8b95a9" : "#8A86A8";
  const valueColor = isDark ? "#dde2ed" : "#1F1B3A";
  const rowBorder = isDark ? "rgba(255,255,255,0.06)" : "rgba(124,92,255,0.1)";

  // Device card wrapper
  const DevCard = ({ children }: { children: React.ReactNode }) => (
    <div
      className="flex flex-col h-full rounded-lg overflow-hidden shadow-[0_8px_24px_rgba(17,12,46,0.12)] transition-all duration-250 hover:-translate-y-0.5"
      style={{ background: devCardBg, border: `1px solid ${devCardBorder}` }}
    >
      {children}
    </div>
  );

  // Device card header
  const DevHeader = ({ title, showSettings = false }: { title: string; showSettings?: boolean }) => (
    <div
      className="p-3 flex items-center justify-between min-h-[48px]"
      style={{ backgroundColor: devHeaderBg, borderBottom: `1px solid ${devHeaderBorder}` }}
    >
      <span className="font-medium text-sm" style={{ color: titleColor }}>{title}</span>
      {showSettings && <Settings className="h-4 w-4" style={{ color: labelColor }} />}
    </div>
  );

  // A single data row
  const Row = ({ label, value }: { label: string; value: string }) => (
    <div className="flex justify-between items-center gap-3">
      <span style={{ color: labelColor }}>{label}</span>
      <span className="text-right" style={{ color: valueColor }}>{value}</span>
    </div>
  );

  const occupancy = occupancyQuery.data;
  const stay = occupancy?.current_stay;

  /** Latest reading per parameter, per device. `device_stat` is time-ordered. */
  const latestByDevice = useMemo(() => {
    const map = new Map<string, { label: string; value: string }[]>();
    const seen = new Set<string>();
    for (const stat of statsQuery.data?.items ?? []) {
      const key = `${stat.device_id}:${stat.device_param_id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const rows = map.get(stat.device_id) ?? [];
      const unit = stat.unit ? ` ${stat.unit}` : "";
      rows.push({
        label: stat.param_name ?? `Parameter ${stat.device_param_id}`,
        value: `: ${stat.device_param_value ?? "-"}${unit}`,
      });
      map.set(stat.device_id, rows);
    }
    return map;
  }, [statsQuery.data]);

  const devices = devicesQuery.data?.items ?? [];

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Room Details Card */}
      <div
        className="rounded-lg p-6 transition-all duration-250 ease hover:-translate-y-0.5"
        style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
      >
        <h3 style={{ color: titleColor }} className="font-medium mb-6">Room Details</h3>

        <DataState isLoading={occupancyQuery.isLoading} error={occupancyQuery.error}>
          <div className="grid lg:grid-cols-2 gap-8">
            {/* Occupancy Details */}
            <div>
              <h4 style={{ color: subTitleColor }} className="text-center mb-4 font-medium">Occupancy Details</h4>
              <div className="space-y-3">
                {[
                  { label: "Occupancy No", value: occupancy?.room_name ?? roomNumber ?? "-" },
                  {
                    label: "Occupancy Type",
                    value:
                      occupancy?.package_name ??
                      occupancy?.amenity_type_name ??
                      roomType ??
                      "-",
                  },
                  { label: "Status", value: occupancy?.status_name ?? "-" },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex justify-between py-2"
                    style={{ borderBottom: `1px solid ${rowBorder}` }}
                  >
                    <span style={{ color: labelColor }}>{label}</span>
                    <span style={{ color: valueColor }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Booking Details -- from the room's current stay, when there is one.
                "Booking Date" has no source: the backend's current-stay
                projection carries no booking timestamp, so it stays "-". */}
            <div>
              <h4 style={{ color: subTitleColor }} className="text-center mb-4 font-medium">Booking Details</h4>
              <div className="space-y-3">
                {[
                  { label: "Guest Name", value: stay?.booker?.name ?? "-" },
                  { label: "Stay Reference", value: stay?.internal_stay_ref_number ?? "-" },
                  { label: "Additional Guest", value: stay ? String(Math.max(stay.no_of_guests - 1, 0)) : "-" },
                  { label: "Actual Check In", value: formatDateTime(stay?.actual_checkin_time) },
                  { label: "Expected Check Out", value: formatDateTime(stay?.expected_checkout_time) },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex justify-between py-2"
                    style={{ borderBottom: `1px solid ${rowBorder}` }}
                  >
                    <span style={{ color: labelColor }}>{label}</span>
                    <span style={{ color: valueColor }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </DataState>
      </div>

      {/* Device Details */}
      <div>
        <h3 style={{ color: titleColor }} className="font-medium mb-4">Device Details</h3>
        <DataState
          isLoading={devicesQuery.isLoading || statsQuery.isLoading}
          error={devicesQuery.error ?? statsQuery.error}
          isEmpty={devices.length === 0}
          emptyTitle="No devices installed in this room"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
            {devices.map((device) => {
              const readings = latestByDevice.get(device.id) ?? [];
              return (
                <DevCard key={device.id}>
                  <DevHeader
                    title={`${device.device_type_name ?? "Device"} - ${device.device_name ?? device.device_uid ?? ""}`}
                  />
                  <div className="p-4 space-y-2 text-sm flex-1">
                    <Row label="Health" value={`: ${device.health_status ?? "-"}`} />
                    {readings.length === 0 ? (
                      <p className="pt-2 text-xs" style={{ color: labelColor }}>
                        No readings recorded for this device.
                      </p>
                    ) : (
                      readings.map((reading) => (
                        <Row key={reading.label} label={reading.label} value={reading.value} />
                      ))
                    )}
                  </div>
                </DevCard>
              );
            })}
          </div>
        </DataState>
      </div>
    </div>
  );
};
